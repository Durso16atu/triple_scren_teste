# -*- coding: utf-8 -*-
import unittest
from unittest.mock import patch, MagicMock
from src.options_market_validator import OptionsMarketValidator

class TestOptionsMarketValidator(unittest.TestCase):
    def setUp(self):
        self.validator = OptionsMarketValidator(timeout_sec=2)
        self.grade_teorica = [
            {"Código B3": "PETRK34", "Strike": 34.0, "Prêmio Est.": 0.50, "Alvo (+150%)": 1.25}
        ]

    def test_auditar_spread_aceitavel(self):
        self.assertTrue(self.validator.auditar_spread(bid=1.00, ask=1.10, midpoint=1.05))

    def test_auditar_spread_alerta_liquidez(self):
        self.assertFalse(self.validator.auditar_spread(bid=0.50, ask=1.50, midpoint=1.00))

    @patch('src.options_market_validator.yf.Ticker')
    def test_validar_grade_sucesso_mercado(self, mock_ticker):
        # Configurar o mock do yfinance para simular cotação real
        mock_instance = MagicMock()
        import pandas as pd
        
        # Simula hist()
        mock_hist = pd.DataFrame({
            "Close": [0.60],
            "Volume": [1500]
        })
        mock_instance.history.return_value = mock_hist
        
        # Simula info
        mock_instance.info = {"bid": 0.55, "ask": 0.65}
        
        mock_ticker.return_value = mock_instance
        
        grade_validada = self.validator.validar_grade(self.grade_teorica)
        opt = grade_validada[0]
        
        self.assertEqual(opt["tipo_dado"], "🟢 MERCADO REAL")
        self.assertEqual(opt["Prêmio Est."], 0.60)
        self.assertEqual(opt["Alvo (+150%)"], 1.50)
        self.assertEqual(opt["volume_real"], 1500)
        
        # 0.10 / 0.60 = 0.166... > 15%, so it SHOULD alert!
        self.assertTrue(opt["alerta_liquidez"])

    @patch('src.options_market_validator.yf.Ticker')
    def test_validar_grade_fallback_timeout(self, mock_ticker):
        # Simula falha na API ou timeout
        mock_ticker.side_effect = Exception("Timeout Simulado")
        
        grade_validada = self.validator.validar_grade(self.grade_teorica)
        opt = grade_validada[0]
        
        self.assertEqual(opt["tipo_dado"], "⚪ TEÓRICO (BS)")
        self.assertEqual(opt["Prêmio Est."], 0.50) # manteve o original
        self.assertEqual(opt["Alvo (+150%)"], 1.25)
        self.assertFalse(opt["alerta_liquidez"])

if __name__ == '__main__':
    unittest.main()
