import colorsys
import json
import os
import sys
import webbrowser

import pandas as pd

ARQUIVO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "dados_small_arms.xlsx"
)

LABELS: dict[int, str] = {
    93019000: "Outras Armas de Guerra",
    93020000: "Revólveres e Pistolas",
    93031000: "Armas de Carregar p/ Boca",
    93032000: "Espingarda/Carabina (cano liso)",
    93033000: "Espingarda/Carabina (outras)",
    93062100: "Cartucho (cano liso)",
    93062190: "Outros Cartuchos",
    93063000: "Outros Cartuchos e Partes",
    93051000: "Partes Revólver/Pistola",
    93052000: "Partes Espingarda/Carabina",
    93059100: "Partes Armas de Guerra",
    93059900: "Partes Outras Armas",
}

CATEGORIAS: dict[str, list[int]] = {
    "Armas de Fogo": [93019000, 93020000, 93031000, 93032000, 93033000],
    "Munição e Cartuchos": [93062100, 93062190, 93063000],
    "Partes e Acessórios": [93051000, 93052000, 93059100, 93059900],
}
CATEGORIAS_LIST = list(CATEGORIAS.keys())

CATEGORIA_COR_BASE = {
    "Armas de Fogo": "#22C55E",
    "Munição e Cartuchos": "#3B82F6",
    "Partes e Acessórios": "#F97316",
}

NCM_TO_CATEGORIA = {ncm: cat for cat, lst in CATEGORIAS.items() for ncm in lst}

MES_NOMES = {
    1: "Janeiro",
    2: "Fevereiro",
    3: "Março",
    4: "Abril",
    5: "Maio",
    6: "Junho",
    7: "Julho",
    8: "Agosto",
    9: "Setembro",
    10: "Outubro",
    11: "Novembro",
    12: "Dezembro",
}
MES_ABREV = {
    1: "Jan",
    2: "Fev",
    3: "Mar",
    4: "Abr",
    5: "Mai",
    6: "Jun",
    7: "Jul",
    8: "Ago",
    9: "Set",
    10: "Out",
    11: "Nov",
    12: "Dez",
}

UNIDADE_MAP = {
    "NUMERO (UNIDADE)": "Unidades",
    "QUILOGRAMA LIQUIDO": "kg",
}


def gerar_shades(hex_base: str, n: int) -> list[str]:
    hex_base = hex_base.lstrip("#")
    r = int(hex_base[0:2], 16) / 255
    g = int(hex_base[2:4], 16) / 255
    b = int(hex_base[4:6], 16) / 255
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    if n == 1:
        lights = [l]
    else:
        lo, hi = max(0.28, l - 0.22), min(0.76, l + 0.22)
        step = (hi - lo) / (n - 1)
        lights = [lo + i * step for i in range(n)]
    out = []
    for li in lights:
        rr, gg, bb = colorsys.hls_to_rgb(h, li, s)
        out.append(f"#{round(rr * 255):02X}{round(gg * 255):02X}{round(bb * 255):02X}")
    return out


NCMS: list[str] = []
CORES_CAT: dict[str, str] = {}
for _cat, _ncm_list in CATEGORIAS.items():
    _shades = gerar_shades(CATEGORIA_COR_BASE[_cat], len(_ncm_list))
    for _ncm, _cor in zip(_ncm_list, _shades):
        _label = LABELS[_ncm]
        NCMS.append(_label)
        CORES_CAT[_label] = _cor


def carregar_dados():
    df_raw = pd.read_excel(ARQUIVO, sheet_name="Resultado")

    anos_detectados = sorted(
        {
            int(c.split(" - ")[1])
            for c in df_raw.columns
            if c.startswith("Exportação - ") or c.startswith("Importação - ")
        }
    )

    registros = []
    descricoes = {}
    ncm_unidade: dict[str, str] = {}

    for _, row in df_raw.iterrows():
        ncm = int(row["Código NCM"])
        label = LABELS.get(ncm, str(ncm))
        categoria = NCM_TO_CATEGORIA.get(ncm, "Outros")
        descricoes[ncm] = str(row.get("Descrição NCM", "")).strip()

        unidade_raw = str(row.get("Unidade estatística", "")).strip()
        unidade = UNIDADE_MAP.get(unidade_raw, unidade_raw or "—")
        ncm_unidade[label] = unidade

        mes_raw = str(row["Mês"]).strip()
        try:
            mes_num = int(mes_raw.split(".")[0])
        except (ValueError, IndexError):
            continue
        mes_nome = MES_NOMES.get(mes_num, mes_raw)

        for fluxo in ("Exportação", "Importação"):
            for ano in anos_detectados:
                col_fob = f"{fluxo} - {ano} - Valor US$ FOB"
                col_qtd = f"{fluxo} - {ano} - Quantidade Estatística"
                if col_fob not in df_raw.columns:
                    continue
                fob = float(row[col_fob]) if pd.notna(row[col_fob]) else 0.0
                qtd = (
                    float(row[col_qtd])
                    if col_qtd in df_raw.columns and pd.notna(row[col_qtd])
                    else 0.0
                )
                registros.append(
                    {
                        "NCM": ncm,
                        "Label": label,
                        "Categoria": categoria,
                        "Unidade": unidade,
                        "Fluxo": fluxo,
                        "Ano": ano,
                        "MesNum": mes_num,
                        "Mes": mes_nome,
                        "FOB": fob,
                        "Quantidade": qtd,
                    }
                )

    return pd.DataFrame(registros), descricoes, ncm_unidade


df, NCM_DESCRICOES_OFICIAIS, NCM_UNIDADE = carregar_dados()
ANOS = sorted(int(a) for a in df["Ano"].unique())
MESES = sorted(int(m) for m in df["MesNum"].unique())

CATEGORIA_UNIDADE: dict[str, str] = {}
for _cat, _ncm_list in CATEGORIAS.items():
    _unidades = {NCM_UNIDADE.get(LABELS[n]) for n in _ncm_list}
    CATEGORIA_UNIDADE[_cat] = _unidades.pop() if len(_unidades) == 1 else "Mista"

AVISOS_QUALIDADE: dict[int, str] = {
    93062100: (
        "Quantidade (kg) de 2011-2012 é inconsistente com o restante da série "
        "(preço implícito abaixo de US$ 4/kg, contra US$ 16-33/kg de 2013 em diante), "
        "sugerindo mudança na metodologia de mensuração da Quantidade Estatística pelo "
        "Comex Stat/MDIC nesse período. Os valores de FOB não aparentam ser afetados."
    ),
}


def fmt_usd(v):
    if v >= 1e6:
        return f"US$ {v / 1e6:.1f}M"
    if v >= 1e3:
        return f"US$ {v / 1e3:.0f}K"
    return f"US$ {v:,.0f}"


_total_export_fob = df.loc[df["Fluxo"] == "Exportação", "FOB"].sum()

HEADER_FONTE_TEXTO = (
    f"Fonte: Comex Stat / MDIC · USD FOB · dados mensais · {len(LABELS)} NCMs · "
    f"{MES_ABREV[MESES[0]]}/{ANOS[0]}–{MES_ABREV[MESES[-1]]}/{ANOS[-1]} · "
    f"Total exportado no período: {fmt_usd(_total_export_fob)}"
)

_desc_ordenadas = []
for _cat, _ncm_list in CATEGORIAS.items():
    for _ncm in _ncm_list:
        _unid = NCM_UNIDADE.get(LABELS[_ncm], "—")
        _desc_ordenadas.append(
            f"{_ncm} — {LABELS[_ncm]} ({_unid}): {NCM_DESCRICOES_OFICIAIS.get(_ncm, '')}"
        )
HEADER_DETALHE_TEXTO = "\n".join(_desc_ordenadas)

BG = "#0D1117"
BG2 = "#161B22"
BG3 = "#1C2128"
BORDA = "#30363D"
TEXTO = "#E6EDF3"
TEXTO2 = "#8B949E"


def gerar_html():
    os.makedirs("docs", exist_ok=True)

    records = df.to_dict("records")
    data_json = json.dumps(records, ensure_ascii=False)
    ncms_json = json.dumps(NCMS, ensure_ascii=False)
    categorias_json = json.dumps(CATEGORIAS_LIST, ensure_ascii=False)
    cores_ncm_json = json.dumps(CORES_CAT, ensure_ascii=False)
    cores_cat_json = json.dumps(CATEGORIA_COR_BASE, ensure_ascii=False)
    anos_json = json.dumps(ANOS)
    meses_json = json.dumps(MESES)
    mes_abrev_json = json.dumps(
        {str(k): v for k, v in MES_ABREV.items()}, ensure_ascii=False
    )
    ncm_unidade_json = json.dumps(NCM_UNIDADE, ensure_ascii=False)
    categoria_unidade_json = json.dumps(CATEGORIA_UNIDADE, ensure_ascii=False)

    header_html = HEADER_FONTE_TEXTO
    detalhe_html = HEADER_DETALHE_TEXTO.replace("\n", "<br>")

    js = r"""
    const DATA = __DATA_JSON__;
    const NCMS = __NCMS_JSON__;
    const CATEGORIAS_LIST = __CATEGORIAS_JSON__;
    const CORES_NCM = __CORES_NCM_JSON__;
    const CORES_CAT_BASE = __CORES_CAT_JSON__;
    const ANOS = __ANOS_JSON__;
    const MESES = __MESES_JSON__;
    const MES_ABREV = __MES_ABREV_JSON__;
    const NCM_UNIDADE = __NCM_UNIDADE_JSON__;
    const CATEGORIA_UNIDADE = __CATEGORIA_UNIDADE_JSON__;

    const BG = "__BG__", BG2 = "__BG2__", BG3 = "__BG3__",
        BORDA = "__BORDA__", TEXTO = "__TEXTO__", TEXTO2 = "__TEXTO2__";

    const FLUXO_EXP = "Exporta\u00e7\u00e3o", FLUXO_IMP = "Importa\u00e7\u00e3o";

    function fmtUsd(v) {
        if (v === null || v === undefined) return "\u2014";
        const sign = v < 0 ? "-" : "";
        const av = Math.abs(v);
        if (av >= 1e6) return sign + "US$ " + (av / 1e6).toFixed(1) + "M";
        if (av >= 1e3) return sign + "US$ " + Math.round(av / 1e3) + "K";
        return sign + "US$ " + av.toLocaleString("en-US", { maximumFractionDigits: 0 });
    }
    function fmtQtd(v, unidade) {
        if (v === null || v === undefined) return "\u2014";
        const num = v.toLocaleString("pt-BR", { maximumFractionDigits: 0 });
        return unidade === "kg" ? num + " kg" : num + " un";
    }
    function fmtPreco(v, unidade) {
        if (v === null || v === undefined) return "\u2014";
        const suf = unidade === "kg" ? "/kg" : "/un";
        return "US$ " + v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + suf;
    }
    function metricLabel(metric) {
        return metric === "fob" ? "FOB (US$)" : "Quantidade";
    }
    function unidadeLabel(unidade) {
        return unidade === "kg" ? "kg" : "unidades";
    }

    const PALETA_DINAMICA = [
        "#3B82F6", "#F97316", "#22C55E", "#EF4444", "#A855F7", "#EAB308",
        "#06B6D4", "#EC4899", "#84CC16", "#6366F1", "#F43F5E", "#14B8A6",
    ];
    function corDinamica(indice) {
        return PALETA_DINAMICA[indice % PALETA_DINAMICA.length];
    }

    function getDimInfo(nivel) {
        if (nivel === "Categoria") return { col: "Categoria", order: CATEGORIAS_LIST, colors: CORES_CAT_BASE };
        return { col: "Label", order: NCMS, colors: CORES_NCM };
    }
    function unidadeDoItem(col, item) {
        return col === "Categoria" ? CATEGORIA_UNIDADE[item] : NCM_UNIDADE[item];
    }
    function agruparPorUnidade(ncmSel) {
        const grupos = [];
        for (const unidade of ["Unidades", "kg"]) {
            const itens = NCMS.filter(l => ncmSel.includes(l) && NCM_UNIDADE[l] === unidade);
            if (itens.length) grupos.push({ unidade, itens });
        }
        return grupos;
    }

    function somaFobQtd(arr) {
        let fob = 0, qtd = 0;
        for (const r of arr) { fob += r.FOB; qtd += r.Quantidade; }
        return { fob, qtd };
    }
    function valorMetrica(agg, metric) {
        if (!agg) return null;
        return metric === "fob" ? agg.fob : agg.qtd;
    }
    function formatarAgg(agg, metric, unidade) {
        if (!agg) return "\u2014";
        return metric === "fob" ? fmtUsd(agg.fob) : fmtQtd(agg.qtd, unidade);
    }
    function precoMedio(agg) {
        if (!agg || !agg.qtd) return null;
        return agg.fob / agg.qtd;
    }

    function layoutBase() {
        return {
            paper_bgcolor: BG, plot_bgcolor: BG2,
            font: { family: "Inter, Segoe UI, Arial", color: TEXTO, size: 13 },
            margin: { t: 36, b: 60, l: 105, r: 30 },
            xaxis: { gridcolor: BORDA, zerolinecolor: BORDA,
                    tickfont: { color: TEXTO2 }, title: { font: { color: TEXTO2 } } },
            yaxis: { gridcolor: BORDA, zerolinecolor: BORDA,
                    tickfont: { color: TEXTO2 }, title: { font: { color: TEXTO2 } } },
            legend: { bgcolor: "rgba(0,0,0,0)", bordercolor: BORDA, borderwidth: 1,
                    font: { color: TEXTO, size: 11 }, orientation: "h",
                    yanchor: "bottom", y: 1.0, xanchor: "center", x: 0.5 },
            hoverlabel: { bgcolor: BG3, bordercolor: BORDA, font: { color: TEXTO } },
        };
    }

    function plotVazio(divId, msg) {
        const layout = layoutBase();
        layout.xaxis.visible = false;
        layout.yaxis.visible = false;
        layout.height = 180;
        layout.margin = { t: 10, b: 10, l: 10, r: 10 };
        layout.annotations = [{
            text: "\u26a0  " + msg, x: 0.5, y: 0.5, xref: "paper", yref: "paper",
            showarrow: false, font: { size: 14, color: TEXTO2 }, align: "center",
        }];
        Plotly.newPlot(divId, [], layout, { displayModeBar: true, responsive: true });
    }

    function filterBase(ncmSel, anoMin, anoMax, mesesSel) {
        return DATA.filter(d =>
            ncmSel.includes(d.Label) &&
            d.Ano >= anoMin && d.Ano <= anoMax &&
            mesesSel.includes(d.MesNum)
        );
    }

    function gridPeriodos(anoMin, anoMax, mesesSel, granularidade) {
        if (granularidade === "anual") {
            return ANOS.filter(a => a >= anoMin && a <= anoMax).map(a => ({ key: a, label: String(a) }));
        }
        const out = [];
        for (const ano of ANOS) {
            if (ano < anoMin || ano > anoMax) continue;
            for (const mes of MESES) {
                if (!mesesSel.includes(mes)) continue;
                out.push({ key: ano * 100 + mes, label: MES_ABREV[String(mes)] + "/" + ano });
            }
        }
        return out;
    }
    function chavePeriodo(registro, granularidade) {
        return granularidade === "anual" ? registro.Ano : registro.Ano * 100 + registro.MesNum;
    }

    function montarSubGraficos(containerId, grupos) {
        const cont = document.getElementById(containerId);
        const existentes = cont.querySelectorAll(":scope > .sub-chart");
        if (existentes.length === grupos.length) {
            return grupos.map((g, i) => {
                const wrap = existentes[i];
                let lbl = wrap.querySelector(".sub-chart-label");
                if (g.label) {
                    if (!lbl) {
                        lbl = document.createElement("div");
                        lbl.className = "sub-chart-label";
                        wrap.insertBefore(lbl, wrap.firstChild);
                    }
                    lbl.textContent = g.label;
                } else if (lbl) {
                    lbl.remove();
                }
                return wrap.querySelector(".plot-target").id;
            });
        }
        cont.innerHTML = "";
        return grupos.map((g, i) => {
            const wrap = document.createElement("div");
            wrap.className = "sub-chart";
            if (g.label) {
                const lbl = document.createElement("div");
                lbl.className = "sub-chart-label";
                lbl.textContent = g.label;
                wrap.appendChild(lbl);
            }
            const div = document.createElement("div");
            div.className = "plot-target";
            div.id = containerId + "-plot-" + i;
            wrap.appendChild(div);
            cont.appendChild(wrap);
            return div.id;
        });
    }

    function definirSubtitulo(id, texto) {
        const el = document.getElementById(id);
        if (el) el.textContent = texto;
    }

    function plotEvolucao(divId, ncmSel, anoMin, anoMax, mesesSel, metric, unidade) {
        const d = filterBase(ncmSel, anoMin, anoMax, mesesSel);
        if (d.length === 0 || ncmSel.length === 0) {
            plotVazio(divId, "Nenhuma categoria selecionada ou sem dados no per\u00edodo");
            return;
        }
        const traces = [];
        const specs = [[FLUXO_EXP, "#3B82F6", "rgba(59,130,246,0.12)"], [FLUXO_IMP, "#EF4444", "rgba(239,68,68,0.12)"]];
        let algumDado = false;
        for (const [fluxo, cor, rgba] of specs) {
            const sub = d.filter(x => x.Fluxo === fluxo);
            if (sub.length === 0) continue;
            const map = new Map();
            for (const r of sub) {
                const key = r.Ano * 100 + r.MesNum;
                const cur = map.get(key) || { fob: 0, qtd: 0 };
                cur.fob += r.FOB; cur.qtd += r.Quantidade;
                map.set(key, cur);
            }
            const keys = [...map.keys()].sort((a, b) => a - b);
            if (keys.length === 0) continue;
            const xs = keys.map(k => MES_ABREV[String(k % 100)] + "/" + Math.floor(k / 100));
            const ys = keys.map(k => valorMetrica(map.get(k), metric));
            if (ys.every(v => !v)) continue;
            algumDado = true;
            const customdata = keys.map(k => formatarAgg(map.get(k), metric, unidade));
            traces.push({
                x: xs, y: ys, name: fluxo, mode: "lines+markers",
                line: { color: cor, width: 3 },
                marker: { size: 6, color: cor, line: { color: BG, width: 2 } },
                fill: "tozeroy", fillcolor: rgba,
                customdata: customdata,
                hovertemplate: "<b>%{x}</b><br>" + fluxo + ": %{customdata}<extra></extra>",
            });
        }
        if (!algumDado) {
            plotVazio(divId, "Nenhuma categoria selecionada ou sem dados no per\u00edodo");
            return;
        }
        const layout = layoutBase();
        layout.xaxis = { ...layout.xaxis, title: "M\u00eas / Ano", tickangle: -60, type: "category" };
        layout.yaxis.title = metric === "fob" ? "USD FOB" : ("Quantidade (" + unidade + ")");
        if (metric === "fob") layout.yaxis.tickformat = "$,.0f";
        layout.height = 420;
        Plotly.newPlot(divId, traces, layout, { displayModeBar: true, responsive: true });
    }

    function renderEvolucao() {
        const ncmSel = getSelectedNcms();
        const [anoMin, anoMax] = getAnoRange();
        const mesesSel = getSelectedMeses();
        const metric = document.getElementById("evolucao-metrica").value;

        const grupos = metric === "fob"
            ? [{ label: null, itens: ncmSel, unidade: null }]
            : agruparPorUnidade(ncmSel).map(g => ({
                label: "Quantidade em " + unidadeLabel(g.unidade),
                itens: g.itens,
                unidade: g.unidade,
            }));

        if (grupos.length === 0) {
            const divIds = montarSubGraficos("graph-evolucao-container", [{ label: null }]);
            plotVazio(divIds[0], "Nenhuma categoria selecionada ou sem dados no per\u00edodo");
        } else {
            const divIds = montarSubGraficos("graph-evolucao-container", grupos);
            divIds.forEach((divId, i) => {
                const g = grupos[i];
                plotEvolucao(divId, g.itens, anoMin, anoMax, mesesSel, metric, g.unidade);
            });
        }
        definirSubtitulo("evolucao-subtitle", metricLabel(metric) + " \u2022 Exporta\u00e7\u00e3o vs Importa\u00e7\u00e3o \u2022 mensal");
    }

    function plotSaldo(divId, ncmSel, anoMin, anoMax, mesesSel, nivel, metric, granularidade) {
        const d = filterBase(ncmSel, anoMin, anoMax, mesesSel);
        if (d.length === 0) {
            plotVazio(divId, "Nenhuma categoria selecionada ou sem dados no per\u00edodo");
            return;
        }
        const periodos = gridPeriodos(anoMin, anoMax, mesesSel, granularidade);
        const { col, order, colors } = getDimInfo(nivel);
        const traces = [];
        for (const item of order) {
            if (metric !== "fob" && unidadeDoItem(col, item) === "Mista") continue;
            const sub = d.filter(x => x[col] === item);
            if (sub.length === 0) continue;
            const unidadeItem = unidadeDoItem(col, item);
            const xs = [], ys = [], custom = [];
            for (const p of periodos) {
                const subP = sub.filter(x => chavePeriodo(x, granularidade) === p.key);
                const aggExp = somaFobQtd(subP.filter(x => x.Fluxo === FLUXO_EXP));
                const aggImp = somaFobQtd(subP.filter(x => x.Fluxo === FLUXO_IMP));
                const saldo = valorMetrica(aggExp, metric) - valorMetrica(aggImp, metric);
                xs.push(p.label); ys.push(saldo);
                custom.push(metric === "fob" ? fmtUsd(saldo) : fmtQtd(saldo, unidadeItem));
            }
            if (ys.every(v => v === 0)) continue;
            traces.push({
                x: xs, y: ys, name: item, type: "bar",
                marker: { color: colors[item], opacity: 0.9 },
                customdata: custom,
                hovertemplate: "<b>" + item + "</b><br>%{x}<br>Saldo: %{customdata}<extra></extra>",
            });
        }
        if (traces.length === 0) {
            plotVazio(divId, "Nenhuma categoria selecionada ou sem dados no per\u00edodo para essa m\u00e9trica");
            return;
        }
        const layout = layoutBase();
        layout.barmode = "group";
        layout.xaxis = { ...layout.xaxis, title: granularidade === "anual" ? "Ano" : "M\u00eas / Ano", type: "category", tickangle: -45 };
        layout.yaxis.title = "Saldo";
        if (metric === "fob") layout.yaxis.tickformat = "$,.0f";
        layout.height = 420;
        layout.shapes = [{ type: "line", x0: 0, x1: 1, xref: "paper", y0: 0, y1: 0,
                        line: { color: TEXTO2, width: 1, dash: "dot" } }];
        Plotly.newPlot(divId, traces, layout, { displayModeBar: true, responsive: true });
    }

    function renderSaldo() {
        const ncmSel = getSelectedNcms();
        const [anoMin, anoMax] = getAnoRange();
        const mesesSel = getSelectedMeses();
        const nivel = document.getElementById("saldo-nivel").value;
        const metric = document.getElementById("saldo-metrica").value;
        const granularidade = document.getElementById("saldo-granularidade").value;
        const divIds = montarSubGraficos("graph-saldo-container", [{ label: null }]);
        plotSaldo(divIds[0], ncmSel, anoMin, anoMax, mesesSel, nivel, metric, granularidade);
        const nivelTxt = nivel === "Categoria" ? "Categoria" : "NCM";
        definirSubtitulo("saldo-subtitle", nivelTxt + " \u2022 " + metricLabel(metric) + " \u2022 " + (granularidade === "anual" ? "anual" : "mensal"));
    }

    function plotComposicao(divId, fluxo, ncmSel, anoMin, anoMax, mesesSel, nivel, metric, granularidade) {
        const d = filterBase(ncmSel, anoMin, anoMax, mesesSel).filter(x => x.Fluxo === fluxo);
        if (d.length === 0) {
            plotVazio(divId, "Nenhum dado de " + fluxo + " para os filtros selecionados");
            return;
        }
        const periodos = gridPeriodos(anoMin, anoMax, mesesSel, granularidade);
        const { col, order, colors } = getDimInfo(nivel);
        const traces = [];
        for (const item of order) {
            if (metric !== "fob" && unidadeDoItem(col, item) === "Mista") continue;
            const sub = d.filter(x => x[col] === item);
            if (sub.length === 0) continue;
            const unidadeItem = unidadeDoItem(col, item);
            const xs = [], ys = [], custom = [];
            for (const p of periodos) {
                const subP = sub.filter(x => chavePeriodo(x, granularidade) === p.key);
                const agg = somaFobQtd(subP);
                const v = valorMetrica(agg, metric);
                xs.push(p.label);
                ys.push(v > 0 ? v : null);
                custom.push(v > 0 ? formatarAgg(agg, metric, unidadeItem) : "Sem dados");
            }
            if (ys.every(v => v === null)) continue;
            traces.push({
                x: xs, y: ys, name: item, type: "bar",
                marker: { color: colors[item] },
                customdata: custom,
                hovertemplate: "<b>" + item + "</b><br>%{x}: %{customdata}<extra></extra>",
            });
        }
        if (traces.length === 0) {
            plotVazio(divId, "Nenhum dado de " + fluxo + " para os filtros/m\u00e9trica selecionados");
            return;
        }
        const layout = layoutBase();
        layout.barmode = "stack";
        layout.xaxis = { ...layout.xaxis, title: granularidade === "anual" ? "Ano" : "M\u00eas / Ano", type: "category", tickangle: -45 };
        layout.yaxis.title = fluxo + " (" + metricLabel(metric) + ")";
        if (metric === "fob") layout.yaxis.tickformat = "$,.0f";
        layout.height = 420;
        Plotly.newPlot(divId, traces, layout, { displayModeBar: true, responsive: true });
    }

    function renderComposicao() {
        const ncmSel = getSelectedNcms();
        const [anoMin, anoMax] = getAnoRange();
        const mesesSel = getSelectedMeses();
        const fluxo = document.getElementById("comp-fluxo").value;
        const nivel = document.getElementById("comp-nivel").value;
        const metric = document.getElementById("comp-metrica").value;
        const granularidade = document.getElementById("comp-granularidade").value;
        const divIds = montarSubGraficos("graph-composicao-container", [{ label: null }]);
        plotComposicao(divIds[0], fluxo, ncmSel, anoMin, anoMax, mesesSel, nivel, metric, granularidade);
        const nivelTxt = nivel === "Categoria" ? "Categoria" : "NCM";
        definirSubtitulo("composicao-subtitle", fluxo + " \u2022 " + nivelTxt + " \u2022 " + metricLabel(metric) + " \u2022 " + (granularidade === "anual" ? "anual" : "mensal"));
    }

    function plotHeatmapTrace(divId, z, text, xLabels, yLabels, xTitle, leftMargin) {
        const trace = {
            z: z, x: xLabels, y: yLabels, type: "heatmap",
            colorscale: [
                [0.0, "#1C2128"], [0.15, "#1D4ED8"], [0.4, "#0EA5E9"],
                [0.65, "#22C55E"], [0.85, "#F59E0B"], [1.0, "#EF4444"],
            ],
            text: text, texttemplate: "%{text}",
            textfont: { size: 9, color: TEXTO },
            hoverongaps: false,
            hovertemplate: "<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
            colorbar: { tickfont: { color: TEXTO2 }, bgcolor: BG2,
                        bordercolor: BORDA, outlinecolor: BORDA },
            zmin: 0,
        };
        const layout = layoutBase();
        layout.xaxis = { title: xTitle, gridcolor: BORDA, tickfont: { color: TEXTO2 }, tickangle: -45, type: "category" };
        layout.yaxis = { gridcolor: BORDA, tickfont: { color: TEXTO, size: 10 } };
        layout.margin = { t: 20, b: 60, l: leftMargin, r: 30 };
        layout.height = 110 + 32 * yLabels.length;
        Plotly.newPlot(divId, [trace], layout, { displayModeBar: true, responsive: true });
    }

    function plotHeatmapItens(divId, fluxo, ncmSel, anoMin, anoMax, mesesSel, nivel, metric, granularidade) {
        const d = filterBase(ncmSel, anoMin, anoMax, mesesSel).filter(x => x.Fluxo === fluxo);
        if (d.length === 0) {
            plotVazio(divId, "Nenhum dado de " + fluxo + " para exibir no heatmap");
            return;
        }
        const { col, order, colors } = getDimInfo(nivel);
        const ordemValida = order.filter(item => metric === "fob" || unidadeDoItem(col, item) !== "Mista");
        if (ordemValida.length === 0) {
            plotVazio(divId, "Nenhum item com unidade compat\u00edvel para essa m\u00e9trica");
            return;
        }
        const periodos = gridPeriodos(anoMin, anoMax, mesesSel, granularidade);
        const z = [], text = [];
        for (const item of ordemValida) {
            const unidadeItem = unidadeDoItem(col, item);
            const rowZ = [], rowT = [];
            for (const p of periodos) {
                const agg = somaFobQtd(d.filter(x => x[col] === item && chavePeriodo(x, granularidade) === p.key));
                const v = valorMetrica(agg, metric);
                rowZ.push(v > 0 ? v : null);
                rowT.push(v > 0 ? formatarAgg(agg, metric, unidadeItem) : "\u2014");
            }
            z.push(rowZ); text.push(rowT);
        }
        plotHeatmapTrace(divId, z, text, periodos.map(p => p.label), ordemValida,
            granularidade === "anual" ? "Ano" : "M\u00eas / Ano", nivel === "NCM" ? 230 : 150);
    }

    function plotHeatmapSazonalidade(divId, fluxo, ncmSel, anoMin, anoMax, metric, unidade) {
        const d = DATA.filter(x => x.Fluxo === fluxo && ncmSel.includes(x.Label) && x.Ano >= anoMin && x.Ano <= anoMax);
        if (d.length === 0) {
            plotVazio(divId, "Nenhum dado de " + fluxo + " para exibir no heatmap");
            return;
        }
        const z = [], text = [];
        for (const mes of MESES) {
            const rowZ = [], rowT = [];
            for (const ano of ANOS) {
                if (ano < anoMin || ano > anoMax) continue;
                const agg = somaFobQtd(d.filter(x => x.MesNum === mes && x.Ano === ano));
                const v = valorMetrica(agg, metric);
                rowZ.push(v > 0 ? v : null);
                rowT.push(v > 0 ? formatarAgg(agg, metric, unidade) : "\u2014");
            }
            z.push(rowZ); text.push(rowT);
        }
        const anosFiltrados = ANOS.filter(a => a >= anoMin && a <= anoMax);
        plotHeatmapTrace(divId, z, text, anosFiltrados.map(String), MESES.map(m => MES_ABREV[String(m)]), "Ano", 90);
    }

    function renderHeatmap() {
        const ncmSel = getSelectedNcms();
        const [anoMin, anoMax] = getAnoRange();
        const mesesSel = getSelectedMeses();
        const fluxo = document.getElementById("hm-fluxo").value;
        const nivel = document.getElementById("hm-nivel").value;
        const metric = document.getElementById("hm-metrica").value;
        const eixo = document.getElementById("hm-eixo").value;
        const granularidade = document.getElementById("hm-granularidade").value;

        document.getElementById("hm-nivel-wrap").style.display = eixo === "mes" ? "none" : "";
        document.getElementById("hm-granularidade-wrap").style.display = eixo === "mes" ? "none" : "";

        if (eixo === "itens") {
            const divIds = montarSubGraficos("graph-heatmap-container", [{ label: null }]);
            plotHeatmapItens(divIds[0], fluxo, ncmSel, anoMin, anoMax, mesesSel, nivel, metric, granularidade);
            const nivelTxt = nivel === "Categoria" ? "Categoria" : "NCM";
            definirSubtitulo("heatmap-subtitle", fluxo + " \u2022 " + nivelTxt + " \u00d7 " + (granularidade === "anual" ? "Ano" : "M\u00eas/Ano") + " \u2022 " + metricLabel(metric));
            return;
        }

        const grupos = metric === "fob"
            ? [{ label: null, itens: ncmSel, unidade: null }]
            : agruparPorUnidade(ncmSel).map(g => ({
                label: "Quantidade em " + unidadeLabel(g.unidade),
                itens: g.itens,
                unidade: g.unidade,
            }));

        if (grupos.length === 0) {
            const divIds = montarSubGraficos("graph-heatmap-container", [{ label: null }]);
            plotVazio(divIds[0], "Nenhuma categoria selecionada ou sem dados no per\u00edodo");
        } else {
            const divIds = montarSubGraficos("graph-heatmap-container", grupos);
            divIds.forEach((divId, i) => {
                const g = grupos[i];
                plotHeatmapSazonalidade(divId, fluxo, g.itens, anoMin, anoMax, metric, g.unidade);
            });
        }
        definirSubtitulo("heatmap-subtitle", fluxo + " \u2022 Sazonalidade (M\u00eas \u00d7 Ano) \u2022 " + metricLabel(metric));
    }

    function plotDonut(divId, fluxo, ncmSel, mesesSel, nivel, metric, ano, mes) {
        let d = DATA.filter(x => x.Ano === ano && x.Fluxo === fluxo && ncmSel.includes(x.Label));
        d = mes === "todos" ? d.filter(x => mesesSel.includes(x.MesNum)) : d.filter(x => x.MesNum === mes);
        if (d.length === 0) {
            plotVazio(divId, "Nenhum dado de " + fluxo + " no per\u00edodo selecionado");
            return;
        }
        const { col, order, colors } = getDimInfo(nivel);
        const labels = [], values = [], cores = [], units = [];
        for (const item of order) {
            if (metric !== "fob" && unidadeDoItem(col, item) === "Mista") continue;
            const sub = d.filter(x => x[col] === item);
            if (sub.length === 0) continue;
            const agg = somaFobQtd(sub);
            const v = valorMetrica(agg, metric);
            if (!v || v <= 0) continue;
            labels.push(item); values.push(v); cores.push(colors[item]); units.push(unidadeDoItem(col, item));
        }
        if (labels.length === 0) {
            plotVazio(divId, "Nenhum dado de " + fluxo + " para essa m\u00e9trica no per\u00edodo selecionado");
            return;
        }
        const trace = {
            labels: labels, values: values, type: "pie", hole: 0.48,
            marker: { colors: cores, line: { color: BG, width: 2 } },
            textinfo: "percent",
            textfont: { color: TEXTO, size: 11 },
            customdata: values.map((v, i) => metric === "fob" ? fmtUsd(v) : fmtQtd(v, units[i])),
            hovertemplate: "<b>%{label}</b><br>%{customdata}<br>%{percent}<extra></extra>",
        };
        const layout = layoutBase();
        delete layout.legend;
        layout.showlegend = true;
        layout.legend = { orientation: "v", x: 1.02, y: 0.5, font: { color: TEXTO, size: 10 } };
        layout.height = 420;
        Plotly.newPlot(divId, [trace], layout, { displayModeBar: true, responsive: true });
    }

    function renderDonut() {
        const ncmSel = getSelectedNcms();
        const mesesSel = getSelectedMeses();
        const fluxo = document.getElementById("donut-fluxo").value;
        const nivel = document.getElementById("donut-nivel").value;
        const metric = document.getElementById("donut-metrica").value;
        const ano = parseInt(document.getElementById("donut-ano").value);
        const mesValor = document.getElementById("donut-mes").value;
        const mes = mesValor === "todos" ? "todos" : parseInt(mesValor);
        const divIds = montarSubGraficos("graph-donut-container", [{ label: null }]);
        plotDonut(divIds[0], fluxo, ncmSel, mesesSel, nivel, metric, ano, mes);
        const nivelTxt = nivel === "Categoria" ? "Categoria" : "NCM";
        const periodoTxt = mes === "todos" ? String(ano) : (MES_ABREV[String(mes)] + "/" + ano);
        definirSubtitulo("donut-subtitle", fluxo + " \u2022 " + nivelTxt + " \u2022 " + metricLabel(metric) + " \u2022 " + periodoTxt);
    }

    function plotPrecoMedio(divId, fluxo, ncmSel, anoMin, anoMax, mesesSel, nivel, unidadeAlvo) {
        const { col, order } = getDimInfo(nivel);
        const itensAlvo = order.filter(item => unidadeDoItem(col, item) === unidadeAlvo);
        if (itensAlvo.length === 0) {
            plotVazio(divId, "Nenhum item com unidade \"" + unidadeAlvo + "\" nesse n\u00edvel");
            return;
        }
        const d = filterBase(ncmSel, anoMin, anoMax, mesesSel).filter(x => x.Fluxo === fluxo);
        const traces = [];
        for (const item of itensAlvo) {
            const sub = d.filter(x => x[col] === item);
            if (sub.length === 0) continue;
            const anosSet = [...new Set(sub.map(x => x.Ano))].sort((a, b) => a - b);
            const ys = [], custom = [];
            for (const ano of anosSet) {
                const agg = somaFobQtd(sub.filter(x => x.Ano === ano));
                const p = precoMedio(agg);
                ys.push(p);
                custom.push(p !== null ? fmtPreco(p, unidadeAlvo) : "Sem dados");
            }
            if (ys.every(v => v === null)) continue;
            const cor = corDinamica(traces.length);
            traces.push({
                x: anosSet, y: ys, name: item, mode: "lines+markers",
                line: { color: cor, width: 2.5 },
                marker: { size: 7, color: cor, line: { color: BG, width: 1.5 } },
                customdata: custom,
                hovertemplate: "<b>" + item + "</b><br>%{x}: %{customdata}<extra></extra>",
            });
        }
        if (traces.length === 0) {
            plotVazio(divId, "Sem dados de pre\u00e7o m\u00e9dio (" + fluxo + ") para os filtros selecionados");
            return;
        }
        const layout = layoutBase();
        layout.xaxis = { ...layout.xaxis, title: "Ano", dtick: 1, tickangle: -45 };
        layout.yaxis.title = "US$ / " + unidadeLabel(unidadeAlvo);
        layout.height = 420;
        Plotly.newPlot(divId, traces, layout, { displayModeBar: true, responsive: true });
    }

    function renderPrecoMedio() {
        const ncmSel = getSelectedNcms();
        const [anoMin, anoMax] = getAnoRange();
        const mesesSel = getSelectedMeses();
        const fluxo = document.getElementById("preco-fluxo").value;
        const nivel = document.getElementById("preco-nivel").value;
        const unidade = document.getElementById("preco-unidade").value;
        const divIds = montarSubGraficos("graph-preco-container", [{ label: null }]);
        plotPrecoMedio(divIds[0], fluxo, ncmSel, anoMin, anoMax, mesesSel, nivel, unidade);
        const nivelTxt = nivel === "Categoria" ? "Categoria" : "NCM";
        definirSubtitulo("preco-subtitle", fluxo + " \u2022 " + nivelTxt + " \u2022 US$/" + unidadeLabel(unidade) + " \u2022 anual");
    }

    function getSelectedNcms() {
        return [...document.querySelectorAll(".ncm-check:checked")].map(el => el.value);
    }
    function getSelectedMeses() {
        const sel = [...document.querySelectorAll(".mes-check:checked")].map(el => parseInt(el.value));
        return sel.length ? sel : MESES;
    }
    function getAnoRange() {
        const lo = parseInt(document.getElementById("ano-min").value);
        const hi = parseInt(document.getElementById("ano-max").value);
        return [Math.min(lo, hi), Math.max(lo, hi)];
    }
    function updateAnoLabel() {
        const [lo, hi] = getAnoRange();
        document.getElementById("ano-range-label").textContent = lo + " \u2013 " + hi;
        const min = parseInt(document.getElementById("ano-min").min);
        const max = parseInt(document.getElementById("ano-min").max);
        const pctLo = ((lo - min) / (max - min)) * 100;
        const pctHi = ((hi - min) / (max - min)) * 100;
        const fill = document.getElementById("ano-track-fill");
        fill.style.left = pctLo + "%";
        fill.style.width = (pctHi - pctLo) + "%";
    }

    function renderAll() {
        renderEvolucao();
        renderSaldo();
        renderComposicao();
        renderHeatmap();
        renderDonut();
        renderPrecoMedio();
    }

    function toggleSection(key, visible) {
        const el = document.getElementById("section-" + key);
        if (el) el.style.display = visible ? "" : "none";
    }

    document.addEventListener("DOMContentLoaded", () => {
        document.querySelectorAll(".ncm-check").forEach(el => el.addEventListener("change", renderAll));
        document.querySelectorAll(".mes-check").forEach(el => el.addEventListener("change", renderAll));
        document.getElementById("ano-min").addEventListener("input", () => { updateAnoLabel(); renderAll(); });
        document.getElementById("ano-max").addEventListener("input", () => { updateAnoLabel(); renderAll(); });

        [
            [["evolucao-metrica"], renderEvolucao],
            [["saldo-nivel", "saldo-metrica", "saldo-granularidade"], renderSaldo],
            [["comp-fluxo", "comp-nivel", "comp-metrica", "comp-granularidade"], renderComposicao],
            [["hm-fluxo", "hm-nivel", "hm-metrica", "hm-eixo", "hm-granularidade"], renderHeatmap],
            [["donut-fluxo", "donut-nivel", "donut-metrica", "donut-ano", "donut-mes"], renderDonut],
            [["preco-fluxo", "preco-nivel", "preco-unidade"], renderPrecoMedio],
        ].forEach(([ids, handler]) => {
            ids.forEach(id => document.getElementById(id).addEventListener("change", handler));
        });

        document.querySelectorAll(".viz-check").forEach(el => {
            el.addEventListener("change", () => toggleSection(el.value, el.checked));
        });
        document.getElementById("meses-todos").addEventListener("click", () => {
            document.querySelectorAll(".mes-check").forEach(el => el.checked = true);
            renderAll();
        });
        document.getElementById("meses-nenhum").addEventListener("click", () => {
            document.querySelectorAll(".mes-check").forEach(el => el.checked = false);
            renderAll();
        });

        updateAnoLabel();
        renderAll();
    });
"""

    js = (
        js.replace("__DATA_JSON__", data_json)
        .replace("__NCMS_JSON__", ncms_json)
        .replace("__CATEGORIAS_JSON__", categorias_json)
        .replace("__CORES_NCM_JSON__", cores_ncm_json)
        .replace("__CORES_CAT_JSON__", cores_cat_json)
        .replace("__ANOS_JSON__", anos_json)
        .replace("__MESES_JSON__", meses_json)
        .replace("__MES_ABREV_JSON__", mes_abrev_json)
        .replace("__NCM_UNIDADE_JSON__", ncm_unidade_json)
        .replace("__CATEGORIA_UNIDADE_JSON__", categoria_unidade_json)
        .replace("__BG__", BG)
        .replace("__BG2__", BG2)
        .replace("__BG3__", BG3)
        .replace("__BORDA__", BORDA)
        .replace("__TEXTO__", TEXTO)
        .replace("__TEXTO2__", TEXTO2)
    )

    ano_min, ano_max = ANOS[0], ANOS[-1]
    ano_default = ano_max

    def bloco_ncm_checkboxes(cat_nome, ncm_list):
        cor = CATEGORIA_COR_BASE[cat_nome]
        items = "".join(
            f'<label class="chk"><input type="checkbox" class="ncm-check" value="{LABELS[n]}" checked> '
            f'{LABELS[n]} <span class="unid-tag">{NCM_UNIDADE.get(LABELS[n], "")}</span>'
            + (
                f' <span class="aviso-tag" title="{AVISOS_QUALIDADE[n]}">⚠ 2011–12</span>'
                if n in AVISOS_QUALIDADE
                else ""
            )
            + "</label>"
            for n in ncm_list
        )
        return f'<div class="ncm-group"><div class="ncm-group-title" style="color:{cor}">{cat_nome}</div>{items}</div>'

    ncm_checkboxes_html = "".join(
        bloco_ncm_checkboxes(cat, lst) for cat, lst in CATEGORIAS.items()
    )

    viz_checkboxes = "".join(
        f'<label class="chk"><input type="checkbox" class="viz-check" value="{key}" checked> {label}</label>'
        for key, label in [
            ("evolucao", "Evolução Mensal"),
            ("saldo", "Saldo Comercial"),
            ("composicao", "Composição (Exp/Imp)"),
            ("heatmap", "Heatmap"),
            ("donut", "Participação (Donut)"),
            ("preco", "Preço Médio"),
        ]
    )

    meses_checkboxes = "".join(
        f'<label class="chk chk-mes"><input type="checkbox" class="mes-check" value="{m}" checked> {MES_ABREV[m]}</label>'
        for m in MESES
    )

    ano_options = "".join(f'<option value="{a}">{a}</option>' for a in ANOS)
    mes_options = "".join(f'<option value="{m}">{MES_ABREV[m]}</option>' for m in MESES)

    avisos_itens = "".join(
        f"<li><b>{LABELS[n]}</b> ({n}): {texto}</li>"
        for n, texto in AVISOS_QUALIDADE.items()
    )
    aviso_banner_html = (
        f"""<div class="aviso-banner">
      <div class="icone">⚠️</div>
      <div class="texto">
        <b>Aviso de qualidade de dados</b> — descontinuidades conhecidas na série, mantidas sem alteração:
        <ul>{avisos_itens}</ul>
      </div>
    </div>"""
        if AVISOS_QUALIDADE
        else ""
    )

    nivel_select = """
        <option value="Categoria">Categoria (agrupado)</option>
        <option value="NCM">NCM (detalhado)</option>
    """
    fluxo_select = """
        <option value="Exportação">Exportação</option>
        <option value="Importação">Importação</option>
    """
    metrica_select = """
        <option value="fob">FOB (US$)</option>
        <option value="qtd">Quantidade</option>
    """
    granularidade_select = """
        <option value="anual">Anual</option>
        <option value="mensal">Mensal</option>
    """

    page = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Comércio Exterior — Armas de Fogo</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{BG};color:{TEXTO};font-family:'Inter','Segoe UI',Arial,sans-serif;line-height:1.5}}
header{{background:{BG2};border-bottom:1px solid {BORDA};padding:22px 40px}}
header h1{{font-size:1.4rem;font-weight:700}}
header p{{color:{TEXTO2};font-size:.82rem;margin-top:5px}}
header details{{margin-top:8px}}
header summary{{cursor:pointer;color:{TEXTO2};font-size:.76rem}}
header details pre{{color:{TEXTO2};font-size:.72rem;margin-top:8px;white-space:pre-wrap;font-family:inherit}}
main{{max-width:1240px;margin:0 auto;padding:20px 24px;display:flex;flex-direction:column;gap:20px}}
.card{{background:{BG2};border:1px solid {BORDA};border-radius:12px;padding:20px 16px}}
.card-head{{display:flex;align-items:center;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-bottom:2px}}
.card-head h2{{font-size:.85rem;font-weight:600;color:{TEXTO};text-transform:uppercase;letter-spacing:.5px}}
.card-head select{{min-width:170px}}
.card-subtitle{{color:{TEXTO2};font-size:.74rem;margin-bottom:12px}}
footer{{text-align:center;padding:20px;color:{TEXTO2};font-size:.78rem;border-top:1px solid {BORDA};margin-top:8px}}

.controls{{display:grid;grid-template-columns:1fr 1.6fr;gap:20px;align-items:start}}
.controls-row2{{display:grid;grid-template-columns:2fr 1fr;gap:20px;align-items:start;margin-top:18px}}
.control-group label.title{{display:block;color:{TEXTO2};font-size:.72rem;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}}
.chk{{display:flex;align-items:center;gap:6px;font-size:.78rem;cursor:pointer;color:{TEXTO};margin-bottom:4px}}
.chk input{{accent-color:#3B82F6;cursor:pointer}}
.unid-tag{{color:{TEXTO2};font-size:.68rem;border:1px solid {BORDA};border-radius:4px;padding:0 4px}}
.aviso-tag{{color:#F59E0B;font-size:.68rem;border:1px solid #F59E0B;border-radius:4px;padding:0 4px;cursor:help}}
.aviso-banner{{background:rgba(245,158,11,0.08);border:1px solid #F59E0B;border-radius:12px;padding:14px 16px;display:flex;gap:10px;align-items:flex-start}}
.aviso-banner .icone{{font-size:1.1rem;line-height:1}}
.aviso-banner .texto{{font-size:.8rem;color:{TEXTO}}}
.aviso-banner .texto b{{color:#F59E0B}}
.aviso-banner ul{{margin:6px 0 0 18px}}

.ncm-groups{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}}
.ncm-group-title{{font-size:.76rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px}}

.meses-row{{display:flex;flex-wrap:wrap;gap:10px;align-items:center}}
.chk-mes{{background:{BG3};border:1px solid {BORDA};border-radius:6px;padding:4px 8px;margin-bottom:0}}
.mini-btn{{background:{BG3};color:{TEXTO2};border:1px solid {BORDA};border-radius:6px;padding:4px 10px;font-size:.72rem;cursor:pointer}}
.mini-btn:hover{{color:{TEXTO}}}

select{{background:{BG3};color:{TEXTO};border:1px solid {BORDA};border-radius:8px;padding:7px 10px;font-size:.85rem;font-family:inherit;cursor:pointer}}
select:focus{{outline:1px solid #3B82F6}}

.range-wrap{{position:relative;height:36px;margin-top:6px}}
.range-track-rail{{position:absolute;top:16px;left:0;right:0;height:4px;background:{BORDA};border-radius:2px;pointer-events:none}}
.range-track-fill{{position:absolute;top:16px;height:4px;background:#3B82F6;border-radius:2px;pointer-events:none}}
.range-wrap input[type=range]{{position:absolute;top:12px;left:0;width:100%;margin:0;-webkit-appearance:none;appearance:none;background:transparent;pointer-events:none}}
.range-wrap input[type=range]::-webkit-slider-thumb{{-webkit-appearance:none;appearance:none;pointer-events:auto;width:16px;height:16px;border-radius:50%;background:{BG2};border:3px solid #3B82F6;cursor:pointer;margin-top:-6px;position:relative;z-index:2}}
.range-wrap input[type=range]::-moz-range-thumb{{pointer-events:auto;width:16px;height:16px;border-radius:50%;background:{BG2};border:3px solid #3B82F6;cursor:pointer;z-index:2}}
.range-wrap input[type=range]::-webkit-slider-runnable-track{{height:4px;background:transparent;border-radius:2px}}
.range-wrap input[type=range]::-moz-range-track{{height:4px;background:transparent;border-radius:2px}}
#ano-range-label{{color:{TEXTO};font-size:.85rem;font-weight:600}}

.inline-controls{{display:flex;gap:12px;margin-bottom:10px;flex-wrap:wrap;align-items:end}}
.inline-controls .field label{{display:block;color:{TEXTO2};font-size:.72rem;text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}}

.sub-chart + .sub-chart{{margin-top:14px;padding-top:14px;border-top:1px solid {BORDA}}}
.sub-chart-label{{color:{TEXTO2};font-size:.74rem;font-weight:600;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px}}
</style>
</head>
<body>

<header>
  <h1>Comércio Exterior de Armas de Fogo — Brasil ({ano_min}–{ano_max})</h1>
  <p>{header_html}</p>
  <details>
    <summary>Ver descrição completa dos {len(LABELS)} NCMs</summary>
    <pre>{detalhe_html}</pre>
  </details>
</header>

<main>

  {aviso_banner_html}

  <div class="card">
    <div class="controls">
      <div class="control-group">
        <label class="title">Visualizações ativas</label>
        {viz_checkboxes}
      </div>
      <div class="control-group">
        <label class="title">Categorias / NCM</label>
        <div class="ncm-groups">{ncm_checkboxes_html}</div>
      </div>
    </div>
    <div class="controls-row2">
      <div class="control-group">
        <label class="title">Meses</label>
        <div class="meses-row">
          {meses_checkboxes}
          <button type="button" class="mini-btn" id="meses-todos">Todos</button>
          <button type="button" class="mini-btn" id="meses-nenhum">Nenhum</button>
        </div>
      </div>
      <div class="control-group">
        <label class="title">Intervalo de anos: <span id="ano-range-label"></span></label>
        <div class="range-wrap">
          <div class="range-track-rail"></div>
          <div class="range-track-fill" id="ano-track-fill"></div>
          <input type="range" id="ano-min" min="{ano_min}" max="{ano_max}" step="1" value="{ano_min}">
          <input type="range" id="ano-max" min="{ano_min}" max="{ano_max}" step="1" value="{ano_max}">
        </div>
      </div>
    </div>
  </div>

  <div class="card" id="section-evolucao">
    <div class="card-head">
      <h2>📈 Evolução Mensal</h2>
      <select id="evolucao-metrica">{metrica_select}</select>
    </div>
    <div class="card-subtitle" id="evolucao-subtitle"></div>
    <div id="graph-evolucao-container"></div>
  </div>

  <div class="card" id="section-saldo">
    <div class="card-head">
      <h2>⚖️ Saldo Comercial</h2>
      <select id="saldo-metrica">{metrica_select}</select>
    </div>
    <div class="card-subtitle" id="saldo-subtitle"></div>
    <div class="inline-controls">
      <div class="field"><label>Nível</label>
        <select id="saldo-nivel">{nivel_select}</select>
      </div>
      <div class="field"><label>Granularidade</label>
        <select id="saldo-granularidade">{granularidade_select}</select>
      </div>
    </div>
    <div id="graph-saldo-container"></div>
  </div>

  <div class="card" id="section-composicao">
    <div class="card-head">
      <h2>📦 Composição por Fluxo</h2>
      <select id="comp-metrica">{metrica_select}</select>
    </div>
    <div class="card-subtitle" id="composicao-subtitle"></div>
    <div class="inline-controls">
      <div class="field"><label>Fluxo</label>
        <select id="comp-fluxo">{fluxo_select}</select>
      </div>
      <div class="field"><label>Nível</label>
        <select id="comp-nivel">{nivel_select}</select>
      </div>
      <div class="field"><label>Granularidade</label>
        <select id="comp-granularidade">{granularidade_select}</select>
      </div>
    </div>
    <div id="graph-composicao-container"></div>
  </div>

  <div class="card" id="section-heatmap">
    <div class="card-head">
      <h2>🌡️ Heatmap de Intensidade</h2>
      <select id="hm-metrica">{metrica_select}</select>
    </div>
    <div class="card-subtitle" id="heatmap-subtitle"></div>
    <div class="inline-controls">
      <div class="field"><label>Fluxo</label>
        <select id="hm-fluxo">{fluxo_select}</select>
      </div>
      <div class="field" id="hm-nivel-wrap"><label>Nível</label>
        <select id="hm-nivel">
          <option value="NCM">NCM (detalhado)</option>
          <option value="Categoria">Categoria (agrupado)</option>
        </select>
      </div>
      <div class="field"><label>Eixo</label>
        <select id="hm-eixo">
          <option value="itens">Categoria/NCM × Período</option>
          <option value="mes">Sazonalidade (Mês × Ano)</option>
        </select>
      </div>
      <div class="field" id="hm-granularidade-wrap"><label>Granularidade</label>
        <select id="hm-granularidade">{granularidade_select}</select>
      </div>
    </div>
    <div id="graph-heatmap-container"></div>
  </div>

  <div class="card" id="section-donut">
    <div class="card-head">
      <h2>🥧 Participação por Período</h2>
      <select id="donut-metrica">{metrica_select}</select>
    </div>
    <div class="card-subtitle" id="donut-subtitle"></div>
    <div class="inline-controls">
      <div class="field"><label>Fluxo</label>
        <select id="donut-fluxo">{fluxo_select}</select>
      </div>
      <div class="field"><label>Nível</label>
        <select id="donut-nivel">{nivel_select}</select>
      </div>
      <div class="field"><label>Ano</label>
        <select id="donut-ano">{ano_options}</select>
      </div>
      <div class="field"><label>Mês</label>
        <select id="donut-mes">
          <option value="todos">Ano completo</option>
          {mes_options}
        </select>
      </div>
    </div>
    <div id="graph-donut-container"></div>
  </div>

  <div class="card" id="section-preco">
    <div class="card-head">
      <h2>💲 Preço Médio (FOB / Quantidade)</h2>
    </div>
    <div class="card-subtitle" id="preco-subtitle"></div>
    <div class="inline-controls">
      <div class="field"><label>Fluxo</label>
        <select id="preco-fluxo">{fluxo_select}</select>
      </div>
      <div class="field"><label>Nível</label>
        <select id="preco-nivel">{nivel_select}</select>
      </div>
      <div class="field"><label>Unidade</label>
        <select id="preco-unidade">
          <option value="Unidades">US$ / unidade (armas)</option>
          <option value="kg">US$ / kg (munição e partes)</option>
        </select>
      </div>
    </div>
    <div id="graph-preco-container"></div>
  </div>

</main>

<footer>Grupo de Pesquisa · dados_small_arms.xlsx</footer>

<script>
{js}
</script>
<script>
  document.getElementById("donut-ano").value = "{ano_default}";
</script>
</body>
</html>"""

    with open("docs/comex_antigo.html", "w", encoding="utf-8") as f:
        f.write(page)
    print(
        f"docs/comex_antigo.html gerado — {len(LABELS)} NCMs, dados mensais {ano_min}–{ano_max}"
    )
    return os.path.abspath("docs/comex_antigo.html")


if __name__ == "__main__":
    caminho = gerar_html()
    if "--export" not in sys.argv:
        webbrowser.open(f"file://{caminho}")
