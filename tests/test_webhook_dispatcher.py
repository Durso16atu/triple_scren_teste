# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
from zoneinfo import ZoneInfo
from src.webhook_dispatcher import WebhookDispatcher, TZ_SP


class TestWebhookDispatcher(unittest.TestCase):
    def setUp(self):
        self.dispatcher = WebhookDispatcher(webhook_url="https://mock.webhook.test/exec")

    @patch("requests.post")
    def test_enviar_heartbeat_sucesso(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = '{"status":"ok"}'
        mock_post.return_value = mock_response

        ts = "2026-10-07 13:00:00"
        sucesso = self.dispatcher.enviar_heartbeat(
            status_mercado="ABERTO",
            total_armados=3,
            total_ativados=1,
            timestamp_sp=ts
        )

        self.assertTrue(sucesso)
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://mock.webhook.test/exec")
        payload = kwargs.get("json", {})
        self.assertEqual(payload.get("acao"), "HEARTBEAT")
        self.assertEqual(payload.get("status_mercado"), "ABERTO")
        self.assertEqual(payload.get("total_armados"), 3)
        self.assertEqual(payload.get("total_ativados"), 1)
        self.assertEqual(payload.get("timestamp_sp"), ts)

    @patch("requests.post")
    def test_enviar_heartbeat_timestamp_default(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        sucesso = self.dispatcher.enviar_heartbeat(status_mercado="FECHADO")
        self.assertTrue(sucesso)

        payload = mock_post.call_args[1]["json"]
        self.assertEqual(payload["status_mercado"], "FECHADO")
        self.assertEqual(payload["total_armados"], 0)
        self.assertEqual(payload["total_ativados"], 0)
        self.assertIsNotNone(payload["timestamp_sp"])

    @patch("requests.post")
    def test_enviar_heartbeat_falha_http(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        sucesso = self.dispatcher.enviar_heartbeat(status_mercado="ABERTO")
        self.assertFalse(sucesso)

    @patch("requests.post")
    def test_enviar_heartbeat_exception(self, mock_post):
        mock_post.side_effect = Exception("Connection timeout")
        sucesso = self.dispatcher.enviar_heartbeat(status_mercado="ABERTO")
        self.assertFalse(sucesso)


if __name__ == "__main__":
    unittest.main()

