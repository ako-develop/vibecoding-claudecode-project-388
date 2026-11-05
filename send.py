"""Send plain text to Telegram using only the Python standard library."""
import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib import error, request


class SendError(Exception):
    """Safe diagnostic without tokens, request URLs or response bodies."""


def credentials(env_path=None):
    values = {}
    path = Path(env_path) if env_path is not None else Path(__file__).resolve().with_name('.env')
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if line.startswith('export '):
                line = line[7:]
            key, sep, value = line.partition('=')
            key, value = key.strip(), value.strip()
            if sep and key in ('TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'):
                if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                    value = value[1:-1]
                values[key] = value
    token = os.environ.get('TELEGRAM_BOT_TOKEN', values.get('TELEGRAM_BOT_TOKEN', '')).strip()
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', values.get('TELEGRAM_CHAT_ID', '')).strip()
    if not token or not chat_id:
        raise SendError('Заполни TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в .env или переменных окружения.')
    if not re.fullmatch(r'\d+:[A-Za-z0-9_-]+', token):
        raise SendError('Неверный формат TELEGRAM_BOT_TOKEN.')
    if not re.fullmatch(r'-?\d+|@[A-Za-z0-9_]+', chat_id):
        raise SendError('Неверный формат TELEGRAM_CHAT_ID.')
    return token, chat_id


def api_failure(code):
    messages = {
        400: 'Telegram отклонил запрос: проверь chat id и напиши боту первым.',
        401: 'Telegram отклонил токен бота.',
        403: 'Бот не может писать в этот чат: проверь блокировку и права.',
        429: 'Превышен лимит Telegram. Автоматического повтора не было.',
    }
    return SendError(messages.get(code, 'Ошибка Telegram API. Автоматического повтора не было.'))


def send(text, token, chat_id):
    if not text.strip() or len(text) > 4096:
        raise SendError('Текст должен содержать от 1 до 4096 символов; разбей длинную сводку на части.')
    body = json.dumps({'chat_id': chat_id, 'text': text,
                       'link_preview_options': {'is_disabled': True}}, ensure_ascii=False).encode('utf-8')
    req = request.Request('https://api.telegram.org/bot' + token + '/sendMessage', data=body,
                          headers={'Content-Type': 'application/json; charset=utf-8'}, method='POST')
    try:
        with request.urlopen(req, timeout=20) as response:
            payload = json.load(response)
    except error.HTTPError as exc:
        raise api_failure(exc.code) from None
    except (error.URLError, TimeoutError, OSError, ValueError):
        raise SendError('Статус доставки неизвестен: ошибка сети или ответа. Проверь чат перед повторной отправкой.') from None
    if not isinstance(payload, dict) or payload.get('ok') is not True:
        raise api_failure(payload.get('error_code') if isinstance(payload, dict) else None)
    result = payload.get('result')
    if not isinstance(result, dict) or not isinstance(result.get('message_id'), int):
        raise SendError('Telegram вернул неожиданный ответ. Проверь чат перед повторной отправкой.')
    return result['message_id']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('text', nargs='?', help='Текст сообщения')
    group.add_argument('--file', type=Path, help='UTF-8 файл со сводкой')
    args = parser.parse_args(argv)
    try:
        text = args.file.read_text(encoding='utf-8') if args.file else args.text
        token, chat_id = credentials()
        send(text, token, chat_id)
    except SendError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except (OSError, UnicodeError):
        print('Не удалось прочитать файл настроек или сообщения.', file=sys.stderr)
        return 1
    print('Отправлено.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
