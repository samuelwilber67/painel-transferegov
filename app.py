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


def fmt_brl(value: float) -> str:
    try:
        v = float(value)
    except Exception:
        v = 0.0
    s = f"{v:,.2f}"
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


@st.cache_data(show_spinner=False)
def parse_xlsx(file_bytes: bytes) -> pd.DataFrame:
    # Streamlit upload retorna objeto tipo file; cache funciona melhor com bytes
    from io import BytesIO

    bio = BytesIO(file_bytes)
    df0 = load_xlsx(bio)
    df0 = rename_columns(df0)
    df0 = clean_and_normalize(df0)
    df0 = add_queue_flags(df0)
    return df0


def ensure_loaded_df() -> pd.DataFrame | None:
    return st.session_state.get("df_loaded")


def set_loaded_df(df: pd.DataFrame, filename: str):
    st.session_state["df_loaded"] = df
    st.session_state["df_filename"] = filename


def clear_loaded_df():
    for k in ["df_loaded", "df_filename"]:
        if k in st.session_state:
            del st.session_state[k]


# Header
st.title("Plataforma de Acompanhamento (MVP) — Transferegov")
st.caption("Upload do XLSX → Dashboard / Filas / Lista / Detalhe atualizam automaticamente.")

tabs = st.tabs(["Dados", "Dashboard", "Filas", "Lista", "Detalhe"])

# -------------------
# ABA: DADOS (UPLOAD)
# -------------------
with tabs[0]:
    st.subheader("1) Carregar dados (XLSX)")
    st.write("Faça upload do Excel exportado do Transferegov. Após carregar, as outras abas usam esses dados automaticamente.")

    uploaded = st.file_uploader("Selecione o arquivo XLSX", type=["xlsx"], key="uploader_xlsx")

    col_a, col_b = st.columns([1, 1])
    with col_a:
        if st.button("Limpar dados carregados", use_container_width=True):
            clear_loaded_df()
            st.rerun()

    if uploaded is None:
        df_current = ensure_loaded_df()
        if df_current is None:
            st.info("Nenhum arquivo carregado ainda.")
        else:
            st.success(f"Dados já carregados na sessão: {st.session_state.get('df_filename', 'arquivo')}")
            st.write("Você pode ir para as outras abas.")
    else:
        file_bytes = uploaded.getvalue()
        with st.spinner("Lendo e normalizando o XLSX..."):
            df = parse_xlsx(file_bytes)

        missing = validate_columns(df)
        if missing:
            st.error("O arquivo não tem todas as colunas esperadas. Colunas faltantes:")
            st.write(missing)
            st.stop()

        set_loaded_df(df, uploaded.name)
        st.success(f"Arquivo carregado: {uploaded.name}")

        with st.expander("Prévia do arquivo (primeiras 15 linhas)", expanded=False):
            st.dataframe(df.head(15), use_container_width=True)

        st.write("Agora vá para as abas **Dashboard**, **Filas**, **Lista** e **Detalhe**.")


# -------------------
# DADOS BASE (PARA AS OUTRAS ABAS)
# -------------------
df_loaded = ensure_loaded_df()

if df_loaded is None:
    # Não trava a aba Dados, mas trava as demais de forma elegante
    with tabs[1]:
        st.info("Carregue um XLSX na aba **Dados** para ver o dashboard.")
    with tabs[2]:
        st.info("Carregue um XLSX na aba **Dados** para ver as filas.")
    with tabs[3]:
        st.info("Carregue um XLSX na aba **Dados** para ver a lista.")
    with tabs[4]:
        st.info("Carregue um XLSX na aba **Dados** para ver o detalhe.")
    st.stop()

df_base = df_loaded


# -------------------
# FILTROS GLOBAIS (SIDEBAR) — afetam Dashboard/Filas/Lista/Detalhe
# -------------------
st.sidebar.header("Filtros (globais)")

uf = st.sidebar.multiselect("UF", sorted(df_base["uf"].dropna().unique().tolist()))
municipio = st.sidebar.multiselect("Município", sorted(df_base["municipio"].dropna().unique().tolist()))
situacao = st.sidebar.multiselect("Situação", sorted(df_base["situacao_instrumento"].dropna().unique().tolist()))
subsituacao = st.sidebar.multiselect("Subsituação", sorted(df_base["subsituacao_instrumento"].dropna().unique().tolist()))
possui_obra = st.sidebar.multiselect("Possui obra", sorted(df_base["possui_obra"].dropna().unique().tolist()))
sem_pagto_150 = st.sidebar.multiselect(
    "Sem pagamento +150 dias",
    sorted(df_base["sem_pagamento_a_mais_de_150_dias"].dropna().unique().tolist()),
)

sem_desembolso = st.sidebar.multiselect(
    "Sem desembolso (faixa)", sorted(df_base["sem_desembolso"].dropna().unique().tolist())
)
ultimo_pagamento = st.sidebar.multiselect(
    "Último pagamento (faixa)", sorted(df_base["ultimo_pagamento"].dropna().unique().tolist())
)

situacao_inst_contratual = st.sidebar.multiselect(
    "Situação inst. contratual",
    sorted(df_base["situacao_inst_contratual"].dropna().unique().tolist()),
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
    df=df_base,
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


# -------------------
# ABA: DASHBOARD
# -------------------
with tabs[1]:
    st.subheader("2) Dashboard (visão geral)")

    m = compute_metrics(filtered)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Instrumentos", f"{m['qtd_instrumentos']:,}".replace(",", "."))
    c2.metric("Valor global (soma)", fmt_brl(m["soma_valor_global"]))
    c3.metric("Repasse (soma)", fmt_brl(m["soma_valor_de_repasse"]))
    c4.metric("Desembolsado (soma)", fmt_brl(m["soma_valor_desembolsado_acumulado"]))
    c5.metric("Média execução", f"{m['media_execucao_financeira']:.4f}")

    st.divider()

    # Distribuições simples (mais visual)
    left, right = st.columns(2)

    with left:
        st.write("Situação do instrumento (contagem)")
        s = filtered["situacao_instrumento"].fillna("Sem informação").value_counts().reset_index()
        s.columns = ["situacao_instrumento", "qtd"]
        st.bar_chart(s.set_index("situacao_instrumento"))

    with right:
        st.write("Possui obra (contagem)")
        p = filtered["possui_obra"].fillna("Sem informação").value_counts().reset_index()
        p.columns = ["possui_obra", "qtd"]
        st.bar_chart(p.set_index("possui_obra"))

    st.divider()

    st.write("Download do resultado filtrado")
    cols_export = [c for c in filtered.columns if c in df_base.columns]
    st.download_button(
        label="Baixar CSV (resultado filtrado)",
        data=to_csv_bytes(filtered[cols_export]),
        file_name="instrumentos_filtrados.csv",
        mime="text/csv",
        use_container_width=True,
    )


# -------------------
# ABA: FILAS
# -------------------
with tabs[2]:
    st.subheader("3) Filas (priorização)")

    # Contadores das filas (com base no df_base, sem aplicar os checkboxes para não confundir)
    # Aqui a lógica é mostrar o volume e permitir "aplicar" via botão.
    def count_flag(col: str) -> int:
        if col not in df_base.columns:
            return 0
        return int(df_base[col].fillna(False).sum())

    f1, f2, f3, f4 = st.columns(4)
    f1.metric("Sem exec >90 (faixa)", f"{count_flag('fila_sem_exec_90'):,}".replace(",", "."))
    f2.metric("Sem exec >180 (faixa)", f"{count_flag('fila_sem_exec_180'):,}".replace(",", "."))
    f3.metric("Sem exec >365 (faixa)", f"{count_flag('fila_sem_exec_365'):,}".replace(",", "."))
    f4.metric("Sem pagto +150 (indicador)", f"{count_flag('fila_sem_pagto_150'):,}".replace(",", "."))

    g1, g2, g3 = st.columns(3)
    g1.metric("Últ pagto >90 (faixa)", f"{count_flag('fila_ult_pagto_90'):,}".replace(",", "."))
    g2.metric("Últ pagto >180 (faixa)", f"{count_flag('fila_ult_pagto_180'):,}".replace(",", "."))
    g3.metric("Últ pagto = Sem desemb.", f"{count_flag('fila_sem_desembolso_ult_pagto'):,}".replace(",", "."))

    st.caption("Use os checkboxes de filas na barra lateral para filtrar a lista/detalhe.")

    st.divider()

    st.write("Prévia da lista filtrada pelas seleções atuais (sidebar)")
    cols_show = [
        "no_instrumento",
        "no_processo",
        "uf",
        "municipio",
        "nome_proponente",
        "situacao_instrumento",
        "possui_obra",
        "sem_pagamento_a_mais_de_150_dias",
        "ultimo_pagamento",
        "sem_desembolso",
        "valor_global",
        "valor_de_repasse",
        "valor_desembolsado_acumulado",
        "execucao_financeira",
    ]
    cols_show = [c for c in cols_show if c in filtered.columns]
    st.dataframe(filtered[cols_show], use_container_width=True, height=420)


# -------------------
# ABA: LISTA
# -------------------
with tabs[3]:
    st.subheader("4) Lista (consulta)")

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
    ]
    cols_show = [c for c in cols_show if c in filtered.columns]

    st.dataframe(filtered[cols_show], use_container_width=True, height=560)

    st.divider()

    st.write("Exportação")
    st.download_button(
        "Baixar CSV da lista atual (filtrada)",
        data=to_csv_bytes(filtered[cols_show]),
        file_name="lista_filtrada.csv",
        mime="text/csv",
        use_container_width=True,
    )


# -------------------
# ABA: DETALHE
# -------------------
with tabs[4]:
    st.subheader("5) Detalhe do instrumento")

    options = filtered["no_instrumento"].dropna().astype("string").unique().tolist()
    options = sorted(options)

    if not options:
        st.warning("Nenhum instrumento encontrado com os filtros atuais. Ajuste os filtros na barra lateral.")
        st.stop()

    selected = st.selectbox("Selecione o número do instrumento", options=options, index=0)

    row = filtered[filtered["no_instrumento"].astype("string") == str(selected)].head(1)
    if row.empty:
        st.warning("Não foi possível carregar o detalhe deste instrumento (verifique filtros).")
        st.stop()

    r = row.iloc[0].to_dict()

    # Cabeçalho tipo "card"
    top1, top2, top3, top4 = st.columns([1.2, 1.2, 1.2, 1.2])
    top1.metric("Instrumento", str(r.get("no_instrumento", "")))
    top2.metric("UF", str(r.get("uf", "")))
    top3.metric("Município", str(r.get("municipio", "")))
    top4.metric("Possui obra", str(r.get("possui_obra", "")))

    st.divider()

    left, right = st.columns([2, 3])

    with left:
        st.write("Identificação / Status")
        st.write(f"Proponente: **{r.get('nome_proponente')}**")
        st.write(f"CNPJ: **{r.get('cnpj')}**")
        if "no_processo" in filtered.columns:
            st.write(f"Processo (NUP): **{r.get('no_processo')}**")
        st.write(f"Ano assinatura: **{r.get('ano_assinatura')}**")
        st.write(f"Situação: **{r.get('situacao_instrumento')}**")
        st.write(f"Subsituação: **{r.get('subsituacao_instrumento')}**")
        st.write(f"Sit. inst. contratual: **{r.get('situacao_inst_contratual')}**")

        st.write("Indicadores")
        st.write(f"Sem pagto +150 dias: **{r.get('sem_pagamento_a_mais_de_150_dias')}**")
        st.write(f"Último pagamento: **{r.get('ultimo_pagamento')}**")
        st.write(f"Sem desembolso: **{r.get('sem_desembolso')}**")

        link = r.get("link_externo")
        if link and isinstance(link, str):
            st.link_button("Abrir no Transferegov", link, use_container_width=True)

    with right:
        st.write("Objeto")
        st.info(r.get("objeto") or "Sem informação")

        st.write("Financeiro")
        a, b, c = st.columns(3)
        a.metric("Valor global", fmt_brl(r.get("valor_global") or 0))
        b.metric("Repasse", fmt_brl(r.get("valor_de_repasse") or 0))
        c.metric("Contrapartida", fmt_brl(r.get("valor_de_contrapartida") or 0))

        d, e, f = st.columns(3)
        d.metric("Empenhado acum.", fmt_brl(r.get("valor_empenhado_acumulado") or 0))
        e.metric("Desembolsado acum.", fmt_brl(r.get("valor_desembolsado_acumulado") or 0))
        f.metric("Saldo em conta", fmt_brl(r.get("saldo_em_conta") or 0))

        st.write(f"Execução financeira: **{r.get('execucao_financeira')}**")
