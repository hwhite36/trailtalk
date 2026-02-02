from google import genai
from functools import wraps
from os import getenv
from dotenv import load_dotenv
from flask import Flask, request, abort
from twilio.twiml.messaging_response import MessagingResponse
from twilio.request_validator import RequestValidator

load_dotenv()

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
    # Spin up a connection to the LLM
    gemini_client = genai.Client(api_key=getenv("GEMINI_API_KEY"))
    chat = gemini_client.chats.create(model=getenv("gemini-3-flash-preview"))
    # Customize it with a system prompt: explain context of wilderness, need to use limited characters for SMS

    # Check against in-memory dict of current convos?

    # Spin up new convo if no match

    # Save text of convo if that's needed?
    # If no response received for x days, delete the session and convo history for the number?
    return ""


if __name__ == "__main__":
    # Run locally for testing
    # Real production deployment is handled by Gunicorn + Nginx
    app.run(port=3000, debug=True)
