import logging


logging.basicConfig(
    level=logging.INFO,
    filename='main.log',
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s',
    encoding="utf-8"
)


logging.info('Сообщение отправлено')
