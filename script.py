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
    "Outras Armas (pólvora)": "#FBBF24",
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
        margin=dict(t=70, b=50, l=70, r=30),
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
                marker=dict(
                    color=cor,
                    opacity=0.85,
                    pattern=dict(
                        shape=["/" if v < 0 else "" for v in sub["Saldo"]],
                        fgcolor="rgba(255,255,255,0.25)",
                        size=6,
                    ),
                    line=dict(color=cor, width=0),
                ),
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
/* ── Dropdown wrapper (caixa fechada) ── */
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
/* ── Placeholder e valor ── */
.dash-dropdown-placeholder {{ color: {TEXTO2} !important; }}
.dash-dropdown-value {{ color: {TEXTO} !important; }}
/* ── Tags multi-select ── */
.dash-dropdown-value-item {{
    background: {BG2} !important;
    border: 1px solid {BORDA} !important;
    border-radius: 4px !important;
    color: {TEXTO} !important;
    font-size: 12px !important;
}}
/* ── Contador "N selected" ── */
.dash-dropdown-value-count {{
    background: {BG2} !important;
    color: {TEXTO2} !important;
    border: 1px solid {BORDA} !important;
    border-radius: 4px !important;
    padding: 1px 7px !important;
    font-size: 12px !important;
}}
/* ── Ícone seta/clear ── */
.dash-dropdown-trigger-icon svg,
.dash-dropdown-trigger-icon svg path,
.dash-dropdown-trigger-icon svg polyline {{
    stroke: {TEXTO2} !important;
    fill: none !important;
}}
.dash-dropdown-clear {{ color: {TEXTO2} !important; }}
/* ── Painel de opções aberto ── */
.dash-dropdown-content {{
    background: {BG3} !important;
    border: 1px solid {BORDA} !important;
    border-radius: 8px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.7) !important;
    z-index: 9999 !important;
}}
/* ── Cada opção ── */
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
/* ── Barra de busca ── */
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
/* ── Grid container (multi) ── */
.dash-dropdown-grid-container {{
    background: {BG3} !important;
}}
/* ── Ações (clear all, etc.) ── */
.dash-dropdown-actions {{ background: {BG3} !important; border-top: 1px solid {BORDA} !important; }}
.dash-dropdown-action-button {{ color: {TEXTO2} !important; }}
.dash-dropdown-action-button:hover {{ color: {TEXTO} !important; }}
/* ── Body e root ── */
body, #react-entry-point, ._dash-loading {{
    background-color: {BG} !important;
}}
/* ── RangeSlider track e handle ── */
.rc-slider-track {{ background-color: #3B82F6 !important; }}
.rc-slider-handle {{ border-color: #3B82F6 !important; background: {BG2} !important; }}
.rc-slider-rail {{ background-color: {BORDA} !important; }}
/* ── Tooltip do RangeSlider (classe real: dash-slider-tooltip + CSS vars) ── */
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
                        (
                            "Fonte: Comex Stat / MDIC · USD FOB · NCMs: \n93020000 (Revólveres e pistolas, exceto os das posições 93.03 ou 93.04.)"
                            "\n93032000 (Outras espingardas e carabinas de caça ou de tiro ao alvo, com pelo menos um cano lisoOutras espingardas e carabinas de caça ou de tiro ao alvo, com pelo menos um cano liso)"
                            "\n93033000 (Outras espingardas e carabinas de caça ou de tiro ao alvo)"
                            "\n93039090 (Outras armas de fogo que utilizam deflagração da pólvora, etc.)"
                        ),
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
    os.makedirs("docs", exist_ok=True)
    ano_default = int(ANOS[-1])
    graficos_export = [
        ("📈 Evolução Total", fig_evolucao()),
        ("⚖️ Saldo Comercial", fig_saldo()),
        ("📦 Composição — Exportações", fig_composicao("Exportação")),
        ("📦 Composição — Importações", fig_composicao("Importação")),
        ("🌡️ Heatmap — Exportações", fig_heatmap("Exportação")),
        ("🌡️ Heatmap — Importações", fig_heatmap("Importação")),
        (
            f"🥧 Participação Exportações {ano_default}",
            fig_donut("Exportação", ano_default),
        ),
        (
            f"🥧 Participação Importações {ano_default}",
            fig_donut("Importação", ano_default),
        ),
    ]
    divs_html = ""
    for i, (titulo, fig) in enumerate(graficos_export):
        fig.update_layout(height=480)
        div = fig.to_html(full_html=False, include_plotlyjs=(i == 0))
        divs_html += f'<section class="card"><h2>{titulo}</h2>{div}</section>'

    page = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Comércio Exterior — Armas de Fogo</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{BG};color:{TEXTO};font-family:'Inter','Segoe UI',Arial,sans-serif;line-height:1.5}}
header{{background:{BG2};border-bottom:1px solid {BORDA};padding:24px 40px}}
header h1{{font-size:1.5rem;font-weight:700}}
header p{{color:{TEXTO2};font-size:.85rem;margin-top:6px}}
main{{max-width:1240px;margin:0 auto;padding:28px 20px;display:flex;flex-direction:column;gap:24px}}
.card{{background:{BG2};border:1px solid {BORDA};border-radius:12px;padding:22px 18px}}
.card h2{{font-size:.75rem;font-weight:600;color:{TEXTO2};text-transform:uppercase;letter-spacing:.6px;margin-bottom:14px}}
footer{{text-align:center;padding:20px;color:{TEXTO2};font-size:.78rem;border-top:1px solid {BORDA};margin-top:8px}}
</style>
</head>
<body>
<header>
  <h1>🔫 Comércio Exterior de Armas de Fogo — Brasil (2020–2026)</h1>
  <p>Fonte: Comex Stat / MDIC · USD FOB · NCMs: 93020000 · 93032000 · 93033000 · 93039090</p>
</header>
<main>{divs_html}</main>
<footer>Grupo de Pesquisa · dados_small_arms.xlsx</footer>
</body></html>"""

    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(page)
    print("✅ docs/index.html gerado")


if __name__ == "__main__":
    if "--export" in sys.argv:
        exportar_html_estatico()
    else:
        rodar_dash()
