"""Termômetro: os grandes números da economia brasileira hoje."""
import streamlit as st

import calculos as c
import dados

st.set_page_config(page_title="Observatório da Economia BR", page_icon="📈", layout="wide")
dados.checar_banco()

st.title("Termômetro da economia brasileira")
st.caption(
    f"Fontes: Banco Central (SGS), IBGE e FGV · última carga em {dados.ultima_carga():%d/%m/%Y %H:%M} · "
    "rode `python -m pipeline.carga` para atualizar"
)

selic = dados.serie("selic_meta")
selic_futura = dados.serie_futura("selic_meta")
ipca12 = c.acumulado_12m(dados.serie("ipca"))
metas = dados.metas_inflacao().set_index("ano")
dolar = dados.serie("dolar")
desocupacao = dados.serie("desocupacao")
dbgg = dados.serie("dbgg")
inadimplencia = dados.serie("inadimplencia")
ibc = c.variacao_12m(dados.serie("ibc_br"))
credito = c.variacao_12m(dados.serie("credito_saldo"))

ipca_atual = ipca12.iloc[-1]
meta = metas.loc[ipca12.index[-1].year]
juro_real = ((1 + selic.iloc[-1] / 100) / (1 + ipca_atual / 100) - 1) * 100


def mes(s):
    return f"{s.index[-1]:%m/%Y}"


st.subheader("Juros e inflação")
k1, k2, k3, k4 = st.columns(4, border=True)
k1.metric(
    "Selic meta", f"{c.br(selic.iloc[-1])}% a.a.",
    delta=f"{c.br(selic.iloc[-1] - c.ha_um_ano(selic))} p.p. em 12 meses", delta_color="off",
)
if not selic_futura.empty:
    k1.caption(f"Vigente até {selic_futura.index[-1]:%d/%m/%Y} (próxima reunião do Copom)")
k2.metric(
    "IPCA em 12 meses", f"{c.br(ipca_atual)}%",
    delta=f"{c.br(ipca_atual - meta.meta)} p.p. vs. a meta", delta_color="inverse",
)
k2.caption(f"Até {mes(ipca12)} · meta {c.br(meta.meta)}% (de {c.br(meta.meta - meta.tolerancia)}% a "
           f"{c.br(meta.meta + meta.tolerancia)}%)")
k3.metric("Juro real (ex-post)", f"{c.br(juro_real)}% a.a.")
k3.caption("Selic descontada a inflação dos últimos 12 meses")
k4.metric(
    "IGP-M no mês", f"{c.br(dados.serie('igpm').iloc[-1])}%",
)
k4.caption(f"{mes(dados.serie('igpm'))} · inflação do atacado, antecipa pressões no IPCA")

st.subheader("Atividade, emprego e crédito")
k1, k2, k3, k4 = st.columns(4, border=True)
k1.metric("IBC-Br em 12 meses", f"{c.br(ibc.iloc[-1])}%")
k1.caption(f"{mes(ibc)} vs. mesmo mês do ano anterior · prévia do PIB")
k2.metric(
    "Desocupação", f"{c.br(desocupacao.iloc[-1], 1)}%",
    delta=f"{c.br(desocupacao.iloc[-1] - c.ha_um_ano(desocupacao), 1)} p.p. em 12 meses", delta_color="inverse",
)
k2.caption(f"Trimestre móvel até {mes(desocupacao)}")
k3.metric("Crédito em 12 meses", f"{c.br(credito.iloc[-1], 1)}%")
k3.caption(f"Crescimento do saldo até {mes(credito)}")
k4.metric(
    "Inadimplência", f"{c.br(inadimplencia.iloc[-1])}%",
    delta=f"{c.br(inadimplencia.iloc[-1] - c.ha_um_ano(inadimplencia))} p.p. em 12 meses", delta_color="inverse",
)
k4.caption(f"Atrasos acima de 90 dias · {mes(inadimplencia)}")

st.subheader("Câmbio e contas públicas")
k1, k2, k3, k4 = st.columns(4, border=True)
var_dolar = (dolar.iloc[-1] / c.ha_um_ano(dolar) - 1) * 100
k1.metric("Dólar", f"R$ {c.br(dolar.iloc[-1], 4)}", delta=f"{c.br(var_dolar, 1)}% em 12 meses", delta_color="off")
k1.caption(f"{dolar.index[-1]:%d/%m/%Y}")
k2.metric("Reservas internacionais", f"US$ {c.br(dados.serie('reservas').iloc[-1] / 1000, 0)} bi")
k3.metric(
    "Dívida bruta", f"{c.br(dbgg.iloc[-1], 1)}% do PIB",
    delta=f"{c.br(dbgg.iloc[-1] - c.ha_um_ano(dbgg), 1)} p.p. em 12 meses", delta_color="inverse",
)
k3.caption(f"Governo geral · {mes(dbgg)}")
k4.metric("Dívida líquida", f"{c.br(dados.serie('dlsp').iloc[-1], 1)}% do PIB")
k4.caption(f"Setor público consolidado · {mes(dados.serie('dlsp'))}")

st.subheader("📘 Leitura rápida")
teto = meta.meta + meta.tolerancia
if ipca_atual > teto:
    situacao = f"**acima do teto** da meta ({c.br(teto)}%)"
elif ipca_atual < meta.meta - meta.tolerancia:
    situacao = f"**abaixo do piso** da meta ({c.br(meta.meta - meta.tolerancia)}%)"
else:
    situacao = f"**dentro do intervalo** da meta (de {c.br(meta.meta - meta.tolerancia)}% a {c.br(teto)}%)"
st.markdown(
    f"- A inflação em 12 meses está em **{c.br(ipca_atual)}%**, {situacao}.\n"
    f"- Com a Selic em **{c.br(selic.iloc[-1])}%**, o juro real é de cerca de **{c.br(juro_real, 1)}%** ao ano. "
    "Acima de ~5% ao ano costuma ser considerado juro **contracionista**: ele freia a economia para segurar os preços.\n"
    f"- O desemprego em **{c.br(desocupacao.iloc[-1], 1)}%** indica um mercado de trabalho apertado, o que "
    "sustenta o consumo e a inflação de serviços. É um dos motivos para o BC manter os juros altos."
)
st.page_link("pages/1_Explorar.py", label="Explorar um indicador →")
