from os import getenv
from dotenv import load_dotenv
import logging
load_dotenv()

from google import genai
from google.genai import types
import typing
from functools import wraps
from flask import Flask, request, abort
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from get_weather import weather_tool, get_weather
from logger import setup_logging
from db import (init_db_pool, init_db_schema, check_if_user_exists, get_or_create_user, load_history_from_db,
                save_convo_batch_to_db)

DEFAULT_SYSTEM_PROMPT = ("You are an SMS-based assistant for campers, backpackers, and survivalists that are messaging "
                         "you from the backcountry. Your responses will be sent via SMS. Be extremely concise. Do not "
                         "use emojis, special symbols, or markdown formatting. Keep responses under 150 characters "
                         "whenever possible, but prioritize completeness of important information over multiple "
                         "back-and-forth interactions up to a 1500-character response.")
MODEL_VERSION = "gemini-3.5-flash"
AVAILABLE_TOOLS = [weather_tool]

# We use a passphrase to allow friends to text without manually maintaining an allowlist
SMS_PASSPHRASE = getenv("SMS_PASSPHRASE")

ERROR_REPLY_MODEL_DOWN = "TrailTalk encountered an error when trying to communicate with the LLM. Please try again later."
ERROR_REPLY_5XX = "TrailTalk encountered an internal error. Please consider reporting this on GitHub."

app = Flask(__name__)
setup_logging(app)
init_db_pool()
init_db_schema()
gemini_client = genai.Client(api_key=getenv("GEMINI_API_KEY"))


def validate_twilio_request(f):
    """
    Validates that an incoming request to our endpoint actually originated from Twilio.
    If the request is genuine, it proceeds with the function the wrapper is attached to.
    If not, it returns a 403.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        validator = RequestValidator(getenv('TWILIO_AUTH_TOKEN'))

        request_valid = validator.validate(
            request.url,
            request.form,
            request.headers.get('X-TWILIO-SIGNATURE', ''))

        if request_valid:
            return f(*args, **kwargs)
        else:
            return abort(403)
    return wrapper


@app.route("/wilderness_assistant", methods=['POST', 'GET'])
@validate_twilio_request
def reply_sms():
    """
    Determines if the incoming message is a user or is trying to register in good faith, and responds accordingly

    :return: A MessagingResponse object, which is empty if we don't want to respond
    """
    sender_phone_num = request.values.get('From')
    sender_message = request.values.get('Body', None)
    resp = MessagingResponse()

    user_exists = check_if_user_exists(sender_phone_num)

    if user_exists or sender_message.upper() == SMS_PASSPHRASE:
        user_obj = get_or_create_user(sender_phone_num)
        if not user_exists:
            response_text = getenv("NEW_USER_RESPONSE",
                                   "Welcome to TrailTalk! You are now registered. Reply to begin chatting.")
            logging.info(f"New user {user_obj['id']} created")
            resp.message(response_text)
            return str(resp)

        # For returning users, load the prior convo history and handle response from there
        prior_convo_history = load_history_from_db(user_obj['id'])
        response_text = handle_message_response(sender_message, user_obj['id'], prior_convo_history)
        resp.message(response_text)

    return str(resp) # if this is an empty response, it indicates our reception of the message without sending a reply


def ping_gemini(convo_history: list, tools_to_exclude: typing.List[types.Tool] | None = None):
    """
    Generate a response from Gemini, given the current state of the conversation history.

    :param convo_history: conversation history for the model to reference
    :param tools_to_exclude: Optional -- a list of tools to exclude from offering the model
    :return: Response from the model
    """
    tools_to_exclude = tools_to_exclude or []

    response = gemini_client.models.generate_content(
        model=MODEL_VERSION,
        contents=convo_history,
        config=types.GenerateContentConfig(
            system_instruction=getenv("LLM_SYSTEM_PROMPT", DEFAULT_SYSTEM_PROMPT),
            tools=list(set(AVAILABLE_TOOLS) - set(tools_to_exclude))
        )
    )
    return response


def record_tool_execution(model_request_content, tool_name: str, tool_result, prior_convo_history: list,
                          uncommitted_convo: list):
    """
    Append a Tool call request and subsequent result to the in-memory conversation history fed to Gemini, and the
    yet-uncommitted convo history (also in memory).

    :param model_request_content: the content of the response data from the model, asking to use a tool
    :param tool_name: name of the tool that was run
    :param tool_result: data from the tool execution
    :param prior_convo_history: prior conversation history that's being fed to the model; updated alongside DB convo history
    :param uncommitted_convo: user + tool Content that hasn't been committed to the DB yet
    """
    tool_result_content = types.Content(
        role="user",
        parts=[types.Part.from_function_response(name=tool_name, response=tool_result)],
    )
    prior_convo_history.append(model_request_content)
    prior_convo_history.append(tool_result_content)
    uncommitted_convo.append(model_request_content)
    uncommitted_convo.append(tool_result_content)


def handle_message_response(message: str, user_id: str, prior_convo_history: list):
    """
    Main entrypoint for responding to a text from a user. Orchestrate generating a response from the model and
    running any Tools as requested.

    :param message: The message from the user.
    :param user_id: The user's ID, for associating with conversation history.
    :param prior_convo_history: A user's conversation history. Empty if the user is new.
    :return: A string of the model's response
    """
    uncommitted_convo = []

    # Update in-memory conversation history with new message
    user_convo_obj = types.Content(role="user", parts=[types.Part.from_text(text=message)])
    prior_convo_history.append(user_convo_obj)
    uncommitted_convo.append(user_convo_obj)

    try:
        response = ping_gemini(prior_convo_history)
    except Exception as e:
        logging.error(f"Encountered error when attempting to ping Gemini: {e}")
        return ERROR_REPLY_MODEL_DOWN

    # Check if Gemini wants to do any function calls
    tool_call = response.candidates[0].content.parts[0].function_call
    if tool_call:
        if tool_call.name == "get_weather":
            weather_data = get_weather(**tool_call.args)
            record_tool_execution(response.candidates[0].content, tool_call.name, weather_data, prior_convo_history,
                                  uncommitted_convo)

            # Get the final response from the model now that the conversation history has all the data
            # Note we exclude the weather tool to stop a re-attempt to call it if an error is returned
            try:
                response = ping_gemini(prior_convo_history, tools_to_exclude=[weather_tool])
            except Exception as e:
                logging.error(f"Encountered error when attempting to ping Gemini after tool call: {e}")
                return ERROR_REPLY_MODEL_DOWN
            # Since we reassign response, execution flow continues through the function

        else:
            logging.error("Unrecognized tool call requested by Gemini")
            return ERROR_REPLY_5XX

    # Now that we have a response, return it and save it to the DB
    model_content = types.Content(
        role="model",
        parts=[types.Part.from_text(text=response.text)]
    )
    # Note we save the entire user -> tool (optional) -> model response flow all at once, as Gemini enforces strict
    # turn-taking and if any one stage failed it would bork the convo history
    uncommitted_convo.append(model_content)
    save_convo_batch_to_db(user_id, uncommitted_convo)
    return response.text


if __name__ == "__main__":
    # Run locally for testing
    # Real production deployment is handled by Gunicorn + Nginx
    #app.run(port=3000, debug=True)
    test_response = handle_message_response("What's the weather for 38.889484, -77.035278?", "harrison")
    logging.info(test_response)
