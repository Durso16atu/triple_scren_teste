import pandas as pd
import numpy as np
from data_loader import carregar_dados_ativo

def calcular_telas_elder(df_diario: pd.DataFrame, df_semanal: pd.DataFrame):
    """
    Aplica o Teorema do Triple Screen de Alexander Elder:
    - Tela 1: Média Móvel Exponencial de 13 semanas (Tendência Macro).
    - Tela 2: IFR de 2 períodos Diário (Pullback em sobrevenda).
    - Tela 3: Rompimento da máxima do pregão anterior (Gatilho de Entrada).
    """
    df_d = df_diario.copy()
    df_s = df_semanal.copy()

    # --- TELA 1: A MARÉ (Gráfico Semanal) ---
    # MME de 13 períodos no gráfico semanal
    df_s['EMA13'] = df_s['Close'].ewm(span=13, adjust=False).mean()
    # Tendência de alta quando a média de hoje é maior que a da semana anterior
    df_s['Maree_Alta'] = df_s['EMA13'] > df_s['EMA13'].shift(1)

    # Reindexa a maré semanal para os pregões diários (mantendo o valor da última semana fechada)
    df_d['Maree_Alta'] = df_s['Maree_Alta'].reindex(df_d.index, method='ffill')

    # --- TELA 2: A ONDA (Gráfico Diário) ---
    # IFR de 2 períodos (RSI-2 de Larry Connors / Elder) para medir recuos rápidos
    delta = df_d['Close'].diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)
    
    media_ganho = ganho.rolling(window=2).mean()
    media_perda = perda.rolling(window=2).mean()
    
    rs = media_ganho / (media_perda + 1e-9)
    df_d['IFR2'] = 100 - (100 / (1 + rs))
    
    # Onda de recuo: ativo em sobrevenda (IFR2 < 15) dentro de uma maré semanal compradora
    df_d['Recuo_Sobrevenda'] = df_d['IFR2'] < 15

    # --- TELA 3: A ONDULAÇÃO (Gatilho de Compra) ---
    # Gatilho ocorre quando:
    # 1. A maré semanal é de alta
    # 2. O ativo teve um recuo de sobrevenda recente (no pregão anterior)
    # 3. A máxima de hoje rompe a máxima do dia anterior (Buy-Stop armado)
    df_d['Gatilho_Compra'] = (
        (df_d['Maree_Alta'] == True) &
        (df_d['Recuo_Sobrevenda'].shift(1) == True) &
        (df_d['High'] > df_d['High'].shift(1))
    )

    return df_d

if __name__ == "__main__":
    ticker = "PETR4.SA"
    diario, semanal = carregar_dados_ativo(ticker, start="2023-01-01")
    sinais = calcular_telas_elder(diario, semanal)
    
    entradas = sinais[sinais['Gatilho_Compra'] == True]
    print(f"\n--- Sinais de Entrada (Triple Screen) gerados para {ticker} desde 2023 ---")
    print(f"Total de disparos de compra: {len(entradas)}")
    print(entradas[['Close', 'High', 'IFR2', 'Gatilho_Compra']].tail(5))