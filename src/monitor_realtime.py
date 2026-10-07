# -*- coding: utf-8 -*-
"""
Motor de Varredura em Tempo Real: Triple Screen Homologado B3 (Ações & Opções)
Arquitetura: Maker-Checker com Sincronização Automática via Webhook Google Sheets
"""

import time
import json
import argparse
from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
import pandas as pd
import yfinance as yf
import os
import requests

try:
    from src.webhook_dispatcher import WebhookDispatcher
except ImportError:
    from webhook_dispatcher import WebhookDispatcher

try:
    from src.black_scholes_engine import (
        BlackScholesEngine,
        strike_oficial_b3,
        obter_vencimento_mensal_alvo,
        calcular_terceira_sexta
    )
except ImportError:
    from black_scholes_engine import (
        BlackScholesEngine,
        strike_oficial_b3,
        obter_vencimento_mensal_alvo,
        calcular_terceira_sexta
    )

# Fuso horário oficial da B3
TZ_SP = ZoneInfo("America/Sao_Paulo")

# ------------------------------------------------------------------------------
# 1. PARÂMETROS E GUARDRAILS DE NEGÓCIO
# ------------------------------------------------------------------------------
HORA_INICIO_PREGAO = dtime(10, 0)
HORA_FIM_PREGAO = dtime(17, 0)
PAYOFF_ALVO = 2.0
RISCO_MAX_PCT = 0.07
RISCO_MIN_REAIS = 0.15

# URL do Webhook do Google Apps Script (Camada 2 - Google Sheets / Discord / Slack)
URL_WEBHOOK_SHEETS = os.environ.get(
    "WEBHOOK_URL",
    "https://script.google.com/macros/s/AKfycbxW6yV7HLH9C0OXDfBviiQJ-n_tFP_c-IZkahMcanyE9K_eFM5UeLfcSoRG2FQjn9mt/exec"
)

CESTA_ACOES = [
    "BOVA11.SA", "PETR4.SA", "PRIO3.SA", "VALE3.SA", "GGBR4.SA", "CSNA3.SA",
    "SUZB3.SA", "USIM5.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA", "B3SA3.SA",
    "BPAC11.SA", "WEGE3.SA", "RENT3.SA", "LREN3.SA", "MGLU3.SA", "ABEV3.SA",
    "HAPV3.SA", "CMIG4.SA", "EQTL3.SA"
]

LETRAS_CALL = {1: 'A', 2: 'B', 3: 'C', 4: 'D', 5: 'E', 6: 'F', 7: 'G', 8: 'H', 9: 'I', 10: 'J', 11: 'K', 12: 'L'}
LETRAS_PUT  = {1: 'M', 2: 'N', 3: 'O', 4: 'P', 5: 'Q', 6: 'R', 7: 'S', 8: 'T', 9: 'U', 10: 'V', 11: 'W', 12: 'X'}

@dataclass
class GuardrailsAtuariais:
    premio_min: float = 0.05
    premio_max: float = 5.00
    delta_min: float = 0.05
    delta_max: float = 0.70
    gamma_min: float = 0.005
    theta_pct_max: float = 0.15
    dte_min: int = 15

@dataclass
class PropostaTrade:
    ticker_ativo: str
    data_hora: str
    tipo_operacao: str  # CALL ou PUT
    preco_ativo: float
    gatilho_ordem: float
    stop_loss_macro: float
    alvo_2r: float
    risco_r: float
    ticker_opcao_sugerida: str
    strike_opcao: float
    premio_referencia: float
    delta_estimado: float
    gamma_estimado: float
    theta_pct_estimado: float
    dte_dias_uteis: int
    grade_opcoes: Optional[List[Dict[str, Any]]] = None

# ------------------------------------------------------------------------------
# 2. INGESTÃO E CÁLCULO DAS TELAS
# ------------------------------------------------------------------------------
def baixar_serie(ticker: str, period: str, interval: str) -> pd.DataFrame:
    df = yf.download(ticker, period=period, interval=interval, progress=False, auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df = df.dropna()
    if not df.empty and df.index.tz is not None:
        df.index = df.index.tz_convert('America/Sao_Paulo').tz_localize(None)
    return df

def calcular_indicadores_diario(df_d: pd.DataFrame) -> pd.DataFrame:
    df = df_d.copy()
    df['MME_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
    ema12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    return df

def calcular_indicadores_60m(df_60: pd.DataFrame) -> pd.DataFrame:
    df = df_60.copy()
    low_min = df['Low'].rolling(window=14).min()
    high_max = df['High'].rolling(window=14).max()
    fast_k = 100 * ((df['Close'] - low_min) / (high_max - low_min + 1e-9))
    df['Slow_K'] = fast_k.rolling(window=3).mean()
    df['Slow_D'] = df['Slow_K'].rolling(window=3).mean()
    df['Swing_High'] = df['High'].rolling(window=25).max()
    df['Swing_Low'] = df['Low'].rolling(window=25).min()
    amplitude = df['Swing_High'] - df['Swing_Low']
    df['Fibo_382'] = df['Swing_High'] - 0.382 * amplitude
    df['Fibo_618'] = df['Swing_High'] - 0.618 * amplitude
    return df

def checar_price_action(candle: pd.Series, candle_ant: Optional[pd.Series], tipo: str) -> bool:
    c = float(candle['Close'])
    o = float(candle['Open'])
    h = float(candle['High'])
    l = float(candle['Low'])
    corpo = abs(c - o)
    sombra_inf = min(c, o) - l
    sombra_sup = h - max(c, o)
    amp = h - l

    if tipo == "CALL":
        if (sombra_inf >= 1.5 * corpo) and (sombra_sup <= 0.5 * corpo) and (corpo > 0.01):
            return True
        if amp > 0.05 and (c - l) >= 0.65 * amp:
            return True
    else:  # PUT
        if (sombra_sup >= 1.5 * corpo) and (sombra_inf <= 0.5 * corpo) and (corpo > 0.01):
            return True
        if amp > 0.05 and (h - c) >= 0.65 * amp:
            return True
    return False

def determinar_ticker_opcao(ticker_ativo: str, strike_alvo: float, tipo: str) -> str:
    strike_oficial = strike_oficial_b3(strike_alvo, passo=1.0)
    raiz = ticker_ativo.replace(".SA", "")[:4]
    vencimento, _ = obter_vencimento_mensal_alvo()
    mes_venc = vencimento.month
    tabela = LETRAS_CALL if tipo.upper() == "CALL" else LETRAS_PUT
    letra = tabela.get(mes_venc, 'K' if tipo.upper() == "CALL" else 'W')
    return f"{raiz}{letra}{int(round(strike_oficial))}"

# ------------------------------------------------------------------------------
# 3. MAKER-CHECKER (CREATOR E REVIEWER)
# ------------------------------------------------------------------------------
class SubAgenteCreator:
    def __init__(self, bs_engine: Optional[BlackScholesEngine] = None):
        self.bs_engine = bs_engine or BlackScholesEngine(risk_free_rate=0.1075)

    def avaliar_ativo(self, ticker: str, df_d: pd.DataFrame, df_60: pd.DataFrame, df_15: pd.DataFrame) -> Optional[PropostaTrade]:
        df_d_ind = calcular_indicadores_diario(df_d)
        t1 = df_d_ind.iloc[-1]
        t1_ant = df_d_ind.iloc[-2]
        close_d = float(t1['Close'])
        mme200 = float(t1['MME_200'])

        if close_d > mme200:
            tipo = "CALL"
            if not ((float(t1['EMA9']) > float(t1['EMA21'])) and (float(t1['MACD_Hist']) > float(t1_ant['MACD_Hist']))):
                return None
        else:
            tipo = "PUT"
            if not ((float(t1['EMA9']) < float(t1['EMA21'])) and (float(t1['MACD_Hist']) < float(t1_ant['MACD_Hist']))):
                return None

        df_60_ind = calcular_indicadores_60m(df_60)
        ult_60 = df_60_ind.iloc[-1]
        if tipo == "CALL":
            estocastico_ok = (ult_60['Slow_K'] < 40) and (ult_60['Slow_K'] >= ult_60['Slow_D'])
            fibo_ok = (df_60['Low'].tail(4).min() <= ult_60['Fibo_382'] * 1.005)
        else:
            estocastico_ok = (ult_60['Slow_K'] > 60) and (ult_60['Slow_K'] <= ult_60['Slow_D'])
            fibo_ok = (df_60['High'].tail(4).max() >= ult_60['Fibo_618'] * 0.995)

        if not (estocastico_ok and fibo_ok):
            return None

        candle_15 = df_15.iloc[-1]
        candle_15_ant = df_15.iloc[-2] if len(df_15) >= 2 else None
        if not checar_price_action(candle_15, candle_15_ant, tipo):
            return None

        if tipo == "CALL":
            gatilho = float(candle_15['High']) + 0.01
            stop = float(df_60_ind.iloc[-1]['Swing_Low']) - 0.02
            risco = gatilho - stop
            alvo = gatilho + (PAYOFF_ALVO * risco)
        else:
            gatilho = float(candle_15['Low']) - 0.01
            stop = float(df_60_ind.iloc[-1]['Swing_High']) + 0.02
            risco = stop - gatilho
            alvo = gatilho - (PAYOFF_ALVO * risco)

        if risco < RISCO_MIN_REAIS or risco > (gatilho * RISCO_MAX_PCT):
            return None

        strike_op = strike_oficial_b3(alvo, passo=1.0)
        ticker_op = determinar_ticker_opcao(ticker, strike_op, tipo)

        # Recálculo Dinâmico dos Prêmios Black-Scholes e DTE
        _, dte_uteis = obter_vencimento_mensal_alvo()
        vol = self.bs_engine.calculate_historical_volatility(df_d['Close'])
        spot_price = float(candle_15['Close'])

        greeks = self.bs_engine.evaluate_option(
            spot=spot_price,
            strike=strike_op,
            dte_business_days=dte_uteis,
            option_type=tipo,
            sigma=vol
        )

        df_grade, _, _ = self.bs_engine.gerar_grade_5_strikes(
            ticker=ticker,
            spot=spot_price,
            sigma=vol,
            tipo=tipo
        )

        return PropostaTrade(
            ticker_ativo=ticker,
            data_hora=df_15.index[-1].strftime("%Y-%m-%d %H:%M"),
            tipo_operacao=tipo,
            preco_ativo=spot_price,
            gatilho_ordem=round(gatilho, 2),
            stop_loss_macro=round(stop, 2),
            alvo_2r=round(alvo, 2),
            risco_r=round(risco, 2),
            ticker_opcao_sugerida=ticker_op,
            strike_opcao=strike_op,
            premio_referencia=round(greeks["theoretical_price"], 2),
            delta_estimado=round(greeks["delta"], 4),
            gamma_estimado=round(greeks["gamma"], 4),
            theta_pct_estimado=round(abs(greeks["theta_pct"]), 4),
            dte_dias_uteis=dte_uteis,
            grade_opcoes=df_grade.to_dict(orient="records")
        )

class SubAgenteReviewer:
    def __init__(self, guardrails: GuardrailsAtuariais):
        self.guardrails = guardrails

    def auditar(self, p: PropostaTrade) -> Dict[str, Any]:
        vetos = []
        if not (self.guardrails.premio_min <= p.premio_referencia <= self.guardrails.premio_max):
            vetos.append("Prêmio fora da faixa")
        if not (self.guardrails.delta_min <= abs(p.delta_estimado) <= self.guardrails.delta_max):
            vetos.append("Delta fora do intervalo")
        if p.gamma_estimado < self.guardrails.gamma_min:
            vetos.append("Gamma insuficiente")
        if p.theta_pct_estimado > self.guardrails.theta_pct_max:
            vetos.append("Theta excessivo")
        if p.dte_dias_uteis < self.guardrails.dte_min:
            vetos.append("DTE insuficiente")
        return {"aprovado": len(vetos) == 0, "vetos": vetos}

# ------------------------------------------------------------------------------
# 4. ORQUESTRADOR E SINCRONIZAÇÃO
# ------------------------------------------------------------------------------
class MonitorRealtimeB3:
    def __init__(self, cesta: List[str], webhook: Optional[WebhookDispatcher] = None):
        self.cesta = cesta
        self.creator = SubAgenteCreator()
        self.reviewer = SubAgenteReviewer(GuardrailsAtuariais())
        self.webhook = webhook or WebhookDispatcher()

    def executar_ciclo(self):
        agora_sp = datetime.now(TZ_SP)
        ts_formatado = agora_sp.strftime("%Y-%m-%d %H:%M:%S")

        eh_dia_util = agora_sp.weekday() < 5
        eh_horario_pregao = dtime(10, 0) <= agora_sp.time() <= dtime(17, 0)
        status_str = "ABERTO" if (eh_dia_util and eh_horario_pregao) else "FECHADO"

        print(f"\n[{ts_formatado}] Iniciando varredura em {len(self.cesta)} ativos B3 (Mercado: {status_str})...")
        oportunidades = []
        grades_ativas = {}
        venc_alvo, dte_uteis = obter_vencimento_mensal_alvo()

        for ticker in self.cesta:
            try:
                df_d = baixar_serie(ticker, "60d", "1d")
                df_60 = baixar_serie(ticker, "10d", "60m")
                df_15 = baixar_serie(ticker, "5d", "15m")
                if df_d.empty or df_60.empty or df_15.empty:
                    continue

                # Recalcula a grade de opções com preços atuais do yfinance em cada ciclo
                spot_ticker = float(df_15['Close'].iloc[-1])
                vol_ticker = self.creator.bs_engine.calculate_historical_volatility(df_d['Close'])
                df_g, _, _ = self.creator.bs_engine.gerar_grade_5_strikes(
                    ticker=ticker,
                    spot=spot_ticker,
                    sigma=vol_ticker,
                    tipo="CALL"
                )
                grades_ativas[ticker] = df_g.to_dict(orient="records")

                p = self.creator.avaliar_ativo(ticker, df_d, df_60, df_15)
                if p and self.reviewer.auditar(p)["aprovado"]:
                    oportunidades.append(p)
                    print(f"  -> SINAL CONFIRMADO: {p.ticker_ativo} ({p.tipo_operacao}) | Opção: {p.ticker_opcao_sugerida} | Prêmio: R$ {p.premio_referencia:.2f}")
            except Exception as e:
                continue

        total_armados = len(oportunidades)
        total_ativados = sum(
            1 for p in oportunidades
            if (p.tipo_operacao == "CALL" and p.preco_ativo >= p.gatilho_ordem)
            or (p.tipo_operacao == "PUT" and p.preco_ativo <= p.gatilho_ordem)
        )

        grade_opcoes_ciclo = []
        if oportunidades and oportunidades[0].grade_opcoes:
            grade_opcoes_ciclo = oportunidades[0].grade_opcoes
        elif grades_ativas:
            primeiro_ticker = next((t for t in ["ITUB4.SA", "PETR4.SA", "BOVA11.SA"] if t in grades_ativas), next(iter(grades_ativas.keys())))
            grade_opcoes_ciclo = grades_ativas[primeiro_ticker]

        # Monta o payload estruturado (Contrato de Dados da Etapa 1)
        payload = {
            "metadata": {
                "pipeline_version": "1.3.0",
                "timestamp_execucao": agora_sp.isoformat(),
                "total_cesta": len(self.cesta),
                "total_sinais": len(oportunidades),
                "status_mercado": status_str,
                "vencimento_alvo": venc_alvo.strftime("%d/%m/%Y"),
                "dte_dias_uteis": dte_uteis
            },
            "sinais_ativos": [asdict(p) for p in oportunidades],
            "grade_opcoes": grade_opcoes_ciclo,
            "grades_por_ativo": grades_ativas
        }

        # 1. Salva cópia local (metricas_resumo.json)
        with open("metricas_resumo.json", "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        # 2. Sincroniza via Webhook com o Google Sheets em cada ciclo
        self.sincronizar_google_sheets(payload)

        # 3. Telemetria e Heartbeat garantido ao final de toda execução
        self.webhook.enviar_heartbeat(status_str, total_armados, total_ativados, ts_formatado)

    def sincronizar_google_sheets(self, payload: dict):
        try:
            print("[*] Enviando dados para o Google Sheets via Webhook...")
            target_url = getattr(self.webhook, "webhook_url", None) or URL_WEBHOOK_SHEETS
            response = requests.post(target_url, json=payload, timeout=15)
            if response.status_code == 200:
                print(f"[OK] Sincronização Google Sheets concluída com sucesso! ({response.text})")
            else:
                print(f"[!] Sincronização Google Sheets retornou código HTTP {response.status_code}")
        except Exception as e:
            print(f"[ERRO SYNC] Falha ao enviar para o Google Sheets: {e}")

if __name__ == "__main__":
    monitor = MonitorRealtimeB3(CESTA_ACOES)
    monitor.executar_ciclo()
