import pandas as pd
import numpy as np

# Import protegido para execução tanto pela raiz quanto por dentro de src
try:
    from src.data_loader import carregar_dados_ativo
except ModuleNotFoundError:
    from data_loader import carregar_dados_ativo


def calcular_telas_elder(df_diario: pd.DataFrame, df_semanal: pd.DataFrame):
    """
    Triple Screen Bidirecional com SELETOR DE REGIME MACRO (MME 200):
    
    1. REGIME DE ALTA (Close > MME 200 Diária):
       - Permite estritamente operações de CALL.
       - Bloqueia compras de PUT.
    
    2. REGIME DE BAIXA (Close < MME 200 Diária):
       - Permite estritamente operações de PUT.
       - Bloqueia compras de CALL.
    """
    df_d = df_diario.copy()
    df_s = df_semanal.copy()

    # =========================================================================
    # SELETOR DE REGIME MACRO (Gráfico Diário - MME 200)
    # =========================================================================
    df_d['EMA200'] = df_d['Close'].ewm(span=200, adjust=False).mean()
    df_d['Regime_Bull'] = df_d['Close'] > df_d['EMA200']
    df_d['Regime_Bear'] = df_d['Close'] < df_d['EMA200']

    # =========================================================================
    # TELA 1: A MARÉ MACRO (Gráfico Semanal)
    # =========================================================================
    df_s['EMA13'] = df_s['Close'].ewm(span=13, adjust=False).mean()
    df_s['EMA50'] = df_s['Close'].ewm(span=50, adjust=False).mean()

    # Maré de Alta: MME 13 subindo E Preço Semanal acima da MME 50
    df_s['Maree_Alta'] = (df_s['EMA13'] > df_s['EMA13'].shift(1)) & (df_s['Close'] > df_s['EMA50'])

    # Maré de Baixa: MME 13 caindo E Preço Semanal abaixo da MME 50
    df_s['Maree_Baixa'] = (df_s['EMA13'] < df_s['EMA13'].shift(1)) & (df_s['Close'] < df_s['EMA50'])

    # Reindexa as marés semanais para os pregões diários
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

    df_d['Recuo_Sobrevenda'] = df_d['IFR2'] < 15
    df_d['Repique_Sobrecompra'] = df_d['IFR2'] > 85

    # =========================================================================
    # TELA 3: GATILHOS COM SELETOR DE REGIME EMBUTIDO
    # =========================================================================
    # CALL: Maré Semanal Alta + Recuo Diário + Rompimento Máxima + REGIME BULL (Close > MME200)
    df_d['Gatilho_Compra'] = (
        (df_d['Regime_Bull'] == True) &
        (df_d['Maree_Alta'] == True) &
        (df_d['Recuo_Sobrevenda'].shift(1) == True) &
        (df_d['High'] > df_d['High'].shift(1))
    )

    # PUT: Maré Semanal Baixa + Repique Diário + Perda Mínima + REGIME BEAR (Close < MME200)
    df_d['Gatilho_Venda'] = (
        (df_d['Regime_Bear'] == True) &
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
    print(f"TESTE COM SELETOR DE REGIME (MME 200): {ticker}")
    print(f"=======================================================")
    print(f"Sinais de Compra (CALL - Permitidos em Bull): {len(compras)}")
    print(f"Sinais de Venda (PUT  - Bloqueados se estiver em Bull): {len(vendas)}")
    print(f"=======================================================\n")