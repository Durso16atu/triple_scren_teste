import numpy as np
import pandas as pd
from scipy.stats import norm
from data_loader import carregar_dados_ativo
from elder_engine import calcular_telas_elder

def black_scholes_call(S, K, T, r, sigma):
    """Calcula o prêmio teórico de uma Call via Black-Scholes."""
    if T <= 0:
        return max(0.0, S - K)
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    call = S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
    return call

def simular_call_seco(df_sinais: pd.DataFrame, dias_vencimento: int = 20, alvo_multiplicacao: float = 1.5, taxa_juros: float = 0.105):
    """
    Simula a compra de Call ATM a cada gatilho:
    - Retorno positivo: +alvo_multiplicacao (+150% do prêmio pago) se o ativo disparar.
    - Retorno negativo: -1.0 (-100%, virou pó) se expirar sem atingir o alvo.
    """
    df = df_sinais.copy()
    # Volatilidade histórica anualizada (janela de 30 pregões)
    df['Volatilidade'] = df['Close'].pct_change().rolling(window=30).std() * np.sqrt(252)
    df['Volatilidade'] = df['Volatilidade'].fillna(0.30) # Valor conservador caso falte dado

    trades = []
    indices_gatilho = df.index[df['Gatilho_Compra'] == True]

    for data_entrada in indices_gatilho:
        pos_entrada = df.index.get_loc(data_entrada)
        
        # Garante que temos pregões suficientes à frente para acompanhar o vencimento
        if pos_entrada + dias_vencimento >= len(df):
            continue

        preco_entrada = df.iloc[pos_entrada]['Close']
        vol = df.iloc[pos_entrada]['Volatilidade']
        strike = preco_entrada # Opção no dinheiro (ATM)
        
        # Preço inicial do prêmio pago (T = dias_vencimento / 252)
        T_anos = dias_vencimento / 252.0
        premio_inicial = black_scholes_call(preco_entrada, strike, T_anos, taxa_juros, vol)

        if premio_inicial <= 0.01:
            continue

        trade_encerrado = False
        resultado_pct = -1.0 # Padrão: virou pó (-100%)

        # Acompanha a vida da opção dia a dia até o vencimento
        for d in range(1, dias_vencimento + 1):
            idx_atual = pos_entrada + d
            preco_atual = df.iloc[idx_atual]['Close']
            dias_restantes = (dias_vencimento - d) / 252.0
            
            # Prêmio atual da Call ao longo dos dias
            premio_atual = black_scholes_call(preco_atual, strike, dias_restantes, taxa_juros, vol)
            variacao_premio = (premio_atual - premio_inicial) / premio_inicial

            # Gatilho de ganho explosivo atingido
            if variacao_premio >= alvo_multiplicacao:
                resultado_pct = alvo_multiplicacao
                trade_encerrado = True
                break

        # Se chegou ao vencimento sem bater o alvo, verifica valor intrínseco final
        if not trade_encerrado:
            preco_final = df.iloc[pos_entrada + dias_vencimento]['Close']
            valor_intrinseco = max(0.0, preco_final - strike)
            variacao_final = (valor_intrinseco - premio_inicial) / premio_inicial
            resultado_pct = max(-1.0, variacao_final)

        trades.append({
            'Data_Entrada': data_entrada,
            'Preco_Acao': preco_entrada,
            'Premio_Pago': premio_inicial,
            'Retorno_Trade': resultado_pct,
            'Status': 'Explosao (Lucro)' if resultado_pct > 0 else 'Virou Po (-100%)'
        })

    return pd.DataFrame(trades)

if __name__ == "__main__":
    ticker = "PETR4.SA"
    diario, semanal = carregar_dados_ativo(ticker, start="2023-01-01")
    sinais = calcular_telas_elder(diario, semanal)
    df_trades = simular_call_seco(sinais, dias_vencimento=20, alvo_multiplicacao=1.5)

    vitorias = (df_trades['Retorno_Trade'] > 0).sum()
    derretimentos = (df_trades['Retorno_Trade'] <= -0.9).sum()
    total_trades = len(df_trades)
    
    taxa_acerto = (vitorias / total_trades) * 100 if total_trades > 0 else 0
    retorno_medio = df_trades['Retorno_Trade'].mean() * 100

    print(f"\n=======================================================")
    print(f"RELATÓRIO DO BACKTEST: CALL A SECO - {ticker}")
    print(f"=======================================================")
    print(f"Total de Operações Avaliadas: {total_trades}")
    print(f"Operações com Ganho Explosivo (+150%): {vitorias}")
    print(f"Operações que Viraram Pó (-100%): {derretimentos}")
    print(f"Taxa de Acerto: {taxa_acerto:.2f}%")
    print(f"Retorno Médio por Operação: {retorno_medio:.2f}%")
    print(f"=======================================================\n")
    print("Últimos 5 trades simulados:")
    print(df_trades[['Data_Entrada', 'Preco_Acao', 'Premio_Pago', 'Retorno_Trade', 'Status']].tail(5))