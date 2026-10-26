"""Acesso aos dados do DuckDB para o app (somente leitura, com cache)."""
from __future__ import annotations

import os
from pathlib import Path

import duckdb
import pandas as pd
import streamlit as st
import yaml

RAIZ = Path(__file__).resolve().parents[1]
CAMINHO_BANCO = Path(os.environ.get("ECON_DB", RAIZ / "data" / "econ.duckdb"))


def _consultar(sql: str, params: list | None = None) -> pd.DataFrame:
    # Conexão curta: no Windows o arquivo fica travado enquanto houver uma conexão aberta,
    # e isso impediria a carga (pipeline.carga) de gravar com o app aberto.
    with duckdb.connect(str(CAMINHO_BANCO), read_only=True) as con:
        return con.execute(sql, params or []).df()


def checar_banco() -> None:
    if not CAMINHO_BANCO.exists():
        st.error(
            f"Banco não encontrado em `{CAMINHO_BANCO}`. Rode a carga primeiro:\n\n"
            "`python -m pipeline.carga`"
        )
        st.stop()


@st.cache_data(ttl=3600)
def dim_serie() -> pd.DataFrame:
    return _consultar("SELECT * FROM silver.dim_serie ORDER BY nome_area, nome")


@st.cache_data(ttl=3600)
def serie(id_serie: str) -> pd.Series:
    df = _consultar("SELECT data, valor FROM silver.serie WHERE id = ? ORDER BY data", [id_serie])
    return pd.Series(df["valor"].values, index=pd.to_datetime(df["data"]), name=id_serie)


@st.cache_data(ttl=3600)
def serie_futura(id_serie: str) -> pd.Series:
    df = _consultar("SELECT data, valor FROM silver.serie_futura WHERE id = ? ORDER BY data", [id_serie])
    return pd.Series(df["valor"].values, index=pd.to_datetime(df["data"]), name=id_serie)


@st.cache_data(ttl=3600)
def ultima_carga():
    df = _consultar("SELECT max(dat_carga) AS dat FROM raw.log_carga WHERE status = 'ok'")
    return df["dat"].iloc[0]


@st.cache_data
def metas_inflacao() -> pd.DataFrame:
    with open(RAIZ / "catalogo" / "metas_inflacao.yaml", encoding="utf-8") as f:
        return pd.DataFrame(yaml.safe_load(f)["metas"])
