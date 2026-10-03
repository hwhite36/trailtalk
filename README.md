# TrailTalk
An SMS-based LLM assistant that is intended to be texted via satellite or SMS-only cell connection when camping or otherwise off the grid.

This repo contains just the code and instructions to deploy a self-hosted version of the service. **There is no publicly-accessible version of TrailTalk currently running.**

## Features
- Lightweight, SMS-optimized responses built with limited connection in mind
- Designed for self-hosting, modularity, and customizability, with overwritable model settings and SMS configurations via `.env` and a clearly documented, Dockerized deployment process
- Customizable SMS passphrase that allows for sharing with friends without manually maintaining an allowlist
- A suite of tools that the LLM can execute to assist you
  - Fetching weather reports (NOAA API) based on user-provided coordinates

## How to run
### Prerequisites
You'll need a server on which to deploy this app. Your server will need:
- a working Docker engine that can host both this and a PostgreSQL container
- the ability to host an API endpoint on the WAN (used by Twilio to contact your server when you get a text)
  - If you are self-hosting, this likely requires some combination of dynamic DNS and a reverse proxy with SSL configured. There are many guides for this online; if you are new to this I recommend looking into [Nginx Proxy Manager](https://nginxproxymanager.com/guide/).
  - **Make sure you follow best security practices whenever you expose your server to the WAN!**
- Enough compute resources and disk space to serve and store conversations for your desired number of users

You will also need API keys for Gemini and Twilio, and an active Twilio number that can send and receive text messages. For more on setting up an automated number, refer to [Messaging Campaigns](#messaging-campaigns) below.

### Deployment
1. Clone the git repo onto your server
2. Create and populate a `.env` file with your API keys and settings, using `.env.example` as a guide
3. Bring the TrailTalk container and database up by running `docker compose up -d`
4. Ensure functionality via log inspection with `docker compose logs`

### Running on development machines
1. Create a venv and install the Pipfile dependencies:
```commandline

```
2. 

## Messaging Campaigns


## Code design
We run a small Flask server that listens for texts on a Twilio number and then sends them to Gemini, alongside a suite of tools the model can execute.
The app is bundled into a scalable Docker container for ease of deployment. 
Conversation history is stored in a parallel PostgreSQL container.

## TODO
- Add types to all functions/ensure function docstrings are up to date
- Connect to Twilio
- Add retry logic to tool calling and graceful error handling
- Publish image and set up docker-compose example in readme
  - Allow for customization of system prompt?
  - Set up CI/CD on GitHub to rebuild image
- Set up additional tools (news fetcher, ?)
- Add support for locally running model / other models
