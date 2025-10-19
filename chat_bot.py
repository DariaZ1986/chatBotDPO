import os
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

# Firebase
import firebase_admin
from firebase_admin import credentials, firestore

# --- Logging ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Load environment ---
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # e.g. @mychannel or -1001234567890
FIREBASE_KEY_PATH = os.getenv("FIREBASE_KEY_PATH", "serviceAccountKey.json")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN not found in .env")

# --- Init Firebase ---
cred = credentials.Certificate(FIREBASE_KEY_PATH)
firebase_admin.initialize_app(cred)
db = firestore.client()


# --- Firestore helpers ---
def get_all_directions():
    """Возвращает список направлений"""
    directions = []
    try:
        for doc in db.collection("directions").stream():
            d = doc.to_dict()
            d["id"] = doc.id
            directions.append(d)
        logger.info(f"Загружено {len(directions)} направлений")
    except Exception as e:
        logger.error(f"Ошибка при загрузке направлений: {e}")
    return directions


def get_direction_by_id(dir_id):
    """Возвращает одно направление по ID"""
    try:
        doc = db.collection("directions").document(dir_id).get()
        if not doc.exists:
            return None
        data = doc.to_dict()
        data["id"] = doc.id
        return data
    except Exception as e:
        logger.error(f"Ошибка при загрузке направления {dir_id}: {e}")
        return None


def get_programs_by_direction(dir_id):
    """Получает программы из подколлекции 'programs'"""
    programs = []
    try:
        programs_ref = db.collection("directions").document(dir_id).collection("programs")
        for doc in programs_ref.stream():
            program_data = doc.to_dict()
            program_data["id"] = doc.id
            program_data["direction_id"] = dir_id
            programs.append(program_data)
        logger.info(f"Найдено {len(programs)} программ для направления {dir_id}")
    except Exception as e:
        logger.error(f"Ошибка при получении программ для направления {dir_id}: {e}")
    return programs


def get_program_by_id(prog_id):
    """Находит программу по ID, перебирая все направления и их подколлекции"""
    try:
        directions = db.collection("directions").stream()
        for direction_doc in directions:
            direction_id = direction_doc.id
            programs_ref = db.collection("directions").document(direction_id).collection("programs")
            program_doc = programs_ref.document(prog_id).get()
            if program_doc.exists:
                program_data = program_doc.to_dict()
                program_data["id"] = prog_id
                program_data["direction_id"] = direction_id
                return program_data
    except Exception as e:
        logger.error(f"Ошибка при поиске программы {prog_id}: {e}")
    return None


# --- Keyboards ---
def main_menu_kb():
    kb = [
        [InlineKeyboardButton("📚 FAQ", callback_data="menu_faq")],
        [InlineKeyboardButton("🎓 Посмотреть программы", callback_data="menu_programs")],
        [InlineKeyboardButton("📝 Оставить заявку на программу", callback_data="menu_apply")]
    ]
    return InlineKeyboardMarkup(kb)


def back_to_main_kb():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")]]
    )


def directions_kb():
    directions = get_all_directions()
    if not directions:
        return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")]])
    
    buttons = []
    for d in directions:
        buttons.append([InlineKeyboardButton(d["name"], callback_data=f"dir_{d['id']}")])
    buttons.append([InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def programs_kb(dir_id):
    programs = get_programs_by_direction(dir_id)
    if not programs:
        buttons = [
            [InlineKeyboardButton("❌ Программы не найдены", callback_data="none")],
            [InlineKeyboardButton("◀️ Назад", callback_data="menu_programs")],
            [InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")]
        ]
        return InlineKeyboardMarkup(buttons)
    
    buttons = []
    for p in programs:
        # Обрезаем длинное название если нужно
        name = p["name"]
        if len(name) > 50:
            name = name[:47] + "..."
        buttons.append([InlineKeyboardButton(name, callback_data=f"prog_{p['id']}")])
    
    buttons.append([InlineKeyboardButton("◀️ Назад", callback_data="menu_programs")])
    buttons.append([InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")])
    return InlineKeyboardMarkup(buttons)


def program_detail_kb(prog_id, dir_id):
    kb = [
        [InlineKeyboardButton("📝 Оставить заявку на эту программу", callback_data=f"apply_prog_{prog_id}")],
        [InlineKeyboardButton("◀️ Назад к программам", callback_data=f"dir_{dir_id}")],
        [InlineKeyboardButton("◀️ Главное меню", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(kb)


def confirm_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Да", callback_data="confirm_yes")],
        [InlineKeyboardButton("❌ Нет", callback_data="confirm_no")]
    ])


# --- Handlers ---
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "👋 Добро пожаловать! Я бот для записи на образовательные программы.\n\n"
            "Выберите действие:",
            reply_markup=main_menu_kb()
        )
    else:
        await update.callback_query.message.edit_text(
            "👋 Добро пожаловать! Выберите действие:",
            reply_markup=main_menu_kb()
        )


FAQ_TEXT = (
    "📘 *FAQ:*\n\n"
    "1️⃣ *Как записаться на программу?*\n"
    "Нажмите 'Посмотреть программы', выберите направление и программу, затем 'Оставить заявку'.\n\n"
    "2️⃣ *Как происходит оплата?*\n"
    "После отправки заявки администратор свяжется с вами для уточнения деталей и оплаты.\n\n"
    "3️⃣ *Можно ли пройти курс дистанционно?*\n"
    "Да, большинство программ доступны в онлайн-формате.\n\n"
    "4️⃣ *Когда начинаются занятия?*\n"
    "Даты начала занятий уточняются при подаче заявки.\n\n"
    "5️⃣ *Выдаются ли документы об окончании?*\n"
    "Да, по окончании программы выдается удостоверение или диплом установленного образца."
)


async def callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    # Главное меню
    if data == "back_main":
        await query.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
        return

    # FAQ
    if data == "menu_faq":
        await query.message.edit_text(FAQ_TEXT, parse_mode="Markdown", reply_markup=back_to_main_kb())
        return

    # Просмотр направлений
    if data == "menu_programs":
        directions = get_all_directions()
        if not directions:
            await query.message.edit_text(
                "❌ Направления временно недоступны. Попробуйте позже.",
                reply_markup=back_to_main_kb()
            )
            return
        await query.message.edit_text("🎓 Выберите направление:", reply_markup=directions_kb())
        return

    # Выбор направления
    if data.startswith("dir_"):
        dir_id = data.split("dir_", 1)[1]
        direction = get_direction_by_id(dir_id)
        if not direction:
            await query.message.edit_text("❌ Направление не найдено.", reply_markup=back_to_main_kb())
            return
        
        programs = get_programs_by_direction(dir_id)
        if not programs:
            await query.message.edit_text(
                f"🎯 *{direction['name']}*\n\n"
                "❌ В этом направлении пока нет доступных программ.",
                parse_mode="Markdown",
                reply_markup=back_to_main_kb()
            )
            return
        
        await query.message.edit_text(
            f"🎯 *{direction['name']}*\n\n"
            f"📚 Доступно программ: {len(programs)}\n"
            "Выберите программу:",
            parse_mode="Markdown",
            reply_markup=programs_kb(dir_id)
        )
        return

    # Выбор программы
    if data.startswith("prog_"):
        prog_id = data.split("prog_", 1)[1]
        program = get_program_by_id(prog_id)
        if not program:
            await query.message.edit_text("❌ Программа не найдена.", reply_markup=back_to_main_kb())
            return
        
        direction = get_direction_by_id(program["direction_id"])
        direction_name = direction["name"] if direction else "Неизвестное направление"
        
        # Форматируем описание
        description = program.get('description', 'Описание отсутствует')
        if description and len(description) > 1000:
            description = description[:1000] + "..."
        
        text = (
            f"🎓 *{program['name']}*\n\n"
            f"📁 *Направление:* {direction_name}\n"
            f"⏱️ *Продолжительность:* {program.get('hours', 'не указана')}\n"
            f"📖 *Формат обучения:* {program.get('form', 'не указан')}\n"
            f"💰 *Стоимость:* {program.get('price', 'не указана')}\n\n"
            f"📝 *Описание:*\n{description}"
        )
        
        await query.message.edit_text(
            text, 
            parse_mode="Markdown", 
            reply_markup=program_detail_kb(prog_id, program["direction_id"])
        )
        return

    # Оставить заявку на программу
    if data.startswith("apply_prog_"):
        prog_id = data.split("apply_prog_", 1)[1]
        program = get_program_by_id(prog_id)
        direction = get_direction_by_id(program["direction_id"]) if program else None
        
        if not program or not direction:
            await query.message.edit_text("❌ Ошибка: программа не найдена.", reply_markup=back_to_main_kb())
            return
        
        context.user_data['apply_prog_id'] = prog_id
        context.user_data['apply_prog_name'] = program['name']
        context.user_data['apply_direction_name'] = direction['name']
        context.user_data['state'] = 'awaiting_fio'
        
        await query.message.edit_text(
            f"📝 *Заявка на программу:*\n\n"
            f"🎓 *Программа:* {program['name']}\n"
            f"📁 *Направление:* {direction['name']}\n\n"
            "Пожалуйста, введите ваши *ФИО*:",
            parse_mode="Markdown"
        )
        return

    # Заявка через меню
    if data == "menu_apply":
        await query.message.edit_text(
            "📝 Чтобы оставить заявку, сначала выберите программу:\n\n"
            "Выберите направление:",
            reply_markup=directions_kb()
        )
        return

    # Подтверждение заявки
    if data == "confirm_yes":
        fio = context.user_data.get('fio')
        contact = context.user_data.get('contact')
        prog_id = context.user_data.get('apply_prog_id')
        
        if not (fio and contact and prog_id):
            await query.message.edit_text("❌ Ошибка: нет данных для заявки.", reply_markup=main_menu_kb())
            context.user_data.clear()
            return
        
        program = get_program_by_id(prog_id)
        direction = get_direction_by_id(program["direction_id"])
        user = query.from_user
        
        userinfo = f"{user.full_name}"
        if user.username:
            userinfo += f" (@{user.username})"
        
        text_to_channel = (
            "📩 *НОВАЯ ЗАЯВКА*\n\n"
            f"👤 *ФИО:* {fio}\n"
            f"📞 *Контакт:* {contact}\n"
            f"🎓 *Программа:* {program['name']}\n"
            f"📁 *Направление:* {direction['name']}\n"
            f"👥 *Telegram:* {userinfo}\n"
            f"🆔 *User ID:* {user.id}"
        )
        
        try:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=text_to_channel, parse_mode="Markdown")
            logger.info(f"Заявка отправлена в канал: {program['name']}")
        except Exception as e:
            logger.error(f"Ошибка отправки в канал: {e}")
            await query.message.edit_text("❌ Ошибка при отправке заявки администратору.", reply_markup=main_menu_kb())
            context.user_data.clear()
            return

        await query.message.edit_text(
            "✅ *Спасибо! Ваша заявка отправлена!*\n\n"
            "Администратор свяжется с вами в ближайшее время для уточнения деталей.",
            parse_mode="Markdown",
            reply_markup=main_menu_kb()
        )
        context.user_data.clear()
        return

    if data == "confirm_no":
        await query.message.edit_text("❌ Заявка отменена.", reply_markup=main_menu_kb())
        context.user_data.clear()
        return

    # Заглушка для неактивных кнопок
    if data == "none":
        await query.answer("Эта кнопка неактивна")
        return

    await query.message.edit_text("❌ Неизвестная команда.", reply_markup=main_menu_kb())


async def text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений при заполнении заявки"""
    state = context.user_data.get('state')
    if not state:
        await update.message.reply_text(
            "👋 Используйте меню для навигации:",
            reply_markup=main_menu_kb()
        )
        return

    if state == 'awaiting_fio':
        fio = update.message.text.strip()
        if len(fio) < 2:
            await update.message.reply_text("❌ Пожалуйста, введите корректные ФИО:")
            return
        
        context.user_data['fio'] = fio
        context.user_data['state'] = 'awaiting_contact'
        
        await update.message.reply_text(
            "✅ ФИО принято.\n\n"
            "Теперь введите *контактные данные* (телефон, email или Telegram):",
            parse_mode="Markdown"
        )
        return

    if state == 'awaiting_contact':
        contact = update.message.text.strip()
        if len(contact) < 3:
            await update.message.reply_text("❌ Пожалуйста, введите корректные контактные данные:")
            return
        
        context.user_data['contact'] = contact
        prog_id = context.user_data.get('apply_prog_id')
        program = get_program_by_id(prog_id)
        direction = get_direction_by_id(program["direction_id"])
        
        summary = (
            "📋 *Проверьте данные заявки:*\n\n"
            f"👤 *ФИО:* {context.user_data['fio']}\n"
            f"📞 *Контакт:* {context.user_data['contact']}\n"
            f"🎓 *Программа:* {program['name']}\n"
            f"📁 *Направление:* {direction['name']}\n\n"
            "✅ *Подтвердить отправку заявки?*"
        )
        
        context.user_data['state'] = 'confirm'
        await update.message.reply_text(summary, parse_mode="Markdown", reply_markup=confirm_kb())
        return

    await update.message.reply_text(
        "❌ Не понимаю сообщение. Начните заново через главное меню:",
        reply_markup=main_menu_kb()
    )
    context.user_data.clear()


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Попробуйте еще раз.",
            reply_markup=main_menu_kb()
        )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CallbackQueryHandler(callbacks))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_messages))
    
    # Обработчик ошибок
    app.add_error_handler(error_handler)

    logger.info("✅ Бот запущен")
    print("Бот запущен! Нажмите Ctrl+C для остановки.")
    
    try:
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")


if __name__ == "__main__":
    main()