import random
import string
import uuid
import sqlite3
from aiogram import Bot, types
from aiogram.dispatcher import Dispatcher
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import markdown
from cryptography.fernet import Fernet

API_TOKEN = 'YOUR_API_TOKEN'  # Замените на свой API токен
# Замените на айди разработчика
developer_chat_id = 'YOUR_ID'

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Подключение к базе данных SQLite
conn = sqlite3.connect('passwords.db')
cursor = conn.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS passwords (user_id INTEGER, password TEXT, guid TEXT)')
conn.commit()

class PasswordGenerate(StatesGroup):
    length = State()
    use_digits = State()
    use_letters = State()
    use_special_chars = State()
    generate_guid = State()

def generate_password(length, use_digits, use_letters, use_special_chars):
    characters = ""
    if use_digits:
        characters += string.digits
    if use_letters:
        characters += string.ascii_letters
    if use_special_chars:
        characters += string.punctuation

    return ''.join(random.choice(characters) for _ in range(length))

@dp.message_handler(Command('generate'))
async def generate_command(message: types.Message):
    await PasswordGenerate.length.set()
    await message.answer("Введите длину пароля:")

@dp.message_handler(state=PasswordGenerate.length)
async def get_password_length(message: types.Message, state: FSMContext):
    length = int(message.text)
    if 1 <= length <= 31:
        await state.update_data(length=length)
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add("Да", "Нет")
        await message.answer("Использовать цифры?", reply_markup=keyboard)
        await PasswordGenerate.next()
    else:
        await message.answer("Пожалуйста, введите корректную длину пароля (1-31):")

@dp.message_handler(lambda message: message.text.lower() in ("да", "нет"), state=PasswordGenerate.use_digits)
async def use_digits_query(message: types.Message, state: FSMContext):
    use_digits = message.text.lower() == "да"
    async with state.proxy() as data:
        data["use_digits"] = use_digits
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Да", "Нет")
    await message.answer("Использовать буквы?", reply_markup=keyboard)
    await PasswordGenerate.next()

@dp.message_handler(lambda message: message.text.lower() in ("да", "нет"), state=PasswordGenerate.use_letters)
async def use_letters_query(message: types.Message, state: FSMContext):
    use_letters = message.text.lower() == "да"
    async with state.proxy() as data:
        data["use_letters"] = use_letters
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Да", "Нет")
    await message.answer("Использовать специальные символы?", reply_markup=keyboard)
    await PasswordGenerate.next()

@dp.message_handler(lambda message: message.text.lower() in ("да", "нет"), state=PasswordGenerate.use_special_chars)
async def use_special_chars_query(message: types.Message, state: FSMContext):
    use_special_chars = message.text.lower() == "да"
    async with state.proxy() as data:
        data["use_special_chars"] = use_special_chars
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Да", "Нет")
    await message.answer("Генерировать GUID?", reply_markup=keyboard)
    await PasswordGenerate.next()

@dp.message_handler(lambda message: message.text.lower() in ("да", "нет"), state=PasswordGenerate.generate_guid)
async def generate_guid_query(message: types.Message, state: FSMContext):
    generate_guid = message.text.lower() == "да"
    async with state.proxy() as data:
        data["generate_guid"] = generate_guid
        length = data["length"]
        use_digits = data["use_digits"]
        use_letters = data["use_letters"]
        use_special_chars = data["use_special_chars"]
        generated_password = generate_password(length, use_digits, use_letters, use_special_chars)
        
        cursor.execute('INSERT INTO passwords (user_id, password, guid) VALUES (?, ?, ?)', (message.from_user.id, generated_password, None))
        if generate_guid:
            generated_guid = str(uuid.uuid4())
            cursor.execute('UPDATE passwords SET guid = ? WHERE user_id = ? AND password = ?', (generated_guid, message.from_user.id, generated_password))
        
        conn.commit()
        
        response = f"Сгенерированный пароль:\n{markdown.escape_md(generated_password)}"
        if generate_guid:
            response += f"\n\nСгенерированный GUID:\n{markdown.escape_md(generated_guid)}"
        
        await message.answer(
            response,
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        await state.finish()

@dp.message_handler(Command('saves'))
async def show_saved_passwords(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    cursor.execute('SELECT password, guid FROM passwords WHERE user_id = ?', (user_id,))
    saved_passwords = cursor.fetchall()

    cipher_key = await state.get_data('cipher_key')  # Получаем ключ шифрования из состояния FSM
    if cipher_key:
        fernet = Fernet(cipher_key.encode())

    if saved_passwords:
        response = "Сохраненные пароли:\n"
        for password, guid in saved_passwords:
            decrypted_password = fernet.decrypt(password.encode()).decode() if cipher_key else password
            decrypted_guid = fernet.decrypt(guid.encode()).decode() if guid and cipher_key else guid
            response += f"\nПароль: {markdown.escape_md(decrypted_password)}\nGUID: {markdown.escape_md(decrypted_guid) if decrypted_guid else 'Нет'}\n"
    else:
        response = "У вас пока нет сохраненных паролей."

    await message.answer(response, parse_mode=ParseMode.MARKDOWN)

class BugReport(StatesGroup):
    description = State()
    screenshot = State()

@dp.message_handler(Command('bug'))
async def report_bug(message: types.Message):
    await message.answer("Опишите подробно, как вызвать ошибку:")
    await BugReport.description.set()

@dp.message_handler(state=BugReport.description)
async def bug_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["bug_description"] = message.text
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Пропустить")
    await message.answer("Прикрепите фотографию, если есть, или нажмите кнопку \"Пропустить\":", reply_markup=keyboard)
    await BugReport.next()

@dp.message_handler(content_types=types.ContentTypes.PHOTO, state=BugReport.screenshot)
async def bug_screenshot(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["bug_screenshot"] = True
    await message.answer("Спасибо за информацию! Ваш отчет об ошибке был отправлен разработчику.")
    
    if data["bug_screenshot"]:
        photo = message.photo[-1].file_id  # Получаем ID фотографии
        await bot.send_photo(
            developer_chat_id,
            photo,
            caption=f"Новый отчет об ошибке:\n"
                    f"Айди пользователя: {message.from_user.id}\n"
                    f"Описание ошибки: {data['bug_description']}\n"
                    f"Фотография: Прикреплена"
        )
    else:
        await bot.send_message(
            developer_chat_id,
            f"Новый отчет об ошибке:\n"
            f"Айди пользователя: {message.from_user.id}\n"
            f"Описание ошибки: {data['bug_description']}\n"
            f"Фотография: Отсутствует"
        )
    
    await state.finish()

@dp.message_handler(lambda message: message.text.lower() == "пропустить", state=BugReport.screenshot)
async def skip_screenshot(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data["bug_screenshot"] = False
    await message.answer("Спасибо за информацию! Ваш отчет об ошибке был отправлен разработчику.")
    await bot.send_message(
        developer_chat_id,
        f"Новый отчет об ошибке:\n"
        f"Айди пользователя: {message.from_user.id}\n"
        f"Описание ошибки: {data['bug_description']}\n"
        f"Фотография: Отсутствует"
    )
    await state.finish()


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)