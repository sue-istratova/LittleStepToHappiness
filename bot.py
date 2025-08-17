import json
import os
import random
import sqlite3
import re
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiohttp import web
import asyncio

# =================== Настройки ===================
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
PORT = int(os.getenv('PORT', 8443))  # Для Render
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Публичный URL + /webhook
LOCAL_MODE = os.getenv('LOCAL_MODE', 'True') == 'True'  # True — локальный запуск

print(">>> Запуск бота", "локально" if LOCAL_MODE else "через webhook")

# =================== Работа с базой ===================
def init_db():
    try:
        conn = sqlite3.connect('db.sqlite')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
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

# =================== Загрузка задач ===================
def load_tasks():
    try:
        with open('tasks.json', 'r', encoding='utf-8') as f:
            tasks = json.load(f)
            print(f"✅ Загружено {len(tasks)} задач из tasks.json")
            return tasks
    except Exception as e:
        print(f"❌ Ошибка при загрузке tasks.json: {e}")
        return []

TASKS = load_tasks()

# =================== Логика бота ===================
def is_valid_time(time_str):
    return bool(re.match(r'^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]$', time_str))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Привет! Я "Little step to happiness". 🌸\n'
        'Каждый день я буду присылать тебе маленькое расслабляющее задание.\n\n'
        'Чтобы установить время напоминаний, введи команду:\n'
        '/settime 10:00'
    )

async def set_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Я "Little step to happiness"! Вот что я умею:\n\n'
        '/start - Начать работу\n'
        '/settime HH:MM - Установить время напоминаний\n'
        '/stop - Отключить напоминания\n'
        '/help - Показать эту справку'
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    remove_user(user_id)
    await update.message.reply_text('❌ Напоминания отключены. Чтобы включить снова — используй /settime HH:MM')

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
init_db()

app = Application.builder().token(TOKEN).build()

# Handlers
app.add_handler(CommandHandler('start', start))
app.add_handler(CommandHandler('settime', set_time))
app.add_handler(CommandHandler('help', help_command))
app.add_handler(CommandHandler('stop', stop))

# Scheduler
scheduler = AsyncIOScheduler()
scheduler.add_job(send_daily_task, 'interval', minutes=1, args=[app])
scheduler.start()

# =================== Webhook ===================
async def webhook_handler(request):
    data = await request.json()
    update = Update.de_json(data, app.bot)
    await app.update_queue.put(update)
    return web.Response()

async def on_startup_webhook(app: Application):
    await app.bot.set_webhook(f"{WEBHOOK_URL}/webhook")
    print(f"✅ Webhook установлен: {WEBHOOK_URL}/webhook")

# =================== Старт ===================
if LOCAL_MODE:
    print("✅ Локальный запуск через polling")
    app.run_polling()
else:
    print("✅ Запуск через webhook (Render)")
    app.on_startup.append(on_startup_webhook)
    web_app = web.Application()
    web_app.router.add_post('/webhook', webhook_handler)
    web.run_app(web_app, port=PORT)