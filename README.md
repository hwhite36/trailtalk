# TrailTalk
An SMS-based LLM assistant that is intended to be texted via satellite or spotty cell connection when camping or otherwise off the grid.

This repo contains only the code and instructions to deploy a self-hosted version of the service. **TrailTalk, as run by the repo maintainer, is only hosted as a closed beta.**

## Features
- Lightweight, SMS-optimized responses built with limited connection in mind
- Full general knowledge and conversational abilities of Gemini Flash 3.8
- Designed for self-hosting, modularity, and customizability, with overwritable model settings + SMS configurations via `.env` and a clearly documented, Dockerized deployment process
- Customizable SMS passphrase that allows for sharing with friends without manually maintaining an allowlist
- A suite of tools that the LLM can execute to assist you
  - Fetching weather reports (NOAA API) based on user-provided coordinates

## High-level design
- A Flask server listens for texts on a Twilio number
- When a text is received, it is inspected for keywords, correlated to a user, and sent to the Gemini API with available tools and prior conversation history
- The Gemini response is parsed and sent as a reply
- Conversation history and user status is saved in a PostgreSQL database
- Deployment is handled by Docker and gunicorn
- Logs are controlled by the Python `logging` module and routed to `stdout`, following standard Docker logging principles

## How to run
### Prerequisites
You will need API keys for Gemini and Twilio, and an active Twilio number that can send and receive text messages. For more on setting up a Twilio number, refer to [Messaging Campaigns (USA-specific)](#messaging-campaigns-usa-specific) below.

You'll also need a server on which to deploy this app. Your server will need:
- a working Docker engine that can host both this and a PostgreSQL container
- the ability to host an API endpoint on the WAN (used by Twilio to contact your server when you get a text)
  - If you are self-hosting, this likely requires some combination of dynamic DNS and a reverse proxy with SSL configured. There are many guides for this online; if you are new to this I recommend looking into [Nginx Proxy Manager](https://nginxproxymanager.com/guide/).
  - **Make sure you follow best security practices whenever you expose your server to the WAN!**
- Enough compute resources and disk space to serve and store conversations for your desired number of users

### Deployment
1. Clone the git repo onto your server
2. Create and populate a `.env` file with your API keys and settings, using `.env.example` as a guide
3. Bring the TrailTalk container and database up by running `docker compose up -d`
4. In the Twilio dashboard, set your number's webhook to point to your server's endpoint
5. Ensure functionality via log inspection with `docker compose logs`

### Running on development machines
1. Create a venv and install the Pipfile dependencies. You can do this many ways, such as with `pipenv`:
```bash
export PIPENV_VENV_IN_PROJECT=1 && pipenv install
```
2. Add your ngrok key to `.env`, and uncomment the ngrok container section in `docker-compose.yml`.
3. Bring the TrailTalk container and database up by running `docker compose up -d`
4. In the Twilio dashboard, set your number's webhook to point to your ngrok project URL
5. Bring down your containers via `docker compose down` and then back up, pulling in any modifications, via `docker compose up -d --build`
6. Destroy Docker volumes (i.e. delete the database) as needed by adding a `-v` flag when bringing down containers: `docker compose down -v`
7. Inspect logs for each container, e.g. `docker compose logs trailtalk`

## Messaging campaigns (USA-specific)
Unfortunately, getting a 10-digit US number to send automated Application To Person (A2P) SMS is rather bureaucratically cumbersome.
This is because of the high potential for abuse and spam.
Below is my understanding of the situation, provided purely for informational purposes. This does not constitute legal or business advice.

You must create a Business profile, submit a Brand, and create a messaging campaign with your SMS API provider (Twilio, in our case). 
The Brand represents your company, and the campaign represents how you'll be messaging customers.
Each of these steps is thoroughly vetted by regulators and requires review that can take several business days.

Also note that there are various fees associated with setting up a brand / messaging campaign (~$25), and these fees can stack if you mess up your submissions and have to have it re-reviewed. 
Check out these fees carefully and make sure you have all your ducks in a row before you submit.

### Setting up a Business profile
The first step is to establish a Business profile in Twilio. This is because an Individual profile only supports creating one Sole Proprietor brand. 
While a Sole Proprietor (SP) brand may seem like a good fit for this use case, SPs aren't allowed to send A2P messages (Twilio does not make this clear until the brand is already set up).

To set up a Business Profile, you'll need an EIN. You can get one for free (and with no tax implications) from the IRS with a simple online form. Even though our 
Brand type won't be a sole proprietorship within Twilio, you can still create your EIN as a sole proprietorship with the IRS, and set up your Twilio Business profile as a sole proprietorship.

Note that creating your Business profile will require approval, and this can sometimes get delayed if your EIN is fresh and hasn't appeared yet in the database that Twilio checks against. 
If this happens, you can request a manual review and submit the letter you received from the IRS with your EIN as proof.

### Setting up a Brand
Once you have your Twilio profile set up as a business profile attached to your EIN, you can create the Brand for your A2P campaign.
Your Brand type will likely want to be something like "Low Volume Mixed", assuming you're not sending thousands of texts per day. Note that different Brand types have different fees associated with them. 
This is where you DON'T want to choose "Sole Proprietorship", since that Brand type isn't allowed to send automated messages. Creating the Brand will also require approval and can take several days.

### Setting up a campaign
Once your Brand is created, you can set up a campaign associated with that Brand. Twilio guides you through the specific questions, but the important theme to keep in mind is that hobbyists are NOT allowed to send A2P messages for personal projects. 
If you intend to get a phone number to run something like TrailTalk, it's important to operate as a *closed beta* for a potential business venture -- not just some hobbyist tinkering. This should come across clearly in your campaign documentation.

The campaign form will ask questions about how actions such as unsubscribe requests are handled, and what the opt-in messages look like, to ensure you are complying with required standards. Take a look at the `reply_sms()` flow in `main.py` to
ensure you understand what standardized keywords are handled and how. This is especially important if you are overriding the default hardcoded messages.

Even though we operate as a closed beta, you will also need a public call to action to submit as proof of your campaign. This can be as simple as a publicly-accessible document that 
explains how an interested user could request to join your beta.

You will also need to draft up a publicly-accessible Terms and Conditions and Privacy Policy.

All the publicly accessible docs that I created and used to get my campaign approved can be found in `campaign-docs/`. **Do NOT reuse these documents verbatim for your campaign** -- they contain specificities that are particular to my campaign, 
and will likely need to be edited for your campaign to be approved.

Once your campaign is approved, your phone number is finally cleared to send and receive messages, and you can hook it up to your application in the Twilio dashboard!

## Potential future features
- Set up additional tools (news fetcher, ?)
- Add support for locally running model / other models
