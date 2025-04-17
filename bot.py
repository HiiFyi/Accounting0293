import os
import telebot
from flask import Flask, request
import json
from telebot import types
from otp_forwarder import set_latest_buyer, otp_client

API_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(API_TOKEN)
server = Flask(__name__)

ADMIN_IDS = [7348205141, 7686142055]
DATA_FILE = "accounts.json"

COUNTRIES = {
    "India": "🇮🇳",
    "USA": "🇺🇸",
    "UK": "🇬🇧",
    "Canada": "🇨🇦",
    "Australia": "🇦🇺",
    "Germany": "🇩🇪",
    "France": "🇫🇷",
    "Japan": "🇯🇵",
    "Brazil": "🇧🇷",
    "UAE": "🇦🇪"
}

user_service_selection = {}

def load_accounts():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_accounts(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

@bot.message_handler(commands=['start'])
def load_users():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_user_balance(user_id):
    users = load_users()
    return users.get(str(user_id), {}).get("balance", 0.00)

def set_user_balance(user_id, balance):
    users = load_users()
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {}
    users[user_id_str]["balance"] = balance
    save_users(users)

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📱 Ready Made Telegram Accounts", callback_data="ready_accounts"))
    markup.add(types.InlineKeyboardButton("🚚 Delivery Ready Accounts", callback_data="delivery_accounts"))
    markup.add(types.InlineKeyboardButton("🛠️ Support Team", url="https://t.me/yourusername"))
    markup.add(types.InlineKeyboardButton("💰 Recharge Your Balance", callback_data="recharge_balance"))
    markup.add(types.InlineKeyboardButton("✅ Successful Purchase", url="https://t.me/yourchannel"))
    markup.add(types.InlineKeyboardButton("🔑 API Key", callback_data="api_key"))
    markup.add(types.InlineKeyboardButton("👥 Your Referrals", callback_data="referrals"))

    bot.send_message(
        user_id,
        f"Welcome {message.from_user.first_name}!\n\nYour Balance: ${balance:.2f}",
        reply_markup=markup
    )
    accounts = load_accounts()
    text = "Welcome to the Account Store!\nAvailable services:\n"
    for idx, item in enumerate(accounts.keys(), start=1):
        text += f"{idx}. {item} - ₹{accounts[item]['price']}\n"
    text += "\nSend the name of the service you want to buy."
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text in load_accounts())
def handle_purchase(message):
    item = message.text
    accounts = load_accounts()
    if item not in accounts:
        bot.send_message(message.chat.id, "Service not available.")
        return

    user_service_selection[message.chat.id] = item  # store selected service

    markup = types.InlineKeyboardMarkup()
    for country, flag in COUNTRIES.items():
        markup.add(types.InlineKeyboardButton(f"{flag} {country}", callback_data=f"country_{country}"))

    bot.send_message(message.chat.id, "Select your country:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("country_"))
def handle_country_selection(call):
    country = call.data.replace("country_", "")
    service = user_service_selection.get(call.message.chat.id)
    if not service:
        bot.answer_callback_query(call.id, "Service not found. Please try again.")
        return

    accounts = load_accounts()
    price = accounts[service].get('country_prices', {}).get(country, accounts[service]['price'])

    # Set buyer for OTP
    set_latest_buyer(service, call.message.chat.id)

    bot.send_message(
        call.message.chat.id,
        f"You selected *{service}* for *{country}*.\nPay ₹{price} to this UPI ID: `yourupi@upi`\n\nAfter payment, send 'PAID {service}'",
        parse_mode='Markdown'
    )
@bot.callback_query_handler(func=lambda call: call.data == "ready_accounts")
def handle_ready_accounts(call):
    markup = types.InlineKeyboardMarkup()
    for country, flag in COUNTRIES.items():
        markup.add(types.InlineKeyboardButton(f"{flag} {country}", callback_data=f"country_{country}"))
    bot.edit_message_text("Choose a country:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "delivery_accounts")
def handle_delivery_accounts(call):
    bot.answer_callback_query(call.id, "You can sell your account to @robotusername", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "recharge_balance")
def handle_recharge_balance(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Razorpay", url="https://razorpay.com"))
    markup.add(types.InlineKeyboardButton("Cryptomus", url="https://cryptomus.com"))
    bot.edit_message_text("Select recharge method:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "api_key")
def handle_api_key(call):
    bot.answer_callback_query(call.id, "Contact support for API Key.", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "referrals")
def handle_referrals(call):
    referrals = 10  # Example: dynamic value laa sakte ho
    bot.send_message(call.message.chat.id, f"Tumne {referrals} logon ko refer kiya.\nReward: ${referrals * 0.01:.2f}")

@bot.message_handler(func=lambda message: message.text.lower().startswith('paid'))
def confirm_payment(message):
    parts = message.text.split(' ', 1)
    if len(parts) != 2:
        bot.send_message(message.chat.id, "Please use: PAID <Service Name>")
        return
    item = parts[1]
    accounts = load_accounts()
    if item in accounts:
        creds = accounts[item]['credentials']
        bot.send_message(message.chat.id, f"Payment received!\nHere are your account details:\n\n{creds}")
    else:
        bot.send_message(message.chat.id, "Service not found.")

@bot.message_handler(commands=['add'])
def add_account(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.replace('/add ', '').split('|')
        name = parts[0].strip()
        email = parts[1].split(':', 1)[1].strip()
        password = parts[2].split(':', 1)[1].strip()
        accounts = load_accounts()
        accounts[name] = {
            "price": "100",
            "credentials": f"Email: {email}\nPass: {password}",
            "country_prices": {}
        }
        save_accounts(accounts)
        bot.send_message(message.chat.id, f"Added: {name}")
    except:
        bot.send_message(message.chat.id, "Use format: /add Name | Email: xyz | Pass: abc")

@bot.message_handler(commands=['setprice'])
def set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.replace('/setprice ', '').split('|')
        name = parts[0].strip()
        country_price_info = parts[1].strip()
        country, new_price = country_price_info.split(':')
        country = country.strip()
        new_price = new_price.strip()

        accounts = load_accounts()
        if name in accounts:
            if 'country_prices' not in accounts[name]:
                accounts[name]['country_prices'] = {}
            accounts[name]['country_prices'][country] = new_price
            save_accounts(accounts)
            bot.send_message(message.chat.id, f"Price for {name} in {country} updated to ₹{new_price}.")
        else:
            bot.send_message(message.chat.id, "Service not found.")
    except:
        bot.send_message(message.chat.id, "Use format: /setprice Service Name | Country: NewPrice")

@bot.message_handler(commands=['list'])
def list_accounts(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    accounts = load_accounts()
    if not accounts:
        bot.send_message(message.chat.id, "No accounts found.")
        return
    text = "Accounts:\n"
    for item in accounts:
        text += f"- {item} (₹{accounts[item]['price']})\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['delete'])
def delete_account(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    name = message.text.replace('/delete ', '').strip()
    accounts = load_accounts()
    if name in accounts:
        del accounts[name]
        save_accounts(accounts)
        bot.send_message(message.chat.id, f"Deleted: {name}")
    else:
        bot.send_message(message.chat.id, "Account not found.")

@server.route(f'/{API_TOKEN}', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "OK", 200
@bot.message_handler(commands=['uploadsession'])
def ask_for_session(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    bot.send_message(message.chat.id, "Please send your `.session` file now.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if not message.document.file_name.endswith(".session"):
        bot.send_message(message.chat.id, "Please send a valid `.session` file.")
        return

    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    with open("main_account.session", "wb") as f:
        f.write(downloaded_file)

    bot.send_message(message.chat.id, "Session file uploaded successfully as `main_account.session`. Restart the bot if required.")
 #   bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
 #   return "OK", 200
@server.route('/')
def index():
    return "Bot is running!", 200

if __name__ == '__main__':
    # Start Pyrogram OTP forwarder in a separate thread
    import threading
    threading.Thread(target=otp_client.run).start()

    bot.remove_webhook()
    bot.set_webhook(url=f"{os.getenv('WEBHOOK_URL')}/{API_TOKEN}")
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
