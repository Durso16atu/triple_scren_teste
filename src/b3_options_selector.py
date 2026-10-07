# -*- coding: utf-8 -*-
"""
Módulo seletor de opções e gerador da grade de 5 strikes da B3.
Padroniza strikes arredondados, calcula gregas e DTE dinâmico via Black-Scholes.
"""

import datetime
from typing import Optional, Tuple
import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

from src.black_scholes_engine import (
    BlackScholesEngine,
    strike_oficial_b3,
    calcular_terceira_sexta,
    obter_vencimento_mensal_alvo,
    LETRAS_CALL,
    LETRAS_PUT,
    TZ_SP
)


def gerar_grade_5_strikes(
    ticker: str,
    preco_atual: float,
    volatilidade: float,
    tipo: str = 'CALL',
    taxa_juros: float = 0.1075,
    passo_strike: float = 1.0,
    data_base: Optional[datetime.date] = None
) -> Tuple[pd.DataFrame, datetime.date, int]:
    """
    Gera a grade oficial de 5 strikes (-6% ITM, -3% ITM, ATM, +3% OTM, +6% OTM)
    com strikes arredondados para degraus oficiais da B3 e métricas Black-Scholes.
    """
    engine = BlackScholesEngine(risk_free_rate=taxa_juros)
    return engine.gerar_grade_5_strikes(
        ticker=ticker,
        spot=preco_atual,
        sigma=volatilidade,
        tipo=tipo,
        passo_strike=passo_strike,
        data_base=data_base
    )