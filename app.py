from __future__ import annotations

import streamlit as st
import pandas as pd

from utils.data import (
    load_xlsx,
    rename_columns,
    validate_columns,
    clean_and_normalize,
    add_queue_flags,
    compute_metrics,
    filter_df,
    to_csv_bytes,
)

st.set_page_config(page_title="Convênios - Base Transferegov", layout="wide")

st.title("Base de instrumentos (Transferegov)")
st.write(
    "Faça upload do XLSX exportado do Transferegov e use filtros/filas para navegação e validação do MVP."
)


def fmt_brl(value: float) -> str:
    # Formatação simples sem depender de locale do servidor
    try:
        v = float(value)
    except Exception:
        v = 0.0
    s = f"{v:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


@st.cache_data(show_spinner=False)
def load_and_prepare(file) -> pd.DataFrame:
    df0 = load_xlsx(file)
    df0 = rename_columns(df0)
    df0 = clean_and_normalize(df0)
    df0 = add_queue_flags(df0)
    return df0


uploaded = st.file_uploader("Arquivo XLSX (exportação do Transferegov)", type=["xlsx"])

if not uploaded:
    st.info("Envie um arquivo XLSX para começar.")
    st.stop()

df = load_and_prepare(uploaded)

missing = validate_columns(df)
if missing:
    st.error("O arquivo não tem todas as colunas esperadas. Colunas faltantes:")
    st.write(missing)
    st.stop()

with st.expander("Prévia do arquivo (primeiras 10 linhas)", expanded=False):
    st.dataframe(df.head(10), use_container_width=True)

# Sidebar: filtros
st.sidebar.header("Filtros")

uf = st.sidebar.multiselect("UF", sorted(df["uf"].dropna().unique().tolist()))
municipio = st.sidebar.multiselect("Município", sorted(df["municipio"].dropna().unique().tolist()))
situacao = st.sidebar.multiselect("Situação", sorted(df["situacao_instrumento"].dropna().unique().tolist()))
subsituacao = st.sidebar.multiselect("Subsituação", sorted(df["subsituacao_instrumento"].dropna().unique().tolist()))
possui_obra = st.sidebar.multiselect("Possui obra", sorted(df["possui_obra"].dropna().unique().tolist()))
sem_pagto_150 = st.sidebar.multiselect(
    "Sem pagamento +150 dias",
    sorted(df["sem_pagamento_a_mais_de_150_dias"].dropna().unique().tolist()),
)

sem_desembolso = st.sidebar.multiselect(
    "Sem desembolso (faixa)", sorted(df["sem_desembolso"].dropna().unique().tolist())
)
ultimo_pagamento = st.sidebar.multiselect(
    "Último pagamento (faixa)", sorted(df["ultimo_pagamento"].dropna().unique().tolist())
)

situacao_inst_contratual = st.sidebar.multiselect(
    "Situação inst. contratual",
    sorted(df["situacao_inst_contratual"].dropna().unique().tolist()),
)

search_text = st.sidebar.text_input("Busca (instrumento, processo/NUP, CNPJ, proponente, objeto)")

st.sidebar.header("Filas (checkbox)")

only_fila_sem_exec_90 = st.sidebar.checkbox("Sem execução financeira > 90 dias (faixa)")
only_fila_sem_exec_180 = st.sidebar.checkbox("Sem execução financeira > 180 dias (faixa)")
only_fila_sem_exec_365 = st.sidebar.checkbox("Sem execução financeira > 365 dias (faixa)")

only_fila_ult_pagto_90 = st.sidebar.checkbox("Último pagamento > 90 dias (faixa)")
only_fila_ult_pagto_180 = st.sidebar.checkbox("Último pagamento > 180 dias (faixa)")

only_fila_sem_desembolso_ult_pagto = st.sidebar.checkbox("Último pagamento = Sem Desembolso")
only_fila_sem_pagto_150 = st.sidebar.checkbox("Sem pagamento +150 dias (indicador)")

filtered = filter_df(
    df=df,
    uf=uf,
    municipio=municipio,
    situacao=situacao,
    subsituacao=subsituacao,
    possui_obra=possui_obra,
    sem_pagto_150=sem_pagto_150,
    sem_desembolso=sem_desembolso,
    ultimo_pagamento=ultimo_pagamento,
    situacao_inst_contratual=situacao_inst_contratual,
    search_text=search_text,
    only_fila_sem_exec_90=only_fila_sem_exec_90,
    only_fila_sem_exec_180=only_fila_sem_exec_180,
    only_fila_sem_exec_365=only_fila_sem_exec_365,
    only_fila_ult_pagto_90=only_fila_ult_pagto_90,
    only_fila_ult_pagto_180=only_fila_ult_pagto_180,
    only_fila_sem_desembolso_ult_pagto=only_fila_sem_desembolso_ult_pagto,
    only_fila_sem_pagto_150=only_fila_sem_pagto_150,
)

# Métricas
m = compute_metrics(filtered)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Instrumentos (únicos)", f"{m['qtd_instrumentos']:,}".replace(",", "."))
c2.metric("Soma valor global", fmt_brl(m["soma_valor_global"]))
c3.metric("Soma desembolsado", fmt_brl(m["soma_valor_desembolsado_acumulado"]))
c4.metric("Média execução financeira", f"{m['media_execucao_financeira']:.4f}")

st.subheader("Resultados")

# Colunas para exibição (inclui no_processo só se existir)
cols_show = [
    "no_instrumento",
    "no_processo",
    "uf",
    "municipio",
    "cnpj",
    "nome_proponente",
    "situacao_instrumento",
    "subsituacao_instrumento",
    "possui_obra",
    "sem_pagamento_a_mais_de_150_dias",
    "ultimo_pagamento",
    "sem_desembolso",
    "valor_global",
    "valor_de_repasse",
    "valor_de_contrapartida",
    "valor_empenhado_acumulado",
    "valor_desembolsado_acumulado",
    "saldo_em_conta",
    "execucao_financeira",
    "situacao_inst_contratual",
    "objeto",
    "link_externo",
]
cols_show = [c for c in cols_show if c in filtered.columns]

st.dataframe(filtered[cols_show], use_container_width=True, height=420)

st.divider()

st.subheader("Detalhe do instrumento")

options = filtered["no_instrumento"].dropna().astype("string").unique().tolist()
options = sorted(options)

selected = st.selectbox(
    "Selecione o número do instrumento",
    options=options,
    index=0 if options else None,
)

if selected:
    row = filtered[filtered["no_instrumento"].astype("string") == str(selected)].head(1)
    if not row.empty:
        r = row.iloc[0].to_dict()

        left, right = st.columns([2, 3])

        with left:
            st.write(f"Instrumento: {r.get('no_instrumento')}")
            if "no_processo" in filtered.columns:
                st.write(f"Processo (NUP): {r.get('no_processo')}")
            st.write(f"UF/Município: {r.get('uf')} / {r.get('municipio')}")
            st.write(f"Proponente: {r.get('nome_proponente')}")
            st.write(f"CNPJ: {r.get('cnpj')}")
            st.write(f"Ano assinatura: {r.get('ano_assinatura')}")
            st.write(f"Situação: {r.get('situacao_instrumento')}")
            st.write(f"Subsituação: {r.get('subsituacao_instrumento')}")
            st.write(f"Possui obra: {r.get('possui_obra')}")
            st.write(f"Sem pagto +150: {r.get('sem_pagamento_a_mais_de_150_dias')}")
            st.write(f"Último pagamento: {r.get('ultimo_pagamento')}")
            st.write(f"Sem desembolso: {r.get('sem_desembolso')}")
            st.write(f"Sit. inst. contratual: {r.get('situacao_inst_contratual')}")

        with right:
            st.write("Objeto")
            st.write(r.get("objeto"))

            st.write("Financeiro")
            st.write(f"Valor global: {fmt_brl(r.get('valor_global') or 0)}")
            st.write(f"Repasse: {fmt_brl(r.get('valor_de_repasse') or 0)}")
            st.write(f"Contrapartida: {fmt_brl(r.get('valor_de_contrapartida') or 0)}")
            st.write(f"Empenhado acumulado: {fmt_brl(r.get('valor_empenhado_acumulado') or 0)}")
            st.write(f"Desembolsado acumulado: {fmt_brl(r.get('valor_desembolsado_acumulado') or 0)}")
            st.write(f"Saldo em conta: {fmt_brl(r.get('saldo_em_conta') or 0)}")
            st.write(f"Execução financeira: {r.get('execucao_financeira')}")

        link = r.get("link_externo")
        if link and isinstance(link, str):
            st.link_button("Abrir no Transferegov", link)

st.divider()

csv_bytes = to_csv_bytes(filtered[cols_show])
st.download_button(
    label="Baixar CSV do resultado filtrado",
    data=csv_bytes,
    file_name="instrumentos_filtrados.csv",
    mime="text/csv",
)
