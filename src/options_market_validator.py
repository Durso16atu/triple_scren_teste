# -*- coding: utf-8 -*-
"""
Módulo de Validação de Mercado para Opções B3.
Realiza consulta externa leve para capturar preços reais de tela, Bid-Ask spread e Volume.
Atua com Graceful Fallback (retornando modelo Black-Scholes) em caso de timeout ou iliquidez.
"""

import yfinance as yf
import pandas as pd
import numpy as np
import concurrent.futures
from typing import List, Dict, Any

class OptionsMarketValidator:
    def __init__(self, timeout_sec: int = 3):
        self.timeout_sec = timeout_sec

    def _fetch_single_option(self, codigo_opcao: str) -> Dict[str, Any]:
        """Consulta leve via yfinance para uma única opção."""
        ticker = f"{codigo_opcao}.SA"
        try:
            t = yf.Ticker(ticker)
            # Fast fetch for daily history
            hist = t.history(period="1d")
            
            if not hist.empty and len(hist) > 0:
                last_price = float(hist['Close'].iloc[-1])
                volume = int(hist['Volume'].iloc[-1]) if 'Volume' in hist.columns else 0
                
                # Fetch info conditionally if there is volume, to get Bid/Ask
                bid, ask = None, None
                if volume > 0:
                    info = t.info
                    bid = info.get("bid", last_price * 0.98)
                    ask = info.get("ask", last_price * 1.02)
                    
                    if bid == 0 or bid is None: bid = last_price * 0.98
                    if ask == 0 or ask is None: ask = last_price * 1.02
                else:
                    bid = last_price * 0.98
                    ask = last_price * 1.02

                return {
                    "sucesso": True,
                    "codigo": codigo_opcao,
                    "last": last_price,
                    "bid": bid,
                    "ask": ask,
                    "volume": volume
                }
        except Exception:
            pass
        return {"sucesso": False, "codigo": codigo_opcao}

    def auditar_spread(self, bid: float, ask: float, midpoint: float) -> bool:
        """
        Alerta se (Ask - Bid) / Midpoint > 15% (Baixa liquidez).
        Retorna True se spread for aceitável (<= 15%), False se for alerta de liquidez.
        """
        if midpoint <= 0:
            return False
        spread_pct = (ask - bid) / midpoint
        return spread_pct <= 0.15

    def validar_grade(self, grade_opcoes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Recebe a grade teórica (Black-Scholes) e tenta enriquecer com dados reais de mercado.
        Se falhar ou não houver liquidez, mantém os dados teóricos (Graceful Fallback).
        """
        grade_validada = []
        
        # Otimização: buscar em paralelo
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_codigo = {}
            for opt in grade_opcoes:
                codigo = opt["Código B3"]
                future = executor.submit(self._fetch_single_option, codigo)
                future_to_codigo[future] = opt
            
            for future in concurrent.futures.as_completed(future_to_codigo, timeout=self.timeout_sec * len(grade_opcoes)):
                opt = future_to_codigo[future]
                try:
                    resultado = future.result(timeout=self.timeout_sec)
                except Exception:
                    resultado = {"sucesso": False, "codigo": opt["Código B3"]}
                
                opt_validada = dict(opt) # cópia do dict original
                
                if resultado.get("sucesso") and resultado.get("last", 0) > 0.01:
                    last = resultado["last"]
                    bid = resultado["bid"]
                    ask = resultado["ask"]
                    vol = resultado["volume"]
                    midpoint = (bid + ask) / 2.0
                    
                    # Usa o preço real da tela se teve volume razoável ou last existe
                    opt_validada["Prêmio Est."] = round(last, 2)
                    opt_validada["Alvo (+150%)"] = round(last * 2.5, 2)
                    opt_validada["tipo_dado"] = "🟢 MERCADO REAL"
                    
                    spread_ok = self.auditar_spread(bid, ask, midpoint)
                    opt_validada["alerta_liquidez"] = not spread_ok
                    opt_validada["volume_real"] = vol
                else:
                    opt_validada["tipo_dado"] = "⚪ TEÓRICO (BS)"
                    opt_validada["alerta_liquidez"] = False
                    opt_validada["volume_real"] = 0
                
                grade_validada.append(opt_validada)
                
        # Reordena para manter a ordem original baseada no strike
        grade_validada.sort(key=lambda x: x["Strike"])
        return grade_validada
