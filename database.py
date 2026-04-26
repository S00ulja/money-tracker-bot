import asyncpg
import os
from datetime import datetime, timedelta

class Database:
    def __init__(self):
        self.pool = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
        await self.create_tables()

    async def create_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    date TEXT NOT NULL,
                    type TEXT NOT NULL
                )
            ''')

    async def add_transaction(self, amount, category, description, transaction_type):
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO transactions (amount, category, description, date, type)
                VALUES ($1, $2, $3, $4, $5)
            ''', amount, category, description, date, transaction_type)

    async def get_all_transactions(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch('SELECT * FROM transactions ORDER BY date DESC')

    async def get_transactions_by_category(self, transaction_type='расход'):
        async with self.pool.acquire() as conn:
            return await conn.fetch('''
                SELECT category, SUM(amount) as total
                FROM transactions WHERE type = $1
                GROUP BY category ORDER BY total DESC
            ''', transaction_type)

    async def get_total_expenses(self):
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT SUM(amount) FROM transactions WHERE type = 'расход'")
            return result or 0

    async def get_total_income(self):
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT SUM(amount) FROM transactions WHERE type = 'доход'")
            return result or 0

    async def get_balance(self):
        return await self.get_total_income() - await self.get_total_expenses()

    async def get_transactions_by_date(self, days=None):
        async with self.pool.acquire() as conn:
            if days is None:
                return await conn.fetch('SELECT * FROM transactions ORDER BY date DESC')
            date_threshold = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            return await conn.fetch('''
                SELECT * FROM transactions WHERE date >= $1 ORDER BY date DESC
            ''', date_threshold)

    async def get_transactions_by_category_filtered(self, category, transaction_type):
        async with self.pool.acquire() as conn:
            return await conn.fetch('''
                SELECT * FROM transactions WHERE category = $1 AND type = $2
                ORDER BY date DESC
            ''', category, transaction_type)

    async def delete_transaction(self, transaction_id):
        async with self.pool.acquire() as conn:
            await conn.execute('DELETE FROM transactions WHERE id = $1', transaction_id)

    async def export_to_text(self):
        transactions = await self.get_all_transactions()
        total_income = await self.get_total_income()
        total_expenses = await self.get_total_expenses()
        balance = await self.get_balance()

        text = "=" * 50 + "\nОТЧЁТ О ФИНАНСАХ\n" + "=" * 50 + "\n\n"
        text += f"📅 Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        text += f"💚 Доход: {total_income} р.\n❌ Расходы: {total_expenses} р.\n💰 Баланс: {balance} р.\n\n"

        for trans in transactions:
            text += f"ID: {trans['id']} | {trans['date']}\n"
            text += f"  {trans['type']} | {trans['category']}: {trans['amount']} р.\n"
            if trans['description']:
                text += f"  {trans['description']}\n"
            text += "\n"
        return text

db = Database()
