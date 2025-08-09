import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv

# ==== CONFIG ====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMINS = list(map(int, os.getenv("ADMINS", "").split(",")))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# ==== FILE PATHS ====
MOVIES_FILE = "data/movies.json"
CHANNELS_FILE = "data/channels.json"

# ==== HELPERS ====
def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

movies_db = load_json(MOVIES_FILE)
channels_db = load_json(CHANNELS_FILE)

def save_movies():
    save_json(MOVIES_FILE, movies_db)

def save_channels():
    save_json(CHANNELS_FILE, channels_db)

# ==== ADMIN PANEL ====
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    if message.from_user.id in ADMINS:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🎬 Kino qo‘shish", callback_data="add_movie"))
        kb.add(InlineKeyboardButton("➕ Qism qo‘shish", callback_data="add_part"))
        kb.add(InlineKeyboardButton("🗑 Kino o‘chirish", callback_data="delete_movie"))
        kb.add(InlineKeyboardButton("📢 Kanal qo‘shish", callback_data="add_channel"))
        kb.add(InlineKeyboardButton("❌ Kanal o‘chirish", callback_data="delete_channel"))
        await message.answer("Admin panel:", reply_markup=kb)
    else:
        # Majburiy obuna tekshirish
        for ch in channels_db.get("channels", []):
            try:
                user = await bot.get_chat_member(ch, message.from_user.id)
                if user.status not in ["member", "administrator", "creator"]:
                    await message.answer("Botdan foydalanish uchun quyidagi kanallarga obuna bo‘ling:")
                    for ch in channels_db.get("channels", []):
                        await message.answer(f"https://t.me/{ch.replace('@','')}")
                    return
            except:
                pass
        await message.answer("Salom! Kino kodini yuboring.")

# ==== ADMIN ACTIONS ====
@dp.callback_query_handler(lambda c: c.data == "add_movie")
async def admin_add_movie(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return
    await callback.message.answer("🎥 Kinoni video formatda yuboring.")
    dp.register_message_handler(process_movie_video, content_types=["video"], state=None)

async def process_movie_video(message: types.Message):
    video = message.video.file_id
    await message.answer("Kodni kiriting:")
    dp.register_message_handler(lambda msg: save_movie(msg, video), content_types=["text"], state=None)

async def save_movie(message: types.Message, video_id):
    code = message.text.strip()
    if code in movies_db:
        await message.answer("❌ Bu kod band.")
    else:
        movies_db[code] = {"parts": [video_id]}
        save_movies()
        await message.answer("✅ Muvoffaqiyatli saqlandi.")

@dp.callback_query_handler(lambda c: c.data == "add_part")
async def admin_add_part(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return
    await callback.message.answer("Kodini yuboring:")
    dp.register_message_handler(process_part_code, content_types=["text"], state=None)

async def process_part_code(message: types.Message):
    code = message.text.strip()
    if code not in movies_db:
        await message.answer("❌ Kod topilmadi.")
        return
    await message.answer("Qism videosini yuboring.")
    dp.register_message_handler(lambda msg: save_part(msg, code), content_types=["video"], state=None)

async def save_part(message: types.Message, code):
    video = message.video.file_id
    movies_db[code]["parts"].append(video)
    save_movies()
    await message.answer("✅ Qism qo‘shildi.")

@dp.callback_query_handler(lambda c: c.data == "delete_movie")
async def admin_delete_movie(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return
    await callback.message.answer("Kodini yuboring:")
    dp.register_message_handler(process_delete_code, content_types=["text"], state=None)

async def process_delete_code(message: types.Message):
    code = message.text.strip()
    if code not in movies_db:
        await message.answer("❌ Kod topilmadi.")
        return
    del movies_db[code]
    save_movies()
    await message.answer("✅ O‘chirildi.")

@dp.callback_query_handler(lambda c: c.data == "add_channel")
async def admin_add_channel(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return
    await callback.message.answer("Kanal username (@ bilan) yuboring:")
    dp.register_message_handler(process_add_channel, content_types=["text"], state=None)

async def process_add_channel(message: types.Message):
    ch = message.text.strip()
    channels = channels_db.get("channels", [])
    if ch not in channels:
        channels.append(ch)
        channels_db["channels"] = channels
        save_channels()
        await message.answer("✅ Kanal qo‘shildi.")
    else:
        await message.answer("❌ Bu kanal allaqachon qo‘shilgan.")

@dp.callback_query_handler(lambda c: c.data == "delete_channel")
async def admin_delete_channel(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMINS:
        return
    await callback.message.answer("O‘chirish uchun kanal username yuboring:")
    dp.register_message_handler(process_delete_channel, content_types=["text"], state=None)

async def process_delete_channel(message: types.Message):
    ch = message.text.strip()
    channels = channels_db.get("channels", [])
    if ch in channels:
        channels.remove(ch)
        channels_db["channels"] = channels
        save_channels()
        await message.answer("✅ O‘chirildi.")
    else:
        await message.answer("❌ Kanal topilmadi.")

# ==== USER REQUEST ====
@dp.message_handler(content_types=["text"])
async def get_movie(message: types.Message):
    code = message.text.strip()
    if code not in movies_db:
        await message.answer("❌ Kod topilmadi.")
        return
    parts = movies_db[code]["parts"]
    if len(parts) == 1:
        await message.answer_video(parts[0])
    else:
        kb = InlineKeyboardMarkup()
        for idx, part in enumerate(parts, start=1):
            kb.add(InlineKeyboardButton(f"{idx}-qism", callback_data=f"sendpart:{code}:{idx}"))
        await message.answer("Qaysi qismini yuboray?", reply_markup=kb)

@dp.callback_query_handler(lambda c: c.data.startswith("sendpart:"))
async def send_part(callback: types.CallbackQuery):
    _, code, idx = callback.data.split(":")
    idx = int(idx)
    await callback.message.answer_video(movies_db[code]["parts"][idx - 1])

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    executor.start_polling(dp, skip_updates=True)
