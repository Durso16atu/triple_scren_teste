import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.data_loader import TICKERS_B3, carregar_dados_ativo
from src.elder_engine import calcular_telas_elder
from src.options_backtest import simular_call_seco, simular_put_seco
from src.b3_options_selector import gerar_grade_5_strikes

# Configuração da página web
st.set_page_config(
    page_title="B3 Triple Screen Options | Terminal Quant",
    page_icon="📈",
    layout="wide"
)

# =============================================================================
# 1. FUNÇÃO DE ESCANEAMENTO RÁPIDO DO RADAR DA B3 (SIDEBAR)
# =============================================================================
@st.cache_data(ttl=900)
def escanear_mercado_b3(tickers):
    radar = []
    dados_carregados = {}

    for t in tickers:
        try:
            diario, semanal = carregar_dados_ativo(t, start="2023-01-01")
            sinais = calcular_telas_elder(diario, semanal)
            dados_carregados[t] = (diario, semanal, sinais)

            ult = sinais.iloc[-1]
            preco = ult['Close']
            ifr2 = ult['IFR2']
            regime_bull = ult['Regime_Bull']
            maree_alta = ult['Maree_Alta']
            maree_baixa = ult['Maree_Baixa']

            if ult['Gatilho_Compra']:
                status = "🚀 CALL ARMADA!"
                prioridade = 1
                tipo_sugestao = "CALL"
            elif ult['Gatilho_Venda']:
                status = "🔻 PUT ARMADA!"
                prioridade = 2
                tipo_sugestao = "PUT"
            elif regime_bull and maree_alta and ifr2 < 20:
                status = "🟡 À CAMINHO (CALL)"
                prioridade = 3
                tipo_sugestao = "CALL"
            elif (not regime_bull) and maree_baixa and ifr2 > 80:
                status = "🟠 À CAMINHO (PUT)"
                prioridade = 4
                tipo_sugestao = "PUT"
            else:
                status = "⚪ Neutro"
                prioridade = 5
                tipo_sugestao = "CALL" if regime_bull else "PUT"

            radar.append({
                "Ticker": t.replace(".SA", ""),
                "Status": status,
                "Preço": preco,
                "IFR-2": round(ifr2, 1),
                "_tipo_sugestao": tipo_sugestao,
                "_prioridade": prioridade,
                "_full_ticker": t
            })
        except Exception:
            continue

    df_radar = pd.DataFrame(radar)
    if not df_radar.empty:
        df_radar = df_radar.sort_values(by=["_prioridade", "Ticker"]).reset_index(drop=True)
    return df_radar, dados_carregados

# =============================================================================
# 2. BARRA LATERAL (SIDEBAR COM GRID DO OPERADOR)
# =============================================================================
st.sidebar.title("⚡ Radar de Agilidade B3")

with st.sidebar:
    with st.spinner("Escaneando mercado B3..."):
        df_radar, dados_ativos = escanear_mercado_b3(TICKERS_B3)

    armadas = (df_radar['Status'].str.contains("ARMADA")).sum()
    a_caminho = (df_radar['Status'].str.contains("CAMINHO")).sum()
    
    col_s1, col_s2 = st.columns(2)
    col_s1.metric("Armadas Hoje", f"🎯 {armadas}")
    col_s2.metric("À Caminho", f"⏳ {a_caminho}")

    st.markdown("### 📋 Grid Operacional:")
    st.dataframe(
        df_radar[["Ticker", "Status", "Preço", "IFR-2"]].style.format({
            "Preço": "R$ {:.2f}",
            "IFR-2": "{:.1f}"
        }),
        height=360,
        use_container_width=True
    )

    st.markdown("---")
    st.subheader("🔍 Ativo Selecionado:")
    
    opcoes_display = {
        row["_full_ticker"]: f"{row['Ticker']} — {row['Status']}"
        for _, row in df_radar.iterrows()
    }

    ticker_selecionado = st.selectbox(
        "Selecione para detalhar:",
        options=list(opcoes_display.keys()),
        format_func=lambda x: opcoes_display.get(x, x),
        index=0
    )

    alvo_lucro = st.slider(
        "Alvo de Ganho Explosivo (% do Prêmio):",
        min_value=1.0,
        max_value=3.0,
        value=1.5,
        step=0.25,
        format="+%.0f00%%"
    )

# =============================================================================
# 3. PAINEL PRINCIPAL (DASHBOARD & GRADE DE 5 STRIKES)
# =============================================================================
st.title("📈 Terminal Quant — Triple Screen & Opções")
st.caption("Estratégia Bidirecional Assimétrica de Alexander Elder com Seletor de Regime Macro (MME 200)")

df_diario, df_semanal, df_sinais = dados_ativos[ticker_selecionado]
trades_call = simular_call_seco(df_sinais, alvo_multiplicacao=alvo_lucro)
trades_put = simular_put_seco(df_sinais, alvo_multiplicacao=alvo_lucro)

ultimo_registro = df_sinais.iloc[-1]
regime_atual = "BULL (Alta)" if ultimo_registro['Regime_Bull'] else "BEAR (Baixa)"
info_ticker = df_radar[df_radar['_full_ticker'] == ticker_selecionado].iloc[0]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Ativo", info_ticker['Ticker'])
c2.metric("Último Preço", f"R$ {ultimo_registro['Close']:.2f}")
c3.metric("Regime Macro", regime_atual)
c4.metric("Status Operacional", info_ticker['Status'])

st.markdown("---")

# =============================================================================
# 4. GRADE DE 5 STRIKES RECOMENDADOS (PARA ACOMPANHAMENTO VISUAL)
# =============================================================================
tipo_derivativo = info_ticker['_tipo_sugestao']
preco_atual = ultimo_registro['Close']
vol_atual = df_sinais['Close'].pct_change().rolling(30).std().iloc[-1] * np.sqrt(252)
if np.isnan(vol_atual):
    vol_atual = 0.30

df_grade, data_venc, dias_uteis = gerar_grade_5_strikes(
    ticker=info_ticker['Ticker'],
    preco_atual=preco_atual,
    volatilidade=vol_atual,
    tipo=tipo_derivativo
)

if "ARMADA" in info_ticker['Status']:
    st.success(f"### 🎯 OPORTUNIDADE ARMADA: Seleção Oficial de Opções ({tipo_derivativo}) — Vencimento: {data_venc.strftime('%d/%m/%Y')} ({dias_uteis} dias úteis)")
elif "CAMINHO" in info_ticker['Status']:
    st.warning(f"### ⏳ ATIVO À CAMINHO: Monitore estes 5 Strikes para o Disparo de {tipo_derivativo} — Vencimento: {data_venc.strftime('%d/%m/%Y')} ({dias_uteis} dias úteis)")
else:
    st.info(f"### ℹ️ Ativo Neutro: Grade Teórica de Strikes para Estudo ({tipo_derivativo}) — Vencimento: {data_venc.strftime('%d/%m/%Y')} ({dias_uteis} dias úteis)")

# Exibe a tabela dos 5 strikes com formatação profissional
st.dataframe(
    df_grade[["Destaque", "Código B3", "Strike", "Distância (%)", "Moneyness", "Delta", "Prêmio Est.", "Alvo (+150%)"]].style.format({
        "Strike": "R$ {:.2f}",
        "Distância (%)": "{:+.1f}%",
        "Delta": "{:.2f}",
        "Prêmio Est.": "R$ {:.2f}",
        "Alvo (+150%)": "R$ {:.2f}"
    }),
    use_container_width=True
)

st.markdown("---")

# =============================================================================
# 5. ABAS DE VISUALIZAÇÃO GRÁFICA E HISTÓRICO
# =============================================================================
aba_graficos, aba_trades, aba_ranking = st.tabs(["📊 Gráficos Interativos", "📋 Histórico de Operações", "🏆 Ranking da Carteira"])

with aba_graficos:
    st.subheader(f"Análise Técnica: {info_ticker['Ticker']}")

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[0.7, 0.3],
        subplot_titles=("Preço Diário, MME 200 e Entradas", "Oscilador IFR-2 (Sobrevenda < 15 | Sobrecompra > 85)")
    )

    fig.add_trace(
        go.Candlestick(
            x=df_sinais.index,
            open=df_sinais['Open'],
            high=df_sinais['High'],
            low=df_sinais['Low'],
            close=df_sinais['Close'],
            name="Preço"
        ),
        row=1, col=1
    )

    fig.add_trace(
        go.Scatter(
            x=df_sinais.index,
            y=df_sinais['EMA200'],
            line=dict(color='orange', width=2),
            name="MME 200"
        ),
        row=1, col=1
    )

    compras = df_sinais[df_sinais['Gatilho_Compra'] == True]
    if not compras.empty:
        fig.add_trace(
            go.Scatter(
                x=compras.index,
                y=compras['Low'] * 0.98,
                mode='markers',
                marker=dict(symbol='triangle-up', size=12, color='green'),
                name="Sinal CALL"
            ),
            row=1, col=1
        )

    vendas = df_sinais[df_sinais['Gatilho_Venda'] == True]
    if not vendas.empty:
        fig.add_trace(
            go.Scatter(
                x=vendas.index,
                y=vendas['High'] * 1.02,
                mode='markers',
                marker=dict(symbol='triangle-down', size=12, color='red'),
                name="Sinal PUT"
            ),
            row=1, col=1
        )

    fig.add_trace(
        go.Scatter(
            x=df_sinais.index,
            y=df_sinais['IFR2'],
            line=dict(color='purple', width=1.5),
            name="IFR-2"
        ),
        row=2, col=1
    )

    fig.add_hline(y=15, line_dash="dash", line_color="green", row=2, col=1)
    fig.add_hline(y=85, line_dash="dash", line_color="red", row=2, col=1)

    fig.update_layout(
        height=600,
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        margin=dict(l=20, r=20, t=30, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)

with aba_trades:
    st.subheader("Histórico de Trades do Ativo")
    todos_trades = pd.concat([trades_call, trades_put]).sort_values(by="Data_Entrada", ascending=False)
    
    if todos_trades.empty:
        st.info("Nenhuma operação registrada para este papel.")
    else:
        vitorias = (todos_trades['Retorno_Trade'] > 0).sum()
        total = len(todos_trades)
        tx_acerto = (vitorias / total) * 100
        ret_total = todos_trades['Retorno_Trade'].sum() * 100

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total de Trades", total)
        m2.metric("Vitórias (+150%)", vitorias)
        m3.metric("Taxa de Acerto", f"{tx_acerto:.1f}%")
        m4.metric("Retorno Total", f"{ret_total:+.1f}%")

        st.dataframe(
            todos_trades.style.format({
                "Preco_Acao": "R$ {:.2f}",
                "Premio_Pago": "R$ {:.2f}",
                "Retorno_Trade": "{:+.1%}"
            }),
            use_container_width=True
        )

with aba_ranking:
    st.subheader("Performance Consolidada da Carteira B3")
    caminho_csv = os.path.join("data", "ranking_bidirecional.csv")
    if os.path.exists(caminho_csv):
        df_csv = pd.read_csv(caminho_csv)
        st.dataframe(
            df_csv.style.format({
                "Ret. Total (%)": "{:+.1f}%",
                "Ret. CALL (%)": "{:+.1f}%",
                "Ret. PUT (%)": "{:+.1f}%",
                "Taxa CALL (%)": "{:.1f}%",
                "Taxa PUT (%)": "{:.1f}%"
            }),
            use_container_width=True
        )