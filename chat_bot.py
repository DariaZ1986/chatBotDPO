import os
import json
import logging
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Load environment ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # e.g. @mychannel or -1001234567890

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not found in .env")

# --- Load data files ---
with open("programs.json", "r", encoding="utf-8") as f:
    DATA = json.load(f)

with open("faq.json", "r", encoding="utf-8") as f:
    FAQ_DATA = json.load(f)

# --- Helpers ---
def find_direction_by_id(dir_id):
    for d in DATA.get("directions", []):
        if d["id"] == dir_id:
            return d
    return None


def find_program_by_id(prog_id):
    for d in DATA.get("directions", []):
        for p in d.get("programs", []):
            if p["id"] == prog_id:
                return p, d
    return None, None


# --- Keyboards ---
def main_menu_kb():
    kb = [
        [InlineKeyboardButton("FAQ", callback_data="menu_faq")],
        [InlineKeyboardButton("Посмотреть программы", callback_data="menu_programs")],
        [InlineKeyboardButton("Оставить заявку на программу", callback_data="menu_apply")]
    ]
    return InlineKeyboardMarkup(kb)


def back_to_main_kb():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("◀ Главное меню", callback_data="back_main")]]
    )


def directions_kb():
    buttons = []
    for d in DATA.get("directions", []):
        buttons.append([InlineKeyboardButton(d["name"], callback_data=f"dir_{d['id']}")])
    buttons.append([InlineKeyboardButton("◀ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def programs_kb(dir_id):
    d = find_direction_by_id(dir_id)
    buttons = []
    if not d:
        return back_to_main_kb()
    for p in d.get("programs", []):
        buttons.append([InlineKeyboardButton(p["name"], callback_data=f"prog_{p['id']}")])
    buttons.append([InlineKeyboardButton("◀ Назад", callback_data="menu_programs")])
    buttons.append([InlineKeyboardButton("◀ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def program_detail_kb(prog_id, dir_id):
    kb = [
        [InlineKeyboardButton("Оставить заявку на эту программу", callback_data=f"apply_prog_{prog_id}")],
        [InlineKeyboardButton("◀ Назад", callback_data=f"dir_{dir_id}")],
        [InlineKeyboardButton("◀ Главное меню", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(kb)


def confirm_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Да", callback_data="confirm_yes")],
        [InlineKeyboardButton("Нет", callback_data="confirm_no")]
    ])


# --- FAQ Keyboards ---
def faq_categories_kb():
    """Клавиатура со списком категорий FAQ"""
    kb = []
    for i, cat in enumerate(FAQ_DATA.get("faq", [])):
        kb.append([InlineKeyboardButton(cat["category"], callback_data=f"faq_cat_{i}")])
    kb.append([InlineKeyboardButton("◀ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(kb)


def faq_questions_kb(cat_index: int):
    """Клавиатура со списком вопросов в категории"""
    cat = FAQ_DATA["faq"][cat_index]
    kb = []
    for j, q in enumerate(cat["questions"]):
        text = q.get("q", "")
        short = text[:60] + ("..." if len(text) > 60 else "")
        kb.append([InlineKeyboardButton(short, callback_data=f"faq_q_{cat_index}_{j}")])
    kb.append([InlineKeyboardButton("◀ Назад", callback_data="menu_faq")])
    kb.append([InlineKeyboardButton("◀ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(kb)


# --- Handlers ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("Привет! Выберите действие:", reply_markup=main_menu_kb())
    else:
        await update.callback_query.message.edit_text("Привет! Выберите действие:", reply_markup=main_menu_kb())


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    # --- Главное меню ---
    if data == "back_main":
        await query.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
        return

    # --- FAQ ---
        # --- FAQ ---
    if data == "menu_faq":
        await query.message.edit_text(
            "📚 Выберите категорию часто задаваемых вопросов:",
            reply_markup=faq_categories_kb()
        )
        return

    if data.startswith("faq_cat_"):
        cat_index = int(data.split("faq_cat_", 1)[1])
        cat = FAQ_DATA["faq"][cat_index]

        # Формируем текст со всеми вопросами и ответами
        text_parts = [f"📂 *{cat['category']}*\n"]
        for q in cat["questions"]:
            question = q.get("q", "Вопрос не найден.")
            answer = q.get("a", "Ответ уточняется.")
            text_parts.append(f"❓ *{question}*\n💬 {answer}\n")

        text = "\n".join(text_parts)

        await query.message.edit_text(
            text,
            parse_mode="Markdown",
            reply_markup=faq_categories_kb()
        )
        return


    # --- Программы ---
    if data == "menu_programs":
        await query.message.edit_text("Выберите направление:", reply_markup=directions_kb())
        return

    if data.startswith("dir_"):
        dir_id = data.split("dir_", 1)[1]
        d = find_direction_by_id(dir_id)
        if not d:
            await query.message.reply_text("Не найдено направление.", reply_markup=back_to_main_kb())
            return
        await query.message.edit_text(
            f"Направление: {d['name']}\nВыберите программу:",
            reply_markup=programs_kb(dir_id)
        )
        return

    if data.startswith("prog_"):
        prog_id = data.split("prog_", 1)[1]
        prog, direction = find_program_by_id(prog_id)
        if not prog:
            await query.message.reply_text("Программа не найдена.", reply_markup=back_to_main_kb())
            return
        text = (
            f"Наименование программы: {prog['name']}\n"
            f"Наименование направления: {direction['name']}\n"
            f"Описание программы: {prog.get('description','-')}\n"
            f"Часы: {prog.get('hours','-')}\n"
            f"Форма обучения: {prog.get('form','-')}\n"
            f"Стоимость за 1 слушателя: {prog.get('price','-')}\n"
        )
        await query.message.edit_text(text, reply_markup=program_detail_kb(prog_id, direction['id']))
        return

    # --- Заявка ---
    if data.startswith("apply_prog_"):
        prog_id = data.split("apply_prog_", 1)[1]
        prog, direction = find_program_by_id(prog_id)
        if not prog:
            await query.message.reply_text("Ошибка: программа не найдена.", reply_markup=back_to_main_kb())
            return
        context.user_data['apply_prog_id'] = prog_id
        context.user_data['state'] = 'awaiting_fio'
        await query.message.reply_text(
            "Вы выбрали программу:\n\n"
            f"{prog['name']} ({direction['name']})\n\n"
            f"Пожалуйста, введите ваши ФИО:"
        )
        return

    if data == "menu_apply":
        context.user_data['from_apply'] = True
        await query.message.edit_text(
            "Сначала выберите направление, затем программу, на которую хотите оставить заявку:",
            reply_markup=directions_kb()
        )
        return

    if data == "confirm_yes":
        fio = context.user_data.get('fio')
        contact = context.user_data.get('contact')
        prog_id = context.user_data.get('apply_prog_id')
        if not (fio and contact and prog_id):
            await query.message.reply_text("Ошибка: нет данных для заявки. Начните заново.", reply_markup=main_menu_kb())
            context.user_data.clear()
            return
        prog, direction = find_program_by_id(prog_id)
        user = query.from_user
        userinfo = f"{user.full_name}"
        if user.username:
            userinfo += f" (@{user.username})"
        text_to_channel = (
            "Пользователь оставил заявку:\n"
            f"ФИО: {fio}\n"
            f"Контакт: {contact}\n"
            f"Программа: {prog['name']} ({direction['name']})\n"
            f"Пользователь Telegram: {userinfo} (id={user.id})"
        )
        try:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=text_to_channel)
        except Exception:
            logger.exception("Ошибка отправки в канал:")
            await query.message.reply_text("Ошибка при отправке заявки администратору. Свяжитесь, пожалуйста, напрямую.")
            context.user_data.clear()
            return

        await query.message.reply_text("Спасибо — ваша заявка отправлена. Мы свяжемся с вами.", reply_markup=main_menu_kb())
        context.user_data.clear()
        return

    if data == "confirm_no":
        await query.message.reply_text("Заявка отменена. Если хотите — начните заново.", reply_markup=main_menu_kb())
        context.user_data.clear()
        return

    await query.message.reply_text("Неизвестная команда. Вернитесь в главное меню.", reply_markup=main_menu_kb())


async def text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state')
    if not state:
        await update.message.reply_text("Нажмите /start или используйте кнопки меню.", reply_markup=main_menu_kb())
        return

    if state == 'awaiting_fio':
        context.user_data['fio'] = update.message.text.strip()
        context.user_data['state'] = 'awaiting_contact'
        await update.message.reply_text("Спасибо. Теперь введите контакт (телефон/почта/Telegram):")
        return

    if state == 'awaiting_contact':
        context.user_data['contact'] = update.message.text.strip()
        prog_id = context.user_data.get('apply_prog_id')
        if not prog_id:
            await update.message.reply_text(
                "Похоже, вы не выбрали программу. Пожалуйста, выберите программу через «Посмотреть программы».",
                reply_markup=main_menu_kb()
            )
            context.user_data.clear()
            return
        prog, direction = find_program_by_id(prog_id)
        summary = (
            "Проверьте данные заявки:\n\n"
            f"ФИО: {context.user_data['fio']}\n"
            f"Контакт: {context.user_data['contact']}\n"
            f"Программа: {prog['name']} ({direction['name']})\n\n"
            "Подтвердить отправку заявки?"
        )
        context.user_data['state'] = 'confirm'
        await update.message.reply_text(summary, reply_markup=confirm_kb())
        return

    await update.message.reply_text("Не понимаю. Начните заново через главное меню:", reply_markup=main_menu_kb())
    context.user_data.clear()


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_messages))

    logger.info("Bot started")
    app.run_polling()


if __name__ == "__main__":
    main()
