# -*- coding: utf-8 -*-
"""
Black-Scholes Pricing & Greeks Engine
Implementação analítica das equações de Black-Scholes-Merton e sensibilidades (Gregas)
para o mercado de opções da B3.
"""

from typing import Dict, Any, Union
import numpy as np
import pandas as pd
from scipy.stats import norm


class BlackScholesEngine:
    """
    Motor analítico de precificação e cálculo de gregas para opções europeias / padrão B3.
    """

    def __init__(self, risk_free_rate: float = 0.1075):
        """
        Inicializa o motor com taxa livre de risco anual configurável.

        :param risk_free_rate: Taxa livre de risco anual contínua/anualizada (padrão: 0.1075 = 10.75% a.a.)
        """
        self.risk_free_rate = float(risk_free_rate)

    @staticmethod
    def calculate_historical_volatility(
        close_prices: Union[pd.Series, np.ndarray, list],
        window: int = 21,
        annualization_factor: int = 252
    ) -> float:
        """
        Calcula a volatilidade histórica anualizada baseada em retornos logarítmicos
        com janela móvel recente e base anual de dias úteis (252).

        :param close_prices: Série temporal ou array com histórico de preços de fechamento.
        :param window: Janela de observação em dias úteis (padrão: 21).
        :param annualization_factor: Dias úteis no ano (padrão: 252).
        :return: Volatilidade anualizada (desvio padrão dos retornos log * sqrt(252)).
        """
        if isinstance(close_prices, pd.Series):
            s = close_prices.dropna()
        else:
            s = pd.Series(close_prices).dropna()

        if len(s) <= 1:
            return 0.0

        # Retornos logarítmicos diários
        log_returns = np.log(s / s.shift(1)).dropna()

        if len(log_returns) < 2:
            return 0.0

        # Usa a janela mais recente disponível caso a série seja menor que a janela solicitada
        effective_window = min(len(log_returns), window)
        vol_sample = log_returns.tail(effective_window)

        # ddof=1 para estimador amostral
        std = vol_sample.std(ddof=1)
        if np.isnan(std):
            return 0.0

        return float(std * np.sqrt(annualization_factor))

    def evaluate_option(
        self,
        spot: float,
        strike: float,
        dte_business_days: float,
        option_type: str,
        sigma: float
    ) -> Dict[str, Any]:
        """
        Calcula analiticamente o prêmio teórico e as sensibilidades (Gregas)
        para opções de CALL ou PUT.

        :param spot: Preço à vista (Spot) do ativo subjacente.
        :param strike: Preço de exercício (Strike) da opção.
        :param dte_business_days: Dias úteis até o vencimento (DTE).
        :param option_type: Tipo da opção ('CALL' ou 'PUT').
        :param sigma: Volatilidade anualizada (ex: 0.30 para 30%).
        :return: Dicionário estruturado com prêmio, delta, gamma, vega, theta diário e theta pct.
        """
        opt_type = option_type.upper().strip()
        if opt_type not in ("CALL", "PUT"):
            raise ValueError(f"option_type inválido: {option_type}. Esperado 'CALL' ou 'PUT'.")

        S = float(spot)
        K = float(strike)
        r = float(self.risk_free_rate)
        sigma = float(sigma)
        dte = float(dte_business_days)

        # Tempo até vencimento em anos na base de 252 dias úteis
        T = max(dte / 252.0, 0.0)

        # Caso limite: Vencimento ou sem tempo restante (T <= 0)
        if T <= 0.0:
            if opt_type == "CALL":
                intrinsic = max(0.0, S - K)
                delta = 1.0 if S > K else (0.5 if S == K else 0.0)
            else:
                intrinsic = max(0.0, K - S)
                delta = -1.0 if S < K else (-0.5 if S == K else 0.0)

            return {
                "spot": S,
                "strike": K,
                "dte_business_days": dte,
                "option_type": opt_type,
                "sigma": sigma,
                "risk_free_rate": r,
                "theoretical_price": intrinsic,
                "delta": delta,
                "gamma": 0.0,
                "vega": 0.0,
                "theta_daily": 0.0,
                "theta_pct": 0.0
            }

        # Caso limite: Volatilidade nula ou desprezível
        if sigma <= 1e-7:
            df = np.exp(-r * T)
            if opt_type == "CALL":
                theoretical_price = max(0.0, S - K * df)
                delta = 1.0 if S > K * df else 0.0
            else:
                theoretical_price = max(0.0, K * df - S)
                delta = -1.0 if S < K * df else 0.0

            theta_annual = -r * K * df if opt_type == "CALL" else r * K * df
            theta_daily = theta_annual / 252.0
            theta_pct = (theta_daily / theoretical_price) if theoretical_price > 1e-6 else 0.0

            return {
                "spot": S,
                "strike": K,
                "dte_business_days": dte,
                "option_type": opt_type,
                "sigma": sigma,
                "risk_free_rate": r,
                "theoretical_price": float(theoretical_price),
                "delta": float(delta),
                "gamma": 0.0,
                "vega": 0.0,
                "theta_daily": float(theta_daily),
                "theta_pct": float(theta_pct)
            }

        sqrt_T = np.sqrt(T)
        d1 = (np.log(S / K) + (r + 0.5 * (sigma ** 2)) * T) / (sigma * sqrt_T)
        d2 = d1 - sigma * sqrt_T

        pdf_d1 = norm.pdf(d1)
        cdf_d1 = norm.cdf(d1)
        cdf_d2 = norm.cdf(d2)
        cdf_neg_d1 = norm.cdf(-d1)
        cdf_neg_d2 = norm.cdf(-d2)
        exp_discount = np.exp(-r * T)

        # Gamma e Vega são idênticos para CALL e PUT
        gamma = pdf_d1 / (S * sigma * sqrt_T)
        vega = S * pdf_d1 * sqrt_T

        if opt_type == "CALL":
            theoretical_price = S * cdf_d1 - K * exp_discount * cdf_d2
            delta = cdf_d1
            # Theta anual (Black-Scholes standard: dV/dt onde dt é decurso de tempo para o vencimento)
            theta_annual = -(S * pdf_d1 * sigma) / (2.0 * sqrt_T) - r * K * exp_discount * cdf_d2
        else:
            theoretical_price = K * exp_discount * cdf_neg_d2 - S * cdf_neg_d1
            delta = -cdf_neg_d1  # cdf_d1 - 1
            theta_annual = -(S * pdf_d1 * sigma) / (2.0 * sqrt_T) + r * K * exp_discount * cdf_neg_d2

        theoretical_price = max(0.0, float(theoretical_price))
        theta_daily = float(theta_annual / 252.0)
        theta_pct = float(theta_daily / theoretical_price) if theoretical_price > 1e-6 else 0.0

        return {
            "spot": S,
            "strike": K,
            "dte_business_days": dte,
            "option_type": opt_type,
            "sigma": sigma,
            "risk_free_rate": r,
            "theoretical_price": theoretical_price,
            "delta": float(delta),
            "gamma": float(gamma),
            "vega": float(vega),
            "theta_daily": theta_daily,
            "theta_pct": theta_pct
        }

