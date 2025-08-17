import json
import os
import random
import sqlite3
from datetime import datetime
import re
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Загрузка переменных окружения из .env
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# Загрузка задач из tasks.json
with open('tasks.json', 'r', encoding='utf-8') as f:
    TASKS = json.load(f)

# Инициализация базы данных SQLite
def init_db():
    try:
        conn = sqlite3.connect('db.sqlite')
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS users')
        c.execute('''CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            reminder_time TEXT
        )''')
        conn.commit()
        print("База данных инициализирована успешно: таблица 'users' создана")
    except sqlite3.Error as e:
        print(f"Ошибка при инициализации базы данных: {e}")
    finally:
        conn.close()

# Сохранение времени напоминания для пользователя
def save_user_time(user_id, time):
    try:
        conn = sqlite3.connect('db.sqlite')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO users (user_id, reminder_time) VALUES (?, ?)', (user_id, time))
        conn.commit()
        print(f"Сохранено время {time} для пользователя {user_id}")
    except sqlite3.Error as e:
        print(f"Ошибка при сохранении времени для пользователя {user_id}: {e}")
    finally:
        conn.close()

# Получение всех пользователей и их времени
def get_users():
    try:
        conn = sqlite3.connect('db.sqlite')
        c = conn.cursor()
        c.execute('SELECT user_id, reminder_time FROM users')
        users = c.fetchall()
        conn.close()
        return {user_id: {'time': time} for user_id, time in users}
    except sqlite3.Error as e:
        print(f"Ошибка при получении пользователей: {e}")
        return {}

# Удаление пользователя
def remove_user(user_id):
    try:
        conn = sqlite3.connect('db.sqlite')
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        print(f"Пользователь {user_id} удалён")
    except sqlite3.Error as e:
        print(f"Ошибка при удалении пользователя {user_id}: {e}")
    finally:
        conn.close()

# Валидация формата времени (HH:MM)
def is_valid_time(time_str):
    return bool(re.match(r'^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$', time_str))

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Привет! Я "Little step to happiness". '
        'Я буду присылать тебе каждый день расслабляющее дело. '
        'Укажи время для напоминаний, например: /settime 10:00'
    )

# Команда /settime
async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('Пожалуйста, укажи время в формате HH:MM, например: /settime 10:00')
        return
    time = context.args[0]
    if not is_valid_time(time):
        await update.message.reply_text('Неверный формат времени! Используй HH:MM, например: /settime 10:00')
        return
    user_id = update.message.from_user.id
    save_user_time(user_id, time)
    await update.message.reply_text(f'Установлено время: {time}. Теперь каждый день в {time} я пришлю тебе расслабляющее дело!')

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Я "Little step to happiness"! Вот что я умею:\n'
        '/start - Начать работу с ботом\n'
        '/settime HH:MM - Установить время ежедневных напоминаний\n'
        '/stop - Отключить напоминания\n'
        '/help - Показать эту справку'
    )

# Команда