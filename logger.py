import logging
import os
from datetime import datetime
from typing import Optional


def setup_logging():
    '''Настройка логирования в файл'''
    log_dir = 'logs'
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    log_file = os.path.join(
        log_dir,
        f'kittybot_{datetime.now().strftime("%Y%m%d")}.log'
    )

    # Настройка root logger
    logging.basicConfig(
        level=logging.INFO,
        filename=log_file,
        encoding='utf-8',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )

    # Также выводим в консоль для удобства разработки
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)

    logging.getLogger().addHandler(console_handler)

    return logging.getLogger(__name__)


def log_command(
        logger,
        user_id: int,
        command: str,
        success: bool = True,
        error: Optional[str] = None
        ):
    '''Логирование команд пользователя'''
    log_message = f'User {user_id}: {command}'
    if not success:
        log_message += f' - ERROR: {error}'
        logger.error(log_message)
    else:
        logger.info(log_message)


def log_error(logger, context: str, error: Exception):
    '''Логирование ошибок'''
    logger.error(f'{context}: {str(error)}')
