import json
import os
import sys

import pandas as pd
import plotly.graph_objects as go

ARQUIVO = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "dados_small_arms.xlsx"
)

LABELS: dict[int, str] = {
    93033000: "Espingardas/Carabinas (estriado)",
    93032000: "Espingardas/Carabinas (liso)",
    93020000: "Revólveres e Pistolas",
    93039090: "Outras Armas (pólvora)",
}

NCM_DESCRICOES = {
    93020000: "Revólveres e pistolas, exceto os das posições 93.03 ou 93.04.",
    93032000: "Outras espingardas e carabinas de caça ou de tiro ao alvo, com pelo menos um cano liso",
    93033000: "Outras espingardas e carabinas de caça ou de tiro ao alvo",
    93039090: "Outras armas de fogo que utilizam deflagração da pólvora, etc.",
}

HEADER_FONTE_TEXTO = "Fonte: Comex Stat / MDIC · USD FOB · NCMs: \n" + "\n".join(
    f"{ncm} ({desc})" for ncm, desc in NCM_DESCRICOES.items()
)


def carregar_dados():
    df_raw = pd.read_excel(ARQUIVO, sheet_name="Resultado")
    registros = []
    for _, row in df_raw.iterrows():
        ncm = int(row["Código NCM"])
        label = LABELS.get(ncm, str(ncm))
        for col in df_raw.columns:
            if col.startswith("Exportação") or col.startswith("Importação"):
                p = col.split(" - ")
                registros.append(
                    {
                        "NCM": ncm,
                        "Label": label,
                        "Fluxo": p[0],
                        "Ano": int(p[1]),
                        "Valor": float(row[col]) if pd.notna(row[col]) else 0.0,
                    }
                )
    return pd.DataFrame(registros)


df = carregar_dados()
ANOS = sorted(df["Ano"].unique())
NCMS = list(LABELS.values())

BG = "#0D1117"
BG2 = "#161B22"
BG3 = "#1C2128"
BORDA = "#30363D"
TEXTO = "#E6EDF3"
TEXTO2 = "#8B949E"

CORES_CAT = {
    "Espingardas/Carabinas (estriado)": "#22C55E",
    "Espingardas/Carabinas (liso)": "#3B82F6",
    "Revólveres e Pistolas": "#EF4444",
    "Outras Armas (pólvora)": "#F97316",
}


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
        margin=dict(t=70, b=50, l=105, r=30),
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
            font=dict(color=TEXTO),
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
                marker=dict(size=9, color=cor, line=dict(color=BG, width=2)),
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
        tickangle=0,
        ticklabelstandoff=8,
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


def fig_saldo(ncms_sel=None, anos_sel=None):
    d = df.copy()
    if ncms_sel is not None:
        d = d[d["Label"].isin(ncms_sel)]
    if anos_sel:
        d = d[d["Ano"].between(anos_sel[0], anos_sel[1])]
    if d.empty:
        return fig_vazio("Nenhuma categoria selecionada ou sem dados no período")
    pivot = (
        d.pivot_table(
            index=["Label", "Ano"], columns="Fluxo", values="Valor", aggfunc="sum"
        )
        .fillna(0)
        .reset_index()
    )
    pivot["Saldo"] = pivot.get("Exportação", 0) - pivot.get("Importação", 0)
    fig = go.Figure()
    for ncm in NCMS:
        if ncms_sel and ncm not in ncms_sel:
            continue
        sub = pivot[pivot["Label"] == ncm].sort_values("Ano")
        if sub.empty:
            continue
        cor = CORES_CAT[ncm]
        fig.add_trace(
            go.Bar(
                x=sub["Ano"],
                y=sub["Saldo"],
                name=ncm,
                marker=dict(color=cor, opacity=0.9),
                hovertemplate=f"<b>{ncm}</b><br>Ano: %{{x}}<br>Saldo: %{{customdata}}<extra></extra>",
                customdata=[fmt_usd(v) for v in sub["Saldo"]],
            )
        )
    fig.add_hline(y=0, line_dash="dot", line_color=TEXTO2, opacity=0.6)
    fig.update_layout(
        **layout_base(),
        title=dict(
            text="Saldo Comercial por Categoria (Exportação − Importação)",
            font=dict(size=15),
        ),
        barmode="group",
        xaxis_title="Ano",
        yaxis_title="Saldo (USD FOB)",
        yaxis_tickformat="$,.0f",
    )
    return fig


def fig_composicao(fluxo="Exportação", ncms_sel=None, anos_sel=None):
    d = df[df["Fluxo"] == fluxo].copy()
    if ncms_sel is not None:
        d = d[d["Label"].isin(ncms_sel)]
    if anos_sel:
        d = d[d["Ano"].between(anos_sel[0], anos_sel[1])]
    if d.empty or d["Valor"].sum() == 0:
        return fig_vazio(f"Nenhum dado de {fluxo} para os filtros selecionados")
    fig = go.Figure()
    for ncm in NCMS:
        if ncms_sel and ncm not in ncms_sel:
            continue
        s = d[d["Label"] == ncm].sort_values("Ano")
        valores = [v if v > 0 else None for v in s["Valor"]]
        custom = [fmt_usd(v) if v else "Sem dados" for v in s["Valor"]]
        fig.add_trace(
            go.Bar(
                x=s["Ano"],
                y=valores,
                name=ncm,
                marker_color=CORES_CAT[ncm],
                hovertemplate=f"<b>{ncm}</b><br>%{{x}}: %{{customdata}}<extra></extra>",
                customdata=custom,
            )
        )
    fig.update_layout(
        **layout_base(),
        title=dict(text=f"Composição das {fluxo}s por Categoria", font=dict(size=15)),
        barmode="stack",
        xaxis_title="Ano",
        yaxis_title=f"{fluxo} (USD FOB)",
        yaxis_tickformat="$,.0f",
    )
    return fig


def fig_heatmap(fluxo="Exportação"):
    d = df[df["Fluxo"] == fluxo]
    pivot = d.pivot_table(
        index="Label", columns="Ano", values="Valor", aggfunc="sum"
    ).fillna(0)
    if pivot.values.sum() == 0:
        return fig_vazio(f"Nenhum dado de {fluxo} para exibir no heatmap")
    z_vals = [[v if v > 0 else None for v in row] for row in pivot.values]
    text = [[fmt_usd(v) if v else "—" for v in row] for row in pivot.values]
    fig = go.Figure(
        data=go.Heatmap(
            z=z_vals,
            x=pivot.columns.astype(str),
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
            textfont=dict(size=11, color=TEXTO),
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
    hml["xaxis"] = dict(title="Ano", gridcolor=BORDA, tickfont=dict(color=TEXTO2))
    hml["yaxis"] = dict(gridcolor=BORDA, tickfont=dict(color=TEXTO, size=10))
    hml["margin"] = dict(t=70, b=50, l=190, r=30)
    fig.update_layout(
        **hml,
        title=dict(
            text=f"Heatmap — Intensidade de {fluxo}s por Categoria e Ano",
            font=dict(size=15),
        ),
        height=340,
    )
    return fig


def fig_donut(fluxo="Exportação", ano=2025):
    d = df[(df["Ano"] == ano) & (df["Fluxo"] == fluxo)]
    d = d[d["Valor"] > 0]
    if d.empty:
        return fig_vazio(f"Nenhum dado de {fluxo} em {ano}")
    cores = [CORES_CAT[l] for l in d["Label"] if l in CORES_CAT]
    fig = go.Figure(
        data=go.Pie(
            labels=d["Label"],
            values=d["Valor"],
            hole=0.48,
            marker=dict(colors=cores, line=dict(color=BG, width=2)),
            textinfo="label+percent",
            textfont=dict(color=TEXTO, size=11),
            hovertemplate="<b>%{label}</b><br>%{customdata}<br>%{percent}<extra></extra>",
            customdata=[fmt_usd(v) for v in d["Valor"]],
        )
    )
    pl = layout_base()
    pl.pop("legend", None)
    fig.update_layout(
        **pl,
        title=dict(text=f"Participação nas {fluxo}s — {ano}", font=dict(size=15)),
        showlegend=True,
        legend=dict(orientation="v", x=1.01, y=0.5, font=dict(color=TEXTO, size=11)),
        height=420,
    )
    return fig


DARK_CSS = f"""
.dash-dropdown-wrapper {{
    background: {BG3} !important;
    border: 1px solid {BORDA} !important;
    border-radius: 8px !important;
}}
.dash-dropdown-trigger {{
    background: {BG3} !important;
    color: {TEXTO} !important;
    border-radius: 8px !important;
    padding: 6px 10px !important;
}}
.dash-dropdown-placeholder {{ color: {TEXTO2} !important; }}
.dash-dropdown-value {{ color: {TEXTO} !important; }}
.dash-dropdown-value-item {{
    background: {BG2} !important;
    border: 1px solid {BORDA} !important;
    border-radius: 4px !important;
    color: {TEXTO} !important;
    font-size: 12px !important;
}}
.dash-dropdown-value-count {{
    background: {BG2} !important;
    color: {TEXTO2} !important;
    border: 1px solid {BORDA} !important;
    border-radius: 4px !important;
    padding: 1px 7px !important;
    font-size: 12px !important;
}}
.dash-dropdown-trigger-icon svg,
.dash-dropdown-trigger-icon svg path,
.dash-dropdown-trigger-icon svg polyline {{
    stroke: {TEXTO2} !important;
    fill: none !important;
}}
.dash-dropdown-clear {{ color: {TEXTO2} !important; }}
.dash-dropdown-content {{
    background: {BG3} !important;
    border: 1px solid {BORDA} !important;
    border-radius: 8px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.7) !important;
    z-index: 9999 !important;
}}
.dash-dropdown-option {{
    background: {BG3} !important;
    color: {TEXTO} !important;
    padding: 8px 12px !important;
}}
.dash-dropdown-option:hover,
.dash-dropdown-option[aria-selected="true"],
.dash-dropdown-option[data-focused="true"] {{
    background: {BG2} !important;
    color: {TEXTO} !important;
}}
.dash-dropdown-search-container {{
    background: {BG3} !important;
    border-bottom: 1px solid {BORDA} !important;
}}
.dash-dropdown-search input {{
    background: transparent !important;
    color: {TEXTO} !important;
    border: none !important;
    outline: none !important;
}}
.dash-dropdown-search input::placeholder {{ color: {TEXTO2} !important; }}
.dash-dropdown-grid-container {{
    background: {BG3} !important;
}}
.dash-dropdown-actions {{ background: {BG3} !important; border-top: 1px solid {BORDA} !important; }}
.dash-dropdown-action-button {{ color: {TEXTO2} !important; }}
.dash-dropdown-action-button:hover {{ color: {TEXTO} !important; }}

body, #react-entry-point, ._dash-loading {{
    background-color: {BG} !important;
}}

.rc-slider-track {{ background-color: #3B82F6 !important; }}
.rc-slider-handle {{ border-color: #3B82F6 !important; background: {BG2} !important; }}
.rc-slider-rail {{ background-color: {BORDA} !important; }}

.dash-slider-tooltip, [class*="dash-slider-tooltip"] {{
    --Dash-Tooltip-Background-Color: {BG2} !important;
    --Dash-Tooltip-Border-Color: {BORDA} !important;
    background: {BG2} !important;
    color: {TEXTO} !important;
    border: 1px solid {BORDA} !important;
}}
.dash-tooltip {{
    background: {BG2} !important;
    color: {TEXTO} !important;
    border: 1px solid {BORDA} !important;
}}
.dash-tooltip::before, .dash-tooltip::after {{
    border-top-color: {BG2} !important;
}}
"""


def rodar_dash():
    import dash
    from dash import Input, Output, callback, dcc, html

    app = dash.Dash(
        __name__,
        title="Armas de Fogo — Comex Stat",
        suppress_callback_exceptions=True,
    )

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

    ncm_opts = [{"label": v, "value": v} for v in NCMS]
    ano_mais_recente = int(ANOS[-1])
    ano_opts = [{"label": str(a), "value": int(a)} for a in ANOS]
    fluxo_opts = [
        {"label": "Exportação", "value": "Exportação"},
        {"label": "Importação", "value": "Importação"},
    ]
    graf_opts = [
        {"label": "📈 Evolução Total", "value": "evolucao"},
        {"label": "⚖️ Saldo Comercial", "value": "saldo"},
        {"label": "📦 Composição (Exp/Imp)", "value": "composicao"},
        {"label": "🌡️ Heatmap", "value": "heatmap"},
        {"label": "🥧 Participação (Donut)", "value": "donut"},
    ]

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
                        "Comércio Exterior de Armas de Fogo — Brasil (2020–2026)",
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
                            "whiteSpace": "pre-line",
                        },
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
                                    "gridTemplateColumns": "2fr 1fr 1fr",
                                    "gap": "16px",
                                    "alignItems": "end",
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
                                            lbl("Categorias (NCM)"),
                                            dcc.Dropdown(
                                                id="sel-ncm",
                                                options=ncm_opts,
                                                value=NCMS,
                                                multi=True,
                                                style=dd_style,
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
                                                        "label": str(a),
                                                        "style": {
                                                            "color": TEXTO2,
                                                            "fontSize": "11px",
                                                        },
                                                    }
                                                    for a in ANOS
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
                    )
                ],
            ),
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
        Output("graficos-container", "children"),
        Input("sel-graficos", "value"),
        Input("sel-ncm", "value"),
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
                fig.update_layout(height=460)
                titulo = "📈 Evolução Total"
                controles = None
                gcontent = dcc.Graph(
                    figure=fig, config={"displayModeBar": True, "responsive": True}
                )

            elif g == "saldo":
                fig = fig_saldo(ncms_sel, anos_sel)
                fig.update_layout(height=460)
                titulo = "⚖️ Saldo Comercial"
                controles = None
                gcontent = dcc.Graph(
                    figure=fig, config={"displayModeBar": True, "responsive": True}
                )

            elif g == "composicao":
                titulo = "📦 Composição por Fluxo"
                controles = html.Div(
                    style={"display": "flex", "gap": "12px", "marginBottom": "10px"},
                    children=[
                        html.Div(
                            [
                                lbl("Fluxo"),
                                dcc.Dropdown(
                                    id="comp-fluxo",
                                    options=fluxo_opts,
                                    value="Exportação",
                                    clearable=False,
                                    style={**dd_style, "width": "160px"},
                                ),
                            ]
                        ),
                    ],
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
                        html.Div(
                            [
                                lbl("Fluxo"),
                                dcc.Dropdown(
                                    id="hm-fluxo",
                                    options=fluxo_opts,
                                    value="Exportação",
                                    clearable=False,
                                    style={**dd_style, "width": "160px"},
                                ),
                            ]
                        ),
                    ],
                )
                gcontent = dcc.Graph(
                    id="graph-heatmap",
                    config={"displayModeBar": True, "responsive": True},
                )

            elif g == "donut":
                titulo = "🥧 Participação por Ano"
                controles = html.Div(
                    style={"display": "flex", "gap": "12px", "marginBottom": "10px"},
                    children=[
                        html.Div(
                            [
                                lbl("Fluxo"),
                                dcc.Dropdown(
                                    id="donut-fluxo",
                                    options=fluxo_opts,
                                    value="Exportação",
                                    clearable=False,
                                    style={**dd_style, "width": "160px"},
                                ),
                            ]
                        ),
                        html.Div(
                            [
                                lbl(
                                    f"Ano (disponível: {int(ANOS[0])}–{int(ANOS[-1])})"
                                ),
                                dcc.Dropdown(
                                    id="donut-ano",
                                    options=ano_opts,
                                    value=ano_mais_recente,
                                    clearable=False,
                                    optionHeight=36,
                                    style={**dd_style, "width": "130px"},
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
                ),
            ]
            if controles:
                inner.append(controles)
            inner.append(gcontent)
            cards_out.append(card(inner))

        return cards_out

    @callback(
        Output("graph-composicao", "figure"),
        Input("comp-fluxo", "value"),
        Input("sel-ncm", "value"),
        Input("sel-anos", "value"),
        prevent_initial_call=False,
    )
    def upd_comp(fluxo, ncms_sel, anos_sel):
        fig = fig_composicao(fluxo, ncms_sel, anos_sel)
        fig.update_layout(height=460)
        return fig

    @callback(
        Output("graph-heatmap", "figure"),
        Input("hm-fluxo", "value"),
        prevent_initial_call=False,
    )
    def upd_hm(fluxo):
        fig = fig_heatmap(fluxo)
        fig.update_layout(height=360)
        return fig

    @callback(
        Output("graph-donut", "figure"),
        Input("donut-fluxo", "value"),
        Input("donut-ano", "value"),
        prevent_initial_call=False,
    )
    def upd_donut(fluxo, ano):
        fig = fig_donut(fluxo, int(ano))
        fig.update_layout(height=440)
        return fig

    app.run(debug=False, port=8050)


def exportar_html_estatico():
    """
    Gera docs/index.html totalmente interativo e estático.

    Diferente de simplesmente chamar fig.to_html() para cada gráfico com
    parâmetros fixos, aqui os dados são embutidos como JSON e os gráficos
    são renderizados via Plotly.js no navegador, com os MESMOS controles
    (checkboxes de NCM, range de anos, seletor de fluxo) que existem na
    versão Dash sem precisar de servidor Python rodando.
    """
    os.makedirs("docs", exist_ok=True)

    records = df.to_dict("records")
    data_json = json.dumps(records, ensure_ascii=False)
    ncms_json = json.dumps(NCMS, ensure_ascii=False)
    cores_json = json.dumps(CORES_CAT, ensure_ascii=False)
    anos_json = json.dumps([int(a) for a in ANOS])

    header_html = HEADER_FONTE_TEXTO.replace("\n", "<br>")

    js = """
const DATA = __DATA_JSON__;
const NCMS = __NCMS_JSON__;
const CORES_CAT = __CORES_JSON__;
const ANOS = __ANOS_JSON__;

const BG = "__BG__", BG2 = "__BG2__", BG3 = "__BG3__",
      BORDA = "__BORDA__", TEXTO = "__TEXTO__", TEXTO2 = "__TEXTO2__";

function fmtUsd(v) {
    if (v >= 1e6) return "US$ " + (v / 1e6).toFixed(1) + "M";
    if (v >= 1e3) return "US$ " + Math.round(v / 1e3) + "K";
    return "US$ " + v.toLocaleString("en-US", {maximumFractionDigits: 0});
}

function layoutBase() {
    return {
        paper_bgcolor: BG, plot_bgcolor: BG2,
        font: { family: "Inter, Segoe UI, Arial", color: TEXTO, size: 13 },
        margin: { t: 70, b: 50, l: 105, r: 30 },
        xaxis: { gridcolor: BORDA, zerolinecolor: BORDA,
                 tickfont: { color: TEXTO2 }, title: { font: { color: TEXTO2 } } },
        yaxis: { gridcolor: BORDA, zerolinecolor: BORDA,
                 tickfont: { color: TEXTO2 }, title: { font: { color: TEXTO2 } } },
        legend: { bgcolor: "rgba(0,0,0,0)", bordercolor: BORDA, borderwidth: 1,
                  font: { color: TEXTO }, orientation: "h",
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

function sumBy(arr, keyFn) {
    const map = new Map();
    for (const item of arr) {
        const k = keyFn(item);
        map.set(k, (map.get(k) || 0) + item.Valor);
    }
    return map;
}

function filterBase(ncmSel, anoMin, anoMax) {
    return DATA.filter(d =>
        ncmSel.includes(d.Label) && d.Ano >= anoMin && d.Ano <= anoMax
    );
}

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
        const byAno = sumBy(sub, x => x.Ano);
        const anos = [...byAno.keys()].sort((a, b) => a - b);
        const valores = anos.map(a => byAno.get(a));
        traces.push({
            x: anos, y: valores, name: fluxo, mode: "lines+markers",
            line: { color: cor, width: 3 },
            marker: { size: 9, color: cor, line: { color: BG, width: 2 } },
            fill: "tozeroy", fillcolor: rgba,
            customdata: valores.map(fmtUsd),
            hovertemplate: "<b>%{x}</b><br>" + fluxo + ": %{customdata}<extra></extra>",
        });
    }
    const layout = layoutBase();
    layout.title = { text: "Evolu\u00e7\u00e3o Total \u2014 Exporta\u00e7\u00e3o vs Importa\u00e7\u00e3o (USD FOB)", font: { size: 15 } };
    layout.xaxis = { ...layout.xaxis, title: "Ano", dtick: 1, tickmode: "linear", tickangle: 0 };
    layout.yaxis.title = "USD FOB";
    layout.yaxis.tickformat = "$,.0f";
    layout.height = 460;
    Plotly.newPlot(divId, traces, layout, { displayModeBar: true, responsive: true });
}

function renderSaldo(divId, ncmSel, anoMin, anoMax) {
    const d = filterBase(ncmSel, anoMin, anoMax);
    if (d.length === 0) {
        plotVazio(divId, "Nenhuma categoria selecionada ou sem dados no per\u00edodo");
        return;
    }
    const traces = [];
    for (const ncm of NCMS) {
        if (!ncmSel.includes(ncm)) continue;
        const sub = d.filter(x => x.Label === ncm);
        if (sub.length === 0) continue;
        const anosSet = [...new Set(sub.map(x => x.Ano))].sort((a, b) => a - b);
        const saldos = anosSet.map(ano => {
            const exp = sub.filter(x => x.Ano === ano && x.Fluxo === "Exporta\u00e7\u00e3o")
                            .reduce((s, x) => s + x.Valor, 0);
            const imp = sub.filter(x => x.Ano === ano && x.Fluxo === "Importa\u00e7\u00e3o")
                            .reduce((s, x) => s + x.Valor, 0);
            return exp - imp;
        });
        const cor = CORES_CAT[ncm];
        traces.push({
            x: anosSet, y: saldos, name: ncm, type: "bar",
            marker: { color: cor, opacity: 0.9 },
            customdata: saldos.map(fmtUsd),
            hovertemplate: "<b>" + ncm + "</b><br>Ano: %{x}<br>Saldo: %{customdata}<extra></extra>",
        });
    }
    const layout = layoutBase();
    layout.title = { text: "Saldo Comercial por Categoria (Exporta\u00e7\u00e3o \u2212 Importa\u00e7\u00e3o)", font: { size: 15 } };
    layout.barmode = "group";
    layout.xaxis.title = "Ano";
    layout.yaxis.title = "Saldo (USD FOB)";
    layout.yaxis.tickformat = "$,.0f";
    layout.height = 460;
    layout.shapes = [{ type: "line", x0: 0, x1: 1, xref: "paper", y0: 0, y1: 0,
                       line: { color: TEXTO2, width: 1, dash: "dot" } }];
    Plotly.newPlot(divId, traces, layout, { displayModeBar: true, responsive: true });
}

function renderComposicao(divId, fluxo, ncmSel, anoMin, anoMax) {
    const d = filterBase(ncmSel, anoMin, anoMax).filter(x => x.Fluxo === fluxo);
    const total = d.reduce((s, x) => s + x.Valor, 0);
    if (d.length === 0 || total === 0) {
        plotVazio(divId, "Nenhum dado de " + fluxo + " para os filtros selecionados");
        return;
    }
    const traces = [];
    for (const ncm of NCMS) {
        if (!ncmSel.includes(ncm)) continue;
        const sub = d.filter(x => x.Label === ncm);
        if (sub.length === 0) continue;
        const anosSet = [...new Set(sub.map(x => x.Ano))].sort((a, b) => a - b);
        const valores = anosSet.map(ano => {
            const v = sub.filter(x => x.Ano === ano).reduce((s, x) => s + x.Valor, 0);
            return v > 0 ? v : null;
        });
        const custom = valores.map(v => v ? fmtUsd(v) : "Sem dados");
        traces.push({
            x: anosSet, y: valores, name: ncm, type: "bar",
            marker: { color: CORES_CAT[ncm] },
            customdata: custom,
            hovertemplate: "<b>" + ncm + "</b><br>%{x}: %{customdata}<extra></extra>",
        });
    }
    const layout = layoutBase();
    layout.title = { text: "Composi\u00e7\u00e3o das " + fluxo + "s por Categoria", font: { size: 15 } };
    layout.barmode = "stack";
    layout.xaxis.title = "Ano";
    layout.yaxis.title = fluxo + " (USD FOB)";
    layout.yaxis.tickformat = "$,.0f";
    layout.height = 460;
    Plotly.newPlot(divId, traces, layout, { displayModeBar: true, responsive: true });
}

function renderHeatmap(divId, fluxo) {
    const d = DATA.filter(x => x.Fluxo === fluxo);
    const total = d.reduce((s, x) => s + x.Valor, 0);
    if (total === 0) {
        plotVazio(divId, "Nenhum dado de " + fluxo + " para exibir no heatmap");
        return;
    }
    const anosSet = [...new Set(d.map(x => x.Ano))].sort((a, b) => a - b);
    const z = [], text = [];
    for (const ncm of NCMS) {
        const rowZ = [], rowT = [];
        for (const ano of anosSet) {
            const v = d.filter(x => x.Label === ncm && x.Ano === ano)
                       .reduce((s, x) => s + x.Valor, 0);
            rowZ.push(v > 0 ? v : null);
            rowT.push(v > 0 ? fmtUsd(v) : "\u2014");
        }
        z.push(rowZ); text.push(rowT);
    }
    const trace = {
        z: z, x: anosSet.map(String), y: NCMS, type: "heatmap",
        colorscale: [
            [0.0, "#1C2128"], [0.15, "#1D4ED8"], [0.4, "#0EA5E9"],
            [0.65, "#22C55E"], [0.85, "#F59E0B"], [1.0, "#EF4444"],
        ],
        text: text, texttemplate: "%{text}",
        textfont: { size: 11, color: TEXTO },
        hoverongaps: false,
        hovertemplate: "<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
        colorbar: { title: { text: "USD FOB", font: { color: TEXTO2 } },
                    tickfont: { color: TEXTO2 }, bgcolor: BG2,
                    bordercolor: BORDA, outlinecolor: BORDA },
        zmin: 0,
    };
    const layout = layoutBase();
    layout.title = { text: "Heatmap \u2014 Intensidade de " + fluxo + "s por Categoria e Ano", font: { size: 15 } };
    layout.xaxis = { title: "Ano", gridcolor: BORDA, tickfont: { color: TEXTO2 } };
    layout.yaxis = { gridcolor: BORDA, tickfont: { color: TEXTO, size: 10 } };
    layout.margin = { t: 70, b: 50, l: 190, r: 30 };
    layout.height = 340;
    Plotly.newPlot(divId, [trace], layout, { displayModeBar: true, responsive: true });
}

function renderDonut(divId, fluxo, ano) {
    const d = DATA.filter(x => x.Ano === ano && x.Fluxo === fluxo && x.Valor > 0);
    if (d.length === 0) {
        plotVazio(divId, "Nenhum dado de " + fluxo + " em " + ano);
        return;
    }
    const labels = d.map(x => x.Label);
    const values = d.map(x => x.Valor);
    const cores = labels.map(l => CORES_CAT[l]);
    const trace = {
        labels: labels, values: values, type: "pie", hole: 0.48,
        marker: { colors: cores, line: { color: BG, width: 2 } },
        textinfo: "label+percent",
        textfont: { color: TEXTO, size: 11 },
        customdata: values.map(fmtUsd),
        hovertemplate: "<b>%{label}</b><br>%{customdata}<br>%{percent}<extra></extra>",
    };
    const layout = layoutBase();
    delete layout.legend;
    layout.title = { text: "Participa\u00e7\u00e3o nas " + fluxo + "s \u2014 " + ano, font: { size: 15 } };
    layout.showlegend = true;
    layout.legend = { orientation: "v", x: 1.01, y: 0.5, font: { color: TEXTO, size: 11 } };
    layout.height = 420;
    Plotly.newPlot(divId, [trace], layout, { displayModeBar: true, responsive: true });
}

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
    renderSaldo("graph-saldo", ncmSel, anoMin, anoMax);

    const compFluxo = document.getElementById("comp-fluxo").value;
    renderComposicao("graph-composicao", compFluxo, ncmSel, anoMin, anoMax);

    const hmFluxo = document.getElementById("hm-fluxo").value;
    renderHeatmap("graph-heatmap", hmFluxo);

    const donutFluxo = document.getElementById("donut-fluxo").value;
    const donutAno = parseInt(document.getElementById("donut-ano").value);
    renderDonut("graph-donut", donutFluxo, donutAno);
}

function toggleSection(key, visible) {
    const el = document.getElementById("section-" + key);
    if (el) el.style.display = visible ? "" : "none";
}

document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll(".ncm-check").forEach(el => {
        el.addEventListener("change", renderAll);
    });
    document.getElementById("ano-min").addEventListener("input", () => { updateAnoLabel(); renderAll(); });
    document.getElementById("ano-max").addEventListener("input", () => { updateAnoLabel(); renderAll(); });
    document.getElementById("comp-fluxo").addEventListener("change", renderAll);
    document.getElementById("hm-fluxo").addEventListener("change", renderAll);
    document.getElementById("donut-fluxo").addEventListener("change", renderAll);
    document.getElementById("donut-ano").addEventListener("change", renderAll);
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
        .replace("__CORES_JSON__", cores_json)
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

    ncm_checkboxes = "".join(
        f'<label class="chk"><input type="checkbox" class="ncm-check" value="{ncm}" checked> {ncm}</label>'
        for ncm in NCMS
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
header p{{color:{TEXTO2};font-size:.82rem;margin-top:5px;white-space:pre-line}}
main{{max-width:1200px;margin:0 auto;padding:20px 24px;display:flex;flex-direction:column;gap:20px}}
.card{{background:{BG2};border:1px solid {BORDA};border-radius:12px;padding:20px 16px}}
.card h2, .card h3{{font-size:.75rem;font-weight:600;color:{TEXTO2};text-transform:uppercase;letter-spacing:.6px;margin-bottom:10px}}
footer{{text-align:center;padding:20px;color:{TEXTO2};font-size:.78rem;border-top:1px solid {BORDA};margin-top:8px}}

.controls{{display:grid;grid-template-columns:1.4fr 1.2fr 1fr;gap:20px;align-items:start}}
.control-group label.title{{display:block;color:{TEXTO2};font-size:.72rem;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}}
.chk{{display:inline-flex;align-items:center;gap:5px;background:{BG3};border:1px solid {BORDA};
      border-radius:6px;padding:5px 9px;margin:0 6px 6px 0;font-size:.78rem;cursor:pointer;color:{TEXTO}}}
.chk input{{accent-color:#3B82F6;cursor:pointer}}

select{{
    background:{BG3};color:{TEXTO};border:1px solid {BORDA};border-radius:8px;
    padding:7px 10px;font-size:.85rem;font-family:inherit;cursor:pointer;
}}
select:focus{{outline:1px solid #3B82F6}}

.range-wrap{{position:relative;height:36px;margin-top:6px}}
.range-track-rail{{position:absolute;top:16px;left:0;right:0;height:4px;
    background:{BORDA};border-radius:2px;pointer-events:none;}}
.range-track-fill{{position:absolute;top:16px;height:4px;background:#3B82F6;
    border-radius:2px;pointer-events:none;}}
.range-wrap input[type=range]{{
    position:absolute;top:12px;left:0;width:100%;margin:0;
    -webkit-appearance:none;appearance:none;background:transparent;pointer-events:none;
}}
.range-wrap input[type=range]::-webkit-slider-thumb{{
    -webkit-appearance:none;appearance:none;pointer-events:auto;
    width:16px;height:16px;border-radius:50%;background:{BG2};
    border:3px solid #3B82F6;cursor:pointer;margin-top:-6px;position:relative;z-index:2;
}}
.range-wrap input[type=range]::-moz-range-thumb{{
    pointer-events:auto;width:16px;height:16px;border-radius:50%;
    background:{BG2};border:3px solid #3B82F6;cursor:pointer;z-index:2;
}}
.range-wrap input[type=range]::-webkit-slider-runnable-track{{
    height:4px;background:transparent;border-radius:2px;
}}
.range-wrap input[type=range]::-moz-range-track{{
    height:4px;background:transparent;border-radius:2px;
}}
#ano-range-label{{color:{TEXTO};font-size:.85rem;font-weight:600}}

.inline-controls{{display:flex;gap:12px;margin-bottom:10px;flex-wrap:wrap;align-items:end}}
.inline-controls .field label{{display:block;color:{TEXTO2};font-size:.72rem;
    text-transform:uppercase;letter-spacing:.5px;margin-bottom:5px}}
</style>
</head>
<body>

<header>
  <h1>Comércio Exterior de Armas de Fogo — Brasil (2020–2026)</h1>
  <p>{header_html}</p>
</header>

<main>

  <div class="card">
    <div class="controls">
      <div class="control-group">
        <label class="title">Visualizações ativas</label>
        {viz_checkboxes}
      </div>
      <div class="control-group">
        <label class="title">Categorias (NCM)</label>
        {ncm_checkboxes}
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
    <div id="graph-saldo"></div>
  </div>

  <div class="card" id="section-composicao">
    <h2>📦 Composição por Fluxo</h2>
    <div class="inline-controls">
      <div class="field">
        <label>Fluxo</label>
        <select id="comp-fluxo">
          <option value="Exportação">Exportação</option>
          <option value="Importação">Importação</option>
        </select>
      </div>
    </div>
    <div id="graph-composicao"></div>
  </div>

  <div class="card" id="section-heatmap">
    <h2>🌡️ Heatmap de Intensidade</h2>
    <div class="inline-controls">
      <div class="field">
        <label>Fluxo</label>
        <select id="hm-fluxo">
          <option value="Exportação">Exportação</option>
          <option value="Importação">Importação</option>
        </select>
      </div>
    </div>
    <div id="graph-heatmap"></div>
  </div>

  <div class="card" id="section-donut">
    <h2>🥧 Participação por Ano</h2>
    <div class="inline-controls">
      <div class="field">
        <label>Fluxo</label>
        <select id="donut-fluxo">
          <option value="Exportação">Exportação</option>
          <option value="Importação">Importação</option>
        </select>
      </div>
      <div class="field">
        <label>Ano</label>
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
        "✅ docs/index.html gerado — interativo, sem servidor, mesmos filtros do Dash"
    )


if __name__ == "__main__":
    if "--export" in sys.argv:
        exportar_html_estatico()
    else:
        rodar_dash()
