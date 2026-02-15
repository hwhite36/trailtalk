# Wilderness Assistant
An SMS-based LLM that is intended to be texted via satellite when camping or otherwise off the grid.

We run a small Flask server that listens for texts on a Twilio number and then sends them to Gemini, all bundled into a Docker container for ease of deployment.

## How to run

## Code info

## TODO
- Set up interaction with Gemini
- Figure out how to deal with convos statefully
- Set up weather interaction with NOAA API
- Set up logging to file
- Set up gunicorn
- Set up nginx (separate, private server config repo?)
  - Set up let's encrypt/certbot
- Publish image and set up docker-compose example in readme with postgres image
- Add support for locally running model