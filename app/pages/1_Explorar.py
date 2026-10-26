"""Explorar: área → indicador, com o gráfico, as transformações e o bloco "Entenda"."""
import pandas as pd
import streamlit as st

import calculos as c
import dados
import graficos

st.set_page_config(page_title="Explorar · Observatório", page_icon="📈", layout="wide")
dados.checar_banco()

dim = dados.dim_serie()
PERIODOS = {"2 anos": 2, "5 anos": 5, "10 anos": 10, "Tudo": None}

# --- filtros, todos numa linha acima do gráfico ---
f1, f2, f3, f4 = st.columns([2, 3, 3, 2])
areas = dim["nome_area"].unique().tolist()
area = f1.selectbox("Área", areas)
opcoes = dim[dim["nome_area"] == area]
id_serie = f2.selectbox("Indicador", opcoes["id"], format_func=lambda i: opcoes.set_index("id").loc[i, "nome"])
ind = dim.set_index("id").loc[id_serie]
tp = c.tipo(ind["unidade"])
transformacao = f3.selectbox("Mostrar como", c.TRANSFORMACOES[tp])
periodo = f4.segmented_control("Período", list(PERIODOS), default="10 anos")

g1, g2, _ = st.columns([2, 2, 6])
granularidade = "Diária"
if ind["periodicidade"] == "diaria" and transformacao == "Valor":
    granularidade = g1.segmented_control("Granularidade", ["Diária", "Mensal"], default="Mensal")
mostrar_recessoes = g2.toggle("Recessões (CODACE)", value=True)

# --- dados ---
bruta = dados.serie(id_serie)
s, unidade = c.aplicar(bruta, ind["unidade"], transformacao, granularidade or "Mensal")
anos = PERIODOS.get(periodo or "Tudo")
if anos:
    s = s[s.index >= s.index.max() - pd.DateOffset(years=anos)]

meta = None
if id_serie == "ipca" and transformacao == "Acumulado em 12 meses":
    meta = c.meta_mensal(dados.metas_inflacao(), s.index)
futuro = dados.serie_futura(id_serie) if transformacao == "Valor" else None

# --- gráfico + Entenda ---
col_graf, col_texto = st.columns([7, 3])
with col_graf:
    ultimo = s.iloc[-1]
    st.markdown(f"### {ind['nome']}")
    st.markdown(
        f"Último valor: **{c.br(ultimo, 0 if unidade.endswith('milhões') else 2)} {unidade}** "
        f"em {s.index[-1]:%d/%m/%Y}"
        + (f" · fonte original: {ind['fonte_original']}" if pd.notna(ind["fonte_original"]) else "")
    )
    st.plotly_chart(
        graficos.linha(s, unidade, recessoes=mostrar_recessoes, meta=meta, futuro=futuro),
        width="stretch",
    )
    legendas = []
    if mostrar_recessoes:
        legendas.append("faixas cinza = recessões datadas pelo CODACE/FGV")
    if meta is not None:
        legendas.append("faixa e linha tracejada = meta de inflação e intervalo de tolerância")
    if futuro is not None and not futuro.empty:
        legendas.append("pontilhado = valor já programado")
    if legendas:
        st.caption(" · ".join(legendas).capitalize())

with col_texto:
    with st.container(border=True):
        st.markdown("#### 📘 Entenda")
        st.markdown(f"**O que é.** {ind['o_que_e']}")
        st.markdown(f"**Por que importa.** {ind['por_que_importa']}")
        st.markdown(f"**Como ler.** {ind['como_ler']}")
        if ind["se_relaciona_com"]:
            st.markdown("**Se relaciona com:**")
            nomes = dim.set_index("id")["nome"]
            for rel in ind["se_relaciona_com"].split(", "):
                st.markdown(f"- {nomes[rel]}")

with st.expander("Ver os dados em tabela"):
    tabela = s.rename(unidade).to_frame()
    tabela.index = tabela.index.strftime("%d/%m/%Y")
    st.dataframe(tabela.iloc[::-1], width="stretch")
