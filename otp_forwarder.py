from pyrogram import Client, filters

API_ID = 123456  # <-- Apna API ID yaha daalo
API_HASH = "abc123xyz"  # <-- Apna API Hash yaha daalo
SESSION_NAME = "main_account"  # <-- Tumhara .session file ka naam (without .session)

# Service => user_id mapping
latest_buyer = {}

otp_client = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

@otp_client.on_message(filters.chat(777000))
async def otp_handler(client, message):
    for user_id in latest_buyer.values():
        from main import bot  # Import yahi pe karna to avoid circular import
        await bot.send_message(user_id, f"Your OTP:\n\n{message.text}")

def set_latest_buyer(service_name, user_id):
    latest_buyer[service_name] = user_id
