# TrailTalk
An SMS-based LLM that is intended to be texted via satellite when camping or otherwise off the grid.

We run a small Flask server that listens for texts on a Twilio number and then sends them to Gemini, all bundled into a Docker container for ease of deployment.

## How to run

## Code info

## TODO
- Connect to Twilio
- Set up sophisticated logger, logging to file
- Set up conversation history saving to PostgreSQL
- Set up additional tools (news fetcher, ?)
- Set up gunicorn
- Set up nginx (separate, private server config repo?)
  - Set up let's encrypt/certbot
- Add retry logic to tool calling and graceful error handling
- Publish image and set up docker-compose example in readme
  - Allow for customization of system prompt?
  - Set up CI/CD on GitHub to rebuild image
- Add support for locally running model
