# -*- coding: utf-8 -*-
import unittest
import datetime
from zoneinfo import ZoneInfo
import pandas as pd

from src.black_scholes_engine import (
    BlackScholesEngine,
    strike_oficial_b3,
    calcular_terceira_sexta,
    obter_vencimento_mensal_alvo,
    TZ_SP
)
from src.monitor_realtime import determinar_ticker_opcao


class TestBlackScholesEngine(unittest.TestCase):
    def setUp(self):
        self.bs = BlackScholesEngine(risk_free_rate=0.1075)

    def test_strike_oficial_b3(self):
        # Arredondamento oficial de strikes para evitar decimais fracionados
        self.assertEqual(strike_oficial_b3(45.64, 1.0), 46.0)
        self.assertEqual(strike_oficial_b3(44.31, 1.0), 44.0)
        self.assertEqual(strike_oficial_b3(36.12, 1.0), 36.0)
        self.assertEqual(strike_oficial_b3(36.85, 1.0), 37.0)
        self.assertEqual(strike_oficial_b3(10.24, 0.5), 10.0)
        self.assertEqual(strike_oficial_b3(10.36, 0.5), 10.5)

    def test_geracao_codigo_ticker_opcao(self):
        # Teste de geração sem decimais espúrios (ex: ITUBK46 em vez de ITUBK45.64)
        ticker_call_46 = determinar_ticker_opcao("ITUB4.SA", 45.64, "CALL")
        self.assertEqual(ticker_call_46, "ITUBK46")

        ticker_call_45 = determinar_ticker_opcao("ITUB4.SA", 44.80, "CALL")
        self.assertEqual(ticker_call_45, "ITUBK45")

        ticker_put_36 = determinar_ticker_opcao("PETR4.SA", 36.10, "PUT")
        self.assertEqual(ticker_put_36, "PETRW36")

    def test_terceira_sexta_feira_serie_k(self):
        # Terceira sexta-feira de novembro de 2026 (Série K / W) deve ser 20/11/2026
        venc_nov = calcular_terceira_sexta(2026, 11)
        self.assertEqual(venc_nov, datetime.date(2026, 11, 20))

    def test_dte_dinamico_e_rolagem(self):
        # Em 07/10/2026, com menos de 15 DU para outubro, deve rolar para 20/11/2026 (Série K)
        data_base = datetime.date(2026, 10, 7)
        venc, dte = obter_vencimento_mensal_alvo(data_base=data_base, dte_minimo=15)
        self.assertEqual(venc, datetime.date(2026, 11, 20))
        self.assertEqual(dte, 30)

    def test_recalculo_gregas_e_theta(self):
        res = self.bs.evaluate_option(
            spot=44.31,
            strike=46.0,
            dte_business_days=32,
            option_type="CALL",
            sigma=0.25
        )
        self.assertGreater(res["theoretical_price"], 0.0)
        self.assertGreater(res["delta"], 0.0)
        self.assertLess(res["delta"], 1.0)
        self.assertGreater(res["gamma"], 0.0)
        self.assertLess(res["theta_daily"], 0.0)  # Decaimento temporal negativo

    def test_grade_5_strikes_arredondamento_e_alvo_150(self):
        df_grade, venc, dte = self.bs.gerar_grade_5_strikes(
            ticker="ITUB4.SA",
            spot=44.31,
            sigma=0.25,
            tipo="CALL",
            passo_strike=1.0,
            data_base=datetime.date(2026, 10, 7)
        )

        self.assertEqual(len(df_grade), 5)
        self.assertEqual(venc, datetime.date(2026, 11, 20))
        self.assertEqual(dte, 30)

        # Verifica faixas (-6% ITM, -3% ITM, ATM, +3% OTM, +6% OTM)
        moneyness_esperado = [
            "ITM (Dentro)",
            "ITM (Dentro)",
            "ATM (No Dinheiro)",
            "OTM (Fora)",
            "OTM (Fora)"
        ]
        self.assertEqual(df_grade["Moneyness"].tolist(), moneyness_esperado)

        # Strikes devem ser inteiros oficiais da B3 (sem fracionamento)
        for strike in df_grade["Strike"]:
            self.assertEqual(strike, round(strike))

        # Alvo (+150%) deve ser exatamente premio_estimado * 2.5
        for _, row in df_grade.iterrows():
            premio = row["Prêmio Est."]
            alvo_esperado = round(premio * 2.5, 2)
            self.assertEqual(row["Alvo (+150%)"], alvo_esperado)

        # O 4º strike (+3% OTM, idx 3) deve ser a opção recomendada
        self.assertEqual(df_grade.iloc[3]["Destaque"], "⭐ RECOMENDADA")


if __name__ == "__main__":
    unittest.main()


    def test_dte_08_outubro(self):
        # 08/10/2026 -> 20/11/2026 deve ser 29 DU (descontando 12/10 e 02/11)
        data_base = datetime.date(2026, 10, 8)
        venc, dte = obter_vencimento_mensal_alvo(data_base=data_base, dte_minimo=15)
        self.assertEqual(venc, datetime.date(2026, 11, 20))
        self.assertEqual(dte, 29)

    def test_premios_desgenerificados(self):
        # CMIG4 ~ 11.88, Vol ~ 28% (0.28)
        df_cmig, _, _ = self.bs.gerar_grade_5_strikes(
            ticker="CMIG4",
            spot=11.88,
            sigma=0.28,
            tipo="CALL",
            data_base=datetime.date(2026, 10, 8) # 29 DU
        )
        # O strike ATM seria o strike_oficial_b3(11.88, 0.50) => 12.00
        atm_row_cmig = df_cmig[df_cmig["Strike"] == 12.00].iloc[0]
        premio_cmig = atm_row_cmig["Prêmio Est."]
        self.assertTrue(0.40 <= premio_cmig <= 0.55, f"Prêmio CMIG4 {premio_cmig} fora da faixa 0.40-0.55")

        # PRIO3 ~ 42.80, Vol ~ 38% (0.38)
        df_prio, _, _ = self.bs.gerar_grade_5_strikes(
            ticker="PRIO3",
            spot=42.80,
            sigma=0.38,
            tipo="CALL",
            data_base=datetime.date(2026, 10, 8) # 29 DU
        )
        atm_row_prio = df_prio[df_prio["Strike"] == 43.00].iloc[0]
        premio_prio = atm_row_prio["Prêmio Est."]
        self.assertTrue(1.80 <= premio_prio <= 2.40, f"Prêmio PRIO3 {premio_prio} fora da faixa 1.80-2.40")
