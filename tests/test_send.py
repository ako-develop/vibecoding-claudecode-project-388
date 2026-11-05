"""No real Telegram requests: exercise payloads, settings and failure handling."""
import contextlib
import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib import error

spec = importlib.util.spec_from_file_location('telegram_send', Path(__file__).resolve().parents[1] / 'send.py')
sender = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sender)
TOKEN = '123:TEST_TOKEN'


class SendTests(unittest.TestCase):
    def test_env_precedence_and_quotes(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = Path(tmp) / '.env'
            env.write_text('TELEGRAM_BOT_TOKEN="123:FILE_TOKEN"\nTELEGRAM_CHAT_ID=42\n', encoding='utf-8')
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(sender.credentials(env), ('123:FILE_TOKEN', '42'))
            with patch.dict(os.environ, {'TELEGRAM_BOT_TOKEN': TOKEN}, clear=True):
                self.assertEqual(sender.credentials(env), (TOKEN, '42'))

    def test_success_unicode_plain_text_and_cli(self):
        response = io.StringIO(json.dumps({'ok': True, 'result': {'message_id': 7}}))
        with patch.object(sender.request, 'urlopen', return_value=response) as network:
            self.assertEqual(sender.send('Цена <100> ₽\nскидка & рассрочка', TOKEN, '42'), 7)
        req = network.call_args.args[0]
        payload = json.loads(req.data)
        self.assertEqual(req.method, 'POST')
        self.assertEqual(payload['text'], 'Цена <100> ₽\nскидка & рассрочка')
        self.assertNotIn('parse_mode', payload)
        with patch.object(sender, 'credentials', return_value=(TOKEN, '42')), patch.object(sender, 'send') as send, contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(sender.main(['тест']), 0)
            send.assert_called_once_with('тест', TOKEN, '42')
            self.assertEqual(out.getvalue(), 'Отправлено.\n')

    def test_http_and_api_error_without_token_leak(self):
        failure = error.HTTPError('https://api.telegram.org/bot' + TOKEN, 403, TOKEN, {}, None)
        with patch.object(sender.request, 'urlopen', side_effect=failure):
            with self.assertRaises(sender.SendError) as exc:
                sender.send('тест', TOKEN, '42')
        self.assertNotIn(TOKEN, str(exc.exception))
        with patch.object(sender.request, 'urlopen', return_value=io.StringIO('{"ok":false,"error_code":401}')):
            with self.assertRaises(sender.SendError):
                sender.send('тест', TOKEN, '42')

    def test_network_unknown_and_no_retry(self):
        with patch.object(sender.request, 'urlopen', side_effect=error.URLError(TOKEN)) as network:
            with self.assertRaises(sender.SendError) as exc:
                sender.send('тест', TOKEN, '42')
            self.assertIn('неизвестен', str(exc.exception))
            self.assertNotIn(TOKEN, str(exc.exception))
            self.assertEqual(network.call_count, 1)

    def test_missing_credentials_and_invalid_messages(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(sender.SendError):
                sender.credentials('/nonexistent/tracker.env')
        with patch.object(sender.request, 'urlopen') as network:
            for text in ['', '   ', 'x' * 4097]:
                with self.assertRaises(sender.SendError):
                    sender.send(text, TOKEN, '42')
            network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
