import re

with open('app.js', 'r') as f:
    content = f.read()

new_badge = """    const tipoDado = opt["tipo_dado"] || "⚪ TEÓRICO (BS)";
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
"""

# Replace the inner part of gradeBackend.forEach
content = re.sub(
    r'    const isRecomendado = destaque !== "";.*?</td>\n    `;',
    new_badge,
    content,
    flags=re.DOTALL
)

with open('app.js', 'w') as f:
    f.write(content)
