import logging
import requests
from typing import Optional


class ImageAPI:
    '''Класс для работы с API изображений'''

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.urls = {
            'cat': 'https://api.thecatapi.com/v1/images/search',
            'dog': 'https://api.thedogapi.com/v1/images/search'
        }

    def get_image_url(self, animal_type: str) -> Optional[str]:
        '''
        Получение URL изображения животного
        animal_type: 'cat' или 'dog'
        '''
        primary_url = self.urls[animal_type]
        backup_url = (
            self.urls['dog'] if animal_type == 'cat' else self.urls['cat']
        )
        animal_name_ru = 'котов' if animal_type == 'cat' else 'собак'
        data = None

        try:
            response = requests.get(primary_url)
            response.raise_for_status()
            data = response.json()
            self.logger.info(f'Успешный запрос к API {animal_name_ru}')
        except Exception as error:
            self.logger.error(
                f'Ошибка при запросе к основному API {animal_name_ru}: {error}'
            )
            try:
                response = requests.get(backup_url)
                response.raise_for_status()
                data = response.json()
                self.logger.info(
                    f'Успешный запрос к резервному API {animal_name_ru}'
                )
            except Exception as error2:
                self.logger.error(
                    f'Ошибка при запросе к резервному API '
                    f'{animal_name_ru}: {error2}'
                )
                return None

        if data and isinstance(data, list) and len(data) > 0:
            image_url = data[0].get('url')
            return image_url if image_url else None

        return None

    def get_cat_image(self) -> Optional[str]:
        '''Получение URL изображения кота'''
        return self.get_image_url('cat')

    def get_dog_image(self) -> Optional[str]:
        '''Получение URL изображения собаки'''
        return self.get_image_url('dog')


# Глобальный экземпляр API
image_api = ImageAPI()
