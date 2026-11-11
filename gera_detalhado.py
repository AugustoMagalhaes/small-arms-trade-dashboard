"""Gera docs/exportacoes_detalhadas.html (aba "Exportações detalhadas").

Uso:  python gera_detalhado.py [caminho_do_excel]
Fonte: Comex Stat, exportações por UF/país/NCM/mês, 1997-2026 (aba "Resultado").
O mapa usa um GeoJSON dos estados, baixado uma vez e guardado em br_estados.geojson.
"""

import json
import os
import sys
import urllib.request

import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
EXCEL = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.join(
        AQUI, "V_EXPORTACAO_GERAL_1997-01_2026-12_DT20261110_SMALL_ARMS_FILTRADOS.xlsx"
    )
)
GEO_URL = (
    "https://raw.githubusercontent.com/codeforgermany/click_that_hood/"
    "main/public/data/brazil-states.geojson"
)
GEO_CACHE = os.path.join(AQUI, "br_estados.geojson")
SAIDA = os.path.join(AQUI, "docs", "exportacoes_detalhadas.html")

BG, BG2, BG3, BORDA, TEXTO, TEXTO2 = (
    "#0D1117",
    "#161B22",
    "#1C2128",
    "#30363D",
    "#E6EDF3",
    "#8B949E",
)

UF_SIGLA = {
    "Acre": "AC",
    "Alagoas": "AL",
    "Amapá": "AP",
    "Amazonas": "AM",
    "Bahia": "BA",
    "Ceará": "CE",
    "Distrito Federal": "DF",
    "Espírito Santo": "ES",
    "Goiás": "GO",
    "Maranhão": "MA",
    "Mato Grosso": "MT",
    "Mato Grosso do Sul": "MS",
    "Minas Gerais": "MG",
    "Pará": "PA",
    "Paraíba": "PB",
    "Paraná": "PR",
    "Pernambuco": "PE",
    "Piauí": "PI",
    "Rio de Janeiro": "RJ",
    "Rio Grande do Norte": "RN",
    "Rio Grande do Sul": "RS",
    "Rondônia": "RO",
    "Roraima": "RR",
    "Santa Catarina": "SC",
    "São Paulo": "SP",
    "Sergipe": "SE",
    "Tocantins": "TO",
}
SEM_UF = {
    "Não Declarada": "ND",
    "Reexportação": "REEXP",
    "Mercadoria Nacionalizada": "NAC",
}
SEM_UF_NOME = {
    "ND": "Não declarada",
    "REEXP": "Reexportação",
    "NAC": "Mercadoria nacionalizada",
}

CATS = ["Armas de Fogo", "Munição e Cartuchos", "Partes e Acessórios"]
CAT_COR = {
    "Armas de Fogo": "#22C55E",
    "Munição e Cartuchos": "#3B82F6",
    "Partes e Acessórios": "#F97316",
}


def categoria(ncm: int) -> str:
    s = str(ncm)
    if s.startswith(("9303", "9302", "9301")):
        return "Armas de Fogo"
    if s.startswith("9306"):
        return "Munição e Cartuchos"
    if s.startswith("9305"):
        return "Partes e Acessórios"
    raise ValueError(f"NCM fora do escopo small arms: {ncm}")


# ---------- 1) leitura e conferências ----------
df = pd.read_excel(EXCEL, sheet_name="Resultado")
df["Código NCM"] = df["Código NCM"].astype(str).str.strip()

# a) NÃO pode conter posição 9304 (armas de ar/mola etc.)
n9304 = df["Código NCM"].str.startswith("9304").sum()
assert n9304 == 0, f"ERRO: {n9304} linhas com NCM 9304xxxx no arquivo"
# b) só capítulo 93
assert df["Código NCM"].str.startswith("93").all(), "NCM fora do capítulo 93"
# c) cobertura temporal
anos = sorted(df["Ano"].unique())
assert anos[0] == 1997, f"série não começa em 1997: {anos[0]}"
assert df["Valor US$ FOB"].notna().all()
assert not df.duplicated(
    ["Ano", "Mês", "Países", "Código NCM", "Via", "UF do Produto", "URF"]
).any(), "linhas duplicadas na chave Ano/Mês/País/NCM/Via/UF/URF"

df["mes"] = df["Mês"].astype(str).str[:2].astype(int)
df["uf"] = df["UF do Produto"].map({**UF_SIGLA, **SEM_UF})
assert df["uf"].notna().all(), df.loc[df["uf"].isna(), "UF do Produto"].unique()

det = pd.read_excel(EXCEL, sheet_name="Detalhamento")
col_ncm = [c for c in det.columns if str(c).startswith("NCM")][0]
consultadas = sorted(str(int(x)) for x in det[col_ncm].dropna())
assert not any(c.startswith("9304") for c in consultadas), "consulta inclui 9304"
ncms = sorted(df["Código NCM"].unique())
assert set(ncms) <= set(consultadas), "NCM no resultado que não consta no Detalhamento"
print(
    f"Linhas: {len(df):,} | {anos[0]}-{anos[-1]} | total US$ {df['Valor US$ FOB'].sum():,.0f}"
)
print("NCMs presentes:", ", ".join(ncms))
print(
    f"NCMs consultadas: {len(consultadas)} | com exportação: {len(ncms)} | sem: {sorted(set(consultadas) - set(ncms))}"
)
print("OK: nenhuma linha 9304xxxx")

# ---------- 2) GeoJSON simplificado ----------
if not os.path.exists(GEO_CACHE):
    print("Baixando GeoJSON dos estados...")
    urllib.request.urlretrieve(GEO_URL, GEO_CACHE)
geo = json.load(open(GEO_CACHE, encoding="utf-8"))


def simplifica(anel):
    out, ult = [], None
    for x, y in anel:
        p = [round(x, 2), round(y, 2)]
        if p != ult:
            out.append(p)
            ult = p
    return out if len(out) >= 4 else anel


def area(r):
    return (
        sum(r[i][0] * r[i + 1][1] - r[i + 1][0] * r[i][1] for i in range(len(r) - 1))
        / 2
    )


def orienta(poly):
    out = []
    for i, anel in enumerate(poly):
        ccw = area(anel) > 0
        out.append(anel if ccw == (i != 0) else anel[::-1])
    return out


feats = []
for f in geo["features"]:
    g = f["geometry"]
    polys = [g["coordinates"]] if g["type"] == "Polygon" else g["coordinates"]
    polys = [orienta([simplifica(a) for a in poly]) for poly in polys]
    feats.append(
        {
            "type": "Feature",
            "properties": {
                "sigla": f["properties"]["sigla"],
                "nome": f["properties"]["name"],
            },
            "geometry": {"type": "MultiPolygon", "coordinates": polys},
        }
    )
geo_min = {"type": "FeatureCollection", "features": feats}
assert len(feats) == 27

# ---------- 3) dados compactos ----------
NOME = {
    "93019000": "Outras armas de guerra",
    "93020000": "Revólveres e pistolas",
    "93031000": "Armas de fogo de carregar pela boca",
    "93032000": "Espingardas/carabinas (≥1 cano liso)",
    "93033000": "Outras espingardas/carabinas (caça/tiro)",
    "93039000": "Outras armas de fogo",
    "93039090": "Outras armas de fogo (93039090)",
    "93051000": "Partes de revólveres/pistolas",
    "93052000": "Partes de espingardas/carabinas",
    "93052100": "Partes esp./carab. cano liso",
    "93052900": "Partes de outras esp./carab.",
    "93059090": "Partes de outras armas (93059090)",
    "93059100": "Partes de armas de guerra",
    "93059900": "Partes de outras armas (93059900)",
    "93062100": "Cartuchos (espingarda cano liso)",
    "93062190": "Outros cartuchos",
    "93063000": "Outros cartuchos e partes",
}
desc = (
    df.drop_duplicates("Código NCM").set_index("Código NCM")["Descrição NCM"].to_dict()
)
tot_ncm = df.groupby("Código NCM")["Valor US$ FOB"].sum().to_dict()
ano_ncm = df.groupby("Código NCM")["Ano"].agg(["min", "max"]).to_dict("index")
ncm_meta = [
    {
        "code": c,
        "cat": categoria(int(c)),
        "label": f"{c} — {NOME.get(c, c)}",
        "desc": str(desc.get(c, NOME.get(c, ""))).strip(),
        "tem": c in tot_ncm,
        "total": round(float(tot_ncm.get(c, 0)), 2),
        "de": int(ano_ncm[c]["min"]) if c in ano_ncm else None,
        "ate": int(ano_ncm[c]["max"]) if c in ano_ncm else None,
    }
    for c in consultadas
]
ncm_idx = {m["code"]: i for i, m in enumerate(ncm_meta)}
paises = list(
    df.groupby("Países")["Valor US$ FOB"].sum().sort_values(ascending=False).index
)
pais_idx = {p: i for i, p in enumerate(paises)}
ufs = list(df.groupby("uf")["Valor US$ FOB"].sum().sort_values(ascending=False).index)
uf_idx = {u: i for i, u in enumerate(ufs)}
vias = list(df.groupby("Via")["Valor US$ FOB"].sum().sort_values(ascending=False).index)
via_idx = {v: i for i, v in enumerate(vias)}
nome_uf = {v: k for k, v in UF_SIGLA.items()}
nome_uf.update(SEM_UF_NOME)

rows = [
    [int(a), int(m), uf_idx[u], pais_idx[p], ncm_idx[n], via_idx[v], round(float(x), 2)]
    for a, m, u, p, n, v, x in zip(
        df["Ano"],
        df["mes"],
        df["uf"],
        df["Países"],
        df["Código NCM"],
        df["Via"],
        df["Valor US$ FOB"],
    )
]
ult = df.sort_values(["Ano", "mes"]).iloc[-1]
periodo_txt = f"01/{anos[0]} a {int(ult['mes']):02d}/{int(ult['Ano'])}"
n_sem = len(consultadas) - len(ncms)

DADOS = {
    "rows": rows,
    "ufs": ufs,
    "nomeUf": nome_uf,
    "paises": paises,
    "vias": vias,
    "ncms": ncm_meta,
    "cats": CATS,
    "catCor": CAT_COR,
    "anos": [int(a) for a in anos],
    "semUf": list(SEM_UF_NOME),
    "geo": geo_min,
}
dados_json = json.dumps(DADOS, ensure_ascii=False, separators=(",", ":")).replace(
    "</", "<\\/"
)

HTML = r"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Exportações detalhadas — Armas de Fogo</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:__BG__;color:__TEXTO__;font-family:'Inter','Segoe UI',Arial,sans-serif;line-height:1.5}
header{background:__BG2__;border-bottom:1px solid __BORDA__;padding:18px 24px}
header h1{font-size:1.35rem;font-weight:700}
header p{color:__TEXTO2__;font-size:.82rem;margin-top:4px}
main{width:100%;padding:14px 16px;display:flex;flex-direction:column;gap:14px}
.card{background:__BG2__;border:1px solid __BORDA__;border-radius:12px;padding:16px}
.card h2{font-size:.85rem;font-weight:600;text-transform:uppercase;letter-spacing:.5px}
.sub{color:__TEXTO2__;font-size:.74rem;margin:2px 0 8px}
.fgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px}
.box>label.t,.box>.t{display:flex;justify-content:space-between;align-items:center;color:__TEXTO2__;font-size:.72rem;text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
.scroll{max-height:170px;overflow:auto;border:1px solid __BORDA__;border-radius:8px;padding:6px 8px;background:__BG3__}
select,input[type=search]{background:__BG3__;color:__TEXTO__;border:1px solid __BORDA__;border-radius:8px;padding:5px 9px;font-size:.82rem;font-family:inherit}
input[type=search]{width:100%;margin-bottom:6px}
.chk{display:flex;align-items:center;gap:6px;font-size:.78rem;cursor:pointer;margin-bottom:2px;white-space:nowrap}
.chk input{accent-color:#3B82F6;cursor:pointer}
.chk .v{margin-left:auto;color:__TEXTO2__;font-size:.7rem}
.meses{display:flex;flex-wrap:wrap;gap:5px}
.meses .chk{background:__BG3__;border:1px solid __BORDA__;border-radius:6px;padding:2px 7px;margin:0}
.btns{display:flex;gap:5px;flex-wrap:wrap;margin-top:6px}
.btn{background:__BG3__;color:__TEXTO2__;border:1px solid __BORDA__;border-radius:6px;padding:3px 9px;font-size:.72rem;cursor:pointer}
.btn:hover{color:__TEXTO__;border-color:#3B82F6}
.rangew{position:relative;height:32px}
.rail{position:absolute;top:14px;left:0;right:0;height:4px;background:__BORDA__;border-radius:2px;pointer-events:none}
.fill{position:absolute;top:14px;height:4px;background:#3B82F6;border-radius:2px;pointer-events:none}
.rangew input[type=range]{position:absolute;top:10px;left:0;width:100%;margin:0;-webkit-appearance:none;appearance:none;background:transparent;pointer-events:none}
.rangew input[type=range]::-webkit-slider-thumb{-webkit-appearance:none;pointer-events:auto;width:16px;height:16px;border-radius:50%;background:__BG2__;border:3px solid #3B82F6;cursor:pointer;margin-top:-6px;position:relative}
.rangew input[type=range]::-moz-range-thumb{pointer-events:auto;width:14px;height:14px;border-radius:50%;background:__BG2__;border:3px solid #3B82F6;cursor:pointer}
.rangew input[type=range]::-webkit-slider-runnable-track{height:4px;background:transparent}
.rangew input[type=range]::-moz-range-track{height:4px;background:transparent}
#ano-label{color:__TEXTO__;font-weight:600;font-size:.9rem;text-transform:none;letter-spacing:0}
.grid{display:grid;grid-template-columns:minmax(380px,.85fr) minmax(0,1.5fr);gap:14px;align-items:start}
.sticky{position:sticky;top:10px}
@media(max-width:1100px){.grid{grid-template-columns:1fr}.sticky{position:static}}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:8px 0 10px}
.kpi{background:__BG3__;border:1px solid __BORDA__;border-radius:8px;padding:8px 10px}
.kpi b{display:block;font-size:1.1rem}.kpi span{color:__TEXTO2__;font-size:.7rem;text-transform:uppercase;letter-spacing:.4px}
.charts{display:grid;grid-template-columns:1fr;gap:14px}
.charts .full{grid-column:1/-1}
.mini{border-top:1px solid __BORDA__;padding-top:10px}
.mini h4{font-size:.74rem;color:__TEXTO2__;text-transform:uppercase;letter-spacing:.4px;margin-bottom:4px}
table{width:100%;border-collapse:collapse;font-size:.78rem}
td:nth-child(3){white-space:nowrap}
th,td{text-align:left;padding:2px 8px;border-bottom:1px solid __BORDA__}
th{color:__TEXTO2__;font-weight:600;font-size:.7rem;text-transform:uppercase}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
tr.uf{cursor:pointer}tr.uf:hover,tr.sel{background:__BG3__}
.sem td{color:__TEXTO2__}
details summary{cursor:pointer;color:__TEXTO2__;font-size:.78rem;margin-top:8px}
.aviso{background:rgba(245,158,11,.08);border:1px solid #F59E0B;border-radius:12px;padding:10px 14px;font-size:.8rem}
.tag{white-space:nowrap;font-size:.68rem;border:1px solid __BORDA__;border-radius:4px;padding:0 5px}
.tag.ok{color:#22C55E;border-color:#22C55E}.tag.no{color:#F59E0B;border-color:#F59E0B}
footer{text-align:center;padding:16px;color:__TEXTO2__;font-size:.78rem;border-top:1px solid __BORDA__}
</style></head><body>
<header>
  <h1>Exportações detalhadas de armas de fogo — por estado, país e NCM</h1>
  <p>Fonte: Comex Stat / MDIC · US$ FOB · dados mensais · __PERIODO__ · <b>__NCONS__ NCMs consultadas</b> (capítulo 93, sem a posição 9304): <b>__NCOM__ com exportação</b> e <b>__NSEM__ sem nenhum valor no período</b></p>
  <details open><summary>NCMs incluídas na consulta e situação de cada uma</summary><div id="ncm-tabela" style="margin-top:6px;max-width:1000px;font-size:.74rem"></div></details>
</header>
<main>
  <div class="aviso">UF = estado de origem do produto. Valores sem UF identificada (não declarada, reexportação, mercadoria nacionalizada) não aparecem no mapa, mas entram nos totais quando selecionados na lista de estados. <b>Mapa:</b> clique num estado para isolá-lo; clique em outros para somar/remover. Cinza = sem exportação no filtro; borda branca = estado selecionado (os demais continuam coloridos).</div>

  <div class="card"><div class="fgrid">
    <div class="box" style="grid-column:span 2">
      <div class="t"><span>Anos</span><span id="ano-label"></span></div>
      <div class="rangew"><div class="rail"></div><div class="fill" id="fill"></div>
        <input type="range" id="ano-min" step="1"><input type="range" id="ano-max" step="1"></div>
      <div class="btns">
        <label style="font-size:.75rem;color:__TEXTO2__">Só o ano: <select id="ano-unico"></select></label>
        <button class="btn" data-p="tudo">Tudo</button><button class="btn" data-p="5">Últimos 5</button>
        <button class="btn" data-p="10">Últimos 10</button><button class="btn" data-p="ult">Último ano</button>
      </div>
    </div>
    <div class="box"><div class="t"><span>Meses</span></div><div class="meses" id="meses"></div>
      <div class="btns"><button class="btn" id="m-todos">Todos</button><button class="btn" id="m-nenhum">Nenhum</button>
        <button class="btn" id="m-s1">1º sem.</button><button class="btn" id="m-s2">2º sem.</button></div></div>
    <div class="box"><div class="t"><span>Estados (UF)</span></div><div class="scroll" id="f-uf"></div>
      <div class="btns"><button class="btn" id="uf-todos">Todos</button><button class="btn" id="uf-nenhum">Nenhum</button></div></div>
    <div class="box"><div class="t"><span>NCM (só as com dados)</span></div><div class="scroll" id="f-ncm"></div>
      <div class="btns"><button class="btn" id="ncm-todos">Todas</button><button class="btn" id="ncm-nenhum">Nenhuma</button></div></div>
    <div class="box"><div class="t"><span>País de destino</span></div>
      <input type="search" id="pais-busca" placeholder="Buscar país..."><div class="scroll" id="f-pais"></div>
      <div class="btns"><button class="btn" id="pais-todos">Todos</button><button class="btn" id="pais-nenhum">Nenhum</button>
        <button class="btn" id="pais-top10">Top 10</button></div></div>
  </div></div>

  <div class="grid">
    <div class="card sticky">
      <h2>🗺️ Exportações por estado</h2><div class="sub" id="mapa-sub"></div>
      <div id="mapa" style="height:620px"></div>
      <div class="mini"><h4>Sem UF identificada</h4><div id="sem-uf" style="font-size:.8rem"></div></div>
      <details><summary>Ver como tabela</summary><div id="tabela-uf"></div></details>
    </div>
    <div class="card">
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px"><h2 id="p-titulo"></h2><button class="btn" id="ver-tabela">📋 Ver estes dados em tabela</button></div>
      <div class="kpis">
        <div class="kpi"><span>Total no filtro</span><b id="k-total"></b></div>
        <div class="kpi"><span>% do total (todas as UFs)</span><b id="k-share"></b></div>
        <div class="kpi"><span>Países de destino</span><b id="k-pais"></b></div>
        <div class="kpi"><span>Meses com exportação</span><b id="k-meses"></b></div>
      </div>
      <div class="charts">
        <div class="mini full"><h4 id="t-serie"></h4><div id="g-serie" style="height:340px"></div></div>
        <div class="mini"><h4>Top 10 países de destino</h4><div id="g-dest" style="height:400px"></div></div>
        <div class="mini"><h4>Por NCM</h4><div id="g-ncm" style="height:360px"></div></div>
        <div class="mini"><h4>Por estado (seleção atual)</h4><div id="g-uf" style="height:320px"></div></div>
      </div>
    </div>
  </div>
</main>
<footer>Grupo de Pesquisa · Comex Stat (MDIC) · __ARQ__</footer>
<script>
const D = __DADOS__;
const BG="__BG__",BG2="__BG2__",BG3="__BG3__",BORDA="__BORDA__",TEXTO="__TEXTO__",TEXTO2="__TEXTO2__";
const MES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"];
const ANO_MIN = D.anos[0], ANO_MAX = D.anos[D.anos.length-1];
const CFG = {displayModeBar:false, responsive:true};
const $ = id => document.getElementById(id);

function fmtUsd(v){ if(v>=1e9) return "US$ "+(v/1e9).toFixed(2)+" bi"; if(v>=1e6) return "US$ "+(v/1e6).toFixed(1)+" mi";
  if(v>=1e3) return "US$ "+(v/1e3).toFixed(1)+" mil"; return "US$ "+Math.round(v); }
function unid(max){ if(max>=1e6) return {d:1e6,s:" mi"}; if(max>=1e3) return {d:1e3,s:" mil"}; return {d:1,s:""}; }
function layoutBase(){ return { paper_bgcolor:BG2, plot_bgcolor:BG2, font:{family:"Inter, Segoe UI, Arial",color:TEXTO,size:12},
  margin:{t:10,b:40,l:75,r:15}, xaxis:{gridcolor:BORDA,zerolinecolor:BORDA,tickfont:{color:TEXTO2}},
  yaxis:{gridcolor:BORDA,zerolinecolor:BORDA,tickfont:{color:TEXTO2}},
  legend:{orientation:"h",y:1.13,x:0.5,xanchor:"center",font:{color:TEXTO,size:11},traceorder:"normal"},
  hoverlabel:{bgcolor:BG3,bordercolor:BORDA,font:{color:TEXTO}} }; }
function vazio(id,msg){ const l=layoutBase(); l.xaxis.visible=false; l.yaxis.visible=false;
  l.annotations=[{text:msg,x:.5,y:.5,xref:"paper",yref:"paper",showarrow:false,font:{color:TEXTO2,size:13}}];
  Plotly.react(id,[],l,CFG); }
function soma(a){ let s=0; for(const r of a) s+=r[6]; return s; }
function agrupa(a,k){ const m={}; for(const r of a) m[r[k]]=(m[r[k]]||0)+r[6]; return m; }

// ---------- construção dos filtros ----------
function checklist(id,itens,cls,marcado){
  $(id).innerHTML=itens.map(i=>`<label class="chk"><input type="checkbox" class="${cls}" value="${i.v}" ${marcado(i)?"checked":""}>`+
    `${i.cor?`<span style="color:${i.cor}">●</span>`:""}<span class="lb">${i.l}</span>${i.val?`<span class="v">${i.val}</span>`:""}</label>`).join("");
}
function marcaTodos(cls,on,filtroVisivel){ document.querySelectorAll("."+cls).forEach(e=>{ if(!filtroVisivel||e.closest("label").style.display!=="none") e.checked=on; }); render(); }
const sel = cls => new Set([...document.querySelectorAll("."+cls+":checked")].map(e=>+e.value));
const tudo = cls => { const t=document.querySelectorAll("."+cls); return [...t].every(e=>e.checked); };

function anos(){ const a=+$("ano-min").value,b=+$("ano-max").value; return [Math.min(a,b),Math.max(a,b)]; }
function setAnos(lo,hi){ $("ano-min").value=lo; $("ano-max").value=hi; render(); }

// ---------- filtragem ----------
let CACHE=null;
function base(){   // todos os filtros exceto UF
  const [lo,hi]=anos(), meses=sel("mes"), ncm=sel("ncmc"), pais=sel("paisc");
  return D.rows.filter(r=>r[0]>=lo&&r[0]<=hi&&meses.has(r[1])&&ncm.has(r[4])&&pais.has(r[3]));
}

// ---------- mapa ----------
function renderMapa(rb,ufSel){
  const porUf=agrupa(rb,2), todas=D.geo.features.map(f=>f.properties.sigla);
  const idxDe = {}; D.ufs.forEach((u,i)=>idxDe[u]=i);
  const siglaSel=new Set([...ufSel].map(i=>D.ufs[i]));
  const nome=u=>D.nomeUf[u]||u;
  const comDado=todas.filter(u=>(porUf[idxDe[u]]||0)>0);
  const todosSel = siglaSel.size>=D.ufs.length;
  const base={type:"choropleth",geojson:D.geo,featureidkey:"properties.sigla",locations:todas,z:todas.map(()=>0),
    colorscale:[[0,"#21262D"],[1,"#21262D"]],showscale:false,
    text:todas.map(nome),hovertemplate:"%{text}<br>sem exportação no filtro<extra></extra>",marker:{line:{color:BORDA,width:0.6}}};
  const z=comDado.map(u=>porUf[idxDe[u]]), zmax=Math.max(1,...z);
  const tv=[0,.25,.5,.75,1].map(f=>f*zmax);
  const dados={type:"choropleth",geojson:D.geo,featureidkey:"properties.sigla",locations:comDado,z:z,
    colorscale:[[0,"#1E3A5F"],[1,"#7DB8FF"]],zmin:0,zmax:zmax,
    colorbar:{title:{text:"US$ FOB",font:{color:TEXTO2}},tickvals:tv,ticktext:tv.map(fmtUsd),tickfont:{color:TEXTO2,size:10},len:.6,thickness:10,outlinewidth:0},
    text:comDado.map(nome),customdata:z.map(fmtUsd),
    hovertemplate:"<b>%{text}</b><br>%{customdata}<extra></extra>",
    marker:{line:{color:comDado.map(u=>(!todosSel&&siglaSel.has(u))?"#FFFFFF":BG),width:comDado.map(u=>(!todosSel&&siglaSel.has(u))?3:0.8)}}};
  const lay={paper_bgcolor:BG2,margin:{t:0,b:0,l:0,r:0},
    geo:{fitbounds:"locations",visible:false,bgcolor:BG2,projection:{type:"mercator"}},
    hoverlabel:{bgcolor:BG3,bordercolor:BORDA,font:{color:TEXTO}}};
  Plotly.react("mapa",[base,dados],lay,CFG);
  const el=$("mapa");
  if(!el._ligado){ el._ligado=true; el.on("plotly_click",ev=>{
    const p=ev.points[0]; if(!p) return; const i=D.ufs.indexOf(p.location); if(i<0) return;
    const cbs=[...document.querySelectorAll(".ufc")], me=cbs.find(e=>+e.value===i);
    if(tudo("ufc")){ cbs.forEach(e=>e.checked=(e===me)); } else { me.checked=!me.checked; if(!cbs.some(e=>e.checked)) cbs.forEach(e=>e.checked=true); }
    render(); }); }
  $("mapa-sub").textContent="US$ FOB acumulado no filtro · "+comDado.length+(comDado.length===1?" estado com exportação":" estados com exportação")+(todosSel?"":" · borda branca = selecionado");
  const sem=D.semUf.map(k=>[D.nomeUf[k],(porUf[idxDe[k]]||0),k]).filter(x=>x[1]>0);
  $("sem-uf").innerHTML=sem.length?sem.map(x=>x[0]+": <b>"+fmtUsd(x[1])+"</b>").join(" · "):"—";
  const tot=soma(rb), lin=Object.entries(porUf).sort((a,b)=>b[1]-a[1]);
  $("tabela-uf").innerHTML="<table><tr><th>UF</th><th class='n'>US$ FOB</th><th class='n'>%</th></tr>"+
    lin.map(([i,v])=>`<tr class="uf ${ufSel.has(+i)?"sel":""}" data-i="${i}"><td>${nome(D.ufs[i])}</td><td class="n">${Math.round(v).toLocaleString("pt-BR")}</td><td class="n">${tot?(100*v/tot).toFixed(1):0}%</td></tr>`).join("")+"</table>";
  document.querySelectorAll("tr.uf").forEach(tr=>tr.onclick=()=>{ const c=[...document.querySelectorAll(".ufc")].find(e=>e.value===tr.dataset.i); c.checked=!c.checked; render(); });
}

// ---------- painel ----------
function barH(id,pares,cor,margemL,rotulo,total){
  if(!pares.length){ vazio(id,"Sem dados no filtro"); return; }
  const u=unid(Math.max(...pares.map(p=>p[1])));
  const l=layoutBase(); l.margin={t:5,b:38,l:margemL,r:15}; l.xaxis.tickprefix="US$ "; l.xaxis.ticksuffix=u.s; l.xaxis.tickformat=",.3~f";
  l.yaxis.tickfont={color:TEXTO,size:10}; l.yaxis.automargin=true;
  Plotly.react(id,[{type:"bar",orientation:"h",y:pares.map(p=>rotulo(p[0])),x:pares.map(p=>p[1]/u.d),
    marker:{color:pares.map(p=>typeof cor==="function"?cor(p[0]):cor)},
    customdata:pares.map(p=>fmtUsd(p[1])+" ("+(total?(100*p[1]/total).toFixed(1):0)+"%)"),
    hovertemplate:"<b>%{y}</b><br>%{customdata}<extra></extra>"}],l,CFG);
}
function renderPainel(rb,rs,ufSel){
  const f=anos(), t=soma(rs), tb=soma(rb);
  const nSel=ufSel.size, nTot=D.ufs.length;
  const nomes=[...ufSel].map(i=>D.nomeUf[D.ufs[i]]);
  $("p-titulo").textContent = nSel===nTot ? "Todos os estados (inclui sem UF)" : (nSel<=4? nomes.join(" + ") : nSel+" de "+nTot+" UFs selecionadas");
  $("k-total").textContent=fmtUsd(t);
  $("k-share").textContent= tb?(100*t/tb).toFixed(1)+"%":"—";
  $("k-pais").textContent=new Set(rs.filter(r=>r[6]>0).map(r=>r[3])).size;
  $("k-meses").textContent=new Set(rs.filter(r=>r[6]>0).map(r=>r[0]*100+r[1])).size;

  // série: anual; se for 1 só ano, mensal
  const mensal=f[0]===f[1];
  const eixo=mensal? [...sel("mes")].sort((a,b)=>a-b) : D.anos.filter(a=>a>=f[0]&&a<=f[1]);
  const chave=r=>mensal?r[1]:r[0];
  $("t-serie").textContent= mensal? "Evolução mensal em "+f[0]+" por categoria" : "Evolução anual por categoria";
  const mapaCat={}; D.cats.forEach(c=>mapaCat[c]=eixo.map(()=>0));
  for(const r of rs){ const c=D.ncms[r[4]].cat, k=eixo.indexOf(chave(r)); if(k>=0) mapaCat[c][k]+=r[6]; }
  const mx=Math.max(1,...eixo.map((_,k)=>D.cats.reduce((s,c)=>s+mapaCat[c][k],0))), u=unid(mx);
  const xs=mensal?eixo.map(m=>MES[m-1]):eixo.map(String);
  const traces=D.cats.filter(c=>mapaCat[c].some(v=>v>0)).map(c=>({type:"bar",name:c,x:xs,y:mapaCat[c].map(v=>v/u.d),
    marker:{color:D.catCor[c],line:{color:BG2,width:1}},customdata:mapaCat[c].map(fmtUsd),
    hovertemplate:"<b>"+c+"</b><br>%{x}: %{customdata}<extra></extra>"}));
  if(!traces.length) vazio("g-serie","Sem dados no filtro"); else {
    const l=layoutBase(); l.barmode="stack"; l.xaxis.type="category"; l.xaxis.tickangle=mensal?0:-60;
    l.yaxis.tickprefix="US$ "; l.yaxis.ticksuffix=u.s; l.yaxis.tickformat=",.3~f"; l.margin.l=85;
    Plotly.react("g-serie",traces,l,CFG); }

  const pp=Object.entries(agrupa(rs,3)).filter(x=>x[1]>0).sort((a,b)=>b[1]-a[1]).slice(0,10).reverse();
  barH("g-dest",pp,"#3B82F6",130,i=>D.paises[i],t);
  const nn=Object.entries(agrupa(rs,4)).filter(x=>x[1]>0).sort((a,b)=>a[1]-b[1]);
  barH("g-ncm",nn,i=>D.catCor[D.ncms[i].cat],200,i=>D.ncms[i].label,t);
  const uu=Object.entries(agrupa(rs,2)).filter(x=>x[1]>0).sort((a,b)=>a[1]-b[1]);
  barH("g-uf",uu,"#06B6D4",130,i=>D.nomeUf[D.ufs[i]],t);
}

function render(){
  const [lo,hi]=anos();
  $("ano-label").textContent= lo===hi? String(lo) : lo+" – "+hi;
  const mn=+$("ano-min").min, mx=+$("ano-min").max;
  $("fill").style.left=((lo-mn)/(mx-mn)*100)+"%"; $("fill").style.width=((hi-lo)/(mx-mn)*100)+"%";
  $("ano-unico").value = lo===hi? lo : "";
  const rb=base(), ufSel=sel("ufc"), rs=rb.filter(r=>ufSel.has(r[2]));
  renderMapa(rb,ufSel); renderPainel(rb,rs,ufSel);
}

// ---------- init ----------
(function(){
  // tabela de NCMs
  $("ncm-tabela").innerHTML="<table><tr><th>NCM</th><th>Descrição</th><th>Categoria</th><th class='n'>Total US$ FOB</th><th>Anos com dados</th><th>Situação</th></tr>"+
    D.ncms.map(n=>`<tr><td>${n.code}</td><td>${n.desc}</td><td style="color:${D.catCor[n.cat]}">${n.cat}</td><td class="n">${n.tem?Math.round(n.total).toLocaleString("pt-BR"):"—"}</td><td>${n.tem?n.de+"–"+n.ate:"—"}</td><td>${n.tem?'<span class="tag ok">com exportação</span>':'<span class="tag no">sem exportação</span>'}</td></tr>`).join("")+"</table>";

  ["ano-min","ano-max"].forEach(id=>{ $(id).min=ANO_MIN; $(id).max=ANO_MAX; $(id).step=1; });
  $("ano-min").value=ANO_MIN; $("ano-max").value=ANO_MAX;
  $("ano-unico").add(new Option("—",""));  D.anos.forEach(a=>$("ano-unico").add(new Option(a,a)));
  $("ano-min").oninput=$("ano-max").oninput=render;
  $("ano-unico").onchange=e=>{ if(e.target.value) setAnos(+e.target.value,+e.target.value); };
  document.querySelectorAll("[data-p]").forEach(b=>b.onclick=()=>{ const p=b.dataset.p;
    if(p==="tudo") setAnos(ANO_MIN,ANO_MAX); else if(p==="ult") setAnos(ANO_MAX,ANO_MAX); else setAnos(Math.max(ANO_MIN,ANO_MAX-(+p)+1),ANO_MAX); });

  $("meses").innerHTML=MES.map((m,i)=>`<label class="chk"><input type="checkbox" class="mes" value="${i+1}" checked>${m}</label>`).join("");
  const setM=fn=>{ document.querySelectorAll(".mes").forEach(e=>e.checked=fn(+e.value)); render(); };
  $("m-todos").onclick=()=>setM(()=>true); $("m-nenhum").onclick=()=>setM(()=>false);
  $("m-s1").onclick=()=>setM(m=>m<=6); $("m-s2").onclick=()=>setM(m=>m>6);

  checklist("f-uf",D.ufs.map((u,i)=>({v:i,l:D.nomeUf[u]})),"ufc",()=>true);
  const tem=D.ncms.map((n,i)=>({n,i})).filter(x=>x.n.tem);
  checklist("f-ncm",tem.map(x=>({v:x.i,l:x.n.label,cor:D.catCor[x.n.cat]})),"ncmc",()=>true);
  checklist("f-pais",D.paises.map((p,i)=>({v:i,l:p})),"paisc",()=>true);

  document.querySelectorAll(".mes,.ufc,.ncmc,.paisc").forEach(e=>e.addEventListener("change",render));
  [["uf","ufc"],["ncm","ncmc"],["pais","paisc"]].forEach(([k,c])=>{
    $(k+"-todos").onclick=()=>marcaTodos(c,true,k==="pais"); $(k+"-nenhum").onclick=()=>marcaTodos(c,false,k==="pais"); });
  $("pais-top10").onclick=()=>{ document.querySelectorAll(".paisc").forEach(e=>e.checked=false);
    const top=Object.entries(agrupa(base(),3)).sort((a,b)=>b[1]-a[1]).slice(0,10).map(x=>+x[0]);
    document.querySelectorAll(".paisc").forEach(e=>{ if(top.includes(+e.value)) e.checked=true; }); render(); };
  $("pais-busca").oninput=e=>{ const q=e.target.value.toLowerCase();
    document.querySelectorAll("#f-pais label").forEach(l=>l.style.display=l.textContent.toLowerCase().includes(q)?"":"none"); };
  $("ver-tabela").onclick=()=>{
    const [lo,hi]=anos(), nm=(c,f)=>[...document.querySelectorAll("."+c+":checked")].map(e=>f(+e.value));
    const f={lo,hi,meses:[...sel("mes")],ufs:nm("ufc",i=>D.nomeUf[D.ufs[i]]),paises:nm("paisc",i=>D.paises[i]),
      ncms:nm("ncmc",i=>D.ncms[i].code),vias:D.vias};
    try{ parent.abrirTabela(f); }catch(e){ alert("Abra pelo index.html (aba Tabela de dados) para levar os filtros."); } };
  render();
})();
</script></body></html>
"""
subs = {
    "__DADOS__": dados_json,
    "__PERIODO__": periodo_txt,
    "__NCONS__": str(len(consultadas)),
    "__NCOM__": str(len(ncms)),
    "__NSEM__": str(n_sem),
    "__ARQ__": os.path.basename(EXCEL),
    "__BG3__": BG3,
    "__BG2__": BG2,
    "__BG__": BG,
    "__BORDA__": BORDA,
    "__TEXTO2__": TEXTO2,
    "__TEXTO__": TEXTO,
}
for k, v in subs.items():
    HTML = HTML.replace(k, v)

os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
with open(SAIDA, "w", encoding="utf-8") as fh:
    fh.write(HTML)
print(f"Gerado: {SAIDA} ({os.path.getsize(SAIDA) / 1024:.0f} KB)")
