import os
import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

# ===== Load environment =====
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

# ===== File Paths =====
MOVIES_DIR = "movies_data"
USERS_FILE = "users.txt"
CHANNELS_FILE = "channels.txt"
os.makedirs(MOVIES_DIR, exist_ok=True)

# ===== Admin ID List =====
admin_ids = [5771519241, 8062273832]

# ===== Global State =====
ADMIN_STATE = {}

# ===== Initialize bot and dispatcher =====
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ===== Load Required Channels =====
def get_required_channels():
    if not os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "w"): pass
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

def save_channel(username):
    channels = set(get_required_channels())
    channels.add(username)
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(channels))

def remove_channel(username):
    channels = set(get_required_channels())
    channels.discard(username)
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(channels))

def admin_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("\ud83d\udcca Statistika"),
        KeyboardButton("\ud83c\udfac Kino qo\u2018shish"),
        KeyboardButton("\ud83c\udf9e Qism qo\u2018shish"),
        KeyboardButton("\ud83d\uddd1 Kinoni o\u2018chirish"),
        KeyboardButton("\u2795 Kanal qo\u2018shish"),
        KeyboardButton("\u2796 Kanal o\u2018chirish")
    )
    return markup

async def check_subscriptions(user_id):
    for channel in get_required_channels():
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ("left", "kicked"):
                return False
        except:
            continue
    return True

def save_user(user_id):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w"): pass
    with open(USERS_FILE, "r+") as f:
        users = set(f.read().splitlines())
        if str(user_id) not in users:
            f.write(f"{user_id}\n")

# All previous message and callback handlers go here (not removed for brevity)
# Use the same code as you already provided for message handlers

# ===== Flask Webhook Setup =====
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or f"https://your-deployment-url.onrender.com{WEBHOOK_PATH}"

flask_app = Flask(__name__)

@flask_app.route("/", methods=["GET"])
def index():
    return "Bot is running via Webhook!"

@flask_app.route(WEBHOOK_PATH, methods=["POST"])
async def webhook():
    update = types.Update(**request.json)
    await dp.process_update(update)
    return {"ok": True}

@flask_app.before_first_request
def init_webhook():
    loop = asyncio.get_event_loop()
    loop.create_task(bot.set_webhook(WEBHOOK_URL))

if __name__ == "__main__":
    flask_app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
