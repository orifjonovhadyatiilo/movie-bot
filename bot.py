import json
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from dotenv import load_dotenv
from flask import Flask, request
import logging

# ------------------- CONFIG -------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split()))

# Fayl nomlari
MOVIES_FILE = "movies.json"
CHANNELS_FILE = "channels.json"

# ------------------- BOT & APP -------------------
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

app = Flask(__name__)

# ------------------- HELPERS -------------------
def load_movies():
    if not os.path.exists(MOVIES_FILE):
        with open(MOVIES_FILE, "w") as f:
            json.dump({}, f)
    with open(MOVIES_FILE, "r") as f:
        return json.load(f)

def save_movies(data):
    with open(MOVIES_FILE, "w") as f:
        json.dump(data, f, indent=4)

def load_channels():
    if not os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "w") as f:
            json.dump([], f)
    with open(CHANNELS_FILE, "r") as f:
        return json.load(f)

def save_channels(data):
    with open(CHANNELS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ------------------- FSM -------------------
class AddMovie(StatesGroup):
    waiting_for_video = State()
    waiting_for_code = State()

class AddEpisode(StatesGroup):
    waiting_for_code = State()
    waiting_for_video = State()

class DeleteMovie(StatesGroup):
    waiting_for_code = State()
    waiting_for_episode_choice = State()

class AddChannel(StatesGroup):
    waiting_for_channel_username = State()

class DeleteChannel(StatesGroup):
    waiting_for_channel_username = State()

# ------------------- ADMIN PANEL -------------------
def admin_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🎬 Kino qo‘shish", "🎞 Qism qo‘shish")
    kb.add("🗑 Kino o‘chirish")
    kb.add("➕ Kanal qo‘shish", "➖ Kanal o‘chirish")
    kb.add("📊 Statistika")
    return kb

# ------------------- START -------------------
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    user_id = message.from_user.id
    if user_id in ADMIN_IDS:
        await message.answer("Admin panelga xush kelibsiz!", reply_markup=admin_keyboard())
    else:
        await message.answer("Salom! Kino kodini yuboring va men sizga qismlarni chiqaraman.")

# ------------------- ADD MOVIE -------------------
@dp.message_handler(lambda m: m.text == "🎬 Kino qo‘shish", user_id=ADMIN_IDS)
async def add_movie_start(message: types.Message):
    await message.answer("Kinoni video formatida yuboring (doimiy video).")
    await AddMovie.waiting_for_video.set()

@dp.message_handler(content_types=types.ContentType.VIDEO, state=AddMovie.waiting_for_video, user_id=ADMIN_IDS)
async def add_movie_video(message: types.Message, state: FSMContext):
    await state.update_data(video_id=message.video.file_id)
    await message.answer("Kinoni qaysi kod bilan nomlamoqchisiz?")
    await AddMovie.waiting_for_code.set()

@dp.message_handler(state=AddMovie.waiting_for_code, user_id=ADMIN_IDS)
async def add_movie_code(message: types.Message, state: FSMContext):
    code = str(message.text).strip()
    data = await state.get_data()
    movies = load_movies()
    movies[code] = {"main": data['video_id'], "episodes": {}}
    save_movies(movies)
    await message.answer("✅ Kino muvaffaqiyatli saqlandi!", reply_markup=admin_keyboard())
    await state.finish()

# ------------------- ADD EPISODE -------------------
@dp.message_handler(lambda m: m.text == "🎞 Qism qo‘shish", user_id=ADMIN_IDS)
async def add_episode_start(message: types.Message):
    await message.answer("Qaysi kodga qism qo‘shmoqchisiz?")
    await AddEpisode.waiting_for_code.set()

@dp.message_handler(state=AddEpisode.waiting_for_code, user_id=ADMIN_IDS)
async def add_episode_code(message: types.Message, state: FSMContext):
    code = str(message.text).strip()
    movies = load_movies()
    if code not in movies:
        await message.answer("❌ Bunday kodli kino topilmadi.")
        await state.finish()
        return
    await state.update_data(code=code)
    await message.answer("Qism videosini yuboring (doimiy video).")
    await AddEpisode.waiting_for_video.set()

@dp.message_handler(content_types=types.ContentType.VIDEO, state=AddEpisode.waiting_for_video, user_id=ADMIN_IDS)
async def add_episode_video(message: types.Message, state: FSMContext):
    video_id = message.video.file_id
    data = await state.get_data()
    movies = load_movies()
    code = data['code']
    episode_number = len(movies[code]["episodes"]) + 1
    movies[code]["episodes"][str(episode_number)] = video_id
    save_movies(movies)
    await message.answer(f"✅ {code} kodli kino uchun {episode_number}-qism qo‘shildi.", reply_markup=admin_keyboard())
    await state.finish()

# ------------------- DELETE MOVIE -------------------
@dp.message_handler(lambda m: m.text == "🗑 Kino o‘chirish", user_id=ADMIN_IDS)
async def delete_movie_start(message: types.Message):
    await message.answer("Qaysi kodli kinoni o‘chirmoqchisiz?")
    await DeleteMovie.waiting_for_code.set()

@dp.message_handler(state=DeleteMovie.waiting_for_code, user_id=ADMIN_IDS)
async def delete_movie_code(message: types.Message, state: FSMContext):
    code = str(message.text).strip()
    movies = load_movies()
    if code not in movies:
        await message.answer("❌ Bunday kod topilmadi.")
        await state.finish()
        return

    if movies[code]["episodes"]:
        kb = InlineKeyboardMarkup()
        for ep in movies[code]["episodes"].keys():
            kb.add(InlineKeyboardButton(f"{ep}-qismni o‘chirish", callback_data=f"del_ep:{code}:{ep}"))
        kb.add(InlineKeyboardButton("📌 Hammasini o‘chirish", callback_data=f"del_all:{code}"))
        await message.answer("Qaysi qismini o‘chirasiz?", reply_markup=kb)
        await state.finish()
    else:
        del movies[code]
        save_movies(movies)
        await message.answer("✅ Kino o‘chirildi.", reply_markup=admin_keyboard())
        await state.finish()

@dp.callback_query_handler(lambda c: c.data.startswith("del_ep:") or c.data.startswith("del_all:"))
async def delete_episode_callback(callback_query: types.CallbackQuery):
    data = callback_query.data.split(":")
    movies = load_movies()
    if data[0] == "del_ep":
        code, ep = data[1], data[2]
        del movies[code]["episodes"][ep]
        save_movies(movies)
        await callback_query.message.answer(f"✅ {code} kodli kino {ep}-qismi o‘chirildi.")
    elif data[0] == "del_all":
        code = data[1]
        del movies[code]
        save_movies(movies)
        await callback_query.message.answer(f"✅ {code} kodli kino barcha qismlari bilan o‘chirildi.")

# ------------------- USER REQUEST MOVIE -------------------
@dp.message_handler()
async def get_movie_by_code(message: types.Message):
    code = str(message.text).strip()
    channels = load_channels()
    if channels:
        for ch in channels:
            member = await bot.get_chat_member(ch, message.from_user.id)
            if member.status == "left":
                kb = InlineKeyboardMarkup()
                for c in channels:
                    kb.add(InlineKeyboardButton(f"📢 {c}", url=f"https://t.me/{c.lstrip('@')}"))
                kb.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
                await message.answer("❗ Avval quyidagi kanallarga obuna bo‘ling:", reply_markup=kb)
                return
    movies = load_movies()
    if code not in movies:
        await message.answer("❌ Bunday kod topilmadi.")
        return
    if movies[code]["episodes"]:
        kb = InlineKeyboardMarkup()
        for ep, vid in movies[code]["episodes"].items():
            kb.add(InlineKeyboardButton(f"{ep}-qism", callback_data=f"get_ep:{code}:{ep}"))
        await message.answer("Qaysi qismini tomosha qilasiz?", reply_markup=kb)
    else:
        await message.answer_video(movies[code]["main"])

@dp.callback_query_handler(lambda c: c.data.startswith("get_ep:"))
async def send_episode(callback_query: types.CallbackQuery):
    _, code, ep = callback_query.data.split(":")
    movies = load_movies()
    video_id = movies[code]["episodes"][ep]
    await callback_query.message.answer_video(video_id)

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_subscription(callback_query: types.CallbackQuery):
    channels = load_channels()
    for ch in channels:
        member = await bot.get_chat_member(ch, callback_query.from_user.id)
        if member.status == "left":
            await callback_query.answer("❌ Hali ham barcha kanallarga obuna bo‘lmadingiz!", show_alert=True)
            return
    await callback_query.message.answer("✅ Obuna tasdiqlandi! Endi kino kodini yuboring.")

# ------------------- WEBHOOK -------------------
@app.route("/", methods=["POST"])
def webhook():
    update = types.Update(**request.json)
    dp.process_update(update)
    return "ok"

@app.route("/", methods=["GET"])
def home():
    return "Bot ishlayapti!"

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
