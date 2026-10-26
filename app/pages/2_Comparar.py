"""Comparar: até 4 indicadores empilhados, com o mesmo eixo de tempo."""
import pandas as pd
import streamlit as st

import calculos as c
import dados
import graficos

st.set_page_config(page_title="Comparar · Observatório", page_icon="📈", layout="wide")
dados.checar_banco()

dim = dados.dim_serie().set_index("id")
PERIODOS = {"5 anos": 5, "10 anos": 10, "Tudo": None}
SUGESTOES = {
    "Selic × IPCA": ["selic_meta", "ipca"],
    "Dólar × inflação": ["dolar", "igpm", "ipca"],
    "Juros × crédito": ["selic_meta", "credito_saldo", "inadimplencia"],
    "Desemprego × inflação": ["desocupacao", "ipca"],
}

st.title("Comparar indicadores")
st.caption(
    "Cada indicador ganha o próprio painel, e os painéis compartilham o eixo do tempo. "
    "Assim dá para ver quem se move antes de quem, sem o truque enganoso de dois eixos y no mesmo gráfico."
)

f1, f2, f3 = st.columns([3, 5, 2])
sugestao = f1.selectbox("Comparações sugeridas", ["(escolher livremente)", *SUGESTOES])
padrao = SUGESTOES.get(sugestao, ["selic_meta", "ipca"])
ids = f2.multiselect(
    "Indicadores (até 4)", dim.index.tolist(), default=padrao, max_selections=4,
    format_func=lambda i: f"{dim.loc[i, 'nome']} · {dim.loc[i, 'nome_area']}",
)
periodo = f3.segmented_control("Período", list(PERIODOS), default="Tudo")

if not ids:
    st.info("Escolha pelo menos um indicador.")
    st.stop()

# Cada série no seu formato mais "legível": acumulado em 12 meses para inflação, variação em 12 meses
# para níveis em R$ (que crescem com a inflação), valor mensal para o resto.
series = []
for i in ids:
    ind = dim.loc[i]
    tp = c.tipo(ind["unidade"])
    if tp == "fluxo_pct":
        transf = "Acumulado em 12 meses"
    elif tp == "nivel" and ind["unidade"].startswith("R$ milhões"):
        transf = "Variação em 12 meses (%)"
    else:
        transf = "Valor"
    s, unidade = c.aplicar(dados.serie(i), ind["unidade"], transf, "Mensal")
    series.append((ind["nome"], s, unidade))

inicio = max(s.index.min() for _, s, _ in series)  # período em que todas existem
anos = PERIODOS.get(periodo or "Tudo")
if anos:
    inicio = max(inicio, max(s.index.max() for _, s, _ in series) - pd.DateOffset(years=anos))
series = [(n, s[s.index >= inicio], u) for n, s, u in series]

st.plotly_chart(graficos.paineis(series), width="stretch")
st.caption("Faixas cinza = recessões datadas pelo CODACE/FGV")

if sugestao == "Selic × IPCA":
    st.info(
        "📘 **O que observar:** o BC sobe a Selic *depois* que a inflação acelera, e a inflação só cede "
        "6 a 18 meses depois. Veja 2021–2022: o IPCA passou de 10%, a Selic foi de 2% para 13,75%, "
        "e a inflação caiu em 2023."
    )
elif sugestao == "Desemprego × inflação":
    st.info(
        "📘 **O que observar:** a *curva de Phillips* diz que desemprego baixo tende a vir com inflação mais alta, "
        "porque os salários sobem e as empresas repassam esse custo aos preços. A relação não é mecânica: "
        "choques de oferta (alimentos, energia) também movem a inflação."
    )
