from aiogram import Bot, Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
from dotenv import load_dotenv
from keep_alive import keep_alive
import os
from database import (
    create_tables, add_user, get_users_count,
    add_code, remove_code, get_all_codes, code_exists,
    add_admin, is_admin, get_admins, get_codes_count
)

load_dotenv()
keep_alive()
create_tables()

add_admin(6486825926)  # <-- o‘zingizning ID'ingizni yozing

API_TOKEN = os.getenv("API_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class AdminStates(StatesGroup):
    waiting_for_code = State()
    waiting_for_remove = State()
    waiting_for_admin_id = State()

async def is_user_subscribed(user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except:
        return False

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    add_user(message.from_user.id)

    if await is_user_subscribed(message.from_user.id):
        buttons = [[KeyboardButton("📢 Reklama"), KeyboardButton("💼 Homiylik")]]
        if await is_admin(message.from_user.id):  # await qo'shildi
            buttons.append([KeyboardButton("🛠 Admin panel")])
        markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
        await message.answer("✅ Obuna bor. Kodni yuboring:", reply_markup=markup)
    else:
        markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton("Kanal", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}")
        ).add(
            InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub")
        )
        await message.answer("❗ Iltimos, kanalga obuna bo‘ling:", reply_markup=markup)

@dp.message_handler(commands=["myid"])
async def get_my_id(message: types.Message):
    status = "Admin" if await is_admin(message.from_user.id) else "Oddiy foydalanuvchi"
    await message.answer(f"🆔 ID: `{message.from_user.id}`\n👤 Holat: {status}", parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == "check_sub")
async def check_subscription(callback_query: types.CallbackQuery):
    if await is_user_subscribed(callback_query.from_user.id):
        await callback_query.message.edit_text("\u2705 Obuna tekshirildi. Kod yuboring.")
    else:
        await callback_query.answer("\u2757 Hali ham obuna emassiz!", show_alert=True)

@dp.message_handler(lambda message: message.text == "📢 Reklama")
async def reklama_handler(message: types.Message):
    await message.answer("📢 Reklama bo‘limi. Reklama uchun @DiyorbekPTMA ga murojat qiling.")

@dp.message_handler(lambda message: message.text == "💼 Homiylik")
async def homiylik_handler(message: types.Message):
    await message.answer("💼 Homiylik bo‘limi. Homiylik uchun karta: ''8800904257677885''")

@dp.message_handler(lambda m: m.text == "🛠 Admin panel")
async def admin_handler(message: types.Message):
    if await is_user_subscribed(message.from_user.id) and await is_admin(message.from_user.id):
        markup = ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            KeyboardButton("➕ Kod qo‘shish"), KeyboardButton("📄 Kodlar ro‘yxati")
        )
        markup.add(
            KeyboardButton("❌ Kodni o‘chirish"), KeyboardButton("📊 Statistika")
        )
        markup.add(
            KeyboardButton("👤 Admin qo‘shish"), KeyboardButton("🔙 Orqaga")
        )
        await message.answer("👮‍♂️ Admin paneliga xush kelibsiz!", reply_markup=markup)
    else:
        await message.answer("⛔ Siz admin emassiz yoki kanalga obuna bo'lmagansiz!")

@dp.message_handler(lambda m: m.text == "🔙 Orqaga")
async def back_to_menu(message: types.Message):
    buttons = [[KeyboardButton("📢 Reklama"), KeyboardButton("💼 Homiylik")]]
    if await is_admin(message.from_user.id):  # await qo'shildi
        buttons.append([KeyboardButton("🛠 Admin panel")])
    markup = ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("🏠 Asosiy menyuga qaytdingiz.", reply_markup=markup)

@dp.message_handler(lambda m: m.text == "➕ Kod qo‘shish")
async def start_add_code(message: types.Message):
    await message.answer("➕ Yangi kod va post ID ni yuboring. Masalan: 47 1000")
    await AdminStates.waiting_for_code.set()

@dp.message_handler(state=AdminStates.waiting_for_code)
async def add_code_handler(message: types.Message, state: FSMContext):
    parts = message.text.strip().split()
    if len(parts) != 2 or not all(p.isdigit() for p in parts):
        await message.answer("❌ Noto‘g‘ri format! Masalan: 47 1000")
        return
    code, msg_id = parts
    add_code(code, int(msg_id))
    await message.answer(f"✅ Kod qo‘shildi: {code} → {msg_id}")
    await state.finish()

@dp.message_handler(lambda m: m.text == "❌ Kodni o‘chirish")
async def start_remove_code(message: types.Message):
    await message.answer("🗑 O‘chirmoqchi bo‘lgan kodni yuboring:")
    await AdminStates.waiting_for_remove.set()

@dp.message_handler(state=AdminStates.waiting_for_remove)
async def remove_code_handler(message: types.Message, state: FSMContext):
    code = message.text.strip()
    if code_exists(code):
        remove_code(code)
        await message.answer(f"✅ Kod o‘chirildi: {code}")
    else:
        await message.answer("❌ Bunday kod yo‘q.")
    await state.finish()

@dp.message_handler(lambda m: m.text == "📄 Kodlar ro‘yxati")
async def list_codes_handler(message: types.Message):
    codes = get_all_codes()
    if not codes:
        await message.answer("📜 Hozircha hech qanday kod yo‘q.")
    else:
        text = "📄 Kodlar ro‘yxati:\n"
        for code, msg_id in codes.items():
            text += f"🔑 {code} — ID: {msg_id}\n"
        await message.answer(text)

@dp.message_handler(lambda m: m.text == "📊 Statistika")
async def stat_handler(message: types.Message):
    try:
        chat = await bot.get_chat(CHANNEL_USERNAME)
        members = await bot.get_chat_members_count(chat.id)
        users = get_users_count()
        codes = get_codes_count()
        await message.answer(f"👥 Obunachilar: {members}\n📜 Kodlar soni: {codes} ta\n👤 Foydalanuvchilar: {users} ta")
    except Exception as e:
        await message.answer("⚠️ Statistika olishda xatolik!")

@dp.message_handler(lambda m: m.text == "👤 Admin qo‘shish")
async def start_add_admin(message: types.Message):
    await message.answer("🆕 Yangi adminning Telegram ID raqamini yuboring:")
    await AdminStates.waiting_for_admin_id.set()

@dp.message_handler(state=AdminStates.waiting_for_admin_id)
async def add_admin_handler(message: types.Message, state: FSMContext):
    user_id = message.text.strip()
    if user_id.isdigit():
        user_id = int(user_id)
        if not await is_admin(user_id):  # await qo'shildi
            add_admin(user_id)
            await message.answer(f"✅ Admin qo‘shildi: `{user_id}`")
        else:
            await message.answer("⚠️ Bu foydalanuvchi allaqachon admin.")
    else:
        await message.answer("❌ Noto‘g‘ri ID!")
    await state.finish()

@dp.message_handler(lambda msg: msg.text.strip().isdigit())
async def handle_code(message: types.Message):
    code = message.text.strip()
    if not await is_user_subscribed(message.from_user.id):
        await message.answer("❗ Koddan foydalanish uchun avval kanalga obuna bo‘ling.")
        return
    msg_id = code_exists(code)
    if msg_id:
        await bot.copy_message(
            chat_id=message.chat.id,
            from_chat_id=CHANNEL_USERNAME,
            message_id=msg_id,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("📥 Yuklab olish", url=f"https://t.me/{CHANNEL_USERNAME.strip('@')}/{msg_id}")
            )
        )
    else:
        await message.answer("❌ Bunday kod topilmadi. Iltimos, to‘g‘ri kod yuboring.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
