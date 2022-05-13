import sys
import time
import logging
from logging import StreamHandler
import os

import requests

from telegram.ext import updater

import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/12'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler()
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправка сообщения ботом."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )
    except Exception as error:
        message = f'Ошибка отправки сообщения {error}'
        logger.error(message)
    else:
        logger.info('Бот успешно отправил сообщение')


def get_api_answer(current_timestamp):
    """Запрос к API Яндекс-Практикума."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        logger.error('отсутствие подключения к API')
        raise TypeError('отсутствие подключения к API')
    return response.json()


def check_response(response):
    """Проверка API на корректность.
    Возвращение списка домашних работ.
    """
    if not isinstance(response, dict):
        raise TypeError('Формат ответа API отличается от ожидаемого')
    homework = response.get('homeworks')
    if homework is None:
        raise KeyError('Ответ API не содержит ключ \'homeworks\'')
        logger.error('Ответ API не содержит ключ \'homeworks\'')
    if not isinstance(homework, list):
        raise TypeError('Список домашних заданий не является списком')
        logger.error('Список домашних заданий не является списком')
    return homework


def parse_status(homework_list):
    """Извлечение статуса о домашней работе."""
    homework_status = homework_list['status']
    homework_name = homework_list['homework_name']
    if homework_status not in HOMEWORK_STATUSES.keys():
        logger.error('недокументированный статус домашней работы')
        raise KeyError('недокументированный статус домашней работы')
    verdict = HOMEWORK_STATUSES[homework_status]
    message = f'Изменился статус проверки работы "{homework_name}". ' \
              f'{verdict}'
    return message


def check_tokens():
    """Проверка наличия переменных окружения."""
    check = True
    if not PRACTICUM_TOKEN:
        check = False
        logger.critical(
            'отсутствие обязательной переменной окружения '
            'PRACTICUM_TOKEN во время запуска бота ')
    if not TELEGRAM_TOKEN:
        check = False
        logger.critical(
            'отсутствие обязательной переменной окружения'
            ' TELEGRAM_TOKEN во время запуска бота ')
    if not TELEGRAM_CHAT_ID:
        check = False
        logger.critical(
            'отсутствие обязательной переменной окружения'
            ' TELEGRAM_CHAT_ID во время запуска бота ')
    return check


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Программа остановлена')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = ''
    err_message = ''

    while True:
        try:
            response = get_api_answer(current_timestamp)
            homeworks_ok = check_response(response)
            if homeworks_ok:
                new_status = parse_status(homeworks_ok[0])
                if new_status != status:
                    send_message(bot, new_status)
                    status = new_status
                logger.info(f'Отправка сообщения: {new_status}')
            else:
                logger.debug('Статус работ не изменился')
            current_timestamp = response.get('current_date', current_timestamp)
            time.sleep(RETRY_TIME)
        except Exception as error:
            new_err_message = f'Сбой в работе программы {error}'
            if new_err_message != err_message:
                logger.error(new_err_message, exc_info=True)
                send_message(bot, new_err_message)
                err_message = new_err_message
            time.sleep(RETRY_TIME)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
