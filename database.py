import sqlite3
from datetime import datetime, timedelta
from config import DATABASE_FILE

class Database:
    """Класс для работы с базой данных."""
    
    def __init__(self):
        """Инициализация и создание таблиц."""
        self.connection = sqlite3.connect(DATABASE_FILE)
        self.cursor = self.connection.cursor()
        self.create_tables()
    
    def create_tables(self):
        """Создаёт таблицы в базе данных."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                date TEXT NOT NULL,
                type TEXT NOT NULL
            )
        ''')
        self.connection.commit()
    
    def add_transaction(self, amount, category, description, transaction_type):
        """Добавляет новую транзакцию."""
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute('''
            INSERT INTO transactions (amount, category, description, date, type)
            VALUES (?, ?, ?, ?, ?)
        ''', (amount, category, description, date, transaction_type))
        self.connection.commit()
    
    def get_all_transactions(self):
        """Получает все транзакции."""
        self.cursor.execute('SELECT * FROM transactions ORDER BY date DESC')
        return self.cursor.fetchall()
    
    def get_transactions_by_category(self, transaction_type='расход'):
        """Получает сумму расходов/доходов по каждой категории."""
        self.cursor.execute('''
            SELECT category, SUM(amount) as total
            FROM transactions
            WHERE type = ?
            GROUP BY category
            ORDER BY total DESC
        ''', (transaction_type,))
        return self.cursor.fetchall()
    
    def get_total_expenses(self):
        """Получает общую сумму всех расходов."""
        self.cursor.execute('''
            SELECT SUM(amount) FROM transactions WHERE type = 'расход'
        ''')
        result = self.cursor.fetchone()
        return result[0] if result[0] is not None else 0
    
    def get_total_income(self):
        """Получает общую сумму всех доходов."""
        self.cursor.execute('''
            SELECT SUM(amount) FROM transactions WHERE type = 'доход'
        ''')
        result = self.cursor.fetchone()
        return result[0] if result[0] is not None else 0
    
    def get_balance(self):
        """Получает баланс (доходы - расходы)."""
        income = self.get_total_income()
        expenses = self.get_total_expenses()
        return income - expenses
    
    def get_transactions_by_date(self, days=None):
        """
        Получает транзакции за последние N дней.
        Если days=None, возвращает все.
        Если days=1, возвращает за сегодня.
        Если days=7, возвращает за неделю.
        Если days=30, возвращает за месяц.
        """
        if days is None:
            self.cursor.execute('SELECT * FROM transactions ORDER BY date DESC')
        else:
            date_threshold = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            self.cursor.execute('''
                SELECT * FROM transactions
                WHERE date >= ?
                ORDER BY date DESC
            ''', (date_threshold,))
        return self.cursor.fetchall()
    
    def get_transactions_by_category_filtered(self, category, transaction_type='расход'):
        """Получает все транзакции определённой категории."""
        self.cursor.execute('''
            SELECT * FROM transactions
            WHERE category = ? AND type = ?
            ORDER BY date DESC
        ''', (category, transaction_type))
        return self.cursor.fetchall()
    
    def delete_transaction(self, transaction_id):
        """Удаляет транзакцию по ID."""
        self.cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
        self.connection.commit()
        return True
    
    def get_last_transaction(self):
        """Получает последнюю добавленную транзакцию."""
        self.cursor.execute('SELECT * FROM transactions ORDER BY date DESC LIMIT 1')
        return self.cursor.fetchone()
    
    def export_to_text(self):
        """Экспортирует все транзакции в текстовый формат."""
        transactions = self.get_all_transactions()
        
        text = "=" * 50 + "\n"
        text += "ОТЧЁТ О ФИНАНСАХ\n"
        text += "=" * 50 + "\n\n"
        
        text += f"📅 Дата отчёта: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Статистика
        total_income = self.get_total_income()
        total_expenses = self.get_total_expenses()
        balance = self.get_balance()
        
        text += "📊 СТАТИСТИКА\n"
        text += "-" * 50 + "\n"
        text += f"💚 Общий доход: {total_income} р.\n"
        text += f"❌ Общие расходы: {total_expenses} р.\n"
        text += f"💰 Баланс: {balance} р.\n\n"
        
        # По категориям доход
        income_by_cat = self.get_transactions_by_category('доход')
        if income_by_cat:
            text += "ДОХОД ПО КАТЕГОРИЯМ\n"
            text += "-" * 50 + "\n"
            for category, amount in income_by_cat:
                text += f"  • {category}: {amount} р.\n"
            text += "\n"
        
        # По категориям расход
        expense_by_cat = self.get_transactions_by_category('расход')
        if expense_by_cat:
            text += "РАСХОДЫ ПО КАТЕГОРИЯМ\n"
            text += "-" * 50 + "\n"
            for category, amount in expense_by_cat:
                text += f"  • {category}: {amount} р.\n"
            text += "\n"
        
        # История
        if transactions:
            text += "📋 ИСТОРИЯ ТРАНЗАКЦИЙ\n"
            text += "-" * 50 + "\n"
            for trans in transactions:
                trans_id, amount, category, description, date, trans_type = trans
                text += f"ID: {trans_id} | {date}\n"
                text += f"  Тип: {trans_type}\n"
                text += f"  Категория: {category}\n"
                text += f"  Сумма: {amount} р.\n"
                if description:
                    text += f"  Описание: {description}\n"
                text += "\n"
        
        text += "=" * 50 + "\n"
        
        return text

db = Database()