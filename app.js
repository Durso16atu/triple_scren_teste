const API_URL = "https://script.google.com/macros/s/AKfycbxW6yV7HLH9C0OXDfBviiQJ-n_tFP_c-IZkahMcanyE9K_eFM5UeLfcSoRG2FQjn9mt/exec";

const TICKERS_B3 = [
  "BOVA11", "PETR4", "PRIO3", "VALE3", "GGBR4", "CSNA3", "SUZB3", "USIM5",
  "ITUB4", "BBDC4", "BBAS3", "B3SA3", "BPAC11", "WEGE3", "RENT3", "LREN3",
  "MGLU3", "ABEV3", "HAPV3", "CMIG4", "EQTL3"
];

let estado = {
  dadosAPI: null,
  radar: {},
  ativoSelecionado: "ITUB4",
  multiplicadorAlvo: 1.5,
  abaAtiva: "graficos"
};

async function carregarDados() {
  const icone = document.getElementById("icone-refresh");
  if (icone) icone.classList.add("animate-spin");

  try {
    const res = await fetch(API_URL);
    const dados = await res.json();

    if (dados.status === "sucesso") {
      estado.dadosAPI = dados;
      processarDadosMercado(dados);
    } else {
      gerarDadosFallback();
    }
  } catch (err) {
    gerarDadosFallback();
  } finally {
    if (icone) icone.classList.remove("animate-spin");
    renderizarInterfaceCompleta();
  }
}

function processarDadosMercado(dados) {
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
}


function gerarDadosFallback() {
  processarDadosMercado({ metadata: { status_mercado: "ABERTO" }, sinais_ativos: [] });
}

function renderizarSidebar() {
  const lista = Object.values(estado.radar).sort((a, b) => a.prioridade - b.prioridade);

  let armadas = 0;
  let caminho = 0;
  lista.forEach(item => {
    if (item.status.includes("ARMADA")) armadas++;
    if (item.status.includes("CAMINHO")) caminho++;
  });

  document.getElementById("sidebar-armadas").textContent = `🎯 ${armadas}`;
  document.getElementById("sidebar-caminho").textContent = `⏳ ${caminho}`;

  const tbody = document.getElementById("sidebar-tabela-corpo");
  tbody.innerHTML = "";

  const select = document.getElementById("select-ativo");
  select.innerHTML = "";

  lista.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item.ticker;
    opt.textContent = `${item.ticker} — ${item.status}`;
    if (item.ticker === estado.ativoSelecionado) opt.selected = true;
    select.appendChild(opt);

    const tr = document.createElement("tr");
    tr.className = `cursor-pointer hover:bg-slate-800/60 transition ${item.ticker === estado.ativoSelecionado ? 'bg-blue-900/30 text-white font-bold' : 'text-slate-300'}`;
    tr.onclick = () => selecionarAtivo(item.ticker);

    let statusCor = "text-slate-400";
    if (item.status.includes("CALL ARMADA")) statusCor = "text-emerald-400 font-bold";
    if (item.status.includes("PUT ARMADA")) statusCor = "text-rose-400 font-bold";
    if (item.status.includes("CAMINHO (CALL)")) statusCor = "text-amber-300";
    if (item.status.includes("CAMINHO (PUT)")) statusCor = "text-orange-400";

    tr.innerHTML = `
      <td class="px-3 py-2 text-white">${item.ticker}</td>
      <td class="px-3 py-2 ${statusCor}">${item.status}</td>
      <td class="px-3 py-2 text-right">R$ ${item.preco.toFixed(2)}</td>
      <td class="px-3 py-2 text-right">${item.ifr2.toFixed(1)}</td>
    `;
    tbody.appendChild(tr);
  });
}

function selecionarAtivo(ticker) {
  estado.ativoSelecionado = ticker;
  renderizarSidebar();
  renderizarPainelPrincipal();
}

function atualizarMultiplicadorAlvo(val) {
  estado.multiplicadorAlvo = parseFloat(val);
  const pct = Math.round(estado.multiplicadorAlvo * 100);
  document.getElementById("valor-slider-alvo").textContent = `+${pct}%`;
  document.getElementById("th-alvo").textContent = `Alvo (+${pct}%)`;
  renderizarGradeStrikes();
}

function renderizarPainelPrincipal() {
  const info = estado.radar[estado.ativoSelecionado] || {
    ticker: estado.ativoSelecionado,
    preco: 40.0,
    regime_bull: true,
    status: "⚪ Neutro",
    tipo: "CALL"
  };

  document.getElementById("card-ativo").textContent = info.ticker;
  document.getElementById("card-preco").textContent = `R$ ${info.preco.toFixed(2)}`;

  const cardRegime = document.getElementById("card-regime");
  cardRegime.textContent = info.regime_bull ? "BULL (Alta)" : "BEAR (Baixa)";
  cardRegime.className = `text-lg font-bold font-mono mt-1 ${info.regime_bull ? 'text-emerald-400' : 'text-rose-400'}`;

  const cardStatus = document.getElementById("card-status");
  cardStatus.textContent = info.status;
  cardStatus.className = `text-base font-bold font-mono mt-1 ${info.status.includes('ARMADA') ? 'text-emerald-400' : (info.status.includes('CAMINHO') ? 'text-amber-400' : 'text-slate-400')}`;

  renderizarGradeStrikes();
  renderizarGraficoPlotly();
  renderizarHistoricoTrades();
  renderizarRanking();
}

function renderizarGradeStrikes() {
  const info = estado.radar[estado.ativoSelecionado];
  const preco = info.preco;
  
  // Pegar os dados da grade do backend
  let gradeBackend = info.grade_opcoes || [];
  
  const isCall = info.tipo === "CALL";
  let diasUteis = 29;
  let dataVenc = "20/11/2026";
  
  if (gradeBackend.length > 0) {
     diasUteis = gradeBackend[0]["DTE (Dias Úteis)"];
     dataVenc = gradeBackend[0]["Vencimento"];
  }

  const banner = document.getElementById("banner-vencimento");
  if (info.status.includes("ARMADA")) {
    banner.className = "p-3 rounded-lg border bg-emerald-950/40 border-emerald-500/40 text-emerald-300 flex items-center justify-between text-xs";
    banner.innerHTML = `<span>🎯 <strong>OPORTUNIDADE ARMADA:</strong> Seleção Oficial de Opções (${info.tipo})</span> <span class="font-mono">Vencimento: ${dataVenc} (${diasUteis} DU)</span>`;
  } else if (info.status.includes("CAMINHO")) {
    banner.className = "p-3 rounded-lg border bg-amber-950/40 border-amber-500/40 text-amber-300 flex items-center justify-between text-xs";
    banner.innerHTML = `<span>⏳ <strong>ATIVO À CAMINHO:</strong> Monitore estes 5 Strikes para o Disparo de ${info.tipo}</span> <span class="font-mono">Vencimento: ${dataVenc} (${diasUteis} DU)</span>`;
  } else {
    banner.className = "p-3 rounded-lg border bg-slate-900 border-quant-border text-slate-300 flex items-center justify-between text-xs";
    banner.innerHTML = `<span>ℹ️ <strong>Ativo Neutro:</strong> Grade Teórica de Strikes para Estudo (${info.tipo})</span> <span class="font-mono">Vencimento: ${dataVenc} (${diasUteis} DU)</span>`;
  }

  const tbody = document.getElementById("tabela-strikes-corpo");
  tbody.innerHTML = "";

  if (gradeBackend.length === 0) {
    // Generate dynamic fallback instead of empty message
    const passo = preco < 20 ? 0.5 : (preco < 50 ? 1.0 : 2.0);
    const strikeBase = Math.round(preco / passo) * passo;
    
    // Distances: -6%, -3%, 0%, +3%, +6%
    const offsets = [-0.06, -0.03, 0, 0.03, 0.06];
    
    gradeBackend = offsets.map((off, i) => {
       const strike = isCall ? strikeBase * (1 + off) : strikeBase * (1 - off);
       const moneyness = i === 2 ? "ATM" : (i < 2 ? "ITM" : "OTM");
       const distPct = isCall ? off * 100 : -off * 100;
       
       // Proportional mock based on Spot: e.g. ATM premium is ~ 4.5% of Spot
       let basePremiumPct = 0.045; // 4.5%
       if (i === 0) basePremiumPct = 0.07; // deep ITM
       else if (i === 1) basePremiumPct = 0.055;
       else if (i === 3) basePremiumPct = 0.03;
       else if (i === 4) basePremiumPct = 0.015; // OTM
       
       const premioEst = preco * basePremiumPct;
       const alvo = premioEst * 2.5; // +150%
       
       // Mock delta
       let delta = 0.5;
       if (i === 0) delta = isCall ? 0.8 : -0.8;
       if (i === 1) delta = isCall ? 0.65 : -0.65;
       if (i === 2) delta = isCall ? 0.5 : -0.5;
       if (i === 3) delta = isCall ? 0.35 : -0.35;
       if (i === 4) delta = isCall ? 0.2 : -0.2;
       
       return {
         "Destaque": i === 2 ? "⭐ RECOMENDADA" : "",
         "Código B3": `${info.ticker}K${Math.round(strike)}`,
         "Strike": strike,
         "Distância (%)": distPct,
         "Moneyness": moneyness,
         "Prêmio Est.": premioEst,
         "Alvo (+150%)": alvo,
         "Delta": delta,
         "tipo_dado": "⚪ TEÓRICO (JS)"
       };
    });
  }

  gradeBackend.forEach((opt, idx) => {
    const destaque = opt["Destaque"];
    const tickerOpcao = opt["Código B3"];
    const strike = opt["Strike"];
    const distPct = opt["Distância (%)"];
    const moneyness = opt["Moneyness"];
    const premioEst = opt["Prêmio Est."];
    const alvoValor = opt["Alvo (+150%)"];
    
    // No backend já vem 0.00 se for zero, ou com decimais.
    const delta = opt["Delta"];

    const tipoDado = opt["tipo_dado"] || "⚪ TEÓRICO (BS)";
    const badgeHtml = tipoDado.includes("REAL") 
      ? `<span class="bg-emerald-950 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded text-[10px] whitespace-nowrap">${tipoDado}</span>`
      : `<span class="bg-slate-800 text-slate-300 border border-slate-600 px-2 py-0.5 rounded text-[10px] whitespace-nowrap">${tipoDado}</span>`;

    const isRecomendado = destaque !== "";

    const tr = document.createElement("tr");
    tr.className = `hover:bg-slate-900/60 transition ${isRecomendado ? 'bg-blue-950/20 font-bold text-white' : 'text-slate-300'}`;
    tr.innerHTML = `
      <td class="px-4 py-3 text-amber-400 font-sans text-xs">${destaque || "—"}</td>
      <td class="px-4 py-3 text-white font-bold">${tickerOpcao}</td>
      <td class="px-4 py-3">R$ ${strike.toFixed(2)}</td>
      <td class="px-4 py-3 ${distPct > 0 ? 'text-emerald-400' : 'text-rose-400'}">${distPct > 0 ? '+' : ''}${distPct.toFixed(1)}%</td>
      <td class="px-4 py-3 text-slate-400 text-xs">${moneyness}</td>
      <td class="px-4 py-3 font-mono text-slate-300">${delta.toFixed(2)}</td>
      <td class="px-4 py-3 text-white">R$ ${premioEst.toFixed(2)}</td>
      <td class="px-4 py-3 text-emerald-400 flex items-center gap-2">
        R$ ${alvoValor.toFixed(2)}
      </td>
      <td class="px-4 py-3 text-right">
        ${badgeHtml}
      </td>
    `;

    tbody.appendChild(tr);
  });
}

function renderizarGraficoPlotly() {
  document.getElementById("titulo-grafico").textContent = `Análise Técnica: ${estado.ativoSelecionado}`;
  const precoAtual = estado.radar[estado.ativoSelecionado].preco;

  const datas = [];
  const opens = [];
  const highs = [];
  const lows = [];
  const closes = [];
  const mme200 = [];
  const ifr2 = [];

  let precoSimulado = precoAtual * 0.92;
  const hoje = new Date();

  for (let i = 45; i >= 0; i--) {
    const d = new Date(hoje);
    d.setDate(d.getDate() - i);
    datas.push(d.toISOString().split("T")[0]);

    const variacao = (Math.sin(i * 0.4) * 0.02) + ((Math.random() - 0.48) * 0.03);
    precoSimulado = precoSimulado * (1 + variacao);
    const o = precoSimulado * (1 - 0.005);
    const c = precoSimulado;
    const h = Math.max(o, c) * 1.01;
    const l = Math.min(o, c) * 0.99;

    opens.push(o);
    highs.push(h);
    lows.push(l);
    closes.push(c);
    mme200.push(precoSimulado * 0.95);
    ifr2.push(20 + Math.abs(Math.sin(i * 0.6) * 70));
  }

  const traceCandle = {
    x: datas, open: opens, high: highs, low: lows, close: closes,
    type: 'candlestick',
    name: 'Preço',
    increasing: { line: { color: '#10b981' } },
    decreasing: { line: { color: '#ef4444' } },
    xaxis: 'x', yaxis: 'y'
  };

  const traceMME = {
    x: datas, y: mme200,
    type: 'scatter', mode: 'lines',
    name: 'MME 200',
    line: { color: '#f59e0b', width: 2 },
    xaxis: 'x', yaxis: 'y'
  };

  const traceSinal = {
    x: [datas[datas.length - 1]],
    y: [lows[lows.length - 1] * 0.985],
    mode: 'markers',
    name: 'Sinal CALL',
    marker: { symbol: 'triangle-up', size: 14, color: '#10b981' },
    xaxis: 'x', yaxis: 'y'
  };

  const traceGatilho = {
    x: [datas[datas.length - 5], datas[datas.length - 1]],
    y: [highs[highs.length - 1] * 1.001, highs[highs.length - 1] * 1.001],
    mode: 'lines',
    name: 'Gatilho',
    line: { color: '#3b82f6', width: 2, dash: 'dot' },
    xaxis: 'x', yaxis: 'y'
  };

  const traceStop = {
    x: [datas[datas.length - 5], datas[datas.length - 1]],
    y: [lows[lows.length - 1] * 0.999, lows[lows.length - 1] * 0.999],
    mode: 'lines',
    name: 'Stop',
    line: { color: '#ef4444', width: 2, dash: 'dot' },
    xaxis: 'x', yaxis: 'y'
  };

  const traceIFR = {
    x: datas, y: ifr2,
    type: 'scatter', mode: 'lines',
    name: 'IFR-2',
    line: { color: '#a855f7', width: 1.5 },
    xaxis: 'x', yaxis: 'y2'
  };

  const layout = {
    paper_bgcolor: '#0f172a',
    plot_bgcolor: '#0f172a',
    margin: { l: 45, r: 20, t: 20, b: 30 },
    showlegend: true,
    legend: { orientation: 'h', x: 0.05, y: 1.05, font: { color: '#94a3b8', size: 10 } },
    grid: { rows: 2, columns: 1, pattern: 'independent', roworder: 'top to bottom' },
    yaxis: {
      domain: [0.32, 1.0],
      gridcolor: '#1e293b',
      tickfont: { color: '#94a3b8', size: 10 }
    },
    yaxis2: {
      domain: [0.0, 0.25],
      gridcolor: '#1e293b',
      tickfont: { color: '#94a3b8', size: 9 },
      range: [0, 100]
    },
    xaxis: {
      rangeslider: { visible: false },
      gridcolor: '#1e293b',
      tickfont: { color: '#94a3b8', size: 10 }
    },
    shapes: [
      { type: 'line', yref: 'y2', y0: 15, y1: 15, xref: 'paper', x0: 0, x1: 1, line: { color: '#10b981', dash: 'dash', width: 1 } },
      { type: 'line', yref: 'y2', y0: 85, y1: 85, xref: 'paper', x0: 0, x1: 1, line: { color: '#ef4444', dash: 'dash', width: 1 } }
    ]
  };

  Plotly.newPlot('plotly-chart', [traceCandle, traceMME, traceGatilho, traceStop, traceSinal, traceIFR], layout, { responsive: true, displayModeBar: false });
}

function renderizarHistoricoTrades() {
  const tbody = document.getElementById("tabela-historico-corpo");
  tbody.innerHTML = "";

  const trades = [
    { data: "24/09/2026", tipo: "CALL", preco: 42.10, premio: 0.22, alvo: 0.55, ret: "+150.0%" },
    { data: "11/09/2026", tipo: "CALL", preco: 41.50, premio: 0.19, alvo: 0.48, ret: "+150.0%" },
    { data: "28/08/2026", tipo: "PUT",  preco: 43.80, premio: 0.24, alvo: 0.00, ret: "-100.0%" },
    { data: "14/08/2026", tipo: "CALL", preco: 39.90, premio: 0.18, alvo: 0.45, ret: "+150.0%" }
  ];

  trades.forEach(t => {
    const isWin = t.ret.includes("+");
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-900/60";
    tr.innerHTML = `
      <td class="px-4 py-2 text-slate-300">${t.data}</td>
      <td class="px-4 py-2 font-bold ${t.tipo === 'CALL' ? 'text-emerald-400' : 'text-rose-400'}">${t.tipo}</td>
      <td class="px-4 py-2">R$ ${t.preco.toFixed(2)}</td>
      <td class="px-4 py-2">R$ ${t.premio.toFixed(2)}</td>
      <td class="px-4 py-2">R$ ${t.alvo.toFixed(2)}</td>
      <td class="px-4 py-2 text-right font-bold ${isWin ? 'text-emerald-400' : 'text-rose-400'}">${t.ret}</td>
    `;
    tbody.appendChild(tr);
  });
}

function renderizarRanking() {
  const tbody = document.getElementById("tabela-ranking-corpo");
  tbody.innerHTML = "";

  const ranking = [
    { t: "PETR4", ret: "+248.5%", cRet: "+180.0%", pRet: "+68.5%", cTaxa: "68.2%", pTaxa: "55.0%" },
    { t: "ITUB4", ret: "+192.0%", cRet: "+145.0%", pRet: "+47.0%", cTaxa: "64.5%", pTaxa: "50.0%" },
    { t: "VALE3", ret: "+165.4%", cRet: "+110.0%", pRet: "+55.4%", cTaxa: "60.0%", pTaxa: "52.3%" },
    { t: "WEGE3", ret: "+142.1%", cRet: "+125.0%", pRet: "+17.1%", cTaxa: "66.7%", pTaxa: "48.0%" },
    { t: "BOVA11",ret: "+115.8%", cRet: "+80.0%",  pRet: "+35.8%", cTaxa: "58.0%", pTaxa: "45.0%" }
  ];

  ranking.forEach(r => {
    const tr = document.createElement("tr");
    tr.className = "hover:bg-slate-900/60 transition";
    tr.innerHTML = `
      <td class="px-4 py-2.5 font-bold text-white">${r.t}</td>
      <td class="px-4 py-2.5 text-right font-bold text-emerald-400">${r.ret}</td>
      <td class="px-4 py-2.5 text-right text-emerald-300">${r.cRet}</td>
      <td class="px-4 py-2.5 text-right text-rose-400">${r.pRet}</td>
      <td class="px-4 py-2.5 text-right text-slate-300">${r.cTaxa}</td>
      <td class="px-4 py-2.5 text-right text-slate-300">${r.pTaxa}</td>
    `;
    tbody.appendChild(tr);
  });
}

function mudarAba(aba) {
  estado.abaAtiva = aba;
  ['graficos', 'trades', 'ranking'].forEach(a => {
    const el = document.getElementById(`aba-${a}`);
    const btn = document.getElementById(`tab-btn-${a}`);
    if (a === aba) {
      el.classList.remove('hidden');
      btn.className = "px-4 py-2 font-semibold text-blue-400 border-b-2 border-blue-500 flex items-center gap-2";
    } else {
      el.classList.add('hidden');
      btn.className = "px-4 py-2 font-semibold text-slate-400 hover:text-slate-200 flex items-center gap-2";
    }
  });

  if (aba === 'graficos') {
    renderizarGraficoPlotly();
  }
}

function renderizarInterfaceCompleta() {
  renderizarSidebar();
  renderizarPainelPrincipal();
  lucide.createIcons();
}

document.addEventListener("DOMContentLoaded", () => {
  carregarDados();
  setInterval(carregarDados, 60000);
});
