import os
import json
import asyncio
import threading
from aiogram import Bot, Dispatcher, types, Router
from aiogram.filters import Command
from aiogram.types import WebAppInfo, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# --- НАСТРОЙКИ ---
TOKEN = "8690472693:AAFq-_CTTu6Jk0MwVzt1yeBAtZ_gBRvOupc"  # <--- Твой токен остается здесь!
WEB_APP_URL = "https://specialworldru-ai.github.io/clicker/?v=500"

# Создаем бота без прокси, так как на Render он не нужен
bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)
DB_FILE = "db.json"

# --- ЛОКАЛЬНАЯ БАЗА ДАННЫХ (ФАЙЛ JSON) ---
def load_db():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# --- МИНИ-СЕРВЕР ДЛЯ ПРИЕМА КЛИКОВ ИЗ ИГРЫ (FLASK) ---
app = Flask(__name__)
CORS(app)

# --- РОУТЫ ДЛЯ ОТДАЧИ ФАЙЛОВ ИГРЫ (ИСПРАВЛЕНИЕ ОШИБКИ 404) ---
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory('.', filename)

# --- АПИ ДЛЯ ИГРЫ ---
@app.route('/get_balance', methods=['GET'])
def get_balance():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    data = load_db()

    # Если пользователя нет, создаем дефолтный профиль
    if user_id not in data:
        data[user_id] = {
            "balance": 0,
            "click_level": 1,
            "click_power": 1,
            "username": f"ID: {user_id}"
        }
        save_db(data)

    return jsonify(data[user_id])

@app.route('/get_leaders', methods=['GET'])
def get_leaders():
    try:
        data = load_db()

        # Формируем список лидеров, сортируя по балансу от большего к меньшему
        leaders_list = []
        for u_id, u_data in data.items():
            leaders_list.append({
                "username": u_data.get("username", f"ID: {u_id}"),
                "balance": u_data.get("balance", 0)
            })
        
        # Сортируем по убыванию баланса
        leaders_list = sorted(leaders_list, key=lambda x: x['balance'], reverse=True)
        
        # Отдаем топ-10 игроков
        return jsonify(leaders_list[:10])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/click', methods=['POST'])
def click():
    req_data = request.json
    user_id = str(req_data.get('user_id'))
    username = req_data.get('username', f"ID: {user_id}")
    clicks = req_data.get('clicks', 0)
    
    # Необязательные параметры (передаются при покупке апгрейда)
    click_level = req_data.get('click_level')
    click_power = req_data.get('click_power')

    data = load_db()

    if user_id not in data:
        data[user_id] = {"balance": 0, "click_level": 1, "click_power": 1}

    # Обновляем данные
    data[user_id]['balance'] += clicks
    data[user_id]['username'] = username
    
    if click_level is not None:
        data[user_id]['click_level'] = click_level
    if click_power is not None:
        data[user_id]['click_power'] = click_power

    save_db(data)
    return jsonify({"status": "success", "balance": data[user_id]['balance']})

def run_flask():
    # Render автоматически передает порт, слушаем его и хост 0.0.0.0
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

# --- КОМАНДА /START ДЛЯ БОТА ---
@router.message(Command("start"))
async def start_cmd(message: types.Message):
    btn = KeyboardButton(text="🚀 Играть в Neon Clicker", web_app=WebAppInfo(url=WEB_APP_URL))
    markup = ReplyKeyboardMarkup(keyboard=[[btn]], resize_keyboard=True)
    
    db = load_db()
    user_id = str(message.from_user.id)
    
    # Защита на случай, если структура в бд изменилась (словарь вместо числа)
    user_data = db.get(user_id, 0)
    current_balance = user_data.get("balance", 0) if isinstance(user_data, dict) else user_data
    
    await message.answer(
        f"Привет, {message.from_user.first_name}!\n"
        f"Твой баланс: ⚡ {current_balance} монет.\n\n"
        f"Жми кнопку ниже, чтобы зайти в игру!", 
        reply_markup=markup
    )

# --- ФУНКЦИЯ РАССЫЛКИ ОБ ОБНОВЛЕНИИ ---
async def send_update_notification():
    # Даем боту 5 секунд проснуться после старта
    await asyncio.sleep(5)
    
    db = load_db()
    if not db:
        print("База данных пуста, некому отправлять обновление.")
        return

    print(f"Начинаем рассылку обновления для {len(db)} пользователей...")
    
    btn = InlineKeyboardButton(text="🚀 Открыть Neon Clicker", web_app=WebAppInfo(url=WEB_APP_URL))
    markup = InlineKeyboardMarkup(inline_keyboard=[[btn]])

    text = (
        "🔥 **ВЫШЛО ОБНОВЛЕНИЕ!** 🔥\n\n"
        "Что нового:\n"
        "✨ Изменили дизайн!\n"
        "⚡ Исправили баги!\n\n"
        "Скорее заходи и проверяй обновленного кликера 👇"
    )

    for user_id in db.keys():
        try:
            await bot.send_message(chat_id=user_id, text=text, parse_mode="Markdown", reply_markup=markup)
            await asyncio.sleep(0.05)  # Небольшая задержка, чтобы Telegram не забанил за спам
        except Exception as e:
            print(f"Не удалось отправить сообщение {user_id}: {e}")
            
    print("Рассылка успешно завершена!")

# --- ЗАПУСК ВСЕЙ СИСТЕМЫ ---
async def main():
    # Запускаем Flask сервер кликера в отдельном потоке
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Запускаем задачу рассылки в фоне
    asyncio.create_task(send_update_notification())
    
    print("Бот и Бэкенд успешно запущены на aiogram 3.x!")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    # Корректный запуск асинхронного движка бота
    asyncio.run(main())