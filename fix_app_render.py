with open('app.js', 'r') as f:
    content = f.read()

import re

new_render = """function renderizarGradeStrikes() {
  const info = estado.radar[estado.ativoSelecionado];
  const preco = info.preco;
  
  // Pegar os dados da grade do backend
  let gradeBackend = info.grade_opcoes || [];
  
  const isCall = info.tipo === "CALL";
  let diasUteis = 18;
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
      tbody.innerHTML = "<tr><td colspan='9' class='text-center py-4 text-slate-500'>Aguardando dados da B3...</td></tr>";
      return;
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
      <td class="px-4 py-3 text-emerald-400">R$ ${alvoValor.toFixed(2)}</td>
      <td class="px-4 py-3">
        <button class="bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1 rounded transition-colors shadow shadow-blue-900/20">
          Simular
        </button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}"""

content = re.sub(r'function renderizarGradeStrikes\(\).*?(?=function renderizarGraficoPlotly)', new_render + "\n\n", content, flags=re.DOTALL)

with open('app.js', 'w') as f:
    f.write(content)
