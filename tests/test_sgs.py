"""Testes do cliente SGS sem internet: cada caso simula um comportamento real da API."""
from datetime import date

import pytest
import requests

from ingest import sgs
from pipeline.catalogo import carregar_catalogo, dim_serie


class RespostaFalsa:
    def __init__(self, status=200, tipo="application/json; charset=utf-8", corpo=None, texto=""):
        self.status_code = status
        self.headers = {"Content-Type": tipo}
        self._corpo = corpo
        self.text = texto

    def json(self):
        return self._corpo

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


class SessaoFalsa:
    """Devolve as respostas na ordem e guarda os parâmetros de cada chamada."""

    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.chamadas = []

    def get(self, url, params=None, timeout=None):
        self.chamadas.append(params)
        resposta = self.respostas.pop(0)
        if isinstance(resposta, Exception):
            raise resposta
        return resposta


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch):
    monkeypatch.setattr(sgs.time, "sleep", lambda s: None)


def test_janelas_respeitam_10_anos():
    js = sgs.janelas(date(2000, 1, 1), date(2026, 10, 26))
    assert js[0] == (date(2000, 1, 1), date(2009, 12, 31))
    assert js[1] == (date(2010, 1, 1), date(2019, 12, 31))
    assert js[-1] == (date(2020, 1, 1), date(2026, 10, 26))
    for ini, fim in js:
        assert sgs._somar_anos(ini, 10) > fim


def test_janelas_29_de_fevereiro():
    assert sgs.janelas(date(2004, 2, 29), date(2020, 1, 1))[0] == (date(2004, 2, 29), date(2014, 2, 27))


def test_sempre_envia_filtro_de_data():
    sessao = SessaoFalsa([RespostaFalsa(corpo=[{"data": "01/01/2026", "valor": "0.33"}])])
    sgs.baixar_serie(433, date(2026, 1, 1), date(2026, 10, 26), sessao=sessao)
    assert sessao.chamadas[0]["dataInicial"] == "01/01/2026"
    assert sessao.chamadas[0]["dataFinal"] == "26/10/2026"


def test_tenta_de_novo_apos_502_e_timeout():
    sessao = SessaoFalsa([
        RespostaFalsa(status=502, tipo="text/html"),
        requests.Timeout("tempo esgotado"),
        RespostaFalsa(corpo=[{"data": "20/10/2026", "valor": "13.65"}]),
    ])
    df = sgs.baixar_serie(1178, date(2026, 10, 20), date(2026, 10, 26), sessao=sessao)
    assert len(sessao.chamadas) == 3
    assert df["valor"].tolist() == ["13.65"]


def test_html_com_status_200_e_erro():
    pagina = RespostaFalsa(tipo="text/html; charset=utf-8", texto="<title>Requisição inválida!</title>")
    sessao = SessaoFalsa([pagina] * 3)
    with pytest.raises(sgs.ErroSGS, match="não é JSON"):
        sgs.baixar_serie(433, date(2026, 1, 1), date(2026, 10, 26), sessao=sessao, tentativas=3)


def test_404_json_e_janela_vazia():
    vazio = RespostaFalsa(status=404, corpo={"erro": {"detail": "Value(s) not found"}})
    sessao = SessaoFalsa([vazio])
    df = sgs.baixar_serie(433, date(1950, 1, 1), date(1950, 12, 31), sessao=sessao)
    assert df.empty and list(df.columns) == ["data", "valor"]


def test_ordena_e_remove_duplicatas():
    sessao = SessaoFalsa([RespostaFalsa(corpo=[
        {"data": "01/08/2026", "valor": "82.87"},
        {"data": "01/07/2026", "valor": "82.55"},
        {"data": "01/08/2026", "valor": "82.90"},
    ])])
    df = sgs.baixar_serie(13762, date(2026, 7, 1), date(2026, 8, 31), sessao=sessao)
    assert df["data"].tolist() == [date(2026, 7, 1), date(2026, 8, 1)]
    assert df["valor"].tolist() == ["82.55", "82.90"]


def test_catalogo_e_valido():
    catalogo = carregar_catalogo()
    df = dim_serie(catalogo)
    assert df["id"].is_unique
    assert df["o_que_e"].notna().all()
