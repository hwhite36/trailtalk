from google import genai
from google.genai import types
from functools import wraps
from os import getenv
from dotenv import load_dotenv
from flask import Flask, request, abort
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

load_dotenv()

SYSTEM_PROMPT = ("You are an SMS-based assistant for campers, backpackers, and survivalists that are messaging you "
                 "from the backcountry. Your responses will be sent via SMS. Be extremely concise. Do not use emojis, "
                 "special symbols, or markdown formatting. Keep responses under 150 characters whenever possible, but "
                 "prioritize completeness of important information over multiple back-and-forth interactions "
                 "up to a 1500-character response.")

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
    sms_body = request.values.get('Body', None)
    sender_phone_num = request.values.get()

    resp = MessagingResponse()

    if sms_body:  # TODO flesh out conditions for responding
        response_text = handle_message_response(sms_body, sender_phone_num)
        resp.message(response_text)

    # if no conditions met, return an empty TwiXML response to Twilio, which indicates our reception of the message
    return str(resp)


def handle_message_response(message, sender_id):
    # Update conversation history with new message
    # TODO test for if input sanitation is needed e.g. passing in quotes
    if sender_id not in conversation_history:
        conversation_history[sender_id] = [
            {"role": "user", "parts": [{"text": message}]},
        ]
    else:
        conversation_history[sender_id].append({"role": "user", "parts": [{"text": message}]})

    # Spin up a connection to the LLM
    gemini_client = genai.Client(api_key=getenv("GEMINI_API_KEY"))

    # Build tools for internet-based activities
    # TODO flesh out
    weather_tool = types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="get_weather",
                description="Get the current weather for a specific location",
                parameters=types.Schema()
            )
        ]
    )

    response = gemini_client.models.generate_content(
        model="gemini-3-flash-preview",
        contents=conversation_history[sender_id],
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[weather_tool]
        )
    )

    # Check if Gemini wants to run a tool
    if response.candidates[0].content.parts[0].function_call:
        # TODO test saving tool usage in chat history
        pass

    # Save model's response to history
    conversation_history[sender_id].append(
        {"role": "model", "parts": [{"text": response.text}]}
    )

    # Prune history to only keep most recent 100 texts per user (but ensure the history starts with a user message)
    conversation_history[sender_id] = conversation_history[sender_id][-100:]
    while conversation_history[sender_id][0].get("role") == "model":
        conversation_history[sender_id].pop(0)

    return response.text


if __name__ == "__main__":
    # Run locally for testing
    # Real production deployment is handled by Gunicorn + Nginx
    #app.run(port=3000, debug=True)
    test_response = handle_message_response("How do I repair a busted link on my bike chain?", "harrison")
    print(test_response)
