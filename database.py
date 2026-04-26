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
                    user_id BIGINT NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    date TEXT NOT NULL,
                    type TEXT NOT NULL
                )
            ''')

    async def add_transaction(self, user_id, amount, category, description, transaction_type):
        date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        async with self.pool.acquire() as conn:
            await conn.execute('''
                INSERT INTO transactions (user_id, amount, category, description, date, type)
                VALUES ($1, $2, $3, $4, $5, $6)
            ''', user_id, amount, category, description, date, transaction_type)

    async def get_all_transactions(self, user_id):
        async with self.pool.acquire() as conn:
            return await conn.fetch(
                'SELECT * FROM transactions WHERE user_id = $1 ORDER BY date DESC',
                user_id)

    async def get_transactions_by_category(self, user_id, transaction_type='расход'):
        async with self.pool.acquire() as conn:
            return await conn.fetch('''
                SELECT category, SUM(amount) as total
                FROM transactions WHERE user_id = $1 AND type = $2
                GROUP BY category ORDER BY total DESC
            ''', user_id, transaction_type)

    async def get_total_expenses(self, user_id):
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT SUM(amount) FROM transactions WHERE user_id = $1 AND type = 'расход'",
                user_id)
            return result or 0

    async def get_total_income(self, user_id):
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT SUM(amount) FROM transactions WHERE user_id = $1 AND type = 'доход'",
                user_id)
            return result or 0

    async def get_balance(self, user_id):
        return await self.get_total_income(user_id) - await self.get_total_expenses(user_id)

    async def get_transactions_by_date(self, user_id, days=None):
        async with self.pool.acquire() as conn:
            if days is None:
                return await conn.fetch(
                    'SELECT * FROM transactions WHERE user_id = $1 ORDER BY date DESC',
                    user_id)
            date_threshold = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            return await conn.fetch('''
                SELECT * FROM transactions WHERE user_id = $1 AND date >= $2 ORDER BY date DESC
            ''', user_id, date_threshold)

    async def get_transactions_by_category_filtered(self, user_id, category, transaction_type):
        async with self.pool.acquire() as conn:
            return await conn.fetch('''
                SELECT * FROM transactions WHERE user_id = $1 AND category = $2 AND type = $3
                ORDER BY date DESC
            ''', user_id, category, transaction_type)

    async def delete_transaction(self, user_id, transaction_id):
        async with self.pool.acquire() as conn:
            await conn.execute(
                'DELETE FROM transactions WHERE id = $1 AND user_id = $2',
                transaction_id, user_id)

    async def export_to_text(self, user_id):
        transactions = await self.get_all_transactions(user_id)
        total_income = await self.get_total_income(user_id)
        total_expenses = await self.get_total_expenses(user_id)
        balance = await self.get_balance(user_id)

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
