import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Update
from datetime import datetime
from aiohttp import web
import os
import sys
from config import TOKEN
from database import db

# ================== СОСТОЯНИЯ ==================

class AddExpenseStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_description = State()

class AddIncomeStates(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_description = State()

class DeleteTransactionStates(StatesGroup):
    waiting_for_id = State()

class FilterByDateStates(StatesGroup):
    waiting_for_choice = State()

class FilterByCategoryStates(StatesGroup):
    waiting_for_choice = State()

# ================== ИНИЦИАЛИЗАЦИЯ ==================

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Получаем URL от Render (он сам подставляет переменную окружения)
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")
PORT = int(os.getenv("PORT", 8000))

# ================== КЛАВИАТУРЫ ==================

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Добавить расход"), KeyboardButton(text="💚 Добавить доход")],
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="📋 История")],
        [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="🗑️ Удалить запись")],
        [KeyboardButton(text="📅 По датам"), KeyboardButton(text="🔍 По категории")],
        [KeyboardButton(text="📥 Экспорт")],
    ],
    resize_keyboard=True,
)

expense_categories = ["🍔 Еда", "🚗 Транспорт", "🎬 Развлечения", "💊 Здоровье",
                      "📚 Образование", "🏠 Жилище", "❌ Отмена"]

income_categories = ["💼 Зарплата", "💰 Бизнес", "🎁 Подарок", "📈 Инвестиции",
                     "🤝 Другое", "❌ Отмена"]

def create_categories_keyboard(categories):
    keyboard = [[KeyboardButton(text=cat)] for cat in categories]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

date_filter_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 За сегодня")],
        [KeyboardButton(text="📅 За неделю")],
        [KeyboardButton(text="📅 За месяц")],
        [KeyboardButton(text="📅 За всё время")],
        [KeyboardButton(text="❌ Отмена")],
    ],
    resize_keyboard=True,
)

# ================== ОСНОВНЫЕ КОМАНДЫ ==================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для учёта финансов.\n\nВыбери действие из меню ниже:",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📖 Справка:\n\n"
        "➕ Добавить расход - записать трату\n"
        "💚 Добавить доход - записать доход\n"
        "📊 Статистика - расходы по категориям\n"
        "📋 История - все транзакции\n"
        "💰 Баланс - доходы минус расходы\n"
        "🗑️ Удалить запись - удалить транзакцию\n"
        "📅 По датам - фильтр по дате\n"
        "🔍 По категории - поиск по категории\n"
        "📥 Экспорт - скачать отчёт\n\n"
        "/start - главное меню\n"
        "/help - эта справка"
    )

# ================== ДОБАВЛЕНИЕ РАСХОДА ==================

@dp.message(F.text == "➕ Добавить расход")
async def start_add_expense(message: types.Message, state: FSMContext):
    await state.set_state(AddExpenseStates.waiting_for_amount)
    await message.answer(
        "💰 Введи сумму расхода (например: 100):",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(AddExpenseStates.waiting_for_amount)
async def process_expense_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0. Попробуй снова:")
            return
        await state.update_data(amount=amount)
        await state.set_state(AddExpenseStates.waiting_for_category)
        await message.answer(
            "📂 Выбери категорию расхода:",
            reply_markup=create_categories_keyboard(expense_categories)
        )
    except ValueError:
        await message.answer("❌ Это не число! Введи сумму цифрами (например: 100):")

@dp.message(AddExpenseStates.waiting_for_category)
async def process_expense_category(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление отменено.", reply_markup=main_keyboard)
        return
    category = message.text.split(" ", 1)[1] if " " in message.text else message.text
    await state.update_data(category=category)
    await state.set_state(AddExpenseStates.waiting_for_description)
    await message.answer(
        "📝 Введи описание (или '-' чтобы пропустить):",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(AddExpenseStates.waiting_for_description)
async def process_expense_description(message: types.Message, state: FSMContext):
    description = None if message.text == "-" else message.text
    data = await state.get_data()
    user_id = message.from_user.id

    await db.add_transaction(user_id, data['amount'], data['category'], description, "расход")
    await state.clear()

    response = "✅ Расход добавлен!\n\n"
    response += f"💰 Сумма: {data['amount']} р.\n"
    response += f"📂 Категория: {data['category']}\n"
    if description:
        response += f"📝 Описание: {description}\n"
    await message.answer(response, reply_markup=main_keyboard)

# ================== ДОБАВЛЕНИЕ ДОХОДА ==================

@dp.message(F.text == "💚 Добавить доход")
async def start_add_income(message: types.Message, state: FSMContext):
    await state.set_state(AddIncomeStates.waiting_for_amount)
    await message.answer(
        "💚 Введи сумму дохода (например: 5000):",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(AddIncomeStates.waiting_for_amount)
async def process_income_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0. Попробуй снова:")
            return
        await state.update_data(amount=amount)
        await state.set_state(AddIncomeStates.waiting_for_category)
        await message.answer(
            "📂 Выбери категорию дохода:",
            reply_markup=create_categories_keyboard(income_categories)
        )
    except ValueError:
        await message.answer("❌ Это не число! Введи сумму цифрами (например: 5000):")

@dp.message(AddIncomeStates.waiting_for_category)
async def process_income_category(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Добавление отменено.", reply_markup=main_keyboard)
        return
    category = message.text.split(" ", 1)[1] if " " in message.text else message.text
    await state.update_data(category=category)
    await state.set_state(AddIncomeStates.waiting_for_description)
    await message.answer(
        "📝 Введи описание (или '-' чтобы пропустить):",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(AddIncomeStates.waiting_for_description)
async def process_income_description(message: types.Message, state: FSMContext):
    description = None if message.text == "-" else message.text
    data = await state.get_data()
    user_id = message.from_user.id

    await db.add_transaction(user_id, data['amount'], data['category'], description, "доход")
    await state.clear()

    response = "✅ Доход добавлен!\n\n"
    response += f"💚 Сумма: {data['amount']} р.\n"
    response += f"📂 Категория: {data['category']}\n"
    if description:
        response += f"📝 Описание: {description}\n"
    await message.answer(response, reply_markup=main_keyboard)

# ================== СТАТИСТИКА ==================

@dp.message(F.text == "📊 Статистика")
async def show_statistics(message: types.Message):
    user_id = message.from_user.id
    total_expenses = await db.get_total_expenses(user_id)
    total_income = await db.get_total_income(user_id)

    response = "📊 СТАТИСТИКА\n\n"
    response += f"💚 Доход: {total_income} р.\n"
    response += f"❌ Расходы: {total_expenses} р.\n\n"

    expense_cats = await db.get_transactions_by_category(user_id, 'расход')
    if expense_cats:
        response += "💸 РАСХОДЫ ПО КАТЕГОРИЯМ:\n"
        for row in expense_cats:
            response += f"  • {row['category']}: {row['total']} р.\n"
        response += "\n"

    income_cats = await db.get_transactions_by_category(user_id, 'доход')
    if income_cats:
        response += "💚 ДОХОДЫ ПО КАТЕГОРИЯМ:\n"
        for row in income_cats:
            response += f"  • {row['category']}: {row['total']} р.\n"

    await message.answer(response, reply_markup=main_keyboard)

# ================== БАЛАНС ==================

@dp.message(F.text == "💰 Баланс")
async def show_balance(message: types.Message):
    user_id = message.from_user.id
    income = await db.get_total_income(user_id)
    expenses = await db.get_total_expenses(user_id)
    balance = await db.get_balance(user_id)

    response = "💰 БАЛАНС\n\n"
    response += f"💚 Доход: {income} р.\n"
    response += f"❌ Расходы: {expenses} р.\n"
    response += f"{'💰' if balance >= 0 else '⚠️'} Баланс: {balance} р.\n"

    if balance > 0:
        response += "\n✅ Ты в плюсе!"
    elif balance < 0:
        response += "\n⚠️ Ты в минусе!"
    else:
        response += "\n🎯 Баланс нулевой!"

    await message.answer(response, reply_markup=main_keyboard)

# ================== ИСТОРИЯ ==================

@dp.message(F.text == "📋 История")
async def show_history(message: types.Message):
    user_id = message.from_user.id
    transactions = await db.get_all_transactions(user_id)

    if not transactions:
        await message.answer("📋 История пуста!", reply_markup=main_keyboard)
        return

    response = "📋 ИСТОРИЯ ТРАНЗАКЦИЙ\n\n"
    for trans in transactions:
        emoji = "❌" if trans['type'] == "расход" else "💚"
        response += f"ID: {trans['id']} | {emoji} {trans['date']}\n"
        response += f"   {trans['category']}: {trans['amount']} р."
        if trans['description']:
            response += f" ({trans['description']})"
        response += "\n\n"

    await message.answer(response, reply_markup=main_keyboard)

# ================== УДАЛЕНИЕ ЗАПИСИ ==================

@dp.message(F.text == "🗑️ Удалить запись")
async def start_delete(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    transactions = await db.get_all_transactions(user_id)

    if not transactions:
        await message.answer("📋 Нет записей для удаления!", reply_markup=main_keyboard)
        return

    response = "🗑️ УДАЛЕНИЕ ЗАПИСИ\n\nВот последние записи (введи ID для удаления):\n\n"
    for trans in transactions[:10]:
        emoji = "❌" if trans['type'] == "расход" else "💚"
        response += f"ID: {trans['id']} | {emoji} {trans['category']}: {trans['amount']} р. ({trans['date']})\n"

    await state.set_state(DeleteTransactionStates.waiting_for_id)
    await message.answer(response + "\nВведи ID (или 'отмена'):")

@dp.message(DeleteTransactionStates.waiting_for_id)
async def process_delete(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("❌ Удаление отменено.", reply_markup=main_keyboard)
        return
    try:
        trans_id = int(message.text)
        await db.delete_transaction(message.from_user.id, trans_id)
        await state.clear()
        await message.answer("✅ Запись удалена!", reply_markup=main_keyboard)
    except ValueError:
        await message.answer("❌ Введи корректный ID (число):")

# ================== ФИЛЬТР ПО ДАТАМ ==================

@dp.message(F.text == "📅 По датам")
async def start_date_filter(message: types.Message, state: FSMContext):
    await state.set_state(FilterByDateStates.waiting_for_choice)
    await message.answer("📅 Выбери период:", reply_markup=date_filter_keyboard)

@dp.message(FilterByDateStates.waiting_for_choice)
async def process_date_filter(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Фильтр отменён.", reply_markup=main_keyboard)
        return

    user_id = message.from_user.id

    if message.text == "📅 За сегодня":
        transactions = await db.get_transactions_by_date(user_id, 1)
        period = "за сегодня"
    elif message.text == "📅 За неделю":
        transactions = await db.get_transactions_by_date(user_id, 7)
        period = "за неделю"
    elif message.text == "📅 За месяц":
        transactions = await db.get_transactions_by_date(user_id, 30)
        period = "за месяц"
    elif message.text == "📅 За всё время":
        transactions = await db.get_all_transactions(user_id)
        period = "за всё время"
    else:
        await message.answer("❌ Выбери из предложенных вариантов:")
        return

    await state.clear()

    if not transactions:
        await message.answer(f"📋 Нет транзакций {period}.", reply_markup=main_keyboard)
        return

    response = f"📋 ТРАНЗАКЦИИ {period.upper()}\n\n"
    for trans in transactions:
        emoji = "❌" if trans['type'] == "расход" else "💚"
        response += f"{emoji} {trans['date']}\n"
        response += f"   {trans['category']}: {trans['amount']} р."
        if trans['description']:
            response += f" ({trans['description']})"
        response += "\n\n"

    await message.answer(response, reply_markup=main_keyboard)

# ================== ФИЛЬТР ПО КАТЕГОРИИ ==================

@dp.message(F.text == "🔍 По категории")
async def start_category_filter(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    expense_cats = await db.get_transactions_by_category(user_id, 'расход')
    income_cats = await db.get_transactions_by_category(user_id, 'доход')

    if not expense_cats and not income_cats:
        await message.answer("📋 Нет транзакций!", reply_markup=main_keyboard)
        return

    categories_list = ["Расходы:"]
    for row in expense_cats:
        categories_list.append(f"  ❌ {row['category']}")

    if income_cats:
        categories_list.append("\nДоходы:")
        for row in income_cats:
            categories_list.append(f"  💚 {row['category']}")

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=cat.strip())] for cat in categories_list
                  if cat.strip() and not cat.strip().startswith(("Расходы", "Доходы"))]
                 + [[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )

    response = "🔍 ВЫБЕРИ КАТЕГОРИЮ:\n\n" + "\n".join(categories_list)
    await state.set_state(FilterByCategoryStates.waiting_for_choice)
    await message.answer(response, reply_markup=keyboard)

@dp.message(FilterByCategoryStates.waiting_for_choice)
async def process_category_filter(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Фильтр отменён.", reply_markup=main_keyboard)
        return

    user_id = message.from_user.id
    category = message.text.replace("❌ ", "").replace("💚 ", "").strip()

    expense_trans = await db.get_transactions_by_category_filtered(user_id, category, 'расход')
    income_trans = await db.get_transactions_by_category_filtered(user_id, category, 'доход')
    transactions = list(expense_trans) + list(income_trans)

    await state.clear()

    if not transactions:
        await message.answer(f"📋 Нет транзакций в категории '{category}'.", reply_markup=main_keyboard)
        return

    response = f"🔍 ТРАНЗАКЦИИ - {category.upper()}\n\n"
    total = sum(t['amount'] for t in transactions)
    response += f"💰 Всего: {total} р.\n\n"

    for trans in transactions:
        emoji = "❌" if trans['type'] == "расход" else "💚"
        response += f"{emoji} {trans['date']}\n"
        response += f"   {trans['amount']} р."
        if trans['description']:
            response += f" ({trans['description']})"
        response += "\n"

    await message.answer(response, reply_markup=main_keyboard)

# ================== ЭКСПОРТ ==================

@dp.message(F.text == "📥 Экспорт")
async def export_data(message: types.Message):
    user_id = message.from_user.id
    text_content = await db.export_to_text(user_id)
    filename = f"finance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

    await message.answer_document(
        types.BufferedInputFile(text_content.encode('utf-8'), filename=filename),
        caption="📥 Вот твой отчёт!",
        reply_markup=main_keyboard
    )

# ================== WEBHOOK ENDPOINTS ==================

async def webhook(request):
    """Обработка входящих обновлений от Telegram"""
    try:
        data = await request.json()
        update = Update(**data)
        await dp.feed_update(bot, update)
        return web.Response(status=200)
    except Exception as e:
        print(f"Ошибка в webhook: {e}")
        return web.Response(status=200)  # Всегда отвечаем 200 Telegram

async def health_check(request):
    """Проверка здоровья для Render"""
    return web.Response(text="OK", status=200)

async def on_startup():
    """Действия при запуске приложения"""
    await db.connect()
    print("🤖 Бот запущен...")

    # Устанавливаем вебхук только если есть URL
    if RENDER_EXTERNAL_URL:
        webhook_url = f"{RENDER_EXTERNAL_URL}/webhook"
        await bot.set_webhook(webhook_url)
        print(f"✅ Webhook установлен: {webhook_url}")
    else:
        print("⚠️ RENDER_EXTERNAL_URL не найден, работаем в режиме polling")
        # Если локально, запускаем polling
        asyncio.create_task(dp.start_polling(bot))

async def on_shutdown():
    """Действия при остановке"""
    # Удаляем вебхук при остановке
    await bot.delete_webhook()
    await db.close()
    print("👋 Бот остановлен")

# ================== ЗАПУСК WEB-СЕРВЕРА ==================

async def main():
    # Создаем aiohttp приложение
    app = web.Application()
    app.router.add_post('/webhook', webhook)
    app.router.add_get('/health', health_check)
    
    # Добавляем startup/shutdown хуки
    app.on_startup.append(lambda _: on_startup())
    app.on_shutdown.append(lambda _: on_shutdown())
    
    # Запускаем веб-сервер
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    
    print(f"🌐 Веб-сервер запущен на порту {PORT}")
    print(f"🔗 Health check: http://0.0.0.0:{PORT}/health")
    print(f"🔗 Webhook endpoint: http://0.0.0.0:{PORT}/webhook")
    
    # Держим приложение запущенным
    try:
        while True:
            await asyncio.sleep(3600)  # Спим час
    except KeyboardInterrupt:
        print("\n🛑 Остановка...")
        await runner.cleanup()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
