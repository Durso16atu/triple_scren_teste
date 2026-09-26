import pandas as pd
import numpy as np

# Import protegido para funcionar tanto a partir da raiz quanto dentro de src
try:
    from src.data_loader import carregar_dados_ativo
except ModuleNotFoundError:
    from data_loader import carregar_dados_ativo


def calcular_telas_elder(df_diario: pd.DataFrame, df_semanal: pd.DataFrame):
    """
    Teorema do Triple Screen Bidirecional (Alta e Baixa):
    
    COMPRA (CALL):
    - Tela 1: MME 13 Semanal subindo E Preço acima da MME 50 Semanal (Maré de Alta).
    - Tela 2: IFR-2 Diário em sobrevenda (IFR2 < 15, recuo pontual).
    - Tela 3: Rompimento da máxima do pregão anterior (Gatilho de Compra).
    
    VENDA (PUT):
    - Tela 1: MME 13 Semanal descendo E Preço abaixo da MME 50 Semanal (Maré de Baixa).
    - Tela 2: IFR-2 Diário em sobrecompra (IFR2 > 85, repique pontual).
    - Tela 3: Perda da mínima do pregão anterior (Gatilho de Venda).
    """
    df_d = df_diario.copy()
    df_s = df_semanal.copy()

    # =========================================================================
    # TELA 1: A MARÉ MACRO (Gráfico Semanal)
    # =========================================================================
    df_s['EMA13'] = df_s['Close'].ewm(span=13, adjust=False).mean()
    df_s['EMA50'] = df_s['Close'].ewm(span=50, adjust=False).mean()

    # Maré de Alta: MME 13 inclinada para cima E Preço Semanal acima da MME 50
    df_s['Maree_Alta'] = (df_s['EMA13'] > df_s['EMA13'].shift(1)) & (df_s['Close'] > df_s['EMA50'])

    # Maré de Baixa: MME 13 inclinada para baixo E Preço Semanal abaixo da MME 50
    df_s['Maree_Baixa'] = (df_s['EMA13'] < df_s['EMA13'].shift(1)) & (df_s['Close'] < df_s['EMA50'])

    # Reindexa as marés semanais para os pregões diários (preenchimento contínuo)
    df_d['Maree_Alta'] = df_s['Maree_Alta'].reindex(df_d.index, method='ffill')
    df_d['Maree_Baixa'] = df_s['Maree_Baixa'].reindex(df_d.index, method='ffill')

    # =========================================================================
    # TELA 2: A ONDA (Gráfico Diário - Oscilador IFR-2)
    # =========================================================================
    delta = df_d['Close'].diff()
    ganho = delta.clip(lower=0)
    perda = -delta.clip(upper=0)

    media_ganho = ganho.rolling(window=2).mean()
    media_perda = perda.rolling(window=2).mean()

    rs = media_ganho / (media_perda + 1e-9)
    df_d['IFR2'] = 100 - (100 / (1 + rs))

    # Recuo na alta: sobrevenda no diário
    df_d['Recuo_Sobrevenda'] = df_d['IFR2'] < 15

    # Repique na baixa: sobrecompra no diário
    df_d['Repique_Sobrecompra'] = df_d['IFR2'] > 85

    # =========================================================================
    # TELA 3: A ONDULAÇÃO (Gatilhos de Execução Diários)
    # =========================================================================
    # Gatilho de Compra (Call): Maré Alta + Recuo ontem + Rompimento da máxima hoje
    df_d['Gatilho_Compra'] = (
        (df_d['Maree_Alta'] == True) &
        (df_d['Recuo_Sobrevenda'].shift(1) == True) &
        (df_d['High'] > df_d['High'].shift(1))
    )

    # Gatilho de Venda (Put): Maré Baixa + Repique ontem + Perda da mínima hoje
    df_d['Gatilho_Venda'] = (
        (df_d['Maree_Baixa'] == True) &
        (df_d['Repique_Sobrecompra'].shift(1) == True) &
        (df_d['Low'] < df_d['Low'].shift(1))
    )

    return df_d


if __name__ == "__main__":
    ticker = "PETR4.SA"
    diario, semanal = carregar_dados_ativo(ticker, start="2023-01-01")
    sinais = calcular_telas_elder(diario, semanal)

    compras = sinais[sinais['Gatilho_Compra'] == True]
    vendas = sinais[sinais['Gatilho_Venda'] == True]

    print(f"\n=======================================================")
    print(f"TESTE DE SINAIS BIDIRECIONAIS: {ticker}")
    print(f"=======================================================")
    print(f"Sinais de Compra (CALL): {len(compras)}")
    print(f"Sinais de Venda (PUT):   {len(vendas)}")
    print(f"=======================================================\n")