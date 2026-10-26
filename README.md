# Observatório da Economia Brasileira

Pipeline de dados + app Streamlit para acompanhar e **estudar** a economia brasileira com os dados
públicos do Banco Central e do IBGE. Cada indicador vem com a explicação dele: o que é, por que
importa, como ler e com quais outros indicadores se relaciona.

## Como rodar

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python -m pipeline.carga        # baixa as séries para data/econ.duckdb (incremental)
streamlit run app/Home.py       # abre o app em http://localhost:8501
pytest                          # testes (não usam internet)
```

## Estrutura

| Pasta | Conteúdo |
|---|---|
| `catalogo/` | `indicadores.yaml` (fonte única: séries, metadados e textos de estudo) e as metas de inflação |
| `ingest/` | Clientes das APIs (`sgs.py`: SGS do Banco Central) |
| `pipeline/` | Carga para o DuckDB: camadas `raw` e `silver` |
| `app/` | Streamlit: Termômetro, Explorar e Comparar |
| `tests/` | Testes do cliente SGS, simulando os comportamentos reais da API |

## Indicadores (v1)

15 séries do SGS em 7 áreas: política monetária (Selic meta e efetiva), inflação (IPCA, IGP-M),
câmbio e setor externo (dólar, reservas, balança comercial), atividade (IBC-Br, PIB mensal),
emprego (desocupação), contas públicas (dívida bruta e líquida) e crédito (saldo, inadimplência).

## Cuidados com a API do SGS

- Cada chamada aceita no máximo 10 anos, e o filtro de data é obrigatório (o atalho `/ultimos/N` falha em algumas séries).
- Timeouts, erros 502 e bloqueios temporários (uma página HTML com status 200) são comuns: o cliente faz uma pausa entre as chamadas, tenta de novo com espera crescente e só aceita resposta em JSON.
- A ordem das datas não é garantida, e a Selic meta já traz a taxa programada até a próxima reunião do Copom (fica separada em `silver.serie_futura`).

## Próximos passos

Expectativas Focus (API Olinda), IBGE/SIDRA (PIB trimestral, IPCA por grupo), camada gold,
página de correlação com defasagem e atualização diária pelo GitHub Actions.
