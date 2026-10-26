"""Gráficos Plotly no padrão do projeto: linhas finas, um eixo y por gráfico, hover unificado."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from calculos import RECESSOES

# Paleta categórica em ordem fixa (validada para daltonismo nos pares adjacentes)
CORES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
COR_META = "#898781"


def _fmt(unidade: str) -> str:
    return ",.0f" if unidade.endswith("milhões") else ",.2f"


def _layout(fig: go.Figure, altura: int) -> go.Figure:
    fig.update_layout(
        height=altura,
        margin=dict(l=8, r=8, t=32, b=8),
        hovermode="x unified",
        separators=",.",  # decimal com vírgula
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False, showspikes=True, spikemode="across", spikethickness=1)
    fig.update_yaxes(gridwidth=1, zeroline=True, zerolinewidth=1)
    return fig


def _recessoes(fig: go.Figure, inicio: pd.Timestamp, fim: pd.Timestamp, **kw) -> None:
    for ini, fim_r, nome in RECESSOES:
        ini, fim_r = pd.Timestamp(ini), pd.Timestamp(fim_r)
        if fim_r < inicio or ini > fim:
            continue
        fig.add_vrect(
            x0=max(ini, inicio), x1=min(fim_r, fim), fillcolor="#898781", opacity=0.12,
            line_width=0, layer="below", **kw,
        )


def linha(s: pd.Series, unidade: str, recessoes: bool = True, meta: pd.DataFrame | None = None,
          futuro: pd.Series | None = None, altura: int = 440) -> go.Figure:
    fig = go.Figure()
    if meta is not None:
        fig.add_trace(go.Scatter(x=meta.index, y=meta["teto"], line=dict(width=0), hoverinfo="skip"))
        fig.add_trace(go.Scatter(
            x=meta.index, y=meta["piso"], line=dict(width=0), fill="tonexty",
            fillcolor="rgba(137,135,129,0.18)", hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=meta.index, y=meta["meta"], name="Meta", line=dict(color=COR_META, width=1, dash="dash"),
            hovertemplate="Meta: %{y:.2f}<extra></extra>",
        ))
    fig.add_trace(go.Scatter(
        x=s.index, y=s.values, name=unidade, line=dict(color=CORES[0], width=2),
        hovertemplate=f"%{{y:{_fmt(unidade)}}} {unidade}<extra></extra>",
    ))
    if futuro is not None and not futuro.empty:
        fig.add_trace(go.Scatter(
            x=futuro.index, y=futuro.values, name="Programado", line=dict(color=CORES[0], width=2, dash="dot"),
            hovertemplate=f"Programado: %{{y:{_fmt(unidade)}}}<extra></extra>",
        ))
    if recessoes and len(s):
        _recessoes(fig, s.index.min(), s.index.max())
    fig.update_yaxes(title_text=unidade, tickformat=_fmt(unidade).replace(".2f", ".1f"))
    return _layout(fig, altura)


def paineis(series: list[tuple[str, pd.Series, str]], recessoes: bool = True) -> go.Figure:
    """Pequenos múltiplos: um painel por série, todos com o mesmo eixo de tempo (nunca dois eixos y)."""
    n = len(series)
    fig = make_subplots(rows=n, cols=1, shared_xaxes=True, vertical_spacing=0.06,
                        subplot_titles=[f"{nome} ({unidade})" for nome, _, unidade in series])
    inicio = min(s.index.min() for _, s, _ in series)
    fim = max(s.index.max() for _, s, _ in series)
    for i, (nome, s, unidade) in enumerate(series, start=1):
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=nome, line=dict(color=CORES[(i - 1) % len(CORES)], width=2),
            hovertemplate=f"{nome}: %{{y:{_fmt(unidade)}}} {unidade}<extra></extra>",
        ), row=i, col=1)
        if recessoes:
            _recessoes(fig, inicio, fim, row=i, col=1)
    fig.update_annotations(font_size=13, x=0, xanchor="left")
    return _layout(fig, 220 * n + 40)
