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
TELEGRAM_TOKEN2 = os.getenv('TELEGRAM_TOKEN2')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = StreamHandler()
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)


def send_message(bot, message):
    """Отправка сообщения ботом."""
    if not bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=message
    ):
        logger.error('Ошибка отправки сообщения')
        send_message(bot, 'Ошибка отправки сообщения')
    else:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message
        )


def get_api_answer(current_timestamp):
    """Запрос к API Яндекс-Практикума."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework = requests.get(ENDPOINT, headers=HEADERS, params=params)
    response = homework.json()
    return response


def check_response(response):
    """Проверка API на корректность.
    Возвращение списка домашних работ.
    """
    if not response:
        logger.error('отсутствие ожидаемых ключей в ответе API')
        send_message(bot, 'отсутствие ожидаемых ключей в ответе API')
    else:
        homework = response.get('homeworks')[0]
        return homework


def parse_status(homework):
    """Извлечение статуса о домашней работе."""
    homework_name = homework['lesson_name']
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    message = f'Изменился статус проверки работы "{homework_name}". {verdict}'
    if homework['status'] is None:
        logger.error('недокументированный статус домашней работы')
        send_message(bot, 'недокументированный статус домашней работы')
    else:
        return message


def check_tokens(prtoken, tlgtoken, tlgchatid):
    """Проверка наличия переменных окружения."""
    if not prtoken:
        logger.critical(
            'отсутствие обязательной переменной окружения '
            'PRACTICUM_TOKEN во время запуска бота ')
    elif not tlgtoken:
        logger.critical(
            'отсутствие обязательной переменной окружения'
            ' TELEGRAM_TOKEN во время запуска бота ')
    elif not tlgchatid:
        logger.critical(
            'отсутствие обязательной переменной окружения'
            ' TELEGRAM_CHAT_ID во время запуска бота ')
    else:
        return True


def main():
    """Основная логика работы бота."""


if check_tokens(PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID):
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status = []
    while True:
        try:
            get_api_answer(current_timestamp)
        except Exception as error:
            logger.error(f'Ошибка при запросе к основному API {error}')
            send_message(bot, f'Ошибка при запросе к основному API {error}')
            time.sleep(RETRY_TIME)
        else:
            response = get_api_answer(current_timestamp)
            status.append(parse_status(check_response(response)))
            if len(status) == 1:
                send_message(bot, status[0])
                logger.info(f'Отправка сообщения: {status[0]}')
            if len(status) == 2:
                if status[0] != status[1]:
                    send_message(bot, status[1])
                    logger.info(f'Отправка сообщения: {status[0]}')
                    break
                else:
                    logger.debug('отсутствие в ответе новых статусов')
                    status.pop(1)
            time.sleep(RETRY_TIME)
    updater.start_polling()
    updater.idle()
    print(current_timestamp)

if __name__ == '__main__':
    main()
