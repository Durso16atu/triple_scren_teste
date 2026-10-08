with open('app.js', 'r') as f:
    content = f.read()

fallback_code = """
function gerarDadosFallback() {
  processarDadosMercado({ metadata: { status_mercado: "ABERTO" }, sinais_ativos: [] });
}
"""

content = content.replace("function renderizarSidebar() {", fallback_code + "\nfunction renderizarSidebar() {")

with open('app.js', 'w') as f:
    f.write(content)
