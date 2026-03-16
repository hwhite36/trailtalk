from google import genai
from google.genai import types
import typing
from functools import wraps
from os import getenv
from dotenv import load_dotenv
from flask import Flask, request, abort
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator
from get_weather import weather_tool, get_weather

load_dotenv()

SYSTEM_PROMPT = ("You are an SMS-based assistant for campers, backpackers, and survivalists that are messaging you "
                 "from the backcountry. Your responses will be sent via SMS. Be extremely concise. Do not use emojis, "
                 "special symbols, or markdown formatting. Keep responses under 150 characters whenever possible, but "
                 "prioritize completeness of important information over multiple back-and-forth interactions "
                 "up to a 1500-character response.")

MODEL_VERSION = "gemini-3-flash-preview"
AVAILABLE_TOOLS = [weather_tool]

conversation_history = {}

app = Flask(__name__)


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
    TODO

    :return:
    """
    sms_body = request.values.get('Body', None)
    sender_phone_num = request.values.get()

    resp = MessagingResponse()

    if sms_body:  # TODO flesh out conditions for responding
        response_text = handle_message_response(sms_body, sender_phone_num)
        resp.message(response_text)

    # if no conditions met, return an empty TwiXML response to Twilio, which indicates our reception of the message
    return str(resp)


def ping_gemini(sender_id: str, tools_to_exclude: typing.List[types.Tool] | None = None):
    """
    Generate a response from Gemini, given the current state of the conversation history.

    :param sender_id: ID of the associated conversation history
    :param tools_to_exclude: Optional -- a list of tools to exclude from offering the model
    :return: Response from the model
    """
    tools_to_exclude = tools_to_exclude or []

    gemini_client = genai.Client(api_key=getenv("GEMINI_API_KEY"))
    response = gemini_client.models.generate_content(
        model=MODEL_VERSION,
        contents=conversation_history[sender_id],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=list(set(AVAILABLE_TOOLS) - set(tools_to_exclude))
        )
    )
    return response


def record_tool_execution(model_request_content, tool_name: str, tool_result, sender_id: str):
    """
    Append a Tool call request and subsequent result to the conversation.

    :param model_request_content: the content of the response data from the model, asking to use a tool
    :param tool_name: name of the tool that was run
    :param tool_result: data from the tool execution
    :param sender_id: ID of the user whose conversation the tool usage is associated with
    """
    conversation_history[sender_id].append(model_request_content)
    conversation_history[sender_id].append(
        types.Content(
            role="user",
            parts=[types.Part.from_function_response(name=tool_name, response=tool_result)],
        )
    )


def handle_message_response(message: str, sender_id: str):
    """
    Main entrypoint for responding to a text from a user. Orchestrate generating a response from the model and
    running any Tools as requested.

    :param message: The message from the user.
    :param sender_id: The user's ID, for associating with conversation history.
    :return: A string of the model's response
    """
    if sender_id not in conversation_history:
        conversation_history[sender_id] = []

    # Update conversation history with new message
    conversation_history[sender_id].append(
        types.Content(role="user", parts=[types.Part.from_text(text=message)])
    )

    try:
        response = ping_gemini(sender_id)
    except Exception as e:
        # TODO respond gracefully
        raise e

    # Check if Gemini wants to do any function calls
    tool_call = response.candidates[0].content.parts[0].function_call
    if tool_call:
        if tool_call.name == "get_weather":
            weather_data = get_weather(**tool_call.args)
            record_tool_execution(response.candidates[0].content, tool_call.name, weather_data, sender_id)

            # Get the final response from the model now that the conversation history has all the data
            # Note we exclude the weather tool to stop a re-attempt to call it if an error is returned
            try:
                response = ping_gemini(sender_id, tools_to_exclude=[weather_tool])
            except Exception as e:
                # TODO respond gracefully
                raise e
            # Since we reassign response, execution flow continues through the function

        else:
            print("Tool call not recognized")  # TODO log
            raise Exception("Tool call not recognized")

    record_model_response(response, sender_id)
    # TODO logger debug
    # print(conversation_history)
    return response.text


def record_model_response(response, sender_id: str):
    """
    Save the model's response to the conversation history, and prune the conversation history as it grows.

    :param response: The response body from pinging the Gemini API.
    :param sender_id: ID of the associated conversation.
    """
    conversation_history[sender_id].append(response.candidates[0].content)

    # Prune the history to keep context small
    conversation_history[sender_id] = conversation_history[sender_id][-100:]
    while conversation_history[sender_id]:
        first_msg = conversation_history[sender_id][0]
        # History must start with a user role AND not be a function response
        if first_msg.role == "model" or first_msg.parts[0].function_response:
            conversation_history[sender_id].pop(0)
        else:
            break


if __name__ == "__main__":
    # Run locally for testing
    # Real production deployment is handled by Gunicorn + Nginx
    #app.run(port=3000, debug=True)
    test_response = handle_message_response("What's the weather for 38.889484, -77.035278?", "harrison")
    print(test_response)
