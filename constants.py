# LLM configuration
LLM_SYSTEM_PROMPT: str = ("You are an SMS-based assistant for campers, backpackers, and survivalists that are "
                              "messaging you from the backcountry. Your responses will be sent via SMS. Be extremely "
                              "concise. Do not use emojis, special symbols, or markdown formatting. Keep responses "
                              "under 150 characters whenever possible, but prioritize completeness of important "
                              "information over multiple back-and-forth interactions up to a 1500-character response.")
MODEL_VERSION: str = "gemini-3.5-flash"

# Non-generated text message responses
ERROR_REPLY_MODEL_DOWN: str = "TrailTalk encountered an error when trying to communicate with the LLM. Please try again later."
ERROR_REPLY_5XX: str = "TrailTalk encountered an internal error. Please consider reporting this on GitHub."
NEW_USER_RESPONSE: str = "TrailTalk: Welcome! You are now registered. Reply to begin chatting. Msg & data rates may apply. Reply STOP to cancel."
OPT_OUT_RESPONSE: str = "TrailTalk: You have successfully unsubscribed and will receive no further messages. Reply START to resubscribe."
RE_OPT_IN_RESPONSE: str = "TrailTalk: Welcome back! You are resubscribed. Reply to begin chatting. Msg & data rates may apply. Reply STOP to cancel."
