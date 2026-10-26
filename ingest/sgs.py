"""Cliente da API SGS do Banco Central (Sistema Gerenciador de Séries Temporais).

Proteções contra os comportamentos observados na API (26/10/2026):
1. sempre envia dataInicial/dataFinal (o atalho /ultimos/N falha em algumas séries)
   e quebra o período em janelas de até 10 anos (limite da API);
2. tenta de novo com espera crescente (timeouts e 502 são intermitentes) e faz uma pausa
   entre as chamadas (rajadas de chamadas causam bloqueios temporários de alguns minutos);
3. exige Content-Type JSON (a API às vezes devolve "200 OK" com uma página HTML de erro,
   que é como o bloqueio temporário aparece);
4. ordena por data e remove duplicatas (a ordem não é garantida).
O corte de datas futuras (5ª proteção) fica na camada silver: ver pipeline/carga.py.
"""
from __future__ import annotations

import time
from datetime import date, timedelta

import pandas as pd
import requests

URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados"
MAX_ANOS_POR_CHAMADA = 10
PAUSA_ENTRE_CHAMADAS = 1.0  # segundos
ESPERA_MAXIMA = 60.0  # teto da espera entre tentativas, em segundos


class ErroSGS(RuntimeError):
    """Falha definitiva ao baixar uma série (depois de esgotar as tentativas)."""


def _somar_anos(d: date, anos: int) -> date:
    try:
        return d.replace(year=d.year + anos)
    except ValueError:  # 29/02 caindo em ano não bissexto
        return d.replace(year=d.year + anos, day=28)


def janelas(inicio: date, fim: date, anos: int = MAX_ANOS_POR_CHAMADA) -> list[tuple[date, date]]:
    """Quebra [inicio, fim] em janelas consecutivas de no máximo `anos` anos."""
    resultado = []
    atual = inicio
    while atual <= fim:
        limite = min(fim, _somar_anos(atual, anos) - timedelta(days=1))
        resultado.append((atual, limite))
        atual = limite + timedelta(days=1)
    return resultado


def _baixar_janela(
    sessao: requests.Session,
    codigo: int,
    inicio: date,
    fim: date,
    tentativas: int = 6,
    espera: float = 5.0,
) -> list[dict]:
    params = {
        "formato": "json",
        "dataInicial": inicio.strftime("%d/%m/%Y"),
        "dataFinal": fim.strftime("%d/%m/%Y"),
    }
    ultimo_erro: Exception | None = None
    for tentativa in range(1, tentativas + 1):
        time.sleep(PAUSA_ENTRE_CHAMADAS)
        try:
            r = sessao.get(URL.format(codigo=codigo), params=params, timeout=60)
            eh_json = "json" in r.headers.get("Content-Type", "")
            # 404 em JSON = "Value(s) not found": a janela simplesmente não tem dados
            if r.status_code == 404 and eh_json:
                return []
            r.raise_for_status()
            if not eh_json:
                raise ErroSGS("resposta não é JSON (provável página de erro com status 200)")
            return r.json()
        except (requests.RequestException, ErroSGS, ValueError) as e:
            ultimo_erro = e
            if tentativa < tentativas:
                time.sleep(min(ESPERA_MAXIMA, espera * 2 ** (tentativa - 1)))  # 5, 10, 20, 40, 60 s
    raise ErroSGS(
        f"série {codigo} ({inicio:%d/%m/%Y} a {fim:%d/%m/%Y}): "
        f"falhou após {tentativas} tentativas: {ultimo_erro}"
    )


def baixar_serie(
    codigo: int,
    inicio: date,
    fim: date | None = None,
    sessao: requests.Session | None = None,
    **kwargs,
) -> pd.DataFrame:
    """Baixa a série `codigo` entre `inicio` e `fim` (padrão: hoje + 1 ano, para pegar
    valores já programados, como a Selic meta vigente até a próxima reunião do Copom).

    Devolve um DataFrame com as colunas `data` (date) e `valor` (texto, como veio da API),
    ordenado por data e sem duplicatas.
    """
    fim = fim or _somar_anos(date.today(), 1)
    sessao = sessao or requests.Session()
    linhas: list[dict] = []
    for ini_janela, fim_janela in janelas(inicio, fim):
        linhas.extend(_baixar_janela(sessao, codigo, ini_janela, fim_janela, **kwargs))

    df = pd.DataFrame(linhas, columns=["data", "valor"])
    df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y").dt.date
    return (
        df.drop_duplicates(subset="data", keep="last")
        .sort_values("data")
        .reset_index(drop=True)
    )
