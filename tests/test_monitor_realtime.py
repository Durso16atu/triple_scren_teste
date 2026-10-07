# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
from src.monitor_realtime import MonitorRealtimeB3, TZ_SP
from src.webhook_dispatcher import WebhookDispatcher


class TestMonitorRealtime(unittest.TestCase):
    def test_timezone_sp(self):
        self.assertEqual(str(TZ_SP), "America/Sao_Paulo")

    def test_status_mercado_calculo(self):
        # Quarta-feira (weekday=2) às 14:30 SP -> ABERTO
        dt_aberto = datetime(2026, 10, 7, 14, 30, tzinfo=TZ_SP)
        eh_dia_util = dt_aberto.weekday() < 5
        eh_horario = dtime(10, 0) <= dt_aberto.time() <= dtime(17, 0)
        status = "ABERTO" if (eh_dia_util and eh_horario) else "FECHADO"
        self.assertEqual(status, "ABERTO")

        # Quarta-feira (weekday=2) às 08:30 SP -> FECHADO
        dt_antes = datetime(2026, 10, 7, 8, 30, tzinfo=TZ_SP)
        eh_dia_util = dt_antes.weekday() < 5
        eh_horario = dtime(10, 0) <= dt_antes.time() <= dtime(17, 0)
        status = "ABERTO" if (eh_dia_util and eh_horario) else "FECHADO"
        self.assertEqual(status, "FECHADO")

        # Quarta-feira (weekday=2) às 17:30 SP -> FECHADO
        dt_depois = datetime(2026, 10, 7, 17, 30, tzinfo=TZ_SP)
        eh_dia_util = dt_depois.weekday() < 5
        eh_horario = dtime(10, 0) <= dt_depois.time() <= dtime(17, 0)
        status = "ABERTO" if (eh_dia_util and eh_horario) else "FECHADO"
        self.assertEqual(status, "FECHADO")

        # Sábado (weekday=5) às 14:00 SP -> FECHADO
        dt_sabado = datetime(2026, 10, 10, 14, 0, tzinfo=TZ_SP)
        eh_dia_util = dt_sabado.weekday() < 5
        eh_horario = dtime(10, 0) <= dt_sabado.time() <= dtime(17, 0)
        status = "ABERTO" if (eh_dia_util and eh_horario) else "FECHADO"
        self.assertEqual(status, "FECHADO")

    @patch("src.monitor_realtime.baixar_serie")
    def test_executar_ciclo_chama_heartbeat_sem_sinais(self, mock_baixar):
        # Simula download vazio (sem oportunidades)
        mock_baixar.return_value = MagicMock(empty=True)

        mock_webhook = MagicMock(spec=WebhookDispatcher)
        monitor = MonitorRealtimeB3(cesta=["PETR4.SA"], webhook=mock_webhook)

        monitor.executar_ciclo()

        # Garante que enviar_heartbeat foi chamado com os 4 argumentos
        mock_webhook.enviar_heartbeat.assert_called_once()
        args, kwargs = mock_webhook.enviar_heartbeat.call_args
        status_mercado, total_armados, total_ativados, ts_formatado = args

        self.assertIn(status_mercado, ["ABERTO", "FECHADO"])
        self.assertEqual(total_armados, 0)
        self.assertEqual(total_ativados, 0)
        self.assertRegex(ts_formatado, r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$")


    @patch("src.monitor_realtime.requests.post")
    @patch("src.monitor_realtime.baixar_serie")
    def test_executar_ciclo_recalcula_grade_opcoes(self, mock_baixar, mock_post):
        # Simula DataFrame válido de 15m e diário
        import pandas as pd
        dates = pd.date_range("2026-10-01", periods=10, freq="D")
        df_dummy = pd.DataFrame({
            "Open": [40.0] * 10,
            "High": [41.0] * 10,
            "Low": [39.0] * 10,
            "Close": [40.0] * 10,
            "Volume": [1000] * 10
        }, index=dates)
        mock_baixar.return_value = df_dummy

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_post.return_value = mock_response

        mock_webhook = MagicMock(spec=WebhookDispatcher)
        mock_webhook.webhook_url = "https://mock.test"
        monitor = MonitorRealtimeB3(cesta=["ITUB4.SA"], webhook=mock_webhook)

        monitor.executar_ciclo()

        # Garante envio para Webhook com grade de opções calculada
        mock_post.assert_called_once()
        sent_payload = mock_post.call_args[1]["json"]
        self.assertIn("grade_opcoes", sent_payload)
        self.assertIn("grades_por_ativo", sent_payload)
        self.assertIn("ITUB4.SA", sent_payload["grades_por_ativo"])
        grade_itub = sent_payload["grades_por_ativo"]["ITUB4.SA"]
        self.assertEqual(len(grade_itub), 5)
        self.assertEqual(grade_itub[0]["Moneyness"], "ITM (Dentro)")
        self.assertEqual(grade_itub[2]["Moneyness"], "ATM (No Dinheiro)")
        self.assertEqual(grade_itub[3]["Moneyness"], "OTM (Fora)")


if __name__ == "__main__":
    unittest.main()

