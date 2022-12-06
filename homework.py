import os
import sys
import time
from http import HTTPStatus

import dotenv
import requests
import logging

import telegram

import exceptions
from tests.conftest import BASE_DIR

dotenv.load_dotenv('.env')

PRACTICUM_TOKEN = os.environ['PRACTICUM_TOKEN']
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяем доступность токенов в окружении проекта."""
    return all((TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Отправка сообщения в Telegram чат."""
    try:
        logging.debug('Пытаюсь отправить сообщение')
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
        logging.debug(f'Сообщение отправлено {message}')
    except Exception as error:
        logging.error(f'Ошибка {error}')
        raise exceptions.TelegramMessageSendError(
            f'Упс, не удалось отправить сообщение {error}'
        )


def get_api_answer(timestamp):
    """Запрос к эндпоинту API-сервиса."""
    timestamp = int(time.time())
    params_request_api = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    message = (
        'Начало запроса к API. Запрос: {url}, {headers}, {params}.'
    ).format(**params_request_api)
    logging.info(message)
    try:
        response = requests.get(**params_request_api)
        if response.status_code != HTTPStatus.OK:
            raise exceptions.ConnectionError(
                f'Ответ API не возвращает 200. '
                f'Код ответа: {response.status_code}. '
                f'Причина: {response.reason}. '
                f'Текст: {response.text}.'
            )
        return response.json()
    except Exception as error:
        message = (
            'API не возвращает 200. Запрос: {url}, {headers}, {params}.'
        ).format(**params_request_api)
        raise exceptions.ConnectionError(message, error)


def check_response(response):
    """Проверка ответа API на корректность."""
    logging.debug('Начало проверки')
    try:
        homework = response['homeworks']
    except KeyError as error:
        logging.error(
            f'Ошибка доступа по ключу homeworks {error}'
        )
    if not isinstance(homework, list):
        logging.error('homework не список')
        raise TypeError(
            'В списке домашних работ неверный тип данных'
        )
    return homework


def parse_status(homework):
    """Распарсить ответ."""
    if 'homework_name' not in homework:
        raise KeyError(
            'В ответе отсутсвует ключ homework_name'
        )
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы - {homework_status}')
    return ('Изменился статус проверки работы "{homework_name}" {verdict}'
            ).format(
        homework_name=homework_name,
        verdict=HOMEWORK_VERDICTS[homework_status]
    )


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    if not check_tokens():
        logging.critical(
            'Отсутствие обязательных переменных окружения'
        )
        sys.exit('Бот завершил работу')

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                status = parse_status(homeworks[0])
                send_message(bot, status)
            timestamp = response['current_date']
        except exceptions.TelegramMessageSendError:
            logging.error('Ошибка отправки сообщения в Telegram')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        filename='homework.log',
        format='%(asctime)s, %(levelname)s, %(message)s'
    )
    handler = (
        logging.FileHandler(f'{BASE_DIR}/output.log'),
        logging.StreamHandler(sys.stdout)
    )
    main()
