import os
import telebot
from flask import Flask, request

API_TOKEN = os.getenv("BOT_TOKEN")
bot = telebot.TeleBot(API_TOKEN)
server = Flask(__name__)

accounts = {
    "Netflix Premium": {"price": "150", "credentials": "Email: user1@mail.com\nPass: password123"},
    "Canva Pro": {"price": "100", "credentials": "Email: user2@mail.com\nPass: canva456"},
    "ChatGPT Plus": {"price": "200", "credentials": "Email: user3@mail.com\nPass: gptplus789"}
}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    text = "Welcome to the Account Store!\nAvailable services:\n"
    for idx, item in enumerate(accounts.keys(), start=1):
        text += f"{idx}. {item} - ₹{accounts[item]['price']}\n"
    text += "\nSend the name of the service you want to buy."
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda message: message.text in accounts)
def handle_purchase(message):
    item = message.text
    price = accounts[item]['price']
    bot.send_message(
        message.chat.id,
        f"To buy {item}, pay ₹{price} to this UPI ID: `yourupi@upi`\nSend 'PAID' after payment.",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda message: message.text.lower() == 'paid')
def confirm_payment(message):
    item = list(accounts.keys())[0]
    creds = accounts[item]['credentials']
    bot.send_message(message.chat.id, f"Payment received!\nHere are your account details:\n\n{creds}")

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
