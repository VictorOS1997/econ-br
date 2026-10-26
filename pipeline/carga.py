"""Carga das séries do catálogo para o DuckDB (camadas raw e silver).

Uso:
    python -m pipeline.carga                       # incremental, todas as séries
    python -m pipeline.carga --ids selic_meta ipca # só algumas
    python -m pipeline.carga --completa            # baixa tudo de novo desde o início

Camadas:
    raw.sgs             valores como vieram da API (texto), 1 linha por série × data
    raw.log_carga       histórico de cada execução, série a série
    silver.dim_serie    o catálogo, com os textos de estudo
    silver.serie        valores tipados, só até hoje (5ª proteção: corta as datas futuras)
    silver.serie_futura valores já programados (ex.: Selic meta vigente até a próxima reunião)
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import duckdb
import requests

from ingest import sgs
from pipeline.catalogo import carregar_catalogo, dim_serie

CAMINHO_BANCO = Path(os.environ.get("ECON_DB", Path(__file__).resolve().parents[1] / "data" / "econ.duckdb"))

# Na carga incremental, baixa de novo esta janela para pegar as revisões
# (PIB, IBC-Br e crédito costumam ser revisados meses depois).
JANELA_REVISAO = timedelta(days=400)

DDL = """
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS silver;

CREATE TABLE IF NOT EXISTS raw.sgs (
    cod_fonte  INTEGER   NOT NULL,
    data       DATE      NOT NULL,
    valor      VARCHAR,
    dat_carga  TIMESTAMP NOT NULL,
    PRIMARY KEY (cod_fonte, data)
);

CREATE TABLE IF NOT EXISTS raw.log_carga (
    dat_carga  TIMESTAMP NOT NULL,
    id         VARCHAR   NOT NULL,
    inicio     DATE,
    fim        DATE,
    qtd_linhas INTEGER,
    status     VARCHAR   NOT NULL,
    erro       VARCHAR
);
"""

VIEWS = """
CREATE OR REPLACE VIEW silver.serie_todas AS
SELECT d.id, r.data, TRY_CAST(r.valor AS DOUBLE) AS valor, r.dat_carga
FROM raw.sgs r
JOIN silver.dim_serie d ON d.fonte = 'sgs' AND d.cod_fonte = r.cod_fonte
WHERE TRY_CAST(r.valor AS DOUBLE) IS NOT NULL;

CREATE OR REPLACE VIEW silver.serie AS
SELECT id, data, valor FROM silver.serie_todas WHERE data <= current_date;

CREATE OR REPLACE VIEW silver.serie_futura AS
SELECT id, data, valor FROM silver.serie_todas WHERE data > current_date;
"""


def conectar(caminho: Path = CAMINHO_BANCO) -> duckdb.DuckDBPyConnection:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(caminho))
    con.execute(DDL)
    return con


def _inicio_da_carga(con, cod_fonte: int, inicio_padrao: date, completa: bool) -> date:
    if completa:
        return inicio_padrao
    ultima = con.execute(
        "SELECT max(data) FROM raw.sgs WHERE cod_fonte = ? AND data <= current_date", [cod_fonte]
    ).fetchone()[0]
    if ultima is None:
        return inicio_padrao
    return max(inicio_padrao, ultima - JANELA_REVISAO)


def carregar(ids: list[str] | None = None, completa: bool = False, caminho: Path = CAMINHO_BANCO) -> bool:
    """Carrega as séries e devolve True se todas deram certo."""
    catalogo = carregar_catalogo()
    inicio_padrao = catalogo["inicio_padrao"]
    indicadores = [i for i in catalogo["indicadores"] if ids is None or i["id"] in ids]
    if ids:
        desconhecidos = set(ids) - {i["id"] for i in indicadores}
        if desconhecidos:
            raise SystemExit(f"ids que não estão no catálogo: {sorted(desconhecidos)}")

    con = conectar(caminho)
    df_dim = dim_serie(catalogo)
    con.execute("CREATE OR REPLACE TABLE silver.dim_serie AS SELECT * FROM df_dim")
    con.execute(VIEWS)

    sessao = requests.Session()
    agora = datetime.now()
    falhas = []
    for ind in indicadores:
        if ind["fonte"] != "sgs":
            print(f"  -  {ind['id']:<16} fonte '{ind['fonte']}' ainda não implementada, pulando")
            continue
        inicio = _inicio_da_carga(con, ind["cod_fonte"], inicio_padrao, completa)
        try:
            df = sgs.baixar_serie(ind["cod_fonte"], inicio, sessao=sessao)
            df["cod_fonte"] = ind["cod_fonte"]
            df["dat_carga"] = agora
            con.execute(
                "INSERT OR REPLACE INTO raw.sgs SELECT cod_fonte, data, valor, dat_carga FROM df"
            )
            fim = df["data"].max() if len(df) else None
            con.execute(
                "INSERT INTO raw.log_carga VALUES (?, ?, ?, ?, ?, 'ok', NULL)",
                [agora, ind["id"], inicio, fim, len(df)],
            )
            print(f"  ok {ind['id']:<16} {len(df):>6} linhas desde {inicio:%d/%m/%Y}")
        except sgs.ErroSGS as e:
            falhas.append(ind["id"])
            con.execute(
                "INSERT INTO raw.log_carga VALUES (?, ?, ?, NULL, 0, 'erro', ?)",
                [agora, ind["id"], inicio, str(e)],
            )
            print(f"  XX {ind['id']:<16} {e}")

    con.close()
    if falhas:
        print(f"\n{len(falhas)} série(s) com erro: {', '.join(falhas)}. Rode de novo para tentar só elas: "
              f"python -m pipeline.carga --ids {' '.join(falhas)}")
    return not falhas


def main() -> None:
    parser = argparse.ArgumentParser(description="Carga das séries do catálogo para o DuckDB")
    parser.add_argument("--ids", nargs="+", help="ids do catálogo (padrão: todos)")
    parser.add_argument("--completa", action="store_true", help="ignora o incremental e baixa tudo")
    args = parser.parse_args()
    sys.stdout.reconfigure(line_buffering=True)  # mostra o progresso na hora, mesmo com a saída redirecionada
    print(f"Banco: {CAMINHO_BANCO}")
    sys.exit(0 if carregar(args.ids, args.completa) else 1)


if __name__ == "__main__":
    main()
