"""Gera docs/index.html com 2 abas (cada aba é uma página independente em iframe).
Rode antes: script_antigo.py --export, gera_detalhado.py e gera_tabela.py
"""

import os

DOCS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
ABAS = [
    ("antigo", "Comércio exterior (Exp/Imp por NCM)", "comex_antigo.html"),
    ("detalhado", "Exportações detalhadas", "exportacoes_detalhadas.html"),
    ("tabela", "Tabela de dados", "tabela_dados.html"),
]
for _, _, arq in ABAS:
    assert os.path.exists(os.path.join(DOCS, arq)), f"falta docs/{arq}"

botoes = "".join(f'<button class="tab" data-k="{k}">{t}</button>' for k, t, _ in ABAS)
frames = "".join(
    f'<iframe id="f-{k}" data-src="{a}" title="{t}"></iframe>' for k, t, a in ABAS
)
page = f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Armas de Fogo — Dashboard</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;background:#0D1117;color:#E6EDF3;font-family:'Inter','Segoe UI',Arial,sans-serif}}
nav{{display:flex;gap:4px;background:#161B22;border-bottom:1px solid #30363D;padding:8px 24px 0;height:46px}}
.tab{{background:none;border:0;border-bottom:3px solid transparent;color:#8B949E;font:600 .9rem inherit;font-family:inherit;padding:8px 16px;cursor:pointer}}
.tab:hover{{color:#E6EDF3}}.tab.on{{color:#E6EDF3;border-bottom-color:#3B82F6}}
iframe{{display:none;width:100%;height:calc(100% - 46px);border:0;background:#0D1117}}iframe.on{{display:block}}
</style></head><body>
<nav>{botoes}</nav>{frames}
<script>
function abrir(k){{
  document.querySelectorAll(".tab").forEach(b=>b.classList.toggle("on",b.dataset.k===k));
  document.querySelectorAll("iframe").forEach(f=>{{
    const on=f.id==="f-"+k; f.classList.toggle("on",on);
    if(on&&!f.src) f.src=f.dataset.src;   // carrega só ao abrir (Plotly mede o tamanho certo)
  }});
  history.replaceState(null,"","#"+k);
}}
document.querySelectorAll(".tab").forEach(b=>b.onclick=()=>abrir(b.dataset.k));
function abrirTabela(f){{
  abrir("tabela"); const fr=document.getElementById("f-tabela");
  const go=()=>fr.contentWindow.aplicarFiltros(f);
  if(fr.contentWindow.aplicarFiltros) go(); else fr.addEventListener("load",go,{{once:true}});
}}
abrir(["antigo","detalhado","tabela"].includes(location.hash.slice(1))?location.hash.slice(1):"antigo");
</script></body></html>"""
open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8").write(page)
print("docs/index.html gerado")
