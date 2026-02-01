from google import genai
from twilio.rest import Client
from os import getenv
from dotenv import load_dotenv
from flask import Flask, request, Response
from twilio.twiml.messaging_response import MessagingResponse

load_dotenv()

app = Flask(__name__)

@app.route("/wilderness_assistant", methods=['POST'])
def reply_sms():
    # Create a new Twilio MessagingResponse
    resp = MessagingResponse()
    resp.message("")

    # Return the TwiML (as XML) response
    return Response(str(resp), mimetype='text/xml')

def main():
    # Spin up a connection to the LLM
    client = genai.Client(api_key=getenv("GEMINI_API_KEY"))
    chat = client.chats.create(model=getenv("gemini-3-flash-preview"))
    # Customize it with a system prompt: explain context of wilderness, need to use limited characters for SMS

    # Connect to Twilio to send and receive texts
    client = Client(getenv("TWILIO_ACCOUNT_SID"), getenv("TWILIO_AUTH_TOKEN"))

    message = client.messages.create(
        body="",
        from_="",
        to="",
    )

    # Spin up a server to listen for texts
    app.run(port=3000)

    # Event loop
    # Text is received, creates new conversation session
    # AI gets prompted with system prompt + text message
    # Send response
    # Wait for response
    # If no response received for x days, delete the session and convo history for the number?


    response = chat.send_message("I have 2 dogs in my house.")
    print(response.text)

    response = chat.send_message("How many paws are in my house?")
    print(response.text)

    for message in chat.get_history():
        print(f'role - {message.role}',end=": ")
        print(message.parts[0].text)

if __name__ == "__main__":
    main()