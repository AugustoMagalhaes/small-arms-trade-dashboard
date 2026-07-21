import colorsys
import json
import os
import sys

import pandas as pd
import plotly.graph_objects as go

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
        out.append(
            "#{:02X}{:02X}{:02X}".format(
                round(rr * 255), round(gg * 255), round(bb * 255)
            )
        )
    return out


NCMS: list[str] = []
CORES_CAT: dict[str, str] = {}
for _cat, _ncm_list in CATEGORIAS.items():
    _shades = gerar_shades(CATEGORIA_COR_BASE[_cat], len(_ncm_list))
    for _ncm, _cor in zip(_ncm_list, _shades):
        _label = LABELS[_ncm]
        NCMS.append(_label)
        CORES_CAT[_label] = _cor


def get_dim_info(nivel: str):
    if nivel == "Categoria":
        return "Categoria", CATEGORIAS_LIST, CATEGORIA_COR_BASE
    return "Label", NCMS, CORES_CAT


def carregar_dados():
    df_raw = pd.read_excel(ARQUIVO, sheet_name="Resultado")
    registros = []
    descricoes = {}
    for _, row in df_raw.iterrows():
        ncm = int(row["Código NCM"])
        label = LABELS.get(ncm, str(ncm))
        categoria = NCM_TO_CATEGORIA.get(ncm, "Outros")
        descricoes[ncm] = str(row.get("Descrição NCM", "")).strip()
        for col in df_raw.columns:
            if col.startswith("Exportação") or col.startswith("Importação"):
                p = col.split(" - ")
                registros.append(
                    {
                        "NCM": ncm,
                        "Label": label,
                        "Categoria": categoria,
                        "Fluxo": p[0],
                        "Ano": int(p[1]),
                        "Valor": float(row[col]) if pd.notna(row[col]) else 0.0,
                    }
                )
    return pd.DataFrame(registros), descricoes


df, NCM_DESCRICOES_OFICIAIS = carregar_dados()
ANOS = sorted(df["Ano"].unique())

HEADER_FONTE_TEXTO = "Fonte: Comex Stat / MDIC · USD FOB · {} NCMs · {}–{}".format(
    len(LABELS), int(ANOS[0]), int(ANOS[-1])
)

_desc_ordenadas = []
for _cat, _ncm_list in CATEGORIAS.items():
    for _ncm in _ncm_list:
        _desc_ordenadas.append(
            f"{_ncm} — {LABELS[_ncm]}: {NCM_DESCRICOES_OFICIAIS.get(_ncm, '')}"
        )
HEADER_DETALHE_TEXTO = "\n".join(_desc_ordenadas)

BG = "#0D1117"
BG2 = "#161B22"
BG3 = "#1C2128"
BORDA = "#30363D"
TEXTO = "#E6EDF3"
TEXTO2 = "#8B949E"


def fmt_usd(v):
    if v >= 1e6:
        return f"US$ {v / 1e6:.1f}M"
    if v >= 1e3:
        return f"US$ {v / 1e3:.0f}K"
    return f"US$ {v:,.0f}"


def layout_base():
    return dict(
        paper_bgcolor=BG,
        plot_bgcolor=BG2,
        font=dict(family="Inter, Segoe UI, Arial", color=TEXTO, size=13),
        margin=dict(t=70, b=60, l=105, r=30),
        xaxis=dict(
            gridcolor=BORDA,
            zerolinecolor=BORDA,
            tickfont=dict(color=TEXTO2),
            title_font=dict(color=TEXTO2),
        ),
        yaxis=dict(
            gridcolor=BORDA,
            zerolinecolor=BORDA,
            tickfont=dict(color=TEXTO2),
            title_font=dict(color=TEXTO2),
        ),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            bordercolor=BORDA,
            borderwidth=1,
            font=dict(color=TEXTO, size=11),
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
        ),
        hoverlabel=dict(bgcolor=BG3, bordercolor=BORDA, font=dict(color=TEXTO)),
    )


def fig_vazio(msg="Sem dados para o fluxo/período selecionado"):
    fig = go.Figure()
    fig.add_annotation(
        text=f"<b>⚠  {msg}</b>",
        x=0.5,
        y=0.5,
        xref="paper",
        yref="paper",
        showarrow=False,
        font=dict(size=15, color=TEXTO2),
    )
    l = layout_base()
    l["xaxis"]["visible"] = False
    l["yaxis"]["visible"] = False
    fig.update_layout(**l, height=200)
    return fig


def fig_evolucao(ncms_sel=None, anos_sel=None):
    d = df.copy()
    if ncms_sel is not None:
        d = d[d["Label"].isin(ncms_sel)]
    if anos_sel:
        d = d[d["Ano"].between(anos_sel[0], anos_sel[1])]
    if d.empty or d["Valor"].sum() == 0:
        return fig_vazio("Nenhuma categoria selecionada ou sem dados no período")
    tot = d.groupby(["Ano", "Fluxo"])["Valor"].sum().reset_index()
    fig = go.Figure()
    for fluxo, cor, rgba in [
        ("Exportação", "#3B82F6", "rgba(59,130,246,0.12)"),
        ("Importação", "#EF4444", "rgba(239,68,68,0.12)"),
    ]:
        s = tot[tot["Fluxo"] == fluxo]
        if s.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=s["Ano"],
                y=s["Valor"],
                name=fluxo,
                mode="lines+markers",
                line=dict(color=cor, width=3),
                marker=dict(size=8, color=cor, line=dict(color=BG, width=2)),
                fill="tozeroy",
                fillcolor=rgba,
                hovertemplate=f"<b>%{{x}}</b><br>{fluxo}: %{{customdata}}<extra></extra>",
                customdata=[fmt_usd(v) for v in s["Valor"]],
            )
        )
    lb = layout_base()
    lb["xaxis"] = dict(
        title="Ano",
        gridcolor=BORDA,
        zerolinecolor=BORDA,
        tickfont=dict(color=TEXTO2),
        title_font=dict(color=TEXTO2),
        dtick=1,
        tickmode="linear",
        tickangle=-45,
    )
    fig.update_layout(
        **lb,
        title=dict(
            text="Evolução Total — Exportação vs Importação (USD FOB)",
            font=dict(size=15),
        ),
        yaxis_title="USD FOB",
        yaxis_tickformat="$,.0f",
    )
    return fig


def fig_saldo(ncms_sel=None, anos_sel=None, nivel="Categoria"):
    d = df.copy()
    if ncms_sel is not None:
        d = d[d["Label"].isin(ncms_sel)]
    if anos_sel:
        d = d[d["Ano"].between(anos_sel[0], anos_sel[1])]
    if d.empty:
        return fig_vazio("Nenhuma categoria selecionada ou sem dados no período")
    col, order, colors = get_dim_info(nivel)
    pivot = (
        d.pivot_table(
            index=[col, "Ano"], columns="Fluxo", values="Valor", aggfunc="sum"
        )
        .fillna(0)
        .reset_index()
    )
    pivot["Saldo"] = pivot.get("Exportação", 0) - pivot.get("Importação", 0)
    fig = go.Figure()
    for item in order:
        sub = pivot[pivot[col] == item].sort_values("Ano")
        if sub.empty or sub["Saldo"].abs().sum() == 0:
            continue
        fig.add_trace(
            go.Bar(
                x=sub["Ano"],
                y=sub["Saldo"],
                name=item,
                marker=dict(color=colors[item], opacity=0.9),
                hovertemplate=f"<b>{item}</b><br>Ano: %{{x}}<br>Saldo: %{{customdata}}<extra></extra>",
                customdata=[fmt_usd(v) for v in sub["Saldo"]],
            )
        )
    if not fig.data:
        return fig_vazio("Nenhuma categoria selecionada ou sem dados no período")
    fig.add_hline(y=0, line_dash="dot", line_color=TEXTO2, opacity=0.6)
    fig.update_layout(
        **layout_base(),
        title=dict(
            text="Saldo Comercial por Categoria (Exportação − Importação)"
            if nivel == "Categoria"
            else "Saldo Comercial por NCM (Exportação − Importação)",
            font=dict(size=15),
        ),
        barmode="group",
        xaxis_title="Ano",
        yaxis_title="Saldo (USD FOB)",
        yaxis_tickformat="$,.0f",
    )
    fig.update_xaxes(dtick=1, tickangle=-45)
    return fig


def fig_composicao(fluxo="Exportação", ncms_sel=None, anos_sel=None, nivel="Categoria"):
    d = df[df["Fluxo"] == fluxo].copy()
    if ncms_sel is not None:
        d = d[d["Label"].isin(ncms_sel)]
    if anos_sel:
        d = d[d["Ano"].between(anos_sel[0], anos_sel[1])]
    if d.empty or d["Valor"].sum() == 0:
        return fig_vazio(f"Nenhum dado de {fluxo} para os filtros selecionados")
    col, order, colors = get_dim_info(nivel)
    fig = go.Figure()
    for item in order:
        s = (
            d[d[col] == item]
            .groupby("Ano", as_index=False)["Valor"]
            .sum()
            .sort_values("Ano")
        )
        if s.empty:
            continue
        valores = [v if v > 0 else None for v in s["Valor"]]
        custom = [fmt_usd(v) if v else "Sem dados" for v in s["Valor"]]
        if all(v is None for v in valores):
            continue
        fig.add_trace(
            go.Bar(
                x=s["Ano"],
                y=valores,
                name=item,
                marker_color=colors[item],
                hovertemplate=f"<b>{item}</b><br>%{{x}}: %{{customdata}}<extra></extra>",
                customdata=custom,
            )
        )
    if not fig.data:
        return fig_vazio(f"Nenhum dado de {fluxo} para os filtros selecionados")
    titulo_nivel = "Categoria" if nivel == "Categoria" else "NCM"
    fig.update_layout(
        **layout_base(),
        title=dict(
            text=f"Composição das {fluxo}s por {titulo_nivel}", font=dict(size=15)
        ),
        barmode="stack",
        xaxis_title="Ano",
        yaxis_title=f"{fluxo} (USD FOB)",
        yaxis_tickformat="$,.0f",
    )
    fig.update_xaxes(dtick=1, tickangle=-45)
    return fig


def fig_heatmap(fluxo="Exportação", ncms_sel=None, nivel="NCM"):
    d = df[df["Fluxo"] == fluxo].copy()
    if ncms_sel is not None:
        d = d[d["Label"].isin(ncms_sel)]
    if d.empty or d["Valor"].sum() == 0:
        return fig_vazio(f"Nenhum dado de {fluxo} para exibir no heatmap")
    col, order, colors = get_dim_info(nivel)
    pivot = d.pivot_table(index=col, columns="Ano", values="Valor", aggfunc="sum")
    pivot = pivot.reindex(order).reindex(columns=ANOS).fillna(0)
    z_vals = [[v if v > 0 else None for v in row] for row in pivot.values]
    text = [[fmt_usd(v) if v else "—" for v in row] for row in pivot.values]
    fig = go.Figure(
        data=go.Heatmap(
            z=z_vals,
            x=[str(int(a)) for a in pivot.columns],
            y=pivot.index,
            colorscale=[
                [0.0, "#1C2128"],
                [0.15, "#1D4ED8"],
                [0.4, "#0EA5E9"],
                [0.65, "#22C55E"],
                [0.85, "#F59E0B"],
                [1.0, "#EF4444"],
            ],
            text=text,
            texttemplate="%{text}",
            textfont=dict(size=9, color=TEXTO),
            hoverongaps=False,
            hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
            colorbar=dict(
                title=dict(text="USD FOB", font=dict(color=TEXTO2)),
                tickfont=dict(color=TEXTO2),
                bgcolor=BG2,
                bordercolor=BORDA,
                outlinecolor=BORDA,
            ),
            zmin=0,
        )
    )
    hml = layout_base()
    hml["xaxis"] = dict(
        title="Ano",
        gridcolor=BORDA,
        tickfont=dict(color=TEXTO2),
        dtick=1,
        tickangle=-45,
    )
    hml["yaxis"] = dict(gridcolor=BORDA, tickfont=dict(color=TEXTO, size=10))
    hml["margin"] = dict(t=70, b=60, l=230 if nivel == "NCM" else 150, r=30)
    titulo_nivel = "Categoria" if nivel == "Categoria" else "NCM"
    fig.update_layout(
        **hml,
        title=dict(
            text=f"Heatmap — Intensidade de {fluxo}s por {titulo_nivel} e Ano",
            font=dict(size=15),
        ),
        height=110 + 32 * len(order),
    )
    return fig


def fig_donut(fluxo="Exportação", ano=2025, ncms_sel=None, nivel="Categoria"):
    d = df[(df["Ano"] == ano) & (df["Fluxo"] == fluxo)].copy()
    if ncms_sel is not None:
        d = d[d["Label"].isin(ncms_sel)]
    if d.empty:
        return fig_vazio(f"Nenhum dado de {fluxo} em {ano}")
    col, order, colors = get_dim_info(nivel)
    agg = d.groupby(col, as_index=False)["Valor"].sum()
    agg = agg[agg["Valor"] > 0]
    if agg.empty:
        return fig_vazio(f"Nenhum dado de {fluxo} em {ano}")
    cores = [colors[v] for v in agg[col]]
    fig = go.Figure(
        data=go.Pie(
            labels=agg[col],
            values=agg["Valor"],
            hole=0.48,
            marker=dict(colors=cores, line=dict(color=BG, width=2)),
            textinfo="percent",
            textfont=dict(color=TEXTO, size=11),
            hovertemplate="<b>%{label}</b><br>%{customdata}<br>%{percent}<extra></extra>",
            customdata=[fmt_usd(v) for v in agg["Valor"]],
        )
    )
    pl = layout_base()
    pl.pop("legend", None)
    titulo_nivel = "Categoria" if nivel == "Categoria" else "NCM"
    fig.update_layout(
        **pl,
        title=dict(
            text=f"Participação nas {fluxo}s por {titulo_nivel} — {ano}",
            font=dict(size=15),
        ),
        showlegend=True,
        legend=dict(orientation="v", x=1.02, y=0.5, font=dict(color=TEXTO, size=10)),
        height=440,
    )
    return fig


def rodar_dash():
    import dash
    from dash import Input, Output, callback, dcc, html

    app = dash.Dash(
        __name__,
        title="Armas de Fogo — Comex Stat",
        suppress_callback_exceptions=True,
    )

    DARK_CSS = f"""
.dash-dropdown-wrapper {{ background: {BG3} !important; border: 1px solid {BORDA} !important; border-radius: 8px !important; }}
.dash-dropdown-trigger {{ background: {BG3} !important; color: {TEXTO} !important; border-radius: 8px !important; padding: 6px 10px !important; }}
.dash-dropdown-placeholder {{ color: {TEXTO2} !important; }}
.dash-dropdown-value {{ color: {TEXTO} !important; }}
.dash-dropdown-value-item {{ background: {BG2} !important; border: 1px solid {BORDA} !important; border-radius: 4px !important; color: {TEXTO} !important; font-size: 12px !important; }}
.dash-dropdown-value-count {{ background: {BG2} !important; color: {TEXTO2} !important; border: 1px solid {BORDA} !important; border-radius: 4px !important; padding: 1px 7px !important; font-size: 12px !important; }}
.dash-dropdown-trigger-icon svg, .dash-dropdown-trigger-icon svg path, .dash-dropdown-trigger-icon svg polyline {{ stroke: {TEXTO2} !important; fill: none !important; }}
.dash-dropdown-clear {{ color: {TEXTO2} !important; }}
.dash-dropdown-content {{ background: {BG3} !important; border: 1px solid {BORDA} !important; border-radius: 8px !important; box-shadow: 0 8px 32px rgba(0,0,0,0.7) !important; z-index: 9999 !important; }}
.dash-dropdown-option {{ background: {BG3} !important; color: {TEXTO} !important; padding: 8px 12px !important; }}
.dash-dropdown-option:hover, .dash-dropdown-option[aria-selected="true"], .dash-dropdown-option[data-focused="true"] {{ background: {BG2} !important; color: {TEXTO} !important; }}
.dash-dropdown-search-container {{ background: {BG3} !important; border-bottom: 1px solid {BORDA} !important; }}
.dash-dropdown-search input {{ background: transparent !important; color: {TEXTO} !important; border: none !important; outline: none !important; }}
.dash-dropdown-search input::placeholder {{ color: {TEXTO2} !important; }}
.dash-dropdown-grid-container {{ background: {BG3} !important; }}
.dash-dropdown-actions {{ background: {BG3} !important; border-top: 1px solid {BORDA} !important; }}
.dash-dropdown-action-button {{ color: {TEXTO2} !important; }}
.dash-dropdown-action-button:hover {{ color: {TEXTO} !important; }}
body, #react-entry-point, ._dash-loading {{ background-color: {BG} !important; }}
.rc-slider-track {{ background-color: #3B82F6 !important; }}
.rc-slider-handle {{ border-color: #3B82F6 !important; background: {BG2} !important; }}
.rc-slider-rail {{ background-color: {BORDA} !important; }}
.dash-slider-tooltip, [class*="dash-slider-tooltip"] {{ --Dash-Tooltip-Background-Color: {BG2} !important; --Dash-Tooltip-Border-Color: {BORDA} !important; background: {BG2} !important; color: {TEXTO} !important; border: 1px solid {BORDA} !important; }}
.dash-tooltip {{ background: {BG2} !important; color: {TEXTO} !important; border: 1px solid {BORDA} !important; }}
.dash-tooltip::before, .dash-tooltip::after {{ border-top-color: {BG2} !important; }}
/* checklist de categorias */
.cat-checklist label {{ display:flex; align-items:center; gap:6px; margin-bottom:4px; font-size:0.8rem; color:{TEXTO}; cursor:pointer; }}
.cat-checklist input[type=checkbox] {{ accent-color:#3B82F6; cursor:pointer; }}
details.ncm-details summary {{ cursor:pointer; color:{TEXTO2}; font-size:0.78rem; margin-bottom:8px; }}
"""

    app.index_string = f"""<!DOCTYPE html>
<html>
<head>
    {{%metas%}}
    <title>{{%title%}}</title>
    {{%favicon%}}
    {{%css%}}
    <style>{DARK_CSS}</style>
</head>
<body style="background:{BG};margin:0">
    {{%app_entry%}}
    <footer>{{%config%}}{{%scripts%}}{{%renderer%}}</footer>
</body>
</html>"""

    dd_style = {"borderRadius": "8px"}

    def card(children):
        return html.Div(
            style={
                "background": BG2,
                "border": f"1px solid {BORDA}",
                "borderRadius": "12px",
                "padding": "20px 16px",
            },
            children=children,
        )

    def lbl(txt):
        return html.Label(
            txt,
            style={
                "color": TEXTO2,
                "fontSize": "0.75rem",
                "marginBottom": "6px",
                "display": "block",
                "textTransform": "uppercase",
                "letterSpacing": "0.5px",
            },
        )

    ano_mais_recente = int(ANOS[-1])
    ano_opts = [{"label": str(int(a)), "value": int(a)} for a in ANOS]
    fluxo_opts = [
        {"label": "Exportação", "value": "Exportação"},
        {"label": "Importação", "value": "Importação"},
    ]
    nivel_opts = [
        {"label": "Categoria (agrupado)", "value": "Categoria"},
        {"label": "NCM (detalhado)", "value": "NCM"},
    ]
    graf_opts = [
        {"label": "📈 Evolução Total", "value": "evolucao"},
        {"label": "⚖️ Saldo Comercial", "value": "saldo"},
        {"label": "📦 Composição (Exp/Imp)", "value": "composicao"},
        {"label": "🌡️ Heatmap", "value": "heatmap"},
        {"label": "🥧 Participação (Donut)", "value": "donut"},
    ]

    def checklist_categoria(cat_key, cat_nome, ncm_list):
        opts = [{"label": LABELS[n], "value": LABELS[n]} for n in ncm_list]
        return html.Div(
            style={"marginBottom": "10px"},
            children=[
                html.Div(
                    cat_nome,
                    style={
                        "color": CATEGORIA_COR_BASE[cat_nome],
                        "fontSize": "0.78rem",
                        "fontWeight": "700",
                        "marginBottom": "4px",
                        "textTransform": "uppercase",
                        "letterSpacing": "0.4px",
                    },
                ),
                dcc.Checklist(
                    id=f"ncm-{cat_key}",
                    options=opts,
                    value=[o["value"] for o in opts],
                    className="cat-checklist",
                ),
            ],
        )

    app.layout = html.Div(
        style={
            "background": BG,
            "minHeight": "100vh",
            "fontFamily": "Inter, Segoe UI, Arial",
            "color": TEXTO,
        },
        children=[
            html.Div(
                style={
                    "background": BG2,
                    "borderBottom": f"1px solid {BORDA}",
                    "padding": "22px 40px",
                },
                children=[
                    html.H1(
                        "Comércio Exterior de Armas de Fogo — Brasil (2011–2026)",
                        style={
                            "fontSize": "1.4rem",
                            "fontWeight": "700",
                            "color": TEXTO,
                        },
                    ),
                    html.P(
                        HEADER_FONTE_TEXTO,
                        style={
                            "color": TEXTO2,
                            "fontSize": "0.82rem",
                            "marginTop": "5px",
                        },
                    ),
                    html.Details(
                        className="ncm-details",
                        style={"marginTop": "8px"},
                        children=[
                            html.Summary(
                                f"Ver descrição completa dos {len(LABELS)} NCMs"
                            ),
                            html.Pre(
                                HEADER_DETALHE_TEXTO,
                                style={
                                    "color": TEXTO2,
                                    "fontSize": "0.74rem",
                                    "whiteSpace": "pre-wrap",
                                    "fontFamily": "inherit",
                                    "margin": 0,
                                },
                            ),
                        ],
                    ),
                ],
            ),
            html.Div(
                style={
                    "maxWidth": "1200px",
                    "margin": "0 auto",
                    "padding": "20px 24px 0",
                },
                children=[
                    card(
                        [
                            html.Div(
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "1.3fr 2fr 1.2fr",
                                    "gap": "20px",
                                    "alignItems": "start",
                                },
                                children=[
                                    html.Div(
                                        [
                                            lbl("Visualizações ativas"),
                                            dcc.Dropdown(
                                                id="sel-graficos",
                                                options=graf_opts,
                                                value=[
                                                    "evolucao",
                                                    "saldo",
                                                    "composicao",
                                                    "heatmap",
                                                    "donut",
                                                ],
                                                multi=True,
                                                clearable=False,
                                                style=dd_style,
                                            ),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            lbl("Categorias / NCM"),
                                            html.Div(
                                                style={
                                                    "display": "grid",
                                                    "gridTemplateColumns": "1fr 1fr 1fr",
                                                    "gap": "14px",
                                                },
                                                children=[
                                                    checklist_categoria(
                                                        "armas",
                                                        "Armas de Fogo",
                                                        CATEGORIAS["Armas de Fogo"],
                                                    ),
                                                    checklist_categoria(
                                                        "municao",
                                                        "Munição e Cartuchos",
                                                        CATEGORIAS[
                                                            "Munição e Cartuchos"
                                                        ],
                                                    ),
                                                    checklist_categoria(
                                                        "partes",
                                                        "Partes e Acessórios",
                                                        CATEGORIAS[
                                                            "Partes e Acessórios"
                                                        ],
                                                    ),
                                                ],
                                            ),
                                        ]
                                    ),
                                    html.Div(
                                        [
                                            lbl(
                                                f"Intervalo de anos ({int(ANOS[0])}–{int(ANOS[-1])})"
                                            ),
                                            dcc.RangeSlider(
                                                id="sel-anos",
                                                min=int(ANOS[0]),
                                                max=int(ANOS[-1]),
                                                step=1,
                                                value=[int(ANOS[0]), int(ANOS[-1])],
                                                marks={
                                                    int(a): {
                                                        "label": str(int(a))[2:],
                                                        "style": {
                                                            "color": TEXTO2,
                                                            "fontSize": "10px",
                                                        },
                                                    }
                                                    for a in ANOS
                                                    if int(a) % 2 == 1
                                                },
                                                tooltip={
                                                    "placement": "bottom",
                                                    "always_visible": True,
                                                },
                                            ),
                                        ]
                                    ),
                                ],
                            ),
                        ]
                    ),
                ],
            ),
            dcc.Store(id="ncm-store"),
            html.Div(
                id="graficos-container",
                style={
                    "maxWidth": "1200px",
                    "margin": "0 auto",
                    "padding": "20px 24px",
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "20px",
                },
            ),
            html.Footer(
                "Grupo de Pesquisa · dados_small_arms.xlsx",
                style={
                    "textAlign": "center",
                    "color": TEXTO2,
                    "fontSize": "0.78rem",
                    "padding": "20px",
                    "borderTop": f"1px solid {BORDA}",
                },
            ),
        ],
    )

    @callback(
        Output("ncm-store", "data"),
        Input("ncm-armas", "value"),
        Input("ncm-municao", "value"),
        Input("ncm-partes", "value"),
    )
    def combinar_ncm(a, m, p):
        return (a or []) + (m or []) + (p or [])

    def bloco_nivel(id_nivel, default="Categoria"):
        return html.Div(
            [
                lbl("Nível"),
                dcc.Dropdown(
                    id=id_nivel,
                    options=nivel_opts,
                    value=default,
                    clearable=False,
                    style={**dd_style, "width": "190px"},
                ),
            ]
        )

    def bloco_fluxo(id_fluxo, default="Exportação"):
        return html.Div(
            [
                lbl("Fluxo"),
                dcc.Dropdown(
                    id=id_fluxo,
                    options=fluxo_opts,
                    value=default,
                    clearable=False,
                    style={**dd_style, "width": "160px"},
                ),
            ]
        )

    @callback(
        Output("graficos-container", "children"),
        Input("sel-graficos", "value"),
        Input("ncm-store", "data"),
        Input("sel-anos", "value"),
    )
    def atualizar(graficos_sel, ncms_sel, anos_sel):
        if not graficos_sel:
            return html.P(
                "Selecione ao menos uma visualização.",
                style={"color": TEXTO2, "padding": "40px", "textAlign": "center"},
            )

        cards_out = []
        for g in graficos_sel:
            if g == "evolucao":
                fig = fig_evolucao(ncms_sel, anos_sel)
                fig.update_layout(height=440)
                titulo, controles = "📈 Evolução Total", None
                gcontent = dcc.Graph(
                    figure=fig, config={"displayModeBar": True, "responsive": True}
                )

            elif g == "saldo":
                titulo = "⚖️ Saldo Comercial"
                controles = html.Div(
                    style={"display": "flex", "gap": "12px", "marginBottom": "10px"},
                    children=[bloco_nivel("saldo-nivel")],
                )
                gcontent = dcc.Graph(
                    id="graph-saldo",
                    config={"displayModeBar": True, "responsive": True},
                )

            elif g == "composicao":
                titulo = "📦 Composição por Fluxo"
                controles = html.Div(
                    style={"display": "flex", "gap": "12px", "marginBottom": "10px"},
                    children=[bloco_fluxo("comp-fluxo"), bloco_nivel("comp-nivel")],
                )
                gcontent = dcc.Graph(
                    id="graph-composicao",
                    config={"displayModeBar": True, "responsive": True},
                )

            elif g == "heatmap":
                titulo = "🌡️ Heatmap de Intensidade"
                controles = html.Div(
                    style={"display": "flex", "gap": "12px", "marginBottom": "10px"},
                    children=[
                        bloco_fluxo("hm-fluxo"),
                        bloco_nivel("hm-nivel", default="NCM"),
                    ],
                )
                gcontent = dcc.Graph(
                    id="graph-heatmap",
                    config={"displayModeBar": True, "responsive": True},
                )

            elif g == "donut":
                titulo = "🥧 Participação por Ano"
                controles = html.Div(
                    style={
                        "display": "flex",
                        "gap": "12px",
                        "marginBottom": "10px",
                        "flexWrap": "wrap",
                    },
                    children=[
                        bloco_fluxo("donut-fluxo"),
                        bloco_nivel("donut-nivel"),
                        html.Div(
                            [
                                lbl(f"Ano ({int(ANOS[0])}–{int(ANOS[-1])})"),
                                dcc.Dropdown(
                                    id="donut-ano",
                                    options=ano_opts,
                                    value=ano_mais_recente,
                                    clearable=False,
                                    optionHeight=36,
                                    style={**dd_style, "width": "110px"},
                                ),
                            ]
                        ),
                    ],
                )
                gcontent = dcc.Graph(
                    id="graph-donut",
                    config={"displayModeBar": True, "responsive": True},
                )
            else:
                continue

            inner = [
                html.H3(
                    titulo,
                    style={
                        "color": TEXTO2,
                        "fontSize": "0.75rem",
                        "textTransform": "uppercase",
                        "letterSpacing": "0.5px",
                        "marginBottom": "10px",
                    },
                )
            ]
            if controles:
                inner.append(controles)
            inner.append(gcontent)
            cards_out.append(card(inner))

        return cards_out

    @callback(
        Output("graph-saldo", "figure"),
        Input("saldo-nivel", "value"),
        Input("ncm-store", "data"),
        Input("sel-anos", "value"),
        prevent_initial_call=False,
    )
    def upd_saldo(nivel, ncms_sel, anos_sel):
        fig = fig_saldo(ncms_sel, anos_sel, nivel)
        fig.update_layout(height=440)
        return fig

    @callback(
        Output("graph-composicao", "figure"),
        Input("comp-fluxo", "value"),
        Input("comp-nivel", "value"),
        Input("ncm-store", "data"),
        Input("sel-anos", "value"),
        prevent_initial_call=False,
    )
    def upd_comp(fluxo, nivel, ncms_sel, anos_sel):
        fig = fig_composicao(fluxo, ncms_sel, anos_sel, nivel)
        fig.update_layout(height=440)
        return fig

    @callback(
        Output("graph-heatmap", "figure"),
        Input("hm-fluxo", "value"),
        Input("hm-nivel", "value"),
        Input("ncm-store", "data"),
        prevent_initial_call=False,
    )
    def upd_hm(fluxo, nivel, ncms_sel):
        fig = fig_heatmap(fluxo, ncms_sel, nivel)
        return fig

    @callback(
        Output("graph-donut", "figure"),
        Input("donut-fluxo", "value"),
        Input("donut-ano", "value"),
        Input("donut-nivel", "value"),
        Input("ncm-store", "data"),
        prevent_initial_call=False,
    )
    def upd_donut(fluxo, ano, nivel, ncms_sel):
        fig = fig_donut(fluxo, int(ano), ncms_sel, nivel)
        return fig

    app.run(debug=False, port=8050)


def exportar_html_estatico():
    """
    Gera docs/index.html totalmente interativo e estático (Plotly.js no
    navegador, sem servidor Python). Replica os mesmos controles do Dash:
    checkboxes de NCM agrupadas por categoria, seletor de nível de
    agregação (Categoria/NCM) por gráfico, range de anos e fluxo.
    """
    os.makedirs("docs", exist_ok=True)

    records = df.to_dict("records")
    data_json = json.dumps(records, ensure_ascii=False)
    ncms_json = json.dumps(NCMS, ensure_ascii=False)
    categorias_json = json.dumps(CATEGORIAS_LIST, ensure_ascii=False)
    cores_ncm_json = json.dumps(CORES_CAT, ensure_ascii=False)
    cores_cat_json = json.dumps(CATEGORIA_COR_BASE, ensure_ascii=False)
    anos_json = json.dumps([int(a) for a in ANOS])
    label_to_cat_json = json.dumps(
        {LABELS[ncm]: cat for cat, lst in CATEGORIAS.items() for ncm in lst},
        ensure_ascii=False,
    )

    header_html = HEADER_FONTE_TEXTO
    detalhe_html = HEADER_DETALHE_TEXTO.replace("\n", "<br>")

    js = r"""
const DATA = __DATA_JSON__;
const NCMS = __NCMS_JSON__;
const CATEGORIAS_LIST = __CATEGORIAS_JSON__;
const CORES_NCM = __CORES_NCM_JSON__;
const CORES_CAT_BASE = __CORES_CAT_JSON__;
const LABEL_TO_CAT = __LABEL_TO_CAT_JSON__;
const ANOS = __ANOS_JSON__;

const BG = "__BG__", BG2 = "__BG2__", BG3 = "__BG3__",
      BORDA = "__BORDA__", TEXTO = "__TEXTO__", TEXTO2 = "__TEXTO2__";

function fmtUsd(v) {
    if (v >= 1e6) return "US$ " + (v / 1e6).toFixed(1) + "M";
    if (v >= 1e3) return "US$ " + Math.round(v / 1e3) + "K";
    return "US$ " + v.toLocaleString("en-US", {maximumFractionDigits: 0});
}

function getDimInfo(nivel) {
    if (nivel === "Categoria") return { col: "Categoria", order: CATEGORIAS_LIST, colors: CORES_CAT_BASE };
    return { col: "Label", order: NCMS, colors: CORES_NCM };
}

function layoutBase() {
    return {
        paper_bgcolor: BG, plot_bgcolor: BG2,
        font: { family: "Inter, Segoe UI, Arial", color: TEXTO, size: 13 },
        margin: { t: 70, b: 60, l: 105, r: 30 },
        xaxis: { gridcolor: BORDA, zerolinecolor: BORDA,
                 tickfont: { color: TEXTO2 }, title: { font: { color: TEXTO2 } } },
        yaxis: { gridcolor: BORDA, zerolinecolor: BORDA,
                 tickfont: { color: TEXTO2 }, title: { font: { color: TEXTO2 } } },
        legend: { bgcolor: "rgba(0,0,0,0)", bordercolor: BORDA, borderwidth: 1,
                  font: { color: TEXTO, size: 11 }, orientation: "h",
                  yanchor: "bottom", y: 1.02, xanchor: "center", x: 0.5 },
        hoverlabel: { bgcolor: BG3, bordercolor: BORDA, font: { color: TEXTO } },
    };
}

function plotVazio(divId, msg) {
    const layout = layoutBase();
    layout.xaxis.visible = false;
    layout.yaxis.visible = false;
    layout.height = 200;
    layout.annotations = [{
        text: "\u26a0  " + msg, x: 0.5, y: 0.5, xref: "paper", yref: "paper",
        showarrow: false, font: { size: 15, color: TEXTO2 },
    }];
    Plotly.newPlot(divId, [], layout, { displayModeBar: true, responsive: true });
}

function sumByAno(arr) {
    const map = new Map();
    for (const item of arr) map.set(item.Ano, (map.get(item.Ano) || 0) + item.Valor);
    return map;
}

function filterBase(ncmSel, anoMin, anoMax) {
    return DATA.filter(d => ncmSel.includes(d.Label) && d.Ano >= anoMin && d.Ano <= anoMax);
}

// ── Evolução Total ────────────────────────────────────────────────────────
function renderEvolucao(divId, ncmSel, anoMin, anoMax) {
    const d = filterBase(ncmSel, anoMin, anoMax);
    const total = d.reduce((s, x) => s + x.Valor, 0);
    if (d.length === 0 || total === 0) {
        plotVazio(divId, "Nenhuma categoria selecionada ou sem dados no per\u00edodo");
        return;
    }
    const traces = [];
    const specs = [
        ["Exporta\u00e7\u00e3o", "#3B82F6", "rgba(59,130,246,0.12)"],
        ["Importa\u00e7\u00e3o", "#EF4444", "rgba(239,68,68,0.12)"],
    ];
    for (const [fluxo, cor, rgba] of specs) {
        const sub = d.filter(x => x.Fluxo === fluxo);
        if (sub.length === 0) continue;
        const byAno = sumByAno(sub);
        const anos = [...byAno.keys()].sort((a, b) => a - b);
        const valores = anos.map(a => byAno.get(a));
        traces.push({
            x: anos, y: valores, name: fluxo, mode: "lines+markers",
            line: { color: cor, width: 3 },
            marker: { size: 8, color: cor, line: { color: BG, width: 2 } },
            fill: "tozeroy", fillcolor: rgba,
            customdata: valores.map(fmtUsd),
            hovertemplate: "<b>%{x}</b><br>" + fluxo + ": %{customdata}<extra></extra>",
        });
    }
    const layout = layoutBase();
    layout.title = { text: "Evolu\u00e7\u00e3o Total \u2014 Exporta\u00e7\u00e3o vs Importa\u00e7\u00e3o (USD FOB)", font: { size: 15 } };
    layout.xaxis = { ...layout.xaxis, title: "Ano", dtick: 1, tickangle: -45 };
    layout.yaxis.title = "USD FOB";
    layout.yaxis.tickformat = "$,.0f";
    layout.height = 440;
    Plotly.newPlot(divId, traces, layout, { displayModeBar: true, responsive: true });
}

// ── Saldo Comercial ───────────────────────────────────────────────────────
function renderSaldo(divId, ncmSel, anoMin, anoMax, nivel) {
    const d = filterBase(ncmSel, anoMin, anoMax);
    if (d.length === 0) {
        plotVazio(divId, "Nenhuma categoria selecionada ou sem dados no per\u00edodo");
        return;
    }
    const { col, order, colors } = getDimInfo(nivel);
    const traces = [];
    for (const item of order) {
        const sub = d.filter(x => x[col] === item);
        if (sub.length === 0) continue;
        const anosSet = [...new Set(sub.map(x => x.Ano))].sort((a, b) => a - b);
        const saldos = anosSet.map(ano => {
            const exp = sub.filter(x => x.Ano === ano && x.Fluxo === "Exporta\u00e7\u00e3o").reduce((s, x) => s + x.Valor, 0);
            const imp = sub.filter(x => x.Ano === ano && x.Fluxo === "Importa\u00e7\u00e3o").reduce((s, x) => s + x.Valor, 0);
            return exp - imp;
        });
        if (saldos.every(v => v === 0)) continue;
        traces.push({
            x: anosSet, y: saldos, name: item, type: "bar",
            marker: { color: colors[item], opacity: 0.9 },
            customdata: saldos.map(fmtUsd),
            hovertemplate: "<b>" + item + "</b><br>Ano: %{x}<br>Saldo: %{customdata}<extra></extra>",
        });
    }
    if (traces.length === 0) {
        plotVazio(divId, "Nenhuma categoria selecionada ou sem dados no per\u00edodo");
        return;
    }
    const layout = layoutBase();
    layout.title = {
        text: nivel === "Categoria"
            ? "Saldo Comercial por Categoria (Exporta\u00e7\u00e3o \u2212 Importa\u00e7\u00e3o)"
            : "Saldo Comercial por NCM (Exporta\u00e7\u00e3o \u2212 Importa\u00e7\u00e3o)",
        font: { size: 15 },
    };
    layout.barmode = "group";
    layout.xaxis = { ...layout.xaxis, title: "Ano", dtick: 1, tickangle: -45 };
    layout.yaxis.title = "Saldo (USD FOB)";
    layout.yaxis.tickformat = "$,.0f";
    layout.height = 440;
    layout.shapes = [{ type: "line", x0: 0, x1: 1, xref: "paper", y0: 0, y1: 0,
                       line: { color: TEXTO2, width: 1, dash: "dot" } }];
    Plotly.newPlot(divId, traces, layout, { displayModeBar: true, responsive: true });
}

// ── Composição ────────────────────────────────────────────────────────────
function renderComposicao(divId, fluxo, ncmSel, anoMin, anoMax, nivel) {
    const d = filterBase(ncmSel, anoMin, anoMax).filter(x => x.Fluxo === fluxo);
    const total = d.reduce((s, x) => s + x.Valor, 0);
    if (d.length === 0 || total === 0) {
        plotVazio(divId, "Nenhum dado de " + fluxo + " para os filtros selecionados");
        return;
    }
    const { col, order, colors } = getDimInfo(nivel);
    const traces = [];
    for (const item of order) {
        const sub = d.filter(x => x[col] === item);
        if (sub.length === 0) continue;
        const anosSet = [...new Set(sub.map(x => x.Ano))].sort((a, b) => a - b);
        const valores = anosSet.map(ano => {
            const v = sub.filter(x => x.Ano === ano).reduce((s, x) => s + x.Valor, 0);
            return v > 0 ? v : null;
        });
        if (valores.every(v => v === null)) continue;
        const custom = valores.map(v => v ? fmtUsd(v) : "Sem dados");
        traces.push({
            x: anosSet, y: valores, name: item, type: "bar",
            marker: { color: colors[item] },
            customdata: custom,
            hovertemplate: "<b>" + item + "</b><br>%{x}: %{customdata}<extra></extra>",
        });
    }
    if (traces.length === 0) {
        plotVazio(divId, "Nenhum dado de " + fluxo + " para os filtros selecionados");
        return;
    }
    const layout = layoutBase();
    const nivelTxt = nivel === "Categoria" ? "Categoria" : "NCM";
    layout.title = { text: "Composi\u00e7\u00e3o das " + fluxo + "s por " + nivelTxt, font: { size: 15 } };
    layout.barmode = "stack";
    layout.xaxis = { ...layout.xaxis, title: "Ano", dtick: 1, tickangle: -45 };
    layout.yaxis.title = fluxo + " (USD FOB)";
    layout.yaxis.tickformat = "$,.0f";
    layout.height = 440;
    Plotly.newPlot(divId, traces, layout, { displayModeBar: true, responsive: true });
}

// ── Heatmap ───────────────────────────────────────────────────────────────
function renderHeatmap(divId, fluxo, ncmSel, nivel) {
    let d = DATA.filter(x => x.Fluxo === fluxo);
    if (ncmSel) d = d.filter(x => ncmSel.includes(x.Label));
    const total = d.reduce((s, x) => s + x.Valor, 0);
    if (total === 0) {
        plotVazio(divId, "Nenhum dado de " + fluxo + " para exibir no heatmap");
        return;
    }
    const { col, order, colors } = getDimInfo(nivel);
    const z = [], text = [];
    for (const item of order) {
        const rowZ = [], rowT = [];
        for (const ano of ANOS) {
            const v = d.filter(x => x[col] === item && x.Ano === ano).reduce((s, x) => s + x.Valor, 0);
            rowZ.push(v > 0 ? v : null);
            rowT.push(v > 0 ? fmtUsd(v) : "\u2014");
        }
        z.push(rowZ); text.push(rowT);
    }
    const trace = {
        z: z, x: ANOS.map(String), y: order, type: "heatmap",
        colorscale: [
            [0.0, "#1C2128"], [0.15, "#1D4ED8"], [0.4, "#0EA5E9"],
            [0.65, "#22C55E"], [0.85, "#F59E0B"], [1.0, "#EF4444"],
        ],
        text: text, texttemplate: "%{text}",
        textfont: { size: 9, color: TEXTO },
        hoverongaps: false,
        hovertemplate: "<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
        colorbar: { title: { text: "USD FOB", font: { color: TEXTO2 } },
                    tickfont: { color: TEXTO2 }, bgcolor: BG2,
                    bordercolor: BORDA, outlinecolor: BORDA },
        zmin: 0,
    };
    const layout = layoutBase();
    const nivelTxt = nivel === "Categoria" ? "Categoria" : "NCM";
    layout.title = { text: "Heatmap \u2014 Intensidade de " + fluxo + "s por " + nivelTxt + " e Ano", font: { size: 15 } };
    layout.xaxis = { title: "Ano", gridcolor: BORDA, tickfont: { color: TEXTO2 }, dtick: 1, tickangle: -45 };
    layout.yaxis = { gridcolor: BORDA, tickfont: { color: TEXTO, size: 10 } };
    layout.margin = { t: 70, b: 60, l: nivel === "NCM" ? 230 : 150, r: 30 };
    layout.height = 110 + 32 * order.length;
    Plotly.newPlot(divId, [trace], layout, { displayModeBar: true, responsive: true });
}

// ── Donut ─────────────────────────────────────────────────────────────────
function renderDonut(divId, fluxo, ano, ncmSel, nivel) {
    let d = DATA.filter(x => x.Ano === ano && x.Fluxo === fluxo);
    if (ncmSel) d = d.filter(x => ncmSel.includes(x.Label));
    if (d.length === 0) {
        plotVazio(divId, "Nenhum dado de " + fluxo + " em " + ano);
        return;
    }
    const { col, colors } = getDimInfo(nivel);
    const agg = new Map();
    for (const item of d) {
        const key = item[col];
        agg.set(key, (agg.get(key) || 0) + item.Valor);
    }
    const entries = [...agg.entries()].filter(([, v]) => v > 0);
    if (entries.length === 0) {
        plotVazio(divId, "Nenhum dado de " + fluxo + " em " + ano);
        return;
    }
    const labels = entries.map(e => e[0]);
    const values = entries.map(e => e[1]);
    const cores = labels.map(l => colors[l]);
    const trace = {
        labels: labels, values: values, type: "pie", hole: 0.48,
        marker: { colors: cores, line: { color: BG, width: 2 } },
        textinfo: "percent",
        textfont: { color: TEXTO, size: 11 },
        customdata: values.map(fmtUsd),
        hovertemplate: "<b>%{label}</b><br>%{customdata}<br>%{percent}<extra></extra>",
    };
    const layout = layoutBase();
    delete layout.legend;
    const nivelTxt = nivel === "Categoria" ? "Categoria" : "NCM";
    layout.title = { text: "Participa\u00e7\u00e3o nas " + fluxo + "s por " + nivelTxt + " \u2014 " + ano, font: { size: 15 } };
    layout.showlegend = true;
    layout.legend = { orientation: "v", x: 1.02, y: 0.5, font: { color: TEXTO, size: 10 } };
    layout.height = 440;
    Plotly.newPlot(divId, [trace], layout, { displayModeBar: true, responsive: true });
}

// ── Estado e wiring dos controles ──────────────────────────────────────────
function getSelectedNcms() {
    return [...document.querySelectorAll(".ncm-check:checked")].map(el => el.value);
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
    const ncmSel = getSelectedNcms();
    const [anoMin, anoMax] = getAnoRange();

    renderEvolucao("graph-evolucao", ncmSel, anoMin, anoMax);

    const saldoNivel = document.getElementById("saldo-nivel").value;
    renderSaldo("graph-saldo", ncmSel, anoMin, anoMax, saldoNivel);

    const compFluxo = document.getElementById("comp-fluxo").value;
    const compNivel = document.getElementById("comp-nivel").value;
    renderComposicao("graph-composicao", compFluxo, ncmSel, anoMin, anoMax, compNivel);

    const hmFluxo = document.getElementById("hm-fluxo").value;
    const hmNivel = document.getElementById("hm-nivel").value;
    renderHeatmap("graph-heatmap", hmFluxo, ncmSel, hmNivel);

    const donutFluxo = document.getElementById("donut-fluxo").value;
    const donutAno = parseInt(document.getElementById("donut-ano").value);
    const donutNivel = document.getElementById("donut-nivel").value;
    renderDonut("graph-donut", donutFluxo, donutAno, ncmSel, donutNivel);
}

function toggleSection(key, visible) {
    const el = document.getElementById("section-" + key);
    if (el) el.style.display = visible ? "" : "none";
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".ncm-check").forEach(el => el.addEventListener("change", renderAll));
    document.getElementById("ano-min").addEventListener("input", () => { updateAnoLabel(); renderAll(); });
    document.getElementById("ano-max").addEventListener("input", () => { updateAnoLabel(); renderAll(); });
    ["comp-fluxo", "comp-nivel", "hm-fluxo", "hm-nivel", "donut-fluxo", "donut-ano", "donut-nivel", "saldo-nivel"]
        .forEach(id => document.getElementById(id).addEventListener("change", renderAll));
    document.querySelectorAll(".viz-check").forEach(el => {
        el.addEventListener("change", () => toggleSection(el.value, el.checked));
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
        .replace("__LABEL_TO_CAT_JSON__", label_to_cat_json)
        .replace("__ANOS_JSON__", anos_json)
        .replace("__BG__", BG)
        .replace("__BG2__", BG2)
        .replace("__BG3__", BG3)
        .replace("__BORDA__", BORDA)
        .replace("__TEXTO__", TEXTO)
        .replace("__TEXTO2__", TEXTO2)
    )

    ano_min, ano_max = int(ANOS[0]), int(ANOS[-1])
    ano_default = ano_max

    def bloco_ncm_checkboxes(cat_nome, ncm_list):
        cor = CATEGORIA_COR_BASE[cat_nome]
        items = "".join(
            f'<label class="chk"><input type="checkbox" class="ncm-check" value="{LABELS[n]}" checked> {LABELS[n]}</label>'
            for n in ncm_list
        )
        return f'<div class="ncm-group"><div class="ncm-group-title" style="color:{cor}">{cat_nome}</div>{items}</div>'

    ncm_checkboxes_html = "".join(
        bloco_ncm_checkboxes(cat, lst) for cat, lst in CATEGORIAS.items()
    )

    viz_checkboxes = "".join(
        f'<label class="chk"><input type="checkbox" class="viz-check" value="{key}" checked> {label}</label>'
        for key, label in [
            ("evolucao", "Evolução Total"),
            ("saldo", "Saldo Comercial"),
            ("composicao", "Composição (Exp/Imp)"),
            ("heatmap", "Heatmap"),
            ("donut", "Participação (Donut)"),
        ]
    )
    ano_options = "".join(f'<option value="{int(a)}">{int(a)}</option>' for a in ANOS)

    nivel_select = """
        <option value="Categoria">Categoria (agrupado)</option>
        <option value="NCM">NCM (detalhado)</option>
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
main{{max-width:1200px;margin:0 auto;padding:20px 24px;display:flex;flex-direction:column;gap:20px}}
.card{{background:{BG2};border:1px solid {BORDA};border-radius:12px;padding:20px 16px}}
.card h2{{font-size:.75rem;font-weight:600;color:{TEXTO2};text-transform:uppercase;letter-spacing:.6px;margin-bottom:10px}}
footer{{text-align:center;padding:20px;color:{TEXTO2};font-size:.78rem;border-top:1px solid {BORDA};margin-top:8px}}

.controls{{display:grid;grid-template-columns:1.3fr 2fr 1.2fr;gap:20px;align-items:start}}
.control-group label.title{{display:block;color:{TEXTO2};font-size:.72rem;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}}
.chk{{display:flex;align-items:center;gap:6px;font-size:.78rem;cursor:pointer;color:{TEXTO};margin-bottom:4px}}
.chk input{{accent-color:#3B82F6;cursor:pointer}}

.ncm-groups{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px}}
.ncm-group-title{{font-size:.76rem;font-weight:700;text-transform:uppercase;letter-spacing:.4px;margin-bottom:6px}}

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
</style>
</head>
<body>

<header>
  <h1>Comércio Exterior de Armas de Fogo — Brasil (2011–2026)</h1>
  <p>{header_html}</p>
  <details>
    <summary>Ver descrição completa dos {len(LABELS)} NCMs</summary>
    <pre>{detalhe_html}</pre>
  </details>
</header>

<main>

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
    <h2>📈 Evolução Total</h2>
    <div id="graph-evolucao"></div>
  </div>

  <div class="card" id="section-saldo">
    <h2>⚖️ Saldo Comercial</h2>
    <div class="inline-controls">
      <div class="field"><label>Nível</label>
        <select id="saldo-nivel">{nivel_select}</select>
      </div>
    </div>
    <div id="graph-saldo"></div>
  </div>

  <div class="card" id="section-composicao">
    <h2>📦 Composição por Fluxo</h2>
    <div class="inline-controls">
      <div class="field"><label>Fluxo</label>
        <select id="comp-fluxo">
          <option value="Exportação">Exportação</option>
          <option value="Importação">Importação</option>
        </select>
      </div>
      <div class="field"><label>Nível</label>
        <select id="comp-nivel">{nivel_select}</select>
      </div>
    </div>
    <div id="graph-composicao"></div>
  </div>

  <div class="card" id="section-heatmap">
    <h2>🌡️ Heatmap de Intensidade</h2>
    <div class="inline-controls">
      <div class="field"><label>Fluxo</label>
        <select id="hm-fluxo">
          <option value="Exportação">Exportação</option>
          <option value="Importação">Importação</option>
        </select>
      </div>
      <div class="field"><label>Nível</label>
        <select id="hm-nivel">
          <option value="NCM">NCM (detalhado)</option>
          <option value="Categoria">Categoria (agrupado)</option>
        </select>
      </div>
    </div>
    <div id="graph-heatmap"></div>
  </div>

  <div class="card" id="section-donut">
    <h2>🥧 Participação por Ano</h2>
    <div class="inline-controls">
      <div class="field"><label>Fluxo</label>
        <select id="donut-fluxo">
          <option value="Exportação">Exportação</option>
          <option value="Importação">Importação</option>
        </select>
      </div>
      <div class="field"><label>Nível</label>
        <select id="donut-nivel">{nivel_select}</select>
      </div>
      <div class="field"><label>Ano</label>
        <select id="donut-ano">{ano_options}</select>
      </div>
    </div>
    <div id="graph-donut"></div>
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

    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(page)
    print(
        f"✅ docs/index.html gerado — {len(LABELS)} NCMs, {int(ANOS[0])}–{int(ANOS[-1])}"
    )


if __name__ == "__main__":
    if "--export" in sys.argv:
        exportar_html_estatico()
    else:
        rodar_dash()
