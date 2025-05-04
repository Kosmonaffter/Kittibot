import requests

from telebot import TeleBot


bot = TeleBot(token='7906543500:AAEUmg2HrDpAUzPDDimoElICh1MzwKoCCMM')

URL = 'https://api.thecatapi.com/v1/images/search'

response = requests.get(URL).json()
chat_id = 1367577399
random_cat_url = response[0].get('url')

bot.send_photo(chat_id, random_cat_url)

# chat_id = 1367577399

# text = 'Вам телеграмма!'

# bot.send_message(chat_id, text)

# bot.send_photo(chat_id, URL)
