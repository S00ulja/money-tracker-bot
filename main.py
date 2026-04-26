import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime
from aiohttp import web
from config import TOKEN
from database import db

# ================== СОСТОЯНИЯ ==================

class AddExpenseStates(StatesGroup):
    """Состояния для добавления расхода"""
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_description = State()

class AddIncomeStates(StatesGroup):
    """Состояния для добавления дохода"""
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_description = State()

class DeleteTransactionStates(StatesGroup):
    """Состояния для удаления транзакции"""
    waiting_for_id = State()

class FilterByDateStates(StatesGroup):
    """Состояния для фильтрации по дате"""
    waiting_for_choice = State()

class FilterByCategoryStates(StatesGroup):
    """Состояния для фильтрации по категории"""
    waiting_for_choice = State()

# ================== ИНИЦИАЛИЗАЦИЯ ==================

bot = Bot(token=TOKEN)
dp = Dispatcher()

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
    """Создаёт клавиатуру из списка категорий"""
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
    """Главное меню"""
    await message.answer(
        "👋 Привет! Я бот для учёта финансов.\n\n"
        "Выбери действие из меню ниже:",
        reply_markup=main_keyboard
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    """Справка"""
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
    """Начало добавления расхода"""
    await state.set_state(AddExpenseStates.waiting_for_amount)
    await message.answer(
        "💰 Введи сумму расхода (например: 100):",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(AddExpenseStates.waiting_for_amount)
async def process_expense_amount(message: types.Message, state: FSMContext):
    """Обработка суммы расхода"""
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
    """Обработка категории расхода"""
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
    """Обработка описания расхода"""
    description = None if message.text == "-" else message.text
    data = await state.get_data()
    
    db.add_transaction(data['amount'], data['category'], description, "расход")
    await state.clear()
    
    response = f"✅ Расход добавлен!\n\n"
    response += f"💰 Сумма: {data['amount']} р.\n"
    response += f"📂 Категория: {data['category']}\n"
    if description:
        response += f"📝 Описание: {description}\n"
    
    await message.answer(response, reply_markup=main_keyboard)

# ================== ДОБАВЛЕНИЕ ДОХОДА ==================

@dp.message(F.text == "💚 Добавить доход")
async def start_add_income(message: types.Message, state: FSMContext):
    """Начало добавления дохода"""
    await state.set_state(AddIncomeStates.waiting_for_amount)
    await message.answer(
        "💚 Введи сумму дохода (например: 5000):",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(AddIncomeStates.waiting_for_amount)
async def process_income_amount(message: types.Message, state: FSMContext):
    """Обработка суммы дохода"""
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
    """Обработка категории дохода"""
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
    """Обработка описания дохода"""
    description = None if message.text == "-" else message.text
    data = await state.get_data()
    
    db.add_transaction(data['amount'], data['category'], description, "доход")
    await state.clear()
    
    response = f"✅ Доход добавлен!\n\n"
    response += f"💚 Сумма: {data['amount']} р.\n"
    response += f"📂 Категория: {data['category']}\n"
    if description:
        response += f"📝 Описание: {description}\n"
    
    await message.answer(response, reply_markup=main_keyboard)

# ================== СТАТИСТИКА ==================

@dp.message(F.text == "📊 Статистика")
async def show_statistics(message: types.Message):
    """Показывает статистику"""
    total_expenses = db.get_total_expenses()
    total_income = db.get_total_income()
    
    response = f"📊 СТАТИСТИКА\n\n"
    response += f"💚 Доход: {total_income} р.\n"
    response += f"❌ Расходы: {total_expenses} р.\n\n"
    
    # Расходы по категориям
    expense_cats = db.get_transactions_by_category('расход')
    if expense_cats:
        response += "💸 РАСХОДЫ ПО КАТЕГОРИЯМ:\n"
        for category, amount in expense_cats:
            response += f"  • {category}: {amount} р.\n"
        response += "\n"
    
    # Доходы по категориям
    income_cats = db.get_transactions_by_category('доход')
    if income_cats:
        response += "💚 ДОХОДЫ ПО КАТЕГОРИЯМ:\n"
        for category, amount in income_cats:
            response += f"  • {category}: {amount} р.\n"
    
    await message.answer(response, reply_markup=main_keyboard)

# ================== БАЛАНС ==================

@dp.message(F.text == "💰 Баланс")
async def show_balance(message: types.Message):
    """Показывает баланс"""
    income = db.get_total_income()
    expenses = db.get_total_expenses()
    balance = db.get_balance()
    
    response = f"💰 БАЛАНС\n\n"
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
    """Показывает историю"""
    transactions = db.get_all_transactions()
    
    if not transactions:
        await message.answer(
            "📋 История пуста!",
            reply_markup=main_keyboard
        )
        return
    
    response = "📋 ИСТОРИЯ ТРАНЗАКЦИЙ\n\n"
    
    for trans in transactions:
        trans_id, amount, category, description, date, trans_type = trans
        emoji = "❌" if trans_type == "расход" else "💚"
        response += f"ID: {trans_id} | {emoji} {date}\n"
        response += f"   {category}: {amount} р."
        if description:
            response += f" ({description})"
        response += "\n\n"
    
    await message.answer(response, reply_markup=main_keyboard)

# ================== УДАЛЕНИЕ ЗАПИСИ ==================

@dp.message(F.text == "🗑️ Удалить запись")
async def start_delete(message: types.Message, state: FSMContext):
    """Начало удаления записи"""
    transactions = db.get_all_transactions()
    
    if not transactions:
        await message.answer("📋 Нет записей для удаления!", reply_markup=main_keyboard)
        return
    
    response = "🗑️ УДАЛЕНИЕ ЗАПИСИ\n\n"
    response += "Вот последние записи (введи ID для удаления):\n\n"
    
    for trans in transactions[:10]:  # Показываем последние 10
        trans_id, amount, category, description, date, trans_type = trans
        emoji = "❌" if trans_type == "расход" else "💚"
        response += f"ID: {trans_id} | {emoji} {category}: {amount} р. ({date})\n"
    
    await state.set_state(DeleteTransactionStates.waiting_for_id)
    await message.answer(response + "\nВведи ID (или 'отмена'):")

@dp.message(DeleteTransactionStates.waiting_for_id)
async def process_delete(message: types.Message, state: FSMContext):
    """Обработка удаления"""
    if message.text.lower() == "отмена":
        await state.clear()
        await message.answer("❌ Удаление отменено.", reply_markup=main_keyboard)
        return
    
    try:
        trans_id = int(message.text)
        db.delete_transaction(trans_id)
        await state.clear()
        await message.answer("✅ Запись удалена!", reply_markup=main_keyboard)
    except ValueError:
        await message.answer("❌ Введи корректный ID (число):")

# ================== ФИЛЬТР ПО ДАТАМ ==================

@dp.message(F.text == "📅 По датам")
async def start_date_filter(message: types.Message, state: FSMContext):
    """Начало фильтрации по датам"""
    await state.set_state(FilterByDateStates.waiting_for_choice)
    await message.answer(
        "📅 Выбери период:",
        reply_markup=date_filter_keyboard
    )

@dp.message(FilterByDateStates.waiting_for_choice)
async def process_date_filter(message: types.Message, state: FSMContext):
    """Обработка фильтра по датам"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Фильтр отменён.", reply_markup=main_keyboard)
        return
    
    if message.text == "📅 За сегодня":
        transactions = db.get_transactions_by_date(1)
        period = "за сегодня"
    elif message.text == "📅 За неделю":
        transactions = db.get_transactions_by_date(7)
        period = "за неделю"
    elif message.text == "📅 За месяц":
        transactions = db.get_transactions_by_date(30)
        period = "за месяц"
    elif message.text == "📅 За всё время":
        transactions = db.get_all_transactions()
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
        trans_id, amount, category, description, date, trans_type = trans
        emoji = "❌" if trans_type == "расход" else "💚"
        response += f"{emoji} {date}\n"
        response += f"   {category}: {amount} р."
        if description:
            response += f" ({description})"
        response += "\n\n"
    
    await message.answer(response, reply_markup=main_keyboard)

# ================== ФИЛЬТР ПО КАТЕГОРИИ ==================

@dp.message(F.text == "🔍 По категории")
async def start_category_filter(message: types.Message, state: FSMContext):
    """Начало фильтрации по категориям"""
    expense_cats = db.get_transactions_by_category('расход')
    income_cats = db.get_transactions_by_category('доход')
    
    if not expense_cats and not income_cats:
        await message.answer("📋 Нет транзакций!", reply_markup=main_keyboard)
        return
    
    categories_list = ["Расходы:"]
    for cat, _ in expense_cats:
        categories_list.append(f"  ❌ {cat}")
    
    if income_cats:
        categories_list.append("\nДоходы:")
        for cat, _ in income_cats:
            categories_list.append(f"  💚 {cat}")
    
    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=cat)] for cat in [c.strip() for c in categories_list if c.strip() and not c.startswith(("Расходы", "Доходы"))]] + [[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True
    )
    
    response = "🔍 ВЫБЕРИ КАТЕГОРИЮ:\n\n"
    response += "\n".join(categories_list)
    
    await state.set_state(FilterByCategoryStates.waiting_for_choice)
    await message.answer(response, reply_markup=keyboard)

@dp.message(FilterByCategoryStates.waiting_for_choice)
async def process_category_filter(message: types.Message, state: FSMContext):
    """Обработка фильтра по категориям"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer("❌ Фильтр отменён.", reply_markup=main_keyboard)
        return
    
    category = message.text.replace("❌ ", "").replace("💚 ", "").strip()
    
    # Проверяем расходы
    expense_trans = db.get_transactions_by_category_filtered(category, 'расход')
    income_trans = db.get_transactions_by_category_filtered(category, 'доход')
    
    transactions = expense_trans + income_trans
    
    await state.clear()
    
    if not transactions:
        await message.answer(f"📋 Нет транзакций в категории '{category}'.", reply_markup=main_keyboard)
        return
    
    response = f"🔍 ТРАНЗАКЦИИ - {category.upper()}\n\n"
    total = sum(t[1] for t in transactions)
    response += f"💰 Всего: {total} р.\n\n"
    
    for trans in transactions:
        trans_id, amount, category_name, description, date, trans_type = trans
        emoji = "❌" if trans_type == "расход" else "💚"
        response += f"{emoji} {date}\n"
        response += f"   {amount} р."
        if description:
            response += f" ({description})"
        response += "\n"
    
    await message.answer(response, reply_markup=main_keyboard)

# ================== ЭКСПОРТ ==================

@dp.message(F.text == "📥 Экспорт")
async def export_data(message: types.Message):
    """Экспортирует данные в файл"""
    text_content = db.export_to_text()
    
    # Создаём файл
    filename = f"finance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(text_content)
    
    # Отправляем файл пользователю
    with open(filename, 'rb') as f:
        await message.answer_document(
            types.BufferedInputFile(f.read(), filename=filename),
            caption="📥 Вот твой отчёт!",
            reply_markup=main_keyboard
        )

# ================== ВЕБ-СЕРВЕР ДЛЯ ХОСТИНГА ==================

async def health_check(request):
    """Простой health check endpoint"""
    return web.Response(text="OK", status=200)

async def start_web_server():
    """Запускает веб-сервер на порту 8000"""
    app = web.Application()
    app.router.add_get('/health', health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    print("🌐 Веб-сервер запущен на порту 8000")

# ================== ЗАПУСК ==================

async def main():
    """Запуск бота с веб-сервером"""
    # Запускаем веб-сервер
    web_task = asyncio.create_task(start_web_server())
    
    # Запускаем бота
    print("🤖 Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
