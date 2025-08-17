import json
import os
import random
import sqlite3
import re
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Загружаем переменные окружения (.env должен содержать BOT_TOKEN=...)
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

print(">>> Я запускаю правильный bot.py")

# Загружаем задачи из tasks.json
with open('tasks.json', 'r', encoding='utf-8') as f:
    TASKS = json.load(f)

# =================== Работа с базой ===================

def init_db():
    """Инициализация базы данных"""
    try:
        conn = sqlite3.connect('db.sqlite')
        c = conn.cursor()
        c.execute('DROP TABLE IF EXISTS users')
        c.execute('''CREATE TABLE users (
            user_id INTEGER PRIMARY KEY,
            reminder_time TEXT
        )''')
        conn.commit()
        print("✅ База данных инициализирована успешно")
    except sqlite3.Error as e:
        print(f"❌ Ошибка при инициализации базы: {e}")
    finally:
        conn.close()

def save_user_time(user_id, time):
    """Сохраняем время напоминания для пользователя"""
    try:
        conn = sqlite3.connect('db.sqlite')
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO users (user_id, reminder_time) VALUES (?, ?)', (user_id, time))
        conn.commit()
        print(f"⏰ Сохранено время {time} для пользователя {user_id}")
    except sqlite3.Error as e:
        print(f"❌ Ошибка сохранения времени для {user_id}: {e}")
    finally:
        conn.close()

def get_users():
    """Получаем всех пользователей с их временем"""
    try:
        conn = sqlite3.connect('db.sqlite')
        c = conn.cursor()
        c.execute('SELECT user_id, reminder_time FROM users')
        users = c.fetchall()
        conn.close()
        return {user_id: {'time': time} for user_id, time in users}
    except sqlite3.Error as e:
        print(f"❌ Ошибка при получении пользователей: {e}")
        return {}

def remove_user(user_id):
    """Удаляем пользователя из базы"""
    try:
        conn = sqlite3.connect('db.sqlite')
        c = conn.cursor()
        c.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        conn.commit()
        print(f"🗑 Пользователь {user_id} удалён")
    except sqlite3.Error as e:
        print(f"❌ Ошибка при удалении пользователя {user_id}: {e}")
    finally:
        conn.close()

# =================== Логика бота ===================

def is_valid_time(time_str):
    """Проверка формата времени (HH:MM)"""
    return bool(re.match(r'^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$', time_str))

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        'Привет! Я "Little step to happiness". 🌸\n'
        'Каждый день я буду присылать тебе маленькое расслабляющее задание.\n\n'
        'Чтобы установить время напоминаний, введи команду:\n'
        '/settime 10:00'
    )

async def set_time(update: Update, context: CallbackContext):
    if not context.args:
        await update.message.reply_text('Укажи время в формате HH:MM, например: /settime 10:00')
        return
    time = context.args[0]
    if not is_valid_time(time):
        await update.message.reply_text('Неверный формат времени! Используй HH:MM, например: /settime 10:00')
        return
    user_id = update.message.from_user.id
    save_user_time(user_id, time)
    await update.message.reply_text(f'⏰ Напоминания установлены на {time}! Каждый день в это время я пришлю тебе задание 🌿')

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        'Я "Little step to happiness"! Вот что я умею:\n\n'
        '/start - Начать работу\n'
        '/settime HH:MM - Установить время напоминаний\n'
        '/stop - Отключить напоминания\n'
        '/help - Показать эту справку'
    )

async def stop(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    remove_user(user_id)
    await update.message.reply_text('❌ Напоминания отключены. Чтобы включить снова — используй /settime HH:MM')

# Отправка ежедневных задач
async def send_daily_task(app: Application):
    users = get_users()
    current_time = datetime.now().strftime('%H:%M')
    for user_id, data in users.items():
        if data['time'] == current_time:
            task = random.choice(TASKS)
            try:
                await app.bot.send_message(chat_id=user_id, text=f'✨ Твой маленький шаг к счастью сегодня:\n\n{task}')
                print(f"✅ Отправлена задача пользователю {user_id}: {task}")
            except Exception as e:
                print(f"❌ Ошибка при отправке {user_id}: {e}")

# =================== Запуск ===================

def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('settime', set_time))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('stop', stop))

    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_task, 'interval', minutes=1, args=[app])
    scheduler.start()

    app.run_polling()

if __name__ == '__main__':
    main()