import logging
import requests
from openai import OpenAI
from typing import List, Optional


class GPTClient:
    '''Клиент для работы с GPT провайдерами'''

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.available_models: List[str] = []
        self.setup_clients()

    def setup_clients(self):
        '''Инициализация клиентов GPT провайдеров'''
        # Настройка DeepSeek
        try:
            self.deepseek_client = OpenAI(
                api_key='sk-db2a90605e864a67ad5bdf23c5e8fab4',
                base_url='https://api.deepseek.com'
            )
            self.logger.info('DeepSeek клиент инициализирован')
        except Exception as e:
            self.logger.error(f'Ошибка инициализации DeepSeek: {e}')
            self.deepseek_client = None

        # Настройка Ollama
        self.setup_ollama()

    def check_ollama_server(self) -> bool:
        '''Проверка доступности сервера Ollama'''
        try:
            response = requests.get(
                'http://localhost:11434/api/tags',
                timeout=10
            )
            if response.status_code == 200:
                self.logger.info('Сервер Ollama доступен')
                return True
            else:
                self.logger.warning(
                    f'Сервер Ollama ответил с кодом: {response.status_code}'
                )
                return False
        except requests.exceptions.ConnectionError:
            self.logger.warning('Не удалось подключиться к серверу Ollama')
            return False
        except Exception as e:
            self.logger.warning(f'Ошибка при проверке сервера Ollama: {e}')
            return False

    def setup_ollama(self):
        '''Настройка и проверка доступности Ollama'''
        # Сначала проверяем доступность сервера
        if not self.check_ollama_server():
            self.logger.warning(
                'Сервер Ollama недоступен. '
                'Убедитесь что "ollama serve" запущен.'
            )
            self.ollama_available = False
            self.available_models = []
            return

        try:
            # Получаем список всех доступных моделей через прямой HTTP запрос
            response = requests.get(
                'http://localhost:11434/api/tags',
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                self.available_models = [
                    model['name'] for model in data.get('models', [])
                ]

                if self.available_models:
                    self.ollama_available = True
                    self.logger.info(
                        f'Ollama доступен. '
                        f'Модели: {", ".join(self.available_models)}'
                    )

                    # Рекомендуем лучшую модель
                    best_model = self.get_ollama_model()
                    if best_model:
                        self.logger.info(f'Рекомендуемая модель: {best_model}')
                else:
                    self.ollama_available = False
                    self.logger.warning(
                        'Ollama доступен, но нет скачанных моделей'
                    )
            else:
                self.ollama_available = False
                self.logger.warning(
                    f'Не удалось получить список моделей. '
                    f'Код ответа: {response.status_code}'
                )

        except Exception as e:
            self.logger.error(f'Ошибка при настройке Ollama: {e}')
            self.ollama_available = False
            self.available_models = []

    def get_ollama_model(self) -> Optional[str]:
        '''Получение лучшей доступной модели Ollama'''
        if not self.available_models:
            return None

        # Приоритет моделей (от лучших к хорошим)
        preferred_models = [
            'gemma2:27b', 'gemma3:27b',        # Самые мощные
            'gemma2:9b', 'gemma3:12b',         # Хороший баланс
            'llama3:70b', 'llama3:8b',         # Llama 3
            'mistral', 'gemma:7b',             # Легкие модели
            'llama2', 'tinyllama'              # Базовые
        ]

        # Ищем точное совпадение
        for model in preferred_models:
            if model in self.available_models:
                return model

        # Ищем частичное совпадение
        for preferred in preferred_models:
            base_name = (
                preferred.split(':')[0] if ':' in preferred else preferred
            )
            for available in self.available_models:
                if base_name in available:
                    self.logger.info(
                        f'Найдена модель по базовому имени: {available}'
                    )
                    return available

        # Если ничего не нашли, берем первую доступную
        return self.available_models[0]

    def ask_deepseek(self, message_text: str) -> str:
        '''Запрос к DeepSeek API'''
        if not self.deepseek_client:
            raise Exception('DeepSeek клиент не инициализирован')

        try:
            response = self.deepseek_client.chat.completions.create(
                model='deepseek-chat',
                messages=[
                    {
                        'role': 'system',
                        'content': 'Ты полезный ассистент. '
                        'Отвечай на русском языке.'
                    },
                    {'role': 'user', 'content': message_text},
                ],
                stream=False
            )

            result = response.choices[0].message.content
            if not result:
                raise Exception('Пустой ответ от DeepSeek API')

            return result

        except Exception as e:
            # Если ошибка связана с балансом, помечаем DeepSeek как недоступный
            if '402' in str(e) or 'balance' in str(e).lower():
                self.logger.error('DeepSeek недоступен: недостаточно средств')
                self.deepseek_client = None
            raise e

    def ask_ollama(self, message_text: str) -> str:
        '''Запрос к локальной Ollama'''
        if not self.ollama_available:
            raise Exception('Ollama недоступен')

        model = self.get_ollama_model()
        if not model:
            raise Exception('Нет доступных моделей Ollama')

        self.logger.info(f'Используем модель Ollama: {model}')

        try:
            # Используем прямой HTTP запрос для большей надежности
            response = requests.post(
                'http://localhost:11434/api/chat',
                json={
                    'model': model,
                    'messages': [
                        {
                            'role': 'system',
                            'content': 'Ты полезный ассистент. '
                            'Отвечай на русском языке кратко и по делу.'
                        },
                        {'role': 'user', 'content': message_text}
                    ],
                    'stream': False
                },
                timeout=60
            )

            if response.status_code == 200:
                data = response.json()
                result = data['message']['content']
                if not result:
                    raise Exception('Пустой ответ от Ollama')
                return result
            else:
                raise Exception(
                    f'Ошибка Ollama API: {response.status_code}'
                )

        except Exception as e:
            self.logger.error(f'Ошибка при запросе к Ollama: {e}')
            raise e

    def ask_with_fallback(self, message_text: str) -> str:
        '''
        Запрос к GPT с резервными провайдерами
        Пробует DeepSeek -> Ollama -> возвращает ошибку
        '''
        errors = []

        # Попытка 1: DeepSeek
        if self.deepseek_client:
            try:
                self.logger.info('Попытка запроса к DeepSeek API')
                response = self.ask_deepseek(message_text)
                self.logger.info('Успешный запрос к DeepSeek API')
                return response
            except Exception as e:
                error_msg = f'DeepSeek: {str(e)}'
                errors.append(error_msg)
                self.logger.error(f'Ошибка DeepSeek: {e}')

        # Попытка 2: Ollama
        if self.ollama_available:
            try:
                self.logger.info('Попытка запроса к Ollama')
                response = self.ask_ollama(message_text)
                self.logger.info('Успешный запрос к Ollama')
                return response
            except Exception as e:
                error_msg = f'Ollama: {str(e)}'
                errors.append(error_msg)
                self.logger.error(f'Ошибка Ollama: {e}')

        # Все провайдеры не сработали
        error_msg = 'Все GPT провайдеры недоступны. '
        if errors:
            error_msg += 'Ошибки: ' + '; '.join(errors)

        self.logger.error(error_msg)
        raise Exception(error_msg)


# Глобальный экземпляр клиента
gpt_client = GPTClient()
