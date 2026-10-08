with open('app.js', 'r') as f:
    content = f.read()

new_traces = """  const traceGatilho = {
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
"""

content = content.replace("  const traceIFR =", new_traces + "\n  const traceIFR =")
content = content.replace("[traceCandle, traceMME, traceSinal, traceIFR]", "[traceCandle, traceMME, traceGatilho, traceStop, traceSinal, traceIFR]")

with open('app.js', 'w') as f:
    f.write(content)
