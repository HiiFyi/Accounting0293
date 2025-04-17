import os
import json
import threading
import telebot
from flask import Flask, request
from telebot import types
from otp_forwarder import set_latest_buyer, otp_client

# Load environment variables
API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = telebot.TeleBot(API_TOKEN)
server = Flask(__name__)

# Configurations
ADMIN_IDS = [7348205141, 7686142055]
ACCOUNT_FILE = "accounts.json"
USER_FILE = "users.json"

COUNTRIES = {
    "India": "🇮🇳", "USA": "🇺🇸", "UK": "🇬🇧", "Canada": "🇨🇦",
    "Australia": "🇦🇺", "Germany": "🇩🇪", "France": "🇫🇷",
    "Japan": "🇯🇵", "Brazil": "🇧🇷", "UAE": "🇦🇪"
}

user_service_selection = {}

# -------- JSON Helpers --------

def load_json_file(filename, default={}):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return default.copy()

def save_json_file(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)

def load_users():
    return load_json_file(USER_FILE)

def save_users(data):
    save_json_file(USER_FILE, data)

def load_accounts():
    return load_json_file(ACCOUNT_FILE)

def save_accounts(data):
    save_json_file(ACCOUNT_FILE, data)

# -------- User Handlers --------

def get_user_balance(user_id):
    return load_users().get(str(user_id), {}).get("balance", 0.00)

def set_user_balance(user_id, balance):
    users = load_users()
    uid = str(user_id)
    users.setdefault(uid, {})["balance"] = balance
    save_users(users)

def add_referral(user_id, referred_by):
    users = load_users()
    uid, ref_by = str(user_id), str(referred_by)

    if uid == ref_by:
        return

    if uid not in users:
        users[uid] = {"balance": 0.0, "referrals": 0}

    if "ref_by" not in users[uid]:
        users.setdefault(ref_by, {"balance": 0.0, "referrals": 0})
        users[uid]["ref_by"] = ref_by
        users[ref_by]["referrals"] += 1
        users[ref_by]["balance"] += 0.01
        save_users(users)

# -------- Bot Commands --------

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.chat.id
    args = message.text.split()

    if len(args) > 1:
        add_referral(user_id, args[1])

    if str(user_id) not in load_users():
        set_user_balance(user_id, 0.00)

    balance = get_user_balance(user_id)

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📱 Ready Made Telegram Accounts", callback_data="ready_accounts"),
        types.InlineKeyboardButton("🚚 Delivery Ready Accounts", callback_data="delivery_accounts"),
        types.InlineKeyboardButton("💰 Recharge Your Balance", callback_data="recharge_balance"),
        types.InlineKeyboardButton("🔑 API Key", callback_data="api_key"),
        types.InlineKeyboardButton("👥 Your Referrals", callback_data="referrals"),
        types.InlineKeyboardButton("🛠️ Support Team", url="https://t.me/yourusername"),
        types.InlineKeyboardButton("✅ Successful Purchase", url="https://t.me/yourchannel"),
    )

    bot.send_message(user_id, f"Welcome {message.from_user.first_name}!\n\nYour Balance: ${balance:.2f}", reply_markup=markup)

@bot.message_handler(commands=['uploadsession'])
def ask_for_session(message):
    if message.from_user.id in ADMIN_IDS:
        bot.send_message(message.chat.id, "Please send your `.session` file now.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    if not message.document.file_name.lower().endswith(".session"):
        return bot.send_message(message.chat.id, "Send a valid `.session` file.")

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)

        with open("main_account.session", "wb") as f:
            f.write(downloaded)

        bot.send_message(message.chat.id, "Session file saved as `main_account.session`.")
    except Exception as e:
        bot.send_message(message.chat.id, f"Error: {e}")

# -------- Admin Commands --------

@bot.message_handler(commands=['add'])
def add_account(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        parts = message.text.replace('/add ', '').split('|')
        name = parts[0].strip()
        email = parts[1].split(':')[1].strip()
        password = parts[2].split(':')[1].strip()

        accounts = load_accounts()
        accounts[name] = {
            "price": "100",
            "credentials": f"Email: {email}\nPass: {password}",
            "country_prices": {}
        }
        save_accounts(accounts)
        bot.send_message(message.chat.id, f"Added: {name}")
    except Exception as e:
        bot.send_message(message.chat.id, f"Use format: /add Name | Email: xyz | Pass: abc\nError: {e}")

@bot.message_handler(commands=['setprice'])
def set_price(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        name, country_info = message.text.replace('/setprice ', '').split('|')
        country, price = country_info.split(':')
        accounts = load_accounts()
        name = name.strip()
        country = country.strip()
        price = price.strip()

        if name in accounts:
            accounts[name].setdefault("country_prices", {})[country] = price
            save_accounts(accounts)
            bot.send_message(message.chat.id, f"Set price of {name} in {country} to ₹{price}.")
        else:
            bot.send_message(message.chat.id, "Service not found.")
    except:
        bot.send_message(message.chat.id, "Use format: /setprice Name | Country: Price")

@bot.message_handler(commands=['list'])
def list_accounts(message):
    if message.from_user.id not in ADMIN_IDS:
        return

    accounts = load_accounts()
    if not accounts:
        return bot.send_message(message.chat.id, "No accounts available.")

    msg = "Accounts:\n" + "\n".join([f"- {name} (₹{data['price']})" for name, data in accounts.items()])
    bot.send_message(message.chat.id, msg)

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

# -------- Purchase Flow --------

@bot.message_handler(func=lambda message: message.text in load_accounts())
def handle_purchase(message):
    item = message.text
    user_service_selection[message.chat.id] = item
    markup = types.InlineKeyboardMarkup()
    for country, flag in COUNTRIES.items():
        markup.add(types.InlineKeyboardButton(f"{flag} {country}", callback_data=f"country_{country}"))
    bot.send_message(message.chat.id, "Select your country:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("country_"))
def handle_country_selection(call):
    country = call.data.replace("country_", "")
    service = user_service_selection.get(call.message.chat.id)
    if not service:
        return bot.answer_callback_query(call.id, "Try again.")
    accounts = load_accounts()
    price = accounts[service].get('country_prices', {}).get(country, accounts[service]['price'])
    set_latest_buyer(service, call.message.chat.id)
    bot.send_message(
        call.message.chat.id,
        f"You selected *{service}* for *{country}*.\nPay ₹{price} to: `yourupi@upi`\n\nSend 'PAID {service}' after payment.",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text.lower().startswith('paid'))
def confirm_payment(message):
    try:
        _, item = message.text.split(' ', 1)
        accounts = load_accounts()
        if item in accounts:
            creds = accounts[item]['credentials']
            bot.send_message(message.chat.id, f"Payment confirmed!\n\n{creds}")
        else:
            bot.send_message(message.chat.id, "Service not found.")
    except:
        bot.send_message(message.chat.id, "Use: PAID <Service Name>")

# -------- Callback Buttons --------

@bot.callback_query_handler(func=lambda call: call.data == "referrals")
def handle_referrals(call):
    users = load_users()
    user = users.get(str(call.from_user.id), {})
    count = user.get("referrals", 0)
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, f"You referred {count} users.\nEarned: ${count * 0.01:.2f}")

@bot.callback_query_handler(func=lambda call: call.data == "recharge_balance")
def handle_recharge_balance(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Razorpay", url="https://razorpay.com"))
    markup.add(types.InlineKeyboardButton("Cryptomus", url="https://cryptomus.com"))
    bot.edit_message_text("Choose recharge method:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "ready_accounts")
def handle_ready_accounts(call):
    markup = types.InlineKeyboardMarkup()
    for country, flag in COUNTRIES.items():
        markup.add(types.InlineKeyboardButton(f"{flag} {country}", callback_data=f"country_{country}"))
    bot.edit_message_text("Choose a country:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "delivery_accounts")
def handle_delivery_accounts(call):
    bot.answer_callback_query(call.id, "Sell your account to @robotusername", show_alert=True)

@bot.callback_query_handler(func=lambda call: call.data == "api_key")
def handle_api_key(call):
    bot.answer_callback_query(call.id, "Contact support to get your API Key.", show_alert=True)

# -------- Webhook + Server --------

@server.route(f"/{API_TOKEN}", methods=["POST"])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "OK", 200

@server.route('/')
def index():
    return "Bot is running!", 200

if __name__ == "__main__":
    threading.Thread(target=otp_client.run).start()
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/{API_TOKEN}")
    server.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
