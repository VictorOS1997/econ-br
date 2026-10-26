"""Transformações das séries (acumulado em 12 meses, variações, mudança de granularidade).

Na Semana 2 essas contas vão para a camada gold do DuckDB; por enquanto ficam aqui.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# Recessões datadas pelo CODACE (Comitê de Datação de Ciclos Econômicos, FGV), por trimestre.
RECESSOES = [
    ("2001-04-01", "2001-12-31", "Crise de energia (apagão)"),
    ("2003-01-01", "2003-06-30", "Ajuste após a crise de confiança de 2002"),
    ("2008-10-01", "2009-03-31", "Crise financeira global"),
    ("2014-04-01", "2016-12-31", "Recessão de 2014–2016"),
    ("2020-01-01", "2020-06-30", "Pandemia de covid-19"),
]

TRANSFORMACOES = {
    # "% no mês" (IPCA, IGP-M): o mês isolado oscila; o acumulado em 12 meses é o que importa
    "fluxo_pct": ["Acumulado em 12 meses", "Variação no mês"],
    # taxas e razões (Selic, desemprego, dívida/PIB): comparar em pontos percentuais
    "taxa": ["Valor", "Diferença em 12 meses (p.p.)"],
    # níveis (índices, R$, US$): comparar em variação percentual
    "nivel": ["Valor", "Variação em 12 meses (%)"],
}


def br(x: float, casas: int = 2) -> str:
    """Formata no padrão brasileiro: 1.234,56."""
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def ha_um_ano(s: pd.Series) -> float:
    """Valor da série na mesma data um ano antes da última observação (ou o anterior mais próximo)."""
    return s.asof(s.index.max() - pd.DateOffset(years=1))


def tipo(unidade: str) -> str:
    if unidade.startswith("% no mês"):
        return "fluxo_pct"
    if "%" in unidade:
        return "taxa"
    return "nivel"


def mensal(s: pd.Series) -> pd.Series:
    """Leva uma série diária para mensal: valor do último dia útil, datado no dia 1º do mês."""
    return s.resample("MS").last().dropna()


def acumulado_12m(s: pd.Series) -> pd.Series:
    """Composição de 12 variações mensais: (1+a)(1+b)...(1+l) - 1."""
    return ((1 + s / 100).rolling(12).apply(np.prod, raw=True) - 1).mul(100).dropna()


def _ha_um_ano(s: pd.Series) -> pd.Series:
    return s.shift(freq=pd.DateOffset(years=1)).reindex(s.index)


def variacao_12m(s: pd.Series) -> pd.Series:
    return ((s / _ha_um_ano(s) - 1) * 100).dropna()


def diferenca_12m(s: pd.Series) -> pd.Series:
    return (s - _ha_um_ano(s)).dropna()


def aplicar(s: pd.Series, unidade: str, transformacao: str, granularidade: str) -> tuple[pd.Series, str]:
    """Devolve a série transformada e a unidade resultante."""
    if transformacao == "Acumulado em 12 meses":
        return acumulado_12m(s), "% em 12 meses"
    if transformacao == "Variação em 12 meses (%)":
        return variacao_12m(mensal(s)), "% em 12 meses"
    if transformacao == "Diferença em 12 meses (p.p.)":
        return diferenca_12m(mensal(s)), "p.p. em 12 meses"
    if granularidade == "Mensal":
        return mensal(s), unidade
    return s, unidade


def meta_mensal(metas: pd.DataFrame, indice: pd.DatetimeIndex) -> pd.DataFrame:
    """Meta de inflação e banda de tolerância para cada data do índice."""
    m = metas.set_index("ano").reindex(indice.year)
    m.index = indice
    return pd.DataFrame({
        "meta": m["meta"],
        "piso": m["meta"] - m["tolerancia"],
        "teto": m["meta"] + m["tolerancia"],
    })
