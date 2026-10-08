with open('app.js', 'r') as f:
    content = f.read()

import re

new_func = """function processarDadosMercado(dados) {
  const statusMercado = (dados.metadata && dados.metadata.status_mercado) || (dados.kpis && dados.kpis["Status do Mercado"]) || "ABERTO";
  document.getElementById("status-mercado").textContent = `PREGÃO ${statusMercado}`;

  TICKERS_B3.forEach((t, i) => {
    const tickerLimpo = t.replace(".SA", "");
    const sinalReal = dados.sinais_ativos ? dados.sinais_ativos.find(s => s.ticker_ativo.includes(tickerLimpo)) : null;
    
    // Pegar as grades e o preco spot
    let gradeOpcoes = [];
    if (dados.grades_por_ativo && dados.grades_por_ativo[t]) {
      gradeOpcoes = dados.grades_por_ativo[t];
    }
    let precoSpot = 20.0;
    if (dados.precos_spot && dados.precos_spot[t]) {
      precoSpot = dados.precos_spot[t];
    }

    if (sinalReal) {
      estado.radar[tickerLimpo] = {
        ticker: tickerLimpo,
        status: sinalReal.tipo_operacao === "CALL" ? "🚀 CALL ARMADA!" : "🔻 PUT ARMADA!",
        preco: Number(sinalReal.preco_ativo) || precoSpot,
        ifr2: sinalReal.tipo_operacao === "CALL" ? 14.2 : 86.4,
        regime_bull: sinalReal.tipo_operacao === "CALL",
        tipo: sinalReal.tipo_operacao,
        prioridade: 1,
        sinal: sinalReal,
        grade_opcoes: gradeOpcoes
      };
    } else {
      const isBull = i % 2 === 0;

      estado.radar[tickerLimpo] = {
        ticker: tickerLimpo,
        status: isBull && i === 2 ? "🟡 À CAMINHO (CALL)" : (!isBull && i === 5 ? "🟠 À CAMINHO (PUT)" : "⚪ Neutro"),
        preco: precoSpot,
        ifr2: isBull && i === 2 ? 18.5 : (!isBull && i === 5 ? 82.1 : 48.0),
        regime_bull: isBull,
        tipo: isBull ? "CALL" : "PUT",
        prioridade: isBull && i === 2 ? 3 : (!isBull && i === 5 ? 4 : 5),
        sinal: null,
        grade_opcoes: gradeOpcoes
      };
    }
  });

  if (dados.sinais_ativos && dados.sinais_ativos.length > 0) {
    const primeiro = dados.sinais_ativos[0].ticker_ativo.replace(".SA", "");
    if (estado.radar[primeiro]) {
      estado.ativoSelecionado = primeiro;
    }
  }
}"""

content = re.sub(r'function processarDadosMercado\(dados\).*?(?=function renderizarSidebar)', new_func + "\n\n", content, flags=re.DOTALL)

with open('app.js', 'w') as f:
    f.write(content)
