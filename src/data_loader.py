import os
import yfinance as yf
import pandas as pd

# Os 20 ativos com maior liquidez e mercado ativo de opções na B3
TICKERS_B3 = [
	"PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "BBAS3.SA",
	"RENT3.SA", "B3SA3.SA", "ABEV3.SA", "WEGE3.SA", "SUZB3.SA",
	"GGBR4.SA", "PRIO3.SA", "ELET3.SA", "CSAN3.SA", "RADL3.SA",
	"JBSS3.SA", "RAIL3.SA", "VBBR3.SA", "LREN3.SA", "RDOR3.SA"
]


def carregar_dados_ativo(ticker: str, start: str = "2023-01-01"):
	"""Baixa dados diários e os agrega em dados semanais para a Tela 1."""
	print(f"Baixando dados para: {ticker}...")

	df_diario = yf.download(ticker, start=start, progress=False)

	if df_diario.empty:
		raise ValueError(f"Não foi possível obter dados para {ticker}.")

	# O yfinance pode retornar colunas MultiIndex, mesmo para um único ativo.
	if isinstance(df_diario.columns, pd.MultiIndex):
		df_diario.columns = df_diario.columns.get_level_values(0)

	df_semanal = df_diario.resample("W-FRI").agg({
		"Open": "first",
		"High": "max",
		"Low": "min",
		"Close": "last",
		"Volume": "sum",
	}).dropna()

	return df_diario, df_semanal


if __name__ == "__main__":
	ticker_teste = "PETR4.SA"
	diario, semanal = carregar_dados_ativo(ticker_teste)

	print("\n--- Dados Diários (Últimos 3 pregões) ---")
	print(diario[["Open", "High", "Low", "Close"]].tail(3))

	print("\n--- Dados Semanais - Tela 1 (Últimas 3 semanas) ---")
	print(semanal[["Open", "High", "Low", "Close"]].tail(3))
