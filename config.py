import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")

if not TOKEN:
    raise ValueError("TOKEN не найден! Установи переменную окружения TOKEN")

DATABASE_FILE = "money_tracker.db"