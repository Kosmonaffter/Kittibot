import logging
import os
import requests
import time
import ollama

from collections import deque
from datetime import datetime
from dotenv import load_dotenv
from telebot import TeleBot, types


load_dotenv()
token = os.getenv('TOKEN')

bot = TeleBot(token=token)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)

URL = 'https://api.thecatapi.com/v1/images/search'
URL_DOG = 'https://api.thedogapi.com/v1/images/search'

user_photo_times = {}
MAX_PHOTOS = 5
TIME_WINDOW = 60  # секунд


def ask_gpt(message_text):
    response = ollama.chat(
        model='llama3',  # или другую модель, которую вы скачали
        messages=[{'role': 'user', 'content': message_text}]
    )
    return response['message']['content']


def can_send_photo(user_id):
    """Функция проверки лимита фото"""
    now = time.time()
    if user_id not in user_photo_times:
        user_photo_times[user_id] = deque()

    times = user_photo_times[user_id]

    while times and now - times[0] > TIME_WINDOW:
        times.popleft()

    if len(times) < MAX_PHOTOS:
        times.append(now)
        return True
    else:
        return False


def get_current_time():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def get_new_image():
    try:
        response = requests.get(URL)
        response.raise_for_status()
        data = response.json()
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API котов: {error}')
        try:
            response = requests.get(URL_DOG)
            response.raise_for_status()
            data = response.json()
        except Exception as error2:
            logging.error(
                f'Ошибка при запросе к резервному API собак: {error2}'
            )
            return None
    if data and isinstance(data, list) and len(data) > 0:
        return data[0].get('url')
    return None


def get_new_image_dog():
    try:
        response = requests.get(URL_DOG)
        response.raise_for_status()  # Проверка HTTP-статуса
        data = response.json()
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API собак: {error}')
        try:
            response = requests.get(URL)
            response.raise_for_status()
            data = response.json()
        except Exception as error2:
            logging.error(
                f'Ошибка при запросе к резервному API котов: {error2}'
            )
            return None  # Возвращаем None, если оба запроса упали
    if data and isinstance(data, list) and len(data) > 0:
        return data[0].get('url')
    return None


def get_info():
    welcome_text = (
        "Я - KittyBot, твой помощник и друг! Вот что я умею:\n\n"
        "🐱 Отправлять милые фото котиков - нажми кнопку «Котик» или команду /newcat\n"
        "🐶 Отправлять забавные фото собачек - нажми кнопку «Собачка» или команду /newdog\n"
        "⏰ Узнавать текущее время - нажми кнопку «Который час»\n"
        "🆔 Узнавать твой Telegram ID - нажми кнопку «Какой у меня ID»\n\n"
        "💬 Просто напиши мне любое сообщение, и я отвечу с помощью GPT - умного чат-бота!\n\n"
        "Для получения фото котиков и собачек действует лимит - не более 5 фото в минуту.\n\n"
        "Приятного общения! 😊"
    )
    return welcome_text


@bot.message_handler(commands=['newcat'])
def new_cat(message):
    chat = message.chat
    bot.send_photo(chat.id, get_new_image())


@bot.message_handler(commands=['newdog'])
def new_dog(message):
    chat = message.chat
    bot.send_photo(chat.id, get_new_image_dog())


@bot.message_handler(commands=['info'])
def info(message):
    chat = message.chat
    bot.send_message(chat.id, get_info())


@bot.message_handler(commands=['start'])
def wake_up(message):
    chat = message.chat
    name = message.chat.first_name or "друг"
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_newcat = types.KeyboardButton('Котик')
    button_newdog = types.KeyboardButton('Собачка')
    keyboard.add(button_newcat, button_newdog)
    keyboard.row(
        types.KeyboardButton('Который час'),
        types.KeyboardButton('Какой у меня ID'),
    )
    keyboard.row(
        types.KeyboardButton('info'),
        types.KeyboardButton('/....'),
    )
    welcome_text = (
        f"Привет, {name}! 👋\n\n"
        "Я - KittyBot, твой помощник и друг! Вот что я умею:\n\n"
        "🐱 Отправлять милые фото котиков - нажми кнопку «Котик» или команду /newcat\n"
        "🐶 Отправлять забавные фото собачек - нажми кнопку «Собачка» или команду /newdog\n"
        "⏰ Узнавать текущее время - нажми кнопку «Который час»\n"
        "🆔 Узнавать твой Telegram ID - нажми кнопку «Какой у меня ID»\n\n"
        "💬 Просто напиши мне любое сообщение, и я отвечу с помощью GPT - умного чат-бота!\n\n"
        "Для получения фото котиков и собачек действует лимит - не более 5 фото в минуту.\n\n"
        "Приятного общения! 😊"
    )
    bot.send_message(
        chat_id=chat.id,
        text=welcome_text,
        reply_markup=keyboard
    )

    bot.send_photo(chat.id, get_new_image())


@bot.message_handler(content_types=['text'])
def say_hi(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text.strip().lower()
    user_text = message.text.strip()

    # Обработка кнопок и команд
    if text in ['котик', 'собачка']:
        if not can_send_photo(user_id):
            bot.send_message(
                chat_id,
                'Извините, лимит 5 фото в минуту достигнут. Попробуйте позже.'
            )
            return
        if text == 'котик':
            photo_url = get_new_image()
            if photo_url:
                bot.send_photo(chat_id, photo_url)
            else:
                bot.send_message(chat_id, 'Не удалось получить фото котика.')
            return
        if text == 'собачка':
            photo_url = get_new_image_dog()
            if photo_url:
                bot.send_photo(chat_id, photo_url)
            else:
                bot.send_message(chat_id, 'Не удалось получить фото собачки.')
            return

    if text == 'какой у меня id':
        bot.send_message(chat_id, f'Ваш Telegram ID: {user_id}')
        return

    if text == 'который час':
        bot.send_message(chat_id, f'Сейчас: {get_current_time()}')
        return

    if text == 'info':
        bot.send_message(chat_id, get_info())
        return

    # Всё остальное - отправляем в GPT
    bot.send_message(chat_id, "Ой нужно по думать...")
    try:
        reply = ask_gpt(user_text)
        bot.send_message(chat_id, reply)
    except Exception as e:
        bot.send_message(chat_id, f"Ошибка при обращении к GPT: {e}")


def main():
    bot.polling()


if __name__ == '__main__':
    main()
