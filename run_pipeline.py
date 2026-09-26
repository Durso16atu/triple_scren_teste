import os
import pandas as pd
from joblib import Parallel, delayed

from src.data_loader import TICKERS_B3, carregar_dados_ativo
from src.elder_engine import calcular_telas_elder
from src.options_backtest import simular_call_seco, simular_put_seco


def processar_ativo_bidirecional(ticker: str):
    """
    Executa o pipeline bidirecional:
    1. Baixa cotações
    2. Aplica Triple Screen (Filtro MME50)
    3. Simula CALL (alta) e PUT (baixa)
    4. Consolida retorno total e expectativa
    """
    try:
        diario, semanal = carregar_dados_ativo(ticker, start="2023-01-01")
        sinais = calcular_telas_elder(diario, semanal)

        # Simulações de derivativos
        t_call = simular_call_seco(sinais, dias_vencimento=20, alvo_multiplicacao=1.5)
        t_put = simular_put_seco(sinais, dias_vencimento=20, alvo_multiplicacao=1.5)

        # Métricas de Call
        ops_call = len(t_call)
        vit_call = (t_call['Retorno_Trade'] > 0).sum() if ops_call > 0 else 0
        tx_call = (vit_call / ops_call * 100) if ops_call > 0 else 0.0
        ret_call = (t_call['Retorno_Trade'].sum() * 100) if ops_call > 0 else 0.0

        # Métricas de Put
        ops_put = len(t_put)
        vit_put = (t_put['Retorno_Trade'] > 0).sum() if ops_put > 0 else 0
        tx_put = (vit_put / ops_put * 100) if ops_put > 0 else 0.0
        ret_put = (t_put['Retorno_Trade'].sum() * 100) if ops_put > 0 else 0.0

        # Resultado Combinado (Estratégia Bidirecional)
        total_ops = ops_call + ops_put
        ret_combinado = ret_call + ret_put

        return {
            "Ticker": ticker.replace(".SA", ""),
            "Trades CALL": ops_call,
            "Taxa CALL (%)": round(tx_call, 1),
            "Ret. CALL (%)": round(ret_call, 1),
            "Trades PUT": ops_put,
            "Taxa PUT (%)": round(tx_put, 1),
            "Ret. PUT (%)": round(ret_put, 1),
            "Ret. Total (%)": round(ret_combinado, 1)
        }
    except Exception as e:
        print(f"Erro ao processar {ticker}: {e}")
        return None


if __name__ == "__main__":
    print("\n=================================================================")
    print("INICIANDO BACKTEST BIDIRECIONAL B3 (CALL + PUT - TRIPLE SCREEN)")
    print("Processamento paralelo controlado: 2 núcleos (n_jobs=2)")
    print("=================================================================\n")

    resultados = Parallel(n_jobs=2, verbose=5)(
        delayed(processar_ativo_bidirecional)(ticker) for ticker in TICKERS_B3
    )

    dados_validos = [r for r in resultados if r is not None]
    df_ranking = pd.DataFrame(dados_validos)

    # Ordena pelo Retorno Total Combinado
    df_ranking = df_ranking.sort_values(by="Ret. Total (%)", ascending=False).reset_index(drop=True)

    caminho_csv = os.path.join("data", "ranking_bidirecional.csv")
    df_ranking.to_csv(caminho_csv, index=False)

    print("\n=================================================================")
    print("RANKING CONSOLIDADO BIDIRECIONAL (CALL + PUT)")
    print("=================================================================")
    print(df_ranking.to_string(index=False))
    print(f"\nPlanilha completa salva em: {caminho_csv}")