import numpy as np
import pandas as pd
from scipy.stats import norm

# Import protegido para execução tanto pela raiz quanto por dentro de src
try:
    from src.data_loader import carregar_dados_ativo
    from src.elder_engine import calcular_telas_elder
except ModuleNotFoundError:
    from data_loader import carregar_dados_ativo
    from elder_engine import calcular_telas_elder


# =============================================================================
# 1. MODELOS DE PRECIFICAÇÃO ANALÍTICA (BLACK-SCHOLES)
# =============================================================================
def black_scholes_call(S, K, T, r, sigma):
    """Calcula o prêmio teórico de uma opção de compra (CALL)."""
    if T <= 0:
        return max(0.0, S - K)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return call


def black_scholes_put(S, K, T, r, sigma):
    """Calcula o prêmio teórico de uma opção de venda (PUT)."""
    if T <= 0:
        return max(0.0, K - S)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    put = K * np.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
    return put


# =============================================================================
# 2. SIMULADOR DE COMPRA A SECO DE CALL (OPERAÇÃO DE ALTA)
# =============================================================================
def simular_call_seco(df_sinais: pd.DataFrame, dias_vencimento: int = 20, alvo_multiplicacao: float = 1.5, taxa_juros: float = 0.105):
    """
    Simula compra de Call ATM no sinal 'Gatilho_Compra':
    - Saída no Lucro: Prêmio valoriza >= +150% (+alvo_multiplicacao).
    - Saída no Vencimento/Pó: Se expirar sem bater o alvo (perda máxima = -100%).
    """
    df = df_sinais.copy()
    if 'Volatilidade' not in df.columns:
        df['Volatilidade'] = df['Close'].pct_change().rolling(window=30).std() * np.sqrt(252)
        df['Volatilidade'] = df['Volatilidade'].fillna(0.30)

    trades = []
    if 'Gatilho_Compra' not in df.columns:
        return pd.DataFrame(trades)

    indices_gatilho = df.index[df['Gatilho_Compra'] == True]

    for data_entrada in indices_gatilho:
        pos_entrada = df.index.get_loc(data_entrada)
        if pos_entrada + dias_vencimento >= len(df):
            continue

        preco_entrada = df.iloc[pos_entrada]['Close']
        vol = df.iloc[pos_entrada]['Volatilidade']
        strike = preco_entrada  # Opção ATM

        T_anos = dias_vencimento / 252.0
        premio_inicial = black_scholes_call(preco_entrada, strike, T_anos, taxa_juros, vol)

        if premio_inicial <= 0.01:
            continue

        trade_encerrado = False
        resultado_pct = -1.0

        for d in range(1, dias_vencimento + 1):
            idx_atual = pos_entrada + d
            preco_atual = df.iloc[idx_atual]['Close']
            dias_restantes = (dias_vencimento - d) / 252.0

            premio_atual = black_scholes_call(preco_atual, strike, dias_restantes, taxa_juros, vol)
            variacao_premio = (premio_atual - premio_inicial) / premio_inicial

            if variacao_premio >= alvo_multiplicacao:
                resultado_pct = alvo_multiplicacao
                trade_encerrado = True
                break

        if not trade_encerrado:
            preco_final = df.iloc[pos_entrada + dias_vencimento]['Close']
            valor_intrinseco = max(0.0, preco_final - strike)
            variacao_final = (valor_intrinseco - premio_inicial) / premio_inicial
            resultado_pct = max(-1.0, variacao_final)

        trades.append({
            'Data_Entrada': data_entrada,
            'Tipo': 'CALL',
            'Preco_Acao': preco_entrada,
            'Premio_Pago': premio_inicial,
            'Retorno_Trade': resultado_pct,
            'Status': 'Explosao (Lucro)' if resultado_pct > 0 else 'Virou Po (-100%)'
        })

    return pd.DataFrame(trades)


# =============================================================================
# 3. SIMULADOR DE COMPRA A SECO DE PUT (OPERAÇÃO DE BAIXA)
# =============================================================================
def simular_put_seco(df_sinais: pd.DataFrame, dias_vencimento: int = 20, alvo_multiplicacao: float = 1.5, taxa_juros: float = 0.105):
    """
    Simula compra de Put ATM no sinal 'Gatilho_Venda':
    - Saída no Lucro: Prêmio valoriza >= +150% se a ação cair forte.
    - Saída no Vencimento/Pó: Se expirar sem bater o alvo (perda máxima = -100%).
    """
    df = df_sinais.copy()
    if 'Volatilidade' not in df.columns:
        df['Volatilidade'] = df['Close'].pct_change().rolling(window=30).std() * np.sqrt(252)
        df['Volatilidade'] = df['Volatilidade'].fillna(0.30)

    trades = []
    if 'Gatilho_Venda' not in df.columns:
        return pd.DataFrame(trades)

    indices_gatilho = df.index[df['Gatilho_Venda'] == True]

    for data_entrada in indices_gatilho:
        pos_entrada = df.index.get_loc(data_entrada)
        if pos_entrada + dias_vencimento >= len(df):
            continue

        preco_entrada = df.iloc[pos_entrada]['Close']
        vol = df.iloc[pos_entrada]['Volatilidade']
        strike = preco_entrada  # Put ATM

        T_anos = dias_vencimento / 252.0
        premio_inicial = black_scholes_put(preco_entrada, strike, T_anos, taxa_juros, vol)

        if premio_inicial <= 0.01:
            continue

        trade_encerrado = False
        resultado_pct = -1.0

        for d in range(1, dias_vencimento + 1):
            idx_atual = pos_entrada + d
            preco_atual = df.iloc[idx_atual]['Close']
            dias_restantes = (dias_vencimento - d) / 252.0

            premio_atual = black_scholes_put(preco_atual, strike, dias_restantes, taxa_juros, vol)
            variacao_premio = (premio_atual - premio_inicial) / premio_inicial

            if variacao_premio >= alvo_multiplicacao:
                resultado_pct = alvo_multiplicacao
                trade_encerrado = True
                break

        if not trade_encerrado:
            preco_final = df.iloc[pos_entrada + dias_vencimento]['Close']
            valor_intrinseco = max(0.0, strike - preco_final)
            variacao_final = (valor_intrinseco - premio_inicial) / premio_inicial
            resultado_pct = max(-1.0, variacao_final)

        trades.append({
            'Data_Entrada': data_entrada,
            'Tipo': 'PUT',
            'Preco_Acao': preco_entrada,
            'Premio_Pago': premio_inicial,
            'Retorno_Trade': resultado_pct,
            'Status': 'Explosao (Lucro)' if resultado_pct > 0 else 'Virou Po (-100%)'
        })

    return pd.DataFrame(trades)


# =============================================================================
# 4. TESTE UNITÁRIO LOCAL (PETR4)
# =============================================================================
if __name__ == "__main__":
    ticker = "PETR4.SA"
    diario, semanal = carregar_dados_ativo(ticker, start="2023-01-01")
    sinais = calcular_telas_elder(diario, semanal)

    trades_call = simular_call_seco(sinais)
    trades_put = simular_put_seco(sinais)

    print(f"\n=======================================================")
    print(f"RESULTADO DAS OPERAÇÕES COM OPÇÕES: {ticker}")
    print(f"=======================================================")
    
    if not trades_call.empty:
        vit_call = (trades_call['Retorno_Trade'] > 0).sum()
        tx_call = (vit_call / len(trades_call)) * 100
        print(f"CALLS -> Total: {len(trades_call)} | Lucro (+150%): {vit_call} | Acerto: {tx_call:.1f}% | Ret. Médio: {trades_call['Retorno_Trade'].mean()*100:.1f}%")
    
    if not trades_put.empty:
        vit_put = (trades_put['Retorno_Trade'] > 0).sum()
        tx_put = (vit_put / len(trades_put)) * 100
        print(f"PUTS  -> Total: {len(trades_put)} | Lucro (+150%): {vit_put} | Acerto: {tx_put:.1f}% | Ret. Médio: {trades_put['Retorno_Trade'].mean()*100:.1f}%")
    
    print(f"=======================================================\n")