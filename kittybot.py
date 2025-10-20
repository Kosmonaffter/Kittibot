import os
import time
from collections import deque
from datetime import datetime
from dotenv import load_dotenv
from telebot import TeleBot, types

# Импорт модулей
from logger import setup_logging, log_command, log_error
from gpt_client import gpt_client
from image_api import image_api

# Загрузка конфигурации
load_dotenv()

# Настройка логирования
logger = setup_logging()

# Константы
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError('TOKEN environment variable is not set')

MAX_PHOTOS = 5
TIME_WINDOW = 60  # секунд

# Инициализация бота
bot = TeleBot(token=TOKEN)

# Глобальные переменные
user_photo_times = {}


def get_current_time() -> str:
    '''Получение текущего времени'''
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def can_send_photo(user_id: int) -> bool:
    '''Проверка лимита отправки фото'''
    now = time.time()

    if user_id not in user_photo_times:
        user_photo_times[user_id] = deque()

    times = user_photo_times[user_id]

    # Очистка устаревших записей
    while times and now - times[0] > TIME_WINDOW:
        times.popleft()

    if len(times) < MAX_PHOTOS:
        times.append(now)
        return True
    return False


def get_welcome_message(name: str = 'друг') -> str:
    '''Генерация приветственного сообщения'''
    return (
        f'Привет, {name}! 👋\n\n'
        'Я - KittyBot, твой помощник и друг! Вот что я умею:\n\n'
        '🐱 Отправлять милые фото котиков - нажми кнопку «Котик» '
        'или команду /newcat\n'
        '🐶 Отправлять забавные фото собачек - нажми кнопку '
        '«Собачка» или команду /newdog\n'
        '⏰ Узнавать текущее время - нажми кнопку «Который час»\n'
        '🆔 Узнавать твой Telegram ID - нажми кнопку «Какой у меня ID»\n\n'
        '💬 Просто напиши мне любое сообщение, и я отвечу с помощью '
        'GPT - умного чат-бота!\n\n'
        'Для получения фото котиков и собачек действует лимит - '
        'не более 5 фото в минуту.\n\n'
        'Приятного общения! 😊'
    )


def get_info_message() -> str:
    '''Генерация информационного сообщения'''
    return get_welcome_message('друг').split('👋\n\n')[1]


def create_main_keyboard() -> types.ReplyKeyboardMarkup:
    '''Создание основной клавиатуры'''
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    # Первая строка - животные
    button_newcat = types.KeyboardButton('Котик')
    button_newdog = types.KeyboardButton('Собачка')
    keyboard.add(button_newcat, button_newdog)

    # Вторая строка - время и ID
    keyboard.row(
        types.KeyboardButton('Который час'),
        types.KeyboardButton('Какой у меня ID'),
    )

    # Третья строка - информация
    keyboard.row(types.KeyboardButton('info'))

    return keyboard


def handle_photo_request(chat_id: int, user_id: int, animal_type: str):
    '''Обработка запроса на фото'''
    if not can_send_photo(user_id):
        message = (
            'Извините, лимит 5 фото в минуту достигнут. '
            'Попробуйте позже.'
        )
        bot.send_message(chat_id, message)
        log_command(
            logger, user_id, f'photo_{animal_type}', False, 'rate_limit'
        )
        return

    # Получаем URL изображения
    photo_url = (
        image_api.get_cat_image()
        if animal_type == 'cat'
        else image_api.get_dog_image()
    )
    animal_name = 'котика' if animal_type == 'cat' else 'собачки'

    if photo_url:
        bot.send_photo(chat_id, photo_url)
        log_command(logger, user_id, f'photo_{animal_type}')
    else:
        error_message = f'Не удалось получить фото {animal_name}.'
        bot.send_message(chat_id, error_message)
        log_command(
            logger, user_id, f'photo_{animal_type}', False, 'api_error'
        )


# Обработчики команд
@bot.message_handler(commands=['newcat'])
def new_cat(message):
    '''Обработчик команды /newcat'''
    chat_id = message.chat.id
    user_id = message.from_user.id
    handle_photo_request(chat_id, user_id, 'cat')


@bot.message_handler(commands=['newdog'])
def new_dog(message):
    '''Обработчик команды /newdog'''
    chat_id = message.chat.id
    user_id = message.from_user.id
    handle_photo_request(chat_id, user_id, 'dog')


@bot.message_handler(commands=['info'])
def info(message):
    '''Обработчик команды /info'''
    chat_id = message.chat.id
    user_id = message.from_user.id
    bot.send_message(chat_id, get_info_message())
    log_command(logger, user_id, 'info')


@bot.message_handler(commands=['start'])
def wake_up(message):
    '''Обработчик команды /start'''
    chat_id = message.chat.id
    user_id = message.from_user.id
    name = message.chat.first_name or 'друг'

    keyboard = create_main_keyboard()
    welcome_text = get_welcome_message(name)

    bot.send_message(
        chat_id=chat_id,
        text=welcome_text,
        reply_markup=keyboard
    )

    # Отправляем приветственное фото котика
    photo_url = image_api.get_cat_image()
    if photo_url:
        bot.send_photo(chat_id, photo_url)

    log_command(logger, user_id, 'start')


@bot.message_handler(content_types=['text'])
def handle_text(message):
    '''Обработка текстовых сообщений'''
    chat_id = message.chat.id
    user_id = message.from_user.id
    text = message.text.strip().lower()
    user_text = message.text.strip()

    # Обработка кнопок
    if text in ['котик', 'собачка']:
        animal_type = 'cat' if text == 'котик' else 'dog'
        handle_photo_request(chat_id, user_id, animal_type)
        return

    elif text == 'какой у меня id':
        bot.send_message(chat_id, f'Ваш Telegram ID: {user_id}')
        log_command(logger, user_id, 'get_id')
        return

    elif text == 'который час':
        current_time = get_current_time()
        bot.send_message(chat_id, f'Сейчас: {current_time}')
        log_command(logger, user_id, 'get_time')
        return

    elif text == 'info':
        bot.send_message(chat_id, get_info_message())
        log_command(logger, user_id, 'info_button')
        return

    # Обработка произвольного текста через GPT
    bot.send_message(chat_id, '...')
    try:
        reply = gpt_client.ask_with_fallback(user_text)
        bot.send_message(chat_id, reply)
        log_command(logger, user_id, 'gpt_request')
    except Exception as e:
        error_message = (
            'Извините, в настоящее время я не могу обработать ваш запрос. '
            'Попробуйте позже.'
        )
        bot.send_message(chat_id, error_message)
        log_command(logger, user_id, 'gpt_request', False, str(e))


def main():
    '''Основная функция запуска бота'''
    logger.info('Запуск KittyBot...')
    try:
        bot.polling()
    except Exception as e:
        log_error(logger, 'Ошибка при работе бота', e)
    finally:
        logger.info('Остановка KittyBot')


if __name__ == '__main__':
    main()
