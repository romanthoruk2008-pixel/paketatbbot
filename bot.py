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
        f"Здарова, {hbold(name)}! 🛒\n\n"
        "ПАКЕТ АТБ для сесії вже тут. Легендарний. Помʼятий. Але тримається.\n\n"
        "Тут лежить твоя сесія. І твій mental state теж десь тут.\n\n"
        "Що в пакеті:\n"
        "• Тести — як мівіна на чорний день\n"
        "• Тренажер — щоб життя медом не здавалось\n"
        "• Помилки — архів твоїх страждань\n\n"
        "Пакет витримує:\n"
        "✓ паніку о 2 ночі\n"
        "✓ «я нічого не знаю»\n"
        "✓ 98 відкритих вкладок\n"
        "✓ останню надію\n"
        "✓ екзамен завтра\n\n"
        "Тисни <b>❓ Як пакувати</b> і починай виживання.",
        parse_mode="HTML",
        reply_markup=main_kb()
    )

async def btn_help(message: types.Message):
    await message.answer(
        "🧾 <b>ІНСТРУКЦІЯ НА КАСІ</b>\n\n"
        "1️⃣ Відкрий ChatGPT або Claude\n"
        "2️⃣ Кинь туди свій конспект або слайди\n"
        "3️⃣ Скопіюй промпт з наступного повідомлення і встав його ПЕРЕД матеріалом\n"
        "4️⃣ Отримані тести кинь мені через <b>➕ Закинути тести</b>",
        parse_mode="HTML",
        reply_markup=main_kb()
    )
    await message.answer(
        "<code>"
        "Generate 20 university-level multiple choice exam questions based on the material below.\n\n"
        "Format each question EXACTLY like this (with a blank line between questions):\n\n"
        "Питання: [question text]\n"
        "A: [option]\n"
        "B: [option]\n"
        "C: [option]\n"
        "D: [option]\n"
        "Відповідь: [correct letter]\n"
        "Пояснення: [explanation of why this answer is correct, and why the others are wrong]\n\n"
        "Rules:\n"
        "- One correct answer per question\n"
        "- Wrong answers must be highly plausible — use real terminology, partial truths, and common misconceptions\n"
        "- Never use silly distractors like none of the above or all of the above\n"
        "- Mix question types: definitions, comparisons, application, cause-and-effect, chronology, which is NOT\n"
        "- At least 3 questions should be tricky — where two answers seem correct but one is more precise\n"
        "- Explanations must be detailed: why correct is right AND why the most tempting wrong answer is wrong\n"
        "- Cover the full material evenly\n"
        "- Include at least 2 questions comparing two different authors/theories/concepts\n"
        "- Include at least 2 questions about specific data, dates or figures\n"
        "- Do not number the questions\n"
        "- Write at university final exam level, not high school\n\n"
        "Material:\n"
        "[PASTE YOUR NOTES HERE]"
        "</code>",
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
