"""Gera docs/tabela_dados.html (aba "Tabela de dados"): tabela filtravel/ordenavel com export xlsx/csv.
Uso: python gera_tabela.py [caminho_do_excel]   (mesmo Excel do gera_detalhado.py)
"""

import json
import os
import sys

import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
EXCEL = (
    sys.argv[1]
    if len(sys.argv) > 1
    else os.path.join(
        AQUI, "V_EXPORTACAO_GERAL_1997-01_2026-12_DT20261110_SMALL_ARMS_FILTRADOS.xlsx"
    )
)
SAIDA = os.path.join(AQUI, "docs", "tabela_dados.html")
BG, BG2, BG3, BORDA, TEXTO, TEXTO2 = (
    "#0D1117",
    "#161B22",
    "#1C2128",
    "#30363D",
    "#E6EDF3",
    "#8B949E",
)

df = pd.read_excel(EXCEL, sheet_name="Resultado")
df["Código NCM"] = df["Código NCM"].astype(str).str.strip()
assert not df["Código NCM"].str.startswith("9304").any(), (
    "ERRO: NCM 9304xxxx no arquivo"
)
assert df["Código NCM"].str.startswith("93").all()
df["mes"] = df["Mês"].astype(str).str[:2].astype(int)
df["UF do Produto"] = df["UF do Produto"].replace(
    {
        "Não Declarada": "Não declarada",
        "Mercadoria Nacionalizada": "Mercadoria nacionalizada",
    }
)
print(
    f"Linhas: {len(df):,} | total US$ {df['Valor US$ FOB'].sum():,.0f} | sem 9304: OK"
)


def dim(col):
    vals = sorted(df[col].unique(), key=str)
    return vals, {v: i for i, v in enumerate(vals)}


ufs, ui = dim("UF do Produto")
paises, pi = dim("Países")
ncms, ni = dim("Código NCM")
vias, vi = dim("Via")
urfs, ri = dim("URF")
desc = (
    df.drop_duplicates("Código NCM")
    .set_index("Código NCM")["Descrição NCM"]
    .astype(str)
    .str.strip()
    .to_dict()
)
rows = [
    [int(a), int(m), ui[u], pi[p], ni[n], vi[v], ri[r], round(float(x), 2)]
    for a, m, u, p, n, v, r, x in zip(
        df["Ano"],
        df["mes"],
        df["UF do Produto"],
        df["Países"],
        df["Código NCM"],
        df["Via"],
        df["URF"],
        df["Valor US$ FOB"],
    )
]
D = {
    "rows": rows,
    "uf": ufs,
    "pais": paises,
    "ncm": ncms,
    "ncmDesc": [desc[n] for n in ncms],
    "via": vias,
    "urf": urfs,
}
dados = json.dumps(D, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")

HTML = r"""<!DOCTYPE html>
<html lang="pt-BR"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tabela de dados — Exportações</title>
<script src="https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js"></script>
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:__BG__;color:__TEXTO__;font-family:'Inter','Segoe UI',Arial,sans-serif;line-height:1.5}
header{background:__BG2__;border-bottom:1px solid __BORDA__;padding:16px 24px}
header h1{font-size:1.3rem}header p{color:__TEXTO2__;font-size:.8rem;margin-top:3px}
.bar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;padding:12px 16px}
.btn{background:__BG3__;color:__TEXTO__;border:1px solid __BORDA__;border-radius:8px;padding:6px 12px;font-size:.8rem;cursor:pointer;font-family:inherit}
.btn:hover{border-color:#3B82F6}.btn.pri{background:#1D4ED8;border-color:#1D4ED8}
.info{color:__TEXTO2__;font-size:.8rem}.info b{color:__TEXTO__}
.wrap{margin:0 16px 16px;border:1px solid __BORDA__;border-radius:12px;overflow:visible;background:__BG2__}
table{border-collapse:separate;border-spacing:0;width:100%;font-size:.78rem}
th{position:sticky;top:0;background:#1E293B;z-index:2;text-align:left;padding:8px 10px;border-bottom:2px solid #3B82F6;border-right:1px solid #2D3B55;white-space:nowrap;color:#F1F5F9}
th:first-child{border-top-left-radius:12px}th:last-child{border-top-right-radius:12px;border-right:0}
th .h{display:flex;align-items:center;gap:10px;justify-content:space-between}
th .lb{font-size:.74rem;font-weight:700;text-transform:uppercase;letter-spacing:.5px}
th .bt{display:flex;gap:3px}
th .ib{width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;background:#0F172A;border:1px solid #475569;border-radius:6px;color:#CBD5E1;cursor:pointer;padding:0}
th .ib:hover{border-color:#60A5FA;color:#fff}
th .ib.on{background:#1D4ED8;border-color:#60A5FA;color:#fff}
th .ib svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
th.n .h{justify-content:flex-end}
td{padding:4px 10px;border-bottom:1px solid __BORDA__;white-space:nowrap}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
tr:hover td{background:__BG3__}
.pop{position:fixed;z-index:10;background:__BG3__;border:1px solid #3B82F6;border-radius:10px;padding:10px;width:290px;box-shadow:0 8px 24px rgba(0,0,0,.5)}
.pop input[type=search],.pop input[type=number]{width:100%;background:__BG__;color:__TEXTO__;border:1px solid __BORDA__;border-radius:6px;padding:5px 8px;font-size:.8rem;margin-bottom:6px}
.pop .l{max-height:240px;overflow:auto;border:1px solid __BORDA__;border-radius:6px;padding:4px 6px;background:__BG__}
.pop label{display:flex;gap:6px;align-items:center;font-size:.78rem;cursor:pointer;white-space:nowrap}
.pop .b{display:flex;gap:5px;margin-top:6px}
select{background:__BG3__;color:__TEXTO__;border:1px solid __BORDA__;border-radius:8px;padding:5px 8px;font-size:.8rem}
.pg{display:flex;gap:8px;align-items:center}
</style></head><body>
<header><h1>Tabela de dados — exportações de armas de fogo (Comex Stat)</h1>
<p>__N__ registros · __PERIODO__ · US$ FOB · use as setas de cada coluna para ordenar e o funil para filtrar; exporte o que está filtrado.</p></header>
<div class="bar">
  <button class="btn pri" id="x-xlsx">⬇ Exportar xlsx</button><button class="btn" id="x-csv">⬇ Exportar csv</button>
  <button class="btn" id="limpar">Limpar filtros</button>
  <span class="info" id="info"></span>
  <span style="margin-left:auto" class="pg"><button class="btn" id="ant">‹</button><span class="info" id="pg"></span><button class="btn" id="prox">›</button>
  <select id="tam"><option>50</option><option selected value="100">100</option><option>250</option><option>500</option><option>1000</option><option value="1000000">Todas</option></select><span class="info">linhas/pág.</span></span>
</div>
<div class="wrap"><table><thead id="thead"></thead><tbody id="tbody"></tbody></table></div>
<script>
const D=__DADOS__;
const MES=["","Janeiro","Fevereiro","Março","Abril","Maio","Junho","Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"];
const $=id=>document.getElementById(id);
// colunas: key, rótulo, índice na linha, tipo
const COLS=[
 {k:"ano",l:"Ano",i:0,t:"range"},{k:"mes",l:"Mês",i:1,t:"set",ops:MES.slice(1).map((m,i)=>[i+1,(i+1)+" - "+m])},
 {k:"uf",l:"UF do produto",i:2,t:"set",ops:D.uf.map((v,i)=>[i,v])},
 {k:"pais",l:"País",i:3,t:"set",ops:D.pais.map((v,i)=>[i,v])},
 {k:"ncm",l:"NCM",i:4,t:"set",ops:D.ncm.map((v,i)=>[i,v+" — "+D.ncmDesc[i].slice(0,60)])},
 {k:"via",l:"Via",i:5,t:"set",ops:D.via.map((v,i)=>[i,v])},
 {k:"urf",l:"URF",i:6,t:"set",ops:D.urf.map((v,i)=>[i,v])},
 {k:"val",l:"Valor US$ FOB",i:7,t:"range",n:true}];
let F={}, sortK="ano", sortD=1, page=0, vis=[];
function resetF(){ F={}; COLS.forEach(c=>F[c.k]=c.t==="set"?null:{min:null,max:null}); }
function fmtN(v){return v.toLocaleString("pt-BR",{minimumFractionDigits:2,maximumFractionDigits:2});}
function texto(c,r){ const v=r[c.i];
  if(c.k==="mes") return MES[v]; if(c.k==="ncm") return D.ncm[v];
  if(c.k==="uf") return D.uf[v]; if(c.k==="pais") return D.pais[v]; if(c.k==="via") return D.via[v]; if(c.k==="urf") return D.urf[v];
  return v; }
function passa(r){ for(const c of COLS){ const f=F[c.k];
  if(c.t==="set"){ if(f&&!f.has(r[c.i])) return false; }
  else { const v=r[c.i]; if(f.min!==null&&v<f.min) return false; if(f.max!==null&&v>f.max) return false; } } return true; }
function filtrar(){ vis=D.rows.filter(passa); ordenar(); page=0; desenha(); }
function ordenar(){ const c=COLS.find(c=>c.k===sortK);
  vis.sort((a,b)=>{ const x=c.t==="range"||c.k==="mes"?a[c.i]:String(texto(c,a)), y=c.t==="range"||c.k==="mes"?b[c.i]:String(texto(c,b));
    return (x<y?-1:x>y?1:0)*sortD; }); }
function desenha(){
  const tam=+$("tam").value, np=Math.max(1,Math.ceil(vis.length/tam)); page=Math.min(page,np-1);
  const UP='<svg viewBox="0 0 24 24"><path d="M12 19V5M5 12l7-7 7 7"/></svg>', DOWN='<svg viewBox="0 0 24 24"><path d="M12 5v14M5 12l7 7 7-7"/></svg>', FUN='<svg viewBox="0 0 24 24"><path d="M3 4h18l-7 8.5V19l-4 2v-8.5z"/></svg>';
  $("thead").innerHTML="<tr>"+COLS.map(c=>{ const on=c.t==="set"?F[c.k]!==null:(F[c.k].min!==null||F[c.k].max!==null);
    return `<th class="${c.n?"n":""}"><div class="h"><span class="lb">${c.l}</span><span class="bt">`+
      `<button class="ib ${sortK===c.k&&sortD>0?"on":""}" data-s="${c.k}" data-d="1" title="Ordenar do menor para o maior (A→Z)">${UP}</button>`+
      `<button class="ib ${sortK===c.k&&sortD<0?"on":""}" data-s="${c.k}" data-d="-1" title="Ordenar do maior para o menor (Z→A)">${DOWN}</button>`+
      `<button class="ib ${on?"on":""}" data-f="${c.k}" title="Filtrar esta coluna">${FUN}</button></span></div></th>`; }).join("")+'<th><div class="h"><span class="lb">Descrição NCM</span></div></th></tr>';
  const fatia=vis.slice(page*tam,page*tam+tam);
  $("tbody").innerHTML=fatia.map(r=>"<tr>"+COLS.map(c=>`<td class="${c.n?"n":""}">${c.n?fmtN(r[c.i]):c.k==="mes"?MES[r[c.i]]:texto(c,r)}</td>`).join("")+`<td>${D.ncmDesc[r[4]]}</td></tr>`).join("");
  const tot=vis.reduce((s,r)=>s+r[7],0);
  $("info").innerHTML=`<b>${vis.length.toLocaleString("pt-BR")}</b> de ${D.rows.length.toLocaleString("pt-BR")} linhas · total filtrado: <b>US$ ${fmtN(tot)}</b>`;
  $("pg").textContent=`pág. ${page+1} de ${np}`;
  document.querySelectorAll("[data-s]").forEach(e=>e.onclick=()=>{ sortK=e.dataset.s; sortD=+e.dataset.d; ordenar(); desenha(); });
  document.querySelectorAll("[data-f]").forEach(e=>e.onclick=ev=>{ ev.stopPropagation(); abrePop(e.dataset.f,e); });
}
// ---- popover de filtro ----
function fechaPop(){ const p=document.querySelector(".pop"); if(p) p.remove(); }
document.addEventListener("click",e=>{ if(!e.target.closest(".pop")) fechaPop(); });
function abrePop(k,anchor){ fechaPop(); const c=COLS.find(c=>c.k===k), p=document.createElement("div"); p.className="pop";
  const r=anchor.getBoundingClientRect(); p.style.top=(r.bottom+4)+"px"; p.style.left=Math.min(r.left,innerWidth-310)+"px";
  if(c.t==="range"){
    p.innerHTML=`<div class="info">${c.l}: mínimo e máximo</div><input type="number" id="pmin" placeholder="mínimo" value="${F[k].min??""}"><input type="number" id="pmax" placeholder="máximo" value="${F[k].max??""}"><div class="b"><button class="btn" id="pok">Aplicar</button><button class="btn" id="pclr">Limpar</button></div>`;
    document.body.appendChild(p);
    $("pok").onclick=()=>{ const a=$("pmin").value,b=$("pmax").value; F[k]={min:a===""?null:+a,max:b===""?null:+b}; fechaPop(); filtrar(); };
    $("pclr").onclick=()=>{ F[k]={min:null,max:null}; fechaPop(); filtrar(); }; return; }
  p.innerHTML=`<input type="search" id="pq" placeholder="Buscar..."><div class="l" id="pl"></div><div class="b"><button class="btn" id="pt">Todos</button><button class="btn" id="pn">Nenhum</button><button class="btn" id="pv">Só visíveis</button></div>`;
  document.body.appendChild(p);
  const sel=()=>F[k]===null?new Set(c.ops.map(o=>o[0])):F[k];
  $("pl").innerHTML=c.ops.map(o=>`<label><input type="checkbox" value="${o[0]}" ${sel().has(o[0])?"checked":""}>${o[1]}</label>`).join("");
  const aplica=()=>{ const s=new Set([...p.querySelectorAll("input[type=checkbox]:checked")].map(e=>+e.value)); F[k]=s.size===c.ops.length?null:s; filtrar(); };
  p.querySelectorAll("input[type=checkbox]").forEach(e=>e.onchange=aplica);
  $("pq").oninput=e=>{ const q=e.target.value.toLowerCase(); p.querySelectorAll("#pl label").forEach(l=>l.style.display=l.textContent.toLowerCase().includes(q)?"":"none"); };
  $("pt").onclick=()=>{ p.querySelectorAll("input[type=checkbox]").forEach(e=>e.checked=true); aplica(); };
  $("pn").onclick=()=>{ p.querySelectorAll("input[type=checkbox]").forEach(e=>e.checked=false); aplica(); };
  $("pv").onclick=()=>{ p.querySelectorAll("#pl label").forEach(l=>l.querySelector("input").checked=l.style.display!=="none"); aplica(); };
}
// ---- exportação ----
function linhasExport(){ return vis.map(r=>({"Ano":r[0],"Mês":MES[r[1]],"UF do produto":D.uf[r[2]],"País":D.pais[r[3]],"Código NCM":D.ncm[r[4]],
  "Descrição NCM":D.ncmDesc[r[4]],"Via":D.via[r[5]],"URF":D.urf[r[6]],"Valor US$ FOB":r[7]})); }
function descFiltros(){ const o=[]; COLS.forEach(c=>{ const f=F[c.k];
  if(c.t==="set"&&f) o.push([c.l, f.size<=15?[...f].map(i=>c.ops.find(x=>x[0]===i)[1]).join("; "):f.size+" de "+c.ops.length+" selecionados"]);
  if(c.t==="range"&&(f.min!==null||f.max!==null)) o.push([c.l,"de "+(f.min??"—")+" até "+(f.max??"—")]); }); return o; }
$("x-xlsx").onclick=()=>{ if(typeof XLSX==="undefined"){ alert("Biblioteca xlsx não carregou (sem internet?). Use o csv."); return; }
  const wb=XLSX.utils.book_new(), ws=XLSX.utils.json_to_sheet(linhasExport());
  ws["!cols"]=[8,12,22,26,12,60,18,40,16].map(w=>({wch:w})); XLSX.utils.book_append_sheet(wb,ws,"Dados");
  const fil=descFiltros(); XLSX.utils.book_append_sheet(wb,XLSX.utils.aoa_to_sheet([["Fonte","Comex Stat / MDIC (exportações, US$ FOB)"],["Linhas exportadas",vis.length],["Total US$ FOB",vis.reduce((s,r)=>s+r[7],0)],[],["Filtros ativos"],...(fil.length?fil:[["(nenhum)",""]])]),"Filtros");
  XLSX.writeFile(wb,"exportacoes_filtradas.xlsx"); };
$("x-csv").onclick=()=>{ const L=linhasExport(), h=Object.keys(L[0]||{}); const esc=v=>'"'+String(v).replace(/"/g,'""')+'"';
  const csv=[h.map(esc).join(";"),...L.map(o=>h.map(k=>k==="Valor US$ FOB"?String(o[k]).replace(".",","):esc(o[k])).join(";"))].join("\n");
  const a=document.createElement("a"); a.href=URL.createObjectURL(new Blob(["﻿"+csv],{type:"text/csv;charset=utf-8"})); a.download="exportacoes_filtradas.csv"; a.click(); };
$("limpar").onclick=()=>{ resetF(); sortK="ano"; sortD=1; filtrar(); };
$("ant").onclick=()=>{ if(page>0){page--;desenha();} }; $("prox").onclick=()=>{ if((page+1)*(+$("tam").value)<vis.length){page++;desenha();} };
$("tam").onchange=()=>{ page=0; desenha(); };

// chamada pela aba "Exportações detalhadas": f = {lo,hi,meses[],ufs[],paises[],ncms[],vias[]}
function aplicarFiltros(f){ resetF();
  F.ano={min:f.lo,max:f.hi};
  const set=(k,lista,chave)=>{ const c=COLS.find(c=>c.k===k), alvo=new Set(lista.map(x=>String(x).toLowerCase()));
    const s=new Set(c.ops.filter(o=>alvo.has(String(chave(o)).toLowerCase())).map(o=>o[0])); F[k]=s.size===c.ops.length?null:s; };
  set("mes",f.meses,o=>o[0]); set("uf",f.ufs,o=>o[1]); set("pais",f.paises,o=>o[1]);
  set("ncm",f.ncms,o=>D.ncm[o[0]]); set("via",f.vias,o=>o[1]);
  filtrar(); }
resetF(); filtrar();
</script></body></html>"""
anos = df["Ano"]
subs = {
    "__DADOS__": dados,
    "__N__": f"{len(df):,}".replace(",", "."),
    "__PERIODO__": f"{anos.min()}–{anos.max()}",
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
open(SAIDA, "w", encoding="utf-8").write(HTML)
print(f"Gerado: {SAIDA} ({os.path.getsize(SAIDA) / 1024:.0f} KB)")
