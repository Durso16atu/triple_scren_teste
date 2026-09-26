import pandas as pd
import numpy as np
from src.data_loader import carregar_dados_ativo

def calcular_telas_elder(df_diario: pd.DataFrame, df_semanal: pd.DataFrame):
    """
    Aplica o Teorema do Triple Screen com Filtro Institucional:
    - Tela 1: MME 13 Semanal subindo E Preço Semanal acima da MME 50 Semanal.
    - Tela 2: IFR de 2 períodos Diário em sobrevenda (IFR2 < 15).
    - Tela 3: Rompimento da máxima do pregão anterior (Gatilho de Entrada).
    """
    df_d = df_diario.copy()
    df_s = df_semanal.copy()

    # --- TELA 1: A MARÉ INSTITUCIONAL (Gráfico Semanal) ---
    # MME de 13 semanas (Curto/Médio prazo macro)
    df_s['EMA13'] = df_s['Close'].ewm(span=13, adjust=False).mean()
    # MME de 50 semanas (Tendência Institucional de Longo Prazo)
    df_s['EMA50'] = df_s['Close'].ewm(span=50, adjust=False).mean()
    
    # Maré compradora validada institucionalmente:
    # 1. MME13 inclinada para cima
    # 2. Preço de fechamento da semana ACIMA da MME50
    df_s['Maree_Alta'] = (df_s['EMA13'] > df_s['EMA13'].shift(1)) & (df_s['Close'] > df_s['EMA50'])

    # Reindexa a maré semanal para os pregões diários
    df_d['Maree_Alta'] = df_s['Maree_Alta'].reindex(df_d.index, method='ffill')

    # --- TELA 2: A ONDA (Gráfico Diário) ---
    delta = df_d['Close'].diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)
    
    media_ganho = ganho.rolling(window=2).mean()
    media_perda = perda.rolling(window=2).mean()
    
    rs = media_ganho / (media_perda + 1e-9)
    df_d['IFR2'] = 100 - (100 / (1 + rs))
    
    # Onda de recuo: ativo em sobrevenda (IFR2 < 15)
    df_d['Recuo_Sobrevenda'] = df_d['IFR2'] < 15

    # --- TELA 3: A ONDULAÇÃO (Gatilho de Compra) ---
    df_d['Gatilho_Compra'] = (
        (df_d['Maree_Alta'] == True) &
        (df_d['Recuo_Sobrevenda'].shift(1) == True) &
        (df_d['High'] > df_d['High'].shift(1))
    )

    return df_d

if __name__ == "__main__":
    # Teste comparativo com LREN3 (papel que sofria com mercado de baixa)
    ticker = "LREN3.SA"
    diario, semanal = carregar_dados_ativo(ticker, start="2023-01-01")
    sinais = calcular_telas_elder(diario, semanal)
    
    entradas = sinais[sinais['Gatilho_Compra'] == True]
    print(f"\n--- Sinais gerados para {ticker} COM Filtro MME 50 ---")
    print(f"Total de disparos de compra filtrados: {len(entradas)}")