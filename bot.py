import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.utils.executor import start_webhook
from dotenv import load_dotenv
from flask import Flask, request
from threading import Thread

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g., https://yourapp.onrender.com/webhook
WEBHOOK_PATH = f"/webhook"
WEBAPP_HOST = "0.0.0.0"
WEBAPP_PORT = int(os.environ.get("PORT", 10000))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ================== Example /start handler ==================
@dp.message_handler(commands=["start"])
async def start_handler(message: types.Message):
    await message.answer("✅ Webhook orqali ishlayapman!")

# ================== Flask HTTP server (just for status check) ==================
flask_app = Flask(__name__)

@flask_app.route('/')
def index():
    return "Bot is working with webhook!"

@flask_app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        asyncio.run(dp.process_update(types.Update(**request.json)))
        return {"ok": True}
    return {"ok": False}, 403

# ================== Run everything ==================
async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)

async def on_shutdown(dp):
    await bot.delete_webhook()

def run_flask():
    flask_app.run(host=WEBAPP_HOST, port=WEBAPP_PORT)

if __name__ == '__main__':
    Thread(target=run_flask).start()
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
