# B3 Triple Screen: Arquitetura Multiagente

A arquitetura do projeto **B3 Triple Screen** opera sob um modelo distribuído e especializado com base em 4 agentes autônomos. Esta documentação formaliza a Matriz RACI, os protocolos de comunicação inter-agente e as políticas de isolamento de domínio (Separation of Concerns).

## 1. Agentes Especializados

1. **Market Data Agent (MDA)**: Responsável exclusivamente por extrair cotações, dados históricos e consolidar feeds externos (yfinance/B3).
2. **Strategy Agent (SA)**: Responsável por processar a lógica matemática e os setups gráficos (Elder Triple Screen, EMA 200, IFR-2, Gatilho/Stop).
3. **Options Pricing Agent (OPA)**: Motor atuarial puro (Black-Scholes-Merton) responsável pela geração da grade de opções B3, DTE dinâmico e gregas.
4. **Telemetry Agent (TA)**: Gerenciador de side-effects, I/O externo e disparo de payloads RESTful (Google Sheets Webhook, UI JSON generation).

## 2. Matriz RACI

| Tarefa / Operação | Market Data (MDA) | Strategy (SA) | Options Pricing (OPA) | Telemetry (TA) |
| :--- | :---: | :---: | :---: | :---: |
| Download de séries OHLCV (yfinance) | **R, A** | I | I | I |
| Detecção Setup Triple Screen & Indicadores | I | **R, A** | C | I |
| Cálculo do DTE e Feriados | I | I | **R, A** | I |
| Precificação e Grade B3 (Strikes/Gregas) | I | I | **R, A** | I |
| Despacho Webhook e arquivo JSON | I | I | I | **R, A** |

*(R: Responsible / A: Accountable / C: Consulted / I: Informed)*

## 3. Protocolos de Comunicação (Schemas & Contratos)

### MDA -> SA & OPA
- **Input**: Lista de Tickers e Intervalos de Datas.
- **Artefato Gerado**: Pandas DataFrame puro contendo séries OHLCV indexadas cronologicamente, com imputação de NaNs aplicada.
- **Critério de Aceite**: O output não possui dados faltantes, séries temporais vazias disparam Exception imediata (fail-fast) ao invés de silenciosa.

### SA -> TA
- **Input**: OHLCV DataFrames do MDA.
- **Artefato Gerado**: Dicionário/JSON de status técnico contendo: `{"ticker": "PETR4", "setup_armado": true, "gatilho": 35.50, "stop": 34.00, "ifr2": 15.4}`.
- **Critério de Aceite**: Sinal armados obedecem rigorosamente à MME 200 e filtros de IFR-2.

### OPA -> TA
- **Input**: Spot Price atualizado, taxa Selic/CDI, e Volatilidade Histórica (anualizada).
- **Artefato Gerado**: Lista estruturada contendo as 5 opções oficiais da B3 (ATM, ± ITM, ± OTM), prêmios (BS), Gregas e delta-targeting (0.30 a 0.45 marcado como "RECOMENDADA").
- **Critério de Aceite**: DTE corretamente calculado considerando feriados. Strikes seguindo os degraus exatos de listagem B3. Sem multiplicidade espúria.

### TA -> Sistema Externo (Google Sheets)
- **Input**: Consolidação dos artefatos do SA e OPA.
- **Artefato Gerado**: Dispatch via `requests.post` e sobreposição estrita em `metricas_resumo.json`.
- **Critério de Aceite**: Timeout explícito configurado; payloads validados; fallback graceful para "PREGÃO FECHADO" caso mercado inativo.

## 4. Regra Estrita de Não-Sobreposição (Separation of Concerns)

- O **Market Data Agent (MDA)** não realiza nenhum recálculo de indicadores, limitando-se apenas à extração bruta.
- O **Strategy Agent (SA)** jamais possui dependência de rede (não dispara requests para Webhooks).
- O **Options Pricing Agent (OPA)** opera em modelo *sandbox* puro. Não sabe e não precisa saber se o dado vem do Yahoo Finance ou de CSV local. É uma calculadora atuarial stateless.
- O **Telemetry Agent (TA)** não audita a veracidade matemática dos dados, não ajusta strikes e não refaz avaliações de IFR. Seu papel é agregação e pipeline/streaming.
