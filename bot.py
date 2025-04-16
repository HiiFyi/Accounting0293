import os
import telebot
from flask import Flask, request
import json

API_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(API_TOKEN)
server = Flask(__name__)

ADMIN_IDS = [7348205141, 7686142055]
DATA_FILE = "accounts.json"

def load_accounts():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_accounts(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    accounts = load_accounts()
    text = "Welcome to the Account Store!\nAvailable services:\n"
    for idx, item in enumerate(accounts.keys(), start=1):
        text += f"{idx}. {item} - ₹{accounts[item]['price']}\n"
    text += "\nSend the name of the service you want to buy."
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text in load_accounts())
def handle_purchase(message):
    accounts = load_accounts()
    item = message.text
    price = accounts[item]['price']
    bot.send_message(
        message.chat.id,
        f"To buy {item}, pay ₹{price} to this UPI ID: `yourupi@upi`\nSend 'PAID {item}' after payment.",
        parse_mode='Markdown'
    )

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
            "credentials": f"Email: {email}\nPass: {password}"
        }
        save_accounts(accounts)
        bot.send_message(message.chat.id, f"Added: {name}")
    except:
        bot.send_message(message.chat.id, "Use format: /add Name | Email: xyz | Pass: abc")

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

@bot.message_handler(commands=['setprice'])
def set_price(message):
@bot.message_handler(commands=['remove'])
def remove_account(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    name = message.text.replace('/remove ', '').strip()
    accounts = load_accounts()
    if name in accounts:
        del accounts[name]
        save_accounts(accounts)
        bot.send_message(message.chat.id, f"Removed: {name}")
    else:
        bot.send_message(message.chat.id, "Service not found.")
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.replace('/setprice ', '').split('|')
        name = parts[0].strip()
        new_price = parts[1].strip()
        accounts = load_accounts()
        if name in accounts:
            accounts[name]['price'] = new_price
            save_accounts(accounts)
            bot.send_message(message.chat.id, f"Price for {name} updated to ₹{new_price}.")
        else:
            bot.send_message(message.chat.id, "Service not found.")
    except:
        bot.send_message(message.chat.id, "Use format: /setprice Service Name | NewPrice")

@server.route(f'/{API_TOKEN}', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return "OK", 200

@server.route('/')
def index():
    return "Bot is running!", 200

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=f"{os.getenv('WEBHOOK_URL')}/{API_TOKEN}")
    server.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
