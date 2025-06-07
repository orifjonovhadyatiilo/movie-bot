import os
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
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
admin_ids = [5771519241, 8062273832]  # o'zingizni ID yozing

# ===== Global State =====
ADMIN_STATE = {}

# ===== Initialize bot =====
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# ===== Load Required Channels =====
def get_required_channels():
    if not os.path.exists(CHANNELS_FILE):
        with open(CHANNELS_FILE, "w"): pass
    with open(CHANNELS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

# ===== Save Channels =====
def save_channel(username):
    channels = set(get_required_channels())
    channels.add(username)
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(channels))

# ===== Remove Channels =====
def remove_channel(username):
    channels = set(get_required_channels())
    channels.discard(username)
    with open(CHANNELS_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(channels))

# ===== Admin Keyboard =====
def admin_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        KeyboardButton("📊 Statistika"),
        KeyboardButton("🎬 Kino qo‘shish"),
        KeyboardButton("🎞 Qism qo‘shish"),
        KeyboardButton("🗑 Kinoni o‘chirish"),
        KeyboardButton("➕ Kanal qo‘shish"),
        KeyboardButton("➖ Kanal o‘chirish")
    )
    return markup

# ===== Subscription Check =====
async def check_subscriptions(user_id):
    for channel in get_required_channels():
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ("left", "kicked"):
                return False
        except:
            continue
    return True

# ===== Save User =====
def save_user(user_id):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w"): pass
    with open(USERS_FILE, "r+") as f:
        users = set(f.read().splitlines())
        if str(user_id) not in users:
            f.write(f"{user_id}\n")

# ===== /start handler =====
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    if await check_subscriptions(message.from_user.id):
        save_user(message.from_user.id)
        text = f"👋 Assalomu alaykum {message.from_user.first_name}, botimizga xush kelibsiz.\n\n✍🏻 Kino kodini yuboring..."
        markup = admin_keyboard() if message.from_user.id in admin_ids else types.ReplyKeyboardRemove()
        await message.answer(text, reply_markup=markup)
    else:
        markup = InlineKeyboardMarkup()
        for ch in get_required_channels():
            markup.add(InlineKeyboardButton(f"➕ {ch}", url=f"https://t.me/{ch[1:]}"))
        markup.add(InlineKeyboardButton("✅ Tekshirish", callback_data="check_subs"))
        await message.answer("❌ Iltimos, quyidagi kanallarga obuna bo‘ling:", reply_markup=markup)

# ===== Callback subscription check =====
@dp.callback_query_handler(lambda c: c.data == "check_subs")
async def check_subs_callback(call: types.CallbackQuery):
    if await check_subscriptions(call.from_user.id):
        save_user(call.from_user.id)
        text = f"👋 Assalomu alaykum {call.from_user.first_name}, botimizga xush kelibsiz.\n\n✍🏻 Kino kodini yuboring..."
        markup = admin_keyboard() if call.from_user.id in admin_ids else types.ReplyKeyboardRemove()
        await call.message.edit_text(text)
        await call.message.answer(text, reply_markup=markup)
    else:
        await call.answer("❌ Hali ham barcha kanallarga obuna bo‘lmagansiz!", show_alert=True)

# ===== Admin kino va qism qo‘shish =====
@dp.message_handler(lambda message: message.text in ["🎬 Kino qo‘shish", "🎞 Qism qo‘shish"])
async def admin_step_1(message: types.Message):
    if message.from_user.id not in admin_ids:
        return
    ADMIN_STATE[message.from_user.id] = {"mode": "movie" if message.text == "🎬 Kino qo‘shish" else "part"}
    await message.answer("🎥 Iltimos, kinoni yuboring (video shaklida).")

@dp.message_handler(content_types=types.ContentType.VIDEO)
async def handle_admin_video(message: types.Message):
    if message.from_user.id not in admin_ids or message.from_user.id not in ADMIN_STATE:
        return await message.answer("❗ Avval tugmalardan birini bosing.")
    ADMIN_STATE[message.from_user.id]["file_id"] = message.video.file_id
    await message.answer("🔤 Endi kino kodini yuboring (masalan: abc123)")

@dp.message_handler(lambda message: message.from_user.id in ADMIN_STATE and "file_id" in ADMIN_STATE[message.from_user.id] and "code" not in ADMIN_STATE[message.from_user.id])
async def handle_admin_code(message: types.Message):
    ADMIN_STATE[message.from_user.id]["code"] = message.text.strip()
    if ADMIN_STATE[message.from_user.id]["mode"] == "part":
        await message.answer("📛 Endi qismini nomini yozing (masalan: 1-qism)")
    else:
        code = ADMIN_STATE[message.from_user.id]["code"]
        file_id = ADMIN_STATE[message.from_user.id]["file_id"]
        with open(os.path.join(MOVIES_DIR, f"{code}.txt"), "w", encoding="utf-8") as f:
            f.write(f"full|{file_id}\n")
        ADMIN_STATE.pop(message.from_user.id)
        await message.answer(f"✅ Kino muvaffaqiyatli qo‘shildi!\n🎬 Kod: {code}")

@dp.message_handler(lambda message: message.from_user.id in ADMIN_STATE and ADMIN_STATE[message.from_user.id].get("mode") == "part" and "code" in ADMIN_STATE[message.from_user.id] and "part" not in ADMIN_STATE[message.from_user.id])
async def handle_admin_part_name(message: types.Message):
    ADMIN_STATE[message.from_user.id]["part"] = message.text.strip()
    state = ADMIN_STATE.pop(message.from_user.id)
    path = os.path.join(MOVIES_DIR, f"{state['code']}.txt")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"{state['part']}|{state['file_id']}\n")
    await message.answer("✅ Qism muvaffaqiyatli qo‘shildi.")

# ===== Kino ko‘rish =====
@dp.message_handler(lambda message: message.text and not message.text.startswith("/") and message.from_user.id not in admin_ids)
async def handle_user_code(message: types.Message):
    code = message.text.strip()
    path = os.path.join(MOVIES_DIR, f"{code}.txt")
    if not os.path.exists(path):
        return await message.answer("❌ Kino kodini noto‘g‘ri yubordingiz!")

    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
        parts = [line.split("|")[0] for line in lines]
        files = {line.split("|")[0]: line.split("|")[1] for line in lines}

    if len(parts) == 1:
        await message.answer_chat_action("upload_video")
        await message.answer_video(files[parts[0]])
    else:
        markup = InlineKeyboardMarkup(row_width=2)
        for part in parts:
            markup.add(InlineKeyboardButton(part, callback_data=f"{code}:{part}"))
        await message.answer(f"🎬 {code}\nQaysi qismini ko‘rmoqchisiz?", reply_markup=markup)

@dp.callback_query_handler(lambda c: ":" in c.data)
async def send_movie_part(call: types.CallbackQuery):
    code, part = call.data.split(":")
    path = os.path.join(MOVIES_DIR, f"{code}.txt")
    if not os.path.exists(path):
        return await call.message.answer("❌ Qism topilmadi.")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            p, fid = line.split("|")
            if p == part:
                await call.message.answer_chat_action("upload_video")
                return await call.message.answer_video(fid)
    await call.message.answer("❌ Qism topilmadi.")

# ===== Statistika =====
@dp.message_handler(lambda message: message.text == "📊 Statistika")
async def stats(message: types.Message):
    if message.from_user.id not in admin_ids:
        return
    total_movies = len(os.listdir(MOVIES_DIR))
    total_parts = sum(len(open(os.path.join(MOVIES_DIR, f), encoding="utf-8").readlines()) for f in os.listdir(MOVIES_DIR))
    user_count = len(open(USERS_FILE).readlines()) if os.path.exists(USERS_FILE) else 0
    await message.answer(f"📊 Jami kinolar: {total_movies}\n🎞 Jami qismlar: {total_parts}\n👥 Foydalanuvchilar soni: {user_count}")

# ===== Kino o‘chirish =====
@dp.message_handler(lambda message: message.text == "🗑 Kinoni o‘chirish")
async def delete_movie_start(message: types.Message):
    if message.from_user.id not in admin_ids:
        return
    ADMIN_STATE[message.from_user.id] = {"mode": "delete"}
    await message.answer("❌ O‘chirish uchun kino kodini yuboring.")

@dp.message_handler(lambda message: message.from_user.id in ADMIN_STATE and ADMIN_STATE[message.from_user.id].get("mode") == "delete")
async def delete_movie_confirm(message: types.Message):
    code = message.text.strip()
    path = os.path.join(MOVIES_DIR, f"{code}.txt")
    if os.path.exists(path):
        os.remove(path)
        await message.answer(f"🗑 Kino '{code}' muvaffaqiyatli o‘chirildi.")
    else:
        await message.answer("❌ Bunday kodli kino topilmadi.")
    ADMIN_STATE.pop(message.from_user.id, None)

# ===== Kanal qo‘shish va o‘chirish =====
@dp.message_handler(lambda message: message.text == "➕ Kanal qo‘shish")
async def add_channel_start(message: types.Message):
    if message.from_user.id not in admin_ids:
        return
    ADMIN_STATE[message.from_user.id] = {"mode": "add_channel"}
    await message.answer("📢 Kanal username’ini yuboring (@siz)")

@dp.message_handler(lambda message: message.text == "➖ Kanal o‘chirish")
async def remove_channel_start(message: types.Message):
    if message.from_user.id not in admin_ids:
        return
    ADMIN_STATE[message.from_user.id] = {"mode": "remove_channel"}
    await message.answer("📛 O‘chirish uchun kanal username’ini yuboring (@siz)")

@dp.message_handler(lambda message: message.from_user.id in ADMIN_STATE and ADMIN_STATE[message.from_user.id]["mode"] in ["add_channel", "remove_channel"])
async def handle_channel_ops(message: types.Message):
    state = ADMIN_STATE.pop(message.from_user.id)
    username = message.text.strip()
    if not username.startswith("@"): username = f"@{username}"
    if state["mode"] == "add_channel":
        save_channel(username)
        await message.answer(f"✅ {username} kanal qo‘shildi.")
    else:
        remove_channel(username)
        await message.answer(f"➖ {username} kanal o‘chirildi.")

# ===== HTTP Server for Render =====
app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot is running!'

def run_http_server():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

# ===== Start polling and http =====
if __name__ == '__main__':
    threading.Thread(target=run_http_server).start()
    executor.start_polling(dp, skip_updates=True)
