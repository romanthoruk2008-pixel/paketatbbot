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
BOT_TOKEN = "8353488924:AAGwuXyAKantDxiTyXAMb6DtLsA8_qzXbww"
MINI_APP_URL = "https://paketatb.netlify.app/"

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
            [KeyboardButton(text="🛍 Відкрити пакет", web_app=WebAppInfo(url=MINI_APP_URL))],
            [KeyboardButton(text="➕ Закинути тести"), KeyboardButton(text="🧾 Чек (Статистика)")],
            [KeyboardButton(text="❓ Як пакувати")],
        ],
        resize_keyboard=True
    )

def cancel_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Скасувати (Пакет порвався)")]],
        resize_keyboard=True
    )

# ══════════════════════════════════════════
# HANDLERS
# ══════════════════════════════════════════
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    name = message.from_user.first_name or "студенте"
    await message.answer(
        f"Здарова, {hbold(name)}! 🎒\n\n"
        "Тримай свій ПАКЕТ АТБ для підготовки до сесії. Виживаємо разом.\n\n"
        "Що він витримає:\n"
        "• Збереже твої тести (як мівіну на чорний день)\n"
        "• Прожене по питаннях (тренажер)\n"
        "• Покаже, де ти тупиш (робота над помилками)\n\n"
        "Тисни <b>➕ Закинути тести</b>, щоб наповнити пакет!",
        parse_mode="HTML",
        reply_markup=main_kb()
    )

async def btn_help(message: types.Message):
    await message.answer(
        "🧾 <b>ІНСТРУКЦІЯ НА КАСІ</b>\n\n"
        "1️⃣ Відкриваєш ChatGPT або Claude\n"
        "2️⃣ Кидаєш туди свій конспект\n"
        "3️⃣ Пишеш: <i>«Склади 20 тестових питань з варіантами відповідей A/B/C/D у такому форматі:»</i>\n\n"
        "Потрібний формат (чітко по штрихкоду):\n"
        "<code>Питання: Що таке фотосинтез?\n"
        "A: Процес дихання\n"
        "B: Синтез органіки зі світла\n"
        "C: Поділ клітини\n"
        "D: Синтез білка\n"
        "Відповідь: B\n"
        "Пояснення: Фотосинтез — це...</code>\n\n"
        "4️⃣ Копіюєш і кидаєш мені через <b>➕ Закинути тести</b>",
        parse_mode="HTML",
        reply_markup=main_kb()
    )

async def btn_add(message: types.Message, state: FSMContext):
    await state.set_state(AddQuiz.waiting_subject)
    await message.answer(
        "🏷 <b>КРОК 1/2</b>\n\nНапиши назву предмета (наліпи цінник):",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

async def get_subject(message: types.Message, state: FSMContext):
    if message.text == "❌ Скасувати (Пакет порвався)":
        await state.clear()
        await message.answer("Окей, скасовано. Пакет пустий.", reply_markup=main_kb())
        return

    await state.update_data(subject=message.text.strip())
    await state.set_state(AddQuiz.waiting_questions)
    await message.answer(
        f"✅ Предмет: <b>{message.text.strip()}</b>\n\n"
        "📝 <b>КРОК 2/2</b>\n\n"
        "Тепер вставляй тести у форматі:\n\n"
        "<code>Питання: ...\n"
        "A: ...\nB: ...\nC: ...\nD: ...\n"
        "Відповідь: A\n"
        "Пояснення: ...</code>\n\n"
        "Між питаннями має бути порожній рядок (як пробіл на чеку).",
        parse_mode="HTML",
        reply_markup=cancel_kb()
    )

async def get_questions(message: types.Message, state: FSMContext):
    if message.text == "❌ Скасувати (Пакет порвався)":
        await state.clear()
        await message.answer("Скасовано. Тести розсипались.", reply_markup=main_kb())
        return

    data = await state.get_data()
    subject = data.get('subject', 'Без назви')
    questions = parse_questions(message.text)

    if not questions:
        await message.answer(
            "❌ Брак на виробництві. Не вдалося розпізнати питання.\n\n"
            "Перевір формат — між питаннями має бути порожній рядок.\n"
            "Натисни ❓ Як пакувати для прикладу.",
            reply_markup=cancel_kb()
        )
        return

    payload = json.dumps({
        "subject": subject,
        "questions": questions
    }, ensure_ascii=False)

    from urllib.parse import quote
    encoded = quote(payload)

    if len(encoded) > 400:
        await message.answer(
            f"✅ Запакували <b>{len(questions)}</b> питань!\n\n"
            f"🏷 Предмет: <b>{subject}</b>\n\n"
            "Їх забагато для швидкого посилання. Відкрий пакет і додай їх вручну через кнопку всередині.",
            parse_mode="HTML",
            reply_markup=main_kb()
        )
    else:
        url_with_data = f"{MINI_APP_URL}?data={encoded}"
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text=f"🛍 Закинути в пакет ({len(questions)} шт.)",
                web_app=WebAppInfo(url=url_with_data)
            )
        ]])
        await message.answer(
            f"✅ Чек пробито. <b>{len(questions)}</b> питань\n"
            f"🏷 Предмет: <b>{subject}</b>\n\n"
            "Тисни кнопку, щоб закинути це все в тренажер:",
            parse_mode="HTML",
            reply_markup=kb
        )

    await state.clear()

async def btn_stats(message: types.Message):
    await message.answer(
        "🧾 <b>ТВІЙ ЧЕК (Статистика)</b>\n\n"
        "Відкрий пакет, щоб подивитись деталі:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="🛍 Відкрити пакет",
                web_app=WebAppInfo(url=MINI_APP_URL)
            )
        ]])
    )

async def unknown(message: types.Message):
    await message.answer(
        "Не пробивається по касі. Використай меню нижче 👇",
        reply_markup=main_kb()
    )

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(cmd_start, CommandStart())
    dp.message.register(btn_help, F.text == "❓ Як пакувати")
    dp.message.register(btn_add, F.text == "➕ Закинути тести")
    dp.message.register(btn_stats, F.text == "🧾 Чек (Статистика)")
    dp.message.register(get_subject, AddQuiz.waiting_subject)
    dp.message.register(get_questions, AddQuiz.waiting_questions)
    dp.message.register(unknown)

    print("✅ Пакет АТБ на касі (Бот запущено)!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

if __name__ == "__main__":
    asyncio.run(main())
