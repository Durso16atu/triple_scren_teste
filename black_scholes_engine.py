# -*- coding: utf-8 -*-
"""
Black-Scholes Pricing & Greeks Engine para B3 (Ponto de entrada raiz)
Redireciona para src.black_scholes_engine.
"""

from src.black_scholes_engine import (
    BlackScholesEngine,
    strike_oficial_b3,
    calcular_terceira_sexta,
    obter_vencimento_mensal_alvo,
    LETRAS_CALL,
    LETRAS_PUT,
    TZ_SP
)

__all__ = [
    "BlackScholesEngine",
    "strike_oficial_b3",
    "calcular_terceira_sexta",
    "obter_vencimento_mensal_alvo",
    "LETRAS_CALL",
    "LETRAS_PUT",
    "TZ_SP"
]
