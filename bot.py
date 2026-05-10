"""
Telegram Bot — Тренажер для сесії
Запуск: python bot.py
"""

import os
import json
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, ReplyKeyboardMarkup, KeyboardButton,
    ReplyKeyboardRemove
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.markdown import hbold
import asyncio

# ══════════════════════════════════════════
# КОНФІГ — змінити тут
# ══════════════════════════════════════════
BOT_TOKEN = 8353488924:AAEQxCfIoCZEeSXiy8jVRXMb9Gf7-lJKnB4
MINI_APP_URL = https://paketatb.netlify.app/

# ══════════════════════════════════════════
# FSM СТАНИ
# ══════════════════════════════════════════
class AddQuiz(StatesGroup):
    waiting_subject = State()
    waiting_questions = State()

# ══════════════════════════════════════════
# ПАРСЕР ПИТАНЬ
# ══════════════════════════════════════════
def parse_questions(text: str) -> list[dict]:
    """
    Розбирає текст у форматі:
    Питання: ...
    A: ...
    B: ...
    C: ...
    D: ...
    Відповідь: A
    Пояснення: ...
    """
    blocks = re.split(r'\n\s*\n', text.strip())
    questions = []

    for block in blocks:
        lines = [l.strip() for l in block.split('\n') if l.strip()]
        q = {'options': [None, None, None, None], 'mistaken': False}

        for line in lines:
            if re.match(r'^питання:', line, re.I):
                q['question'] = re.sub(r'^питання:\s*', '', line, flags=re.I)
            elif re.match(r'^a:', line, re.I):
                q['options'][0] = re.sub(r'^a:\s*', '', line, flags=re.I)
            elif re.match(r'^b:', line, re.I):
                q['options'][1] = re.sub(r'^b:\s*', '', line, flags=re.I)
            elif re.match(r'^c:', line, re.I):
                q['options'][2] = re.sub(r'^c:\s*', '', line, flags=re.I)
            elif re.match(r'^d:', line, re.I):
                q['options'][3] = re.sub(r'^d:\s*', '', line, flags=re.I)
            elif re.match(r'^відповідь:', line, re.I):
                q['answer'] = re.sub(r'^відповідь:\s*', '', line, flags=re.I).upper().strip()
            elif re.match(r'^пояснення:', line, re.I):
                q['explanation'] = re.sub(r'^пояснення:\s*', '', line, flags=re.I)

        q['options'] = [o for o in q['options'] if o]

        if q.get('question') and len(q['options']) >= 2 and q.get('answer'):
            questions.append(q)

    return questions

# ══════════════════════════════════════════
# КЛАВІАТУРИ
# ══════════════════════════════════════════
def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Відкрити тренажер", web_app=WebAppInfo(url=MINI_APP_URL))],
            [KeyboardButton(text="➕ Додати тести"), KeyboardButton(text="📊 Моя статистика")],
            [KeyboardButton(text="❓ Як додавати тести")],
        ],
        resize_keyboard=True
    )

def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Скасувати")]],
        resize_keyboard=True
    )

# ══════════════════════════════════════════
# HANDLERS
# ══════════════════════════════════════════
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    name = message.from_user.first_name or "друже"
    await message.answer(
        f"Привіт, {hbold(name)}! 👋\n\n"
        "Я допоможу тобі підготуватися до сесії.\n\n"
        "Ось що я вмію:\n"
        "• Зберігати твої тести по предметах\n"
        "• Запускати інтерактивний тренажер\n"
        "• Відслідковувати помилки\n\n"
        "Натисни <b>➕ Додати тести</b>, щоб почати!",
        parse_mode="HTML",
        reply_markup=main_kb()
    )

async def btn_help(message: types.Message):
    await message.answer(
        "📋 <b>Як додавати тести</b>\n\n"
        "1️⃣ Відкрий ChatGPT або Claude.ai\n"
        "2️⃣ Скинь туди свій конспект або презентацію\n"
        "3️⃣ Напиши: <i>«Склади 20 тестових питань з варіантами відповідей A/B/C/D у такому форматі:»</i>\n\n"
        "Потрібний формат:\n"
        "<code>Питання: Що таке фотосинтез?\n"
        "A: Процес дихання\n"
        "B: Синтез органіки зі світла\n"
        "C: Поділ клітини\n"
        "D: Синтез білка\n"
        "Відповідь: B\n"
        "Пояснення: Фотосинтез — це...</code>\n\n"
        "4️⃣ Скопіюй результат і відправ мені через <b>➕ Додати тести</b>",
        parse_mode="HTML",
        reply_markup=main_kb()
    )

async def btn_add(message: types.Message, state: FSMContext):
    await state.set_state(AddQuiz.waiting_subject)
    await message.answer(
        "📚 <b>Крок 1/2</b>\n\nНапиши назву предмету:",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

async def get_subject(message: types.Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_kb())
        return

    await state.update_data(subject=message.text.strip())
    await state.set_state(AddQuiz.waiting_questions)
    await message.answer(
        f"✅ Предмет: <b>{message.text.strip()}</b>\n\n"
        "📝 <b>Крок 2/2</b>\n\n"
        "Тепер вставте тести у форматі:\n\n"
        "<code>Питання: ...\n"
        "A: ...\nB: ...\nC: ...\nD: ...\n"
        "Відповідь: A\n"
        "Пояснення: ...</code>\n\n"
        "Кілька питань розділяй порожнім рядком.",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

async def get_questions(message: types.Message, state: FSMContext):
    if message.text == "❌ Скасувати":
        await state.clear()
        await message.answer("Скасовано.", reply_markup=main_kb())
        return

    data = await state.get_data()
    subject = data.get('subject', 'Без назви')
    questions = parse_questions(message.text)

    if not questions:
        await message.answer(
            "❌ Не вдалося розпізнати питання.\n\n"
            "Перевір формат — між питаннями має бути порожній рядок.\n"
            "Натисни ❓ Як додавати тести для прикладу.",
            reply_markup=cancel_kb()
        )
        return

    # Відправляємо дані в Mini App через inline кнопку
    payload = json.dumps({
        "subject": subject,
        "questions": questions
    }, ensure_ascii=False)

    # Кодуємо для URL (обрізаємо якщо занадто довго — Telegram ліміт 512 байт)
    from urllib.parse import quote
    encoded = quote(payload)

    if len(encoded) > 400:
        # Занадто багато питань — відправляємо частинами
        # Для простоти зберігаємо в повідомленні
        await message.answer(
            f"✅ Розпізнано <b>{len(questions)}</b> питань!\n\n"
            f"Предмет: <b>{subject}</b>\n\n"
            "Відкрий тренажер і додай їх вручну через кнопку «Додати тести» в самому додатку.",
            parse_mode="HTML",
            reply_markup=main_kb()
        )
    else:
        url_with_data = f"{MINI_APP_URL}?data={encoded}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=f"✅ Відкрити тренажер ({len(questions)} питань)",
                web_app=WebAppInfo(url=url_with_data)
            )
        ]])
        await message.answer(
            f"✅ Готово! Розпізнано <b>{len(questions)}</b> питань\n"
            f"Предмет: <b>{subject}</b>\n\n"
            "Натисни кнопку, щоб завантажити їх у тренажер:",
            parse_mode="HTML",
            reply_markup=kb
        )

    await state.clear()

async def btn_stats(message: types.Message):
    await message.answer(
        "📊 <b>Статистика</b>\n\n"
        "Відкрий тренажер щоб побачити детальну статистику по кожному предмету:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="📱 Відкрити тренажер",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        ]])
    )

async def unknown(message: types.Message):
    await message.answer(
        "Не розумію цю команду. Використай меню нижче 👇",
        reply_markup=main_kb()
    )

# ══════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # Реєстрація хендлерів
    dp.message.register(cmd_start, CommandStart())
    dp.message.register(btn_help, F.text == "❓ Як додавати тести")
    dp.message.register(btn_add, F.text == "➕ Додати тести")
    dp.message.register(btn_stats, F.text == "📊 Моя статистика")
    dp.message.register(get_subject, AddQuiz.waiting_subject)
    dp.message.register(get_questions, AddQuiz.waiting_questions)
    dp.message.register(unknown)

    print("✅ Бот запущено!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
