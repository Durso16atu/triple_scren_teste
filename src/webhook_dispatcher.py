# -*- coding: utf-8 -*-
"""
Módulo de despacho de webhooks para o ecossistema B3 Triple Screen.
Suporta telemetria de heartbeat, sincronização de dados e alertas de mercado.
"""

import os
import requests
from datetime import datetime
from typing import Optional, Dict, Any
from zoneinfo import ZoneInfo

TZ_SP = ZoneInfo("America/Sao_Paulo")

URL_WEBHOOK_PADRAO = (
    "https://script.google.com/macros/s/AKfycbxW6yV7HLH9C0OXDfBviiQJ-n_tFP_c-IZkahMcanyE9K_eFM5UeLfcSoRG2FQjn9mt/exec"
)


class WebhookDispatcher:
    """
    Despachante de eventos e telemetria para Webhook (Google Sheets, Discord, Slack, etc.).
    """

    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.environ.get("WEBHOOK_URL", URL_WEBHOOK_PADRAO)

    def enviar_heartbeat(
        self,
        status_mercado: str,
        total_armados: int = 0,
        total_ativados: int = 0,
        timestamp_sp: Optional[str] = None
    ) -> bool:
        """
        Despacha uma mensagem de telemetria/heartbeat com o status atual do pregão via POST.
        Garante a atualização do status do pregão e timestamp mesmo sem novos sinais no ciclo.
        """
        if timestamp_sp is None:
            timestamp_sp = datetime.now(TZ_SP).strftime("%Y-%m-%d %H:%M:%S")

        payload = {
            "acao": "HEARTBEAT",
            "action": "HEARTBEAT",
            "status_mercado": status_mercado,
            "total_armados": total_armados,
            "total_ativados": total_ativados,
            "timestamp_sp": timestamp_sp,
            "timestamp": timestamp_sp,
            "kpis": {
                "Status do Mercado": status_mercado,
                "Total Armados": total_armados,
                "Total Ativados": total_ativados,
                "Ultima Atualizacao": timestamp_sp
            }
        }

        if not self.webhook_url:
            print("[!] WebhookDispatcher: URL não configurada.")
            return False

        try:
            print(f"[*] Despachando HEARTBEAT ({status_mercado} | Armados: {total_armados} | Ativados: {total_ativados}) para o Webhook...")
            response = requests.post(self.webhook_url, json=payload, timeout=15)
            if 200 <= response.status_code < 300:
                print(f"[OK] Heartbeat enviado com sucesso! Status HTTP: {response.status_code}")
                return True
            else:
                print(f"[!] Heartbeat falhou com status HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"[ERRO] Falha ao despachar Heartbeat: {e}")
            return False

    def enviar_payload(self, payload: Dict[str, Any]) -> bool:
        """
        Envia um payload arbitrário para o Webhook.
        """
        if not self.webhook_url:
            print("[!] WebhookDispatcher: URL não configurada.")
            return False

        try:
            print("[*] Enviando payload para o Webhook...")
            response = requests.post(self.webhook_url, json=payload, timeout=15)
            if 200 <= response.status_code < 300:
                print(f"[OK] Payload enviado com sucesso! Status HTTP: {response.status_code}")
                return True
            else:
                print(f"[!] Envio retornou código HTTP {response.status_code}: {response.text}")
                return False
        except Exception as e:
            print(f"[ERRO] Falha ao enviar payload para o Webhook: {e}")
            return False
