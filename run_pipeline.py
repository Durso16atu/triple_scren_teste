import os
import pandas as pd
from joblib import Parallel, delayed
from src.data_loader import TICKERS_B3, carregar_dados_ativo
from src.elder_engine import calcular_telas_elder
from src.options_backtest import simular_call_seco

def processar_ativo(ticker: str):
    """
    Executa o pipeline completo para um único ativo:
    Download -> Telas de Elder -> Simulação de Call a Seco.
    """
    try:
        diario, semanal = carregar_dados_ativo(ticker, start="2023-01-01")
        sinais = calcular_telas_elder(diario, semanal)
        trades = simular_call_seco(sinais, dias_vencimento=20, alvo_multiplicacao=1.5)
        
        if trades.empty:
            return None
            
        total_ops = len(trades)
        vitorias = (trades['Retorno_Trade'] > 0).sum()
        pós = (trades['Retorno_Trade'] <= -0.9).sum()
        taxa_acerto = (vitorias / total_ops) * 100
        retorno_acumulado = trades['Retorno_Trade'].sum() * 100
        retorno_medio = trades['Retorno_Trade'].mean() * 100
        
        # Expectativa matemática por trade: E = (p * Ganho) - ((1-p) * Perda)
        p = vitorias / total_ops
        ganho_medio = trades[trades['Retorno_Trade'] > 0]['Retorno_Trade'].mean() if vitorias > 0 else 0
        perda_media = abs(trades[trades['Retorno_Trade'] <= 0]['Retorno_Trade'].mean()) if (total_ops - vitorias) > 0 else 0
        expectativa = (p * ganho_medio) - ((1 - p) * perda_media)

        return {
            "Ticker": ticker.replace(".SA", ""),
            "Trades": total_ops,
            "Acertos (+150%)": vitorias,
            "Pó (-100%)": pós,
            "Taxa Acerto (%)": round(taxa_acerto, 1),
            "Ret. Médio (%)": round(retorno_medio, 1),
            "Ret. Total (%)": round(retorno_acumulado, 1),
            "Expectativa (E)": round(expectativa, 3)
        }
    except Exception as e:
        print(f"Erro ao processar {ticker}: {e}")
        return None

if __name__ == "__main__":
    print("\n=================================================================")
    print("INICIANDO BACKTEST B3 (TRIPLE SCREEN + CALL A SECO)")
    print("Contenção de hardware: Limitado rigidamente a 2 threads (n_jobs=2)")
    print("=================================================================\n")

    # Execução controlada para respeitar os 2 núcleos físicos e 8 GB RAM
    resultados = Parallel(n_jobs=2, verbose=5)(
        delayed(processar_ativo)(ticker) for ticker in TICKERS_B3
    )

    # Filtra eventuais nulos e monta tabela consolidada
    dados_validos = [r for r in resultados if r is not None]
    df_ranking = pd.DataFrame(dados_validos)

    # Ordena pelo melhor retorno total
    df_ranking = df_ranking.sort_values(by="Ret. Total (%)", ascending=False).reset_index(drop=True)

    # Salva o resultado em CSV dentro da pasta data/
    caminho_csv = os.path.join("data", "ranking_20_ativos.csv")
    df_ranking.to_csv(caminho_csv, index=False)

    print("\n=================================================================")
    print("RANKING CONSOLIDADO DOS 20 ATIVOS DA B3 (Ordenado por Retorno Total)")
    print("=================================================================")
    print(df_ranking.to_string(index=False))
    print(f"\nRelatório completo salvo em: {caminho_csv}")