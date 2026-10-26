"""Leitura do catálogo de indicadores (catalogo/indicadores.yaml)."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

CAMINHO = Path(__file__).resolve().parents[1] / "catalogo" / "indicadores.yaml"
CAMPOS_OBRIGATORIOS = ["id", "nome", "fonte", "cod_fonte", "area", "unidade", "periodicidade"]


def carregar_catalogo(caminho: Path = CAMINHO) -> dict:
    with open(caminho, encoding="utf-8") as f:
        catalogo = yaml.safe_load(f)

    ids = [ind["id"] for ind in catalogo["indicadores"]]
    repetidos = {i for i in ids if ids.count(i) > 1}
    if repetidos:
        raise ValueError(f"ids repetidos no catálogo: {sorted(repetidos)}")
    for ind in catalogo["indicadores"]:
        faltando = [c for c in CAMPOS_OBRIGATORIOS if c not in ind]
        if faltando:
            raise ValueError(f"indicador {ind.get('id')}: faltam os campos {faltando}")
        if ind["area"] not in catalogo["areas"]:
            raise ValueError(f"indicador {ind['id']}: área desconhecida '{ind['area']}'")
        for rel in ind.get("se_relaciona_com", []):
            if rel not in ids:
                raise ValueError(f"indicador {ind['id']}: se_relaciona_com aponta para '{rel}', que não existe")
    return catalogo


def dim_serie(catalogo: dict) -> pd.DataFrame:
    """Uma linha por indicador, com os textos de estudo (vira silver.dim_serie)."""
    df = pd.DataFrame(catalogo["indicadores"])
    df["nome_area"] = df["area"].map(catalogo["areas"])
    df["se_relaciona_com"] = df["se_relaciona_com"].apply(lambda v: ", ".join(v) if isinstance(v, list) else None)
    colunas = [
        "id", "nome", "fonte", "cod_fonte", "fonte_original", "area", "nome_area",
        "unidade", "periodicidade", "o_que_e", "por_que_importa", "como_ler", "se_relaciona_com",
    ]
    for c in colunas:
        if c not in df:
            df[c] = None
    for c in ["o_que_e", "por_que_importa", "como_ler"]:
        df[c] = df[c].str.strip()
    return df[colunas]
