from __future__ import annotations

import streamlit as st
import pandas as pd

from utils.data import (
    load_and_merge_all,
    save_atribuicao,
    save_edicao,
    get_edicoes,
)

st.set_page_config(page_title="Sistema Gerencial de Convênios", layout="wide")

# -----------------------------
# Estado da sessão
# -----------------------------
if "main_df" not in st.session_state:
    st.session_state.main_df = pd.DataFrame()
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None
if "last_search_ran" not in st.session_state:
    st.session_state.last_search_ran = False


# -----------------------------
# Utilidades (filtros robustos)
# -----------------------------
def _s(v) -> str:
    """Normaliza para comparação textual."""
    if v is None or (isinstance(v, float) and pd.isna(v)) or pd.isna(v):
        return ""
    return str(v).strip()


def _contains(series: pd.Series, text: str) -> pd.Series:
    """Contains case-insensitive, seguro para NaN."""
    t = _s(text)
    if not t:
        return pd.Series([True] * len(series), index=series.index)
    return series.astype("string").fillna("").str.contains(t, case=False, na=False)


def _equals_str(series: pd.Series, text: str) -> pd.Series:
    """Igualdade por string (normaliza)."""
    t = _s(text)
    if not t:
        return pd.Series([True] * len(series), index=series.index)
    return series.astype("string").fillna("").str.strip().eq(t)


def _to_float(series: pd.Series) -> pd.Series:
    """Converte coluna para float de forma segura."""
    return pd.to_numeric(series, errors="coerce")


def apply_filters(df: pd.DataFrame, f: dict) -> pd.DataFrame:
    x = df.copy()

    # Garante colunas como string onde faz sentido
    for col in ["no_instrumento", "ano", "no_processo"]:
        if col in x.columns:
            x[col] = x[col].astype("string").fillna("").str.strip()

    # --- Básicos ---
    if f.get("no_instrumento"):
        # aqui faz mais sentido igualdade exata (mas tolera string)
        if "no_instrumento" in x.columns:
            x = x[_equals_str(x["no_instrumento"], f["no_instrumento"])]

    if f.get("ano"):
        if "ano" in x.columns:
            # usuário pode digitar "2023" e no df pode vir "2023.0"
            ano_txt = _s(f["ano"])
            x = x[x["ano"].str.replace(".0", "", regex=False).eq(ano_txt)]

    if f.get("objeto"):
        if "objeto" in x.columns:
            x = x[_contains(x["objeto"], f["objeto"])]

    if f.get("no_processo"):
        if "no_processo" in x.columns:
            x = x[_contains(x["no_processo"], f["no_processo"])]

    if f.get("uf"):
        if "uf" in x.columns and f["uf"]:
            x = x[x["uf"].astype("string").fillna("").isin(f["uf"])]

    if f.get("municipio"):
        if "municipio" in x.columns:
            x = x[_contains(x["municipio"], f["municipio"])]

    if f.get("parlamentar"):
        if "parlamentar" in x.columns:
            x = x[_contains(x["parlamentar"], f["parlamentar"])]

    # Valor Global (faixa)
    vmin = f.get("valor_global_min")
    vmax = f.get("valor_global_max")
    if ("valor_global_painel" in x.columns) and (vmin is not None or vmax is not None):
        vg = _to_float(x["valor_global_painel"])
        if vmin is not None:
            vg_mask_min = vg >= float(vmin)
            x = x[vg_mask_min.fillna(False)]
        if vmax is not None:
            vg_mask_max = vg <= float(vmax)
            x = x[vg_mask_max.fillna(False)]

    # --- Celebração (PB) ---
    if f.get("situacao_pb") and "situacao_pb" in x.columns:
        x = x[_contains(x["situacao_pb"], f["situacao_pb"])]

    if f.get("analista_pb") and "analista_pb" in x.columns:
        x = x[_contains(x["analista_pb"], f["analista_pb"])]

    if f.get("status_analise_pb") and "status_analise_pb" in x.columns:
        x = x[_contains(x["status_analise_pb"], f["status_analise_pb"])]

    # --- Execução ---
    if f.get("fiscal_exec") and "fiscal_exec" in x.columns:
        x = x[_contains(x["fiscal_exec"], f["fiscal_exec"])]

    if f.get("status_exec") and "status_exec" in x.columns:
        x = x[_contains(x["status_exec"], f["status_exec"])]

    if f.get("status_acao_conv") and "status_acao_conv" in x.columns:
        x = x[_contains(x["status_acao_conv"], f["status_acao_conv"])]

    if f.get("status_obra") and "status_obra" in x.columns:
        x = x[_contains(x["status_obra"], f["status_obra"])]

    # --- Prestação de Contas ---
    if f.get("fiscal_pc") and "fiscal_pc" in x.columns:
        x = x[_contains(x["fiscal_pc"], f["fiscal_pc"])]

    if f.get("status_exec_pc") and "status_exec_pc" in x.columns:
        x = x[_contains(x["status_exec_pc"], f["status_exec_pc"])]

    if f.get("status_obra_pc") and "status_obra_pc" in x.columns:
        x = x[_contains(x["status_obra_pc"], f["status_obra_pc"])]

    if f.get("status_pc") and "status_pc" in x.columns:
        x = x[_contains(x["status_pc"], f["status_pc"])]

    return x


def can_edit_case(row: pd.Series, user_name: str, user_role: str) -> bool:
    """Regra simples: Gestor edita tudo; caso contrário só edita se estiver atribuído."""
    if user_role == "Gestor":
        return True
    eng = _s(row.get("eng_resp"))
    tec = _s(row.get("tec_resp"))
    return (eng == user_name) or (tec == user_name)


def render_detalhe(id_val: str, df_base: pd.DataFrame, user_name: str, user_role: str):
    if st.button("⬅️ Voltar", key="btn_back"):
        st.session_state.selected_id = None
        st.rerun()

    base = df_base.copy()
    base["no_instrumento"] = base.get("no_instrumento", "").astype("string").fillna("").str.strip()
    row_df = base[base["no_instrumento"].eq(str(id_val))].head(1)

    if row_df.empty:
        st.warning("Convênio não encontrado (verifique filtros/arquivo).")
        return

    row = row_df.iloc[0]
    editable = can_edit_case(row, user_name, user_role)

    st.subheader(f"Convênio: {id_val}")

    edicoes = get_edicoes(id_val)

    c1, c2 = st.columns([2, 2])

    with c1:
        st.write("**Dados automáticos (Painel)**")
        st.write(f"UF/Município: **{row.get('uf', '')} / {row.get('municipio', '')}**")
        st.write(f"Ano: **{row.get('ano', '')}**")
        st.write(f"Objeto: {row.get('objeto', '')}")
        st.write(f"Nº Processo: **{row.get('no_processo', '')}**")
        st.write(f"Parlamentar: **{row.get('parlamentar', '')}**")

        v_painel = row.get("valor_global_painel", pd.NA)
        try:
            v_painel_f = float(v_painel) if pd.notna(v_painel) else 0.0
        except Exception:
            v_painel_f = 0.0
        st.write(f"Valor Global (Painel): **R$ {v_painel_f:,.2f}**")

    with c2:
        st.write("**Campos gerenciais (preenchimento)**")
        v_manual_default = edicoes.get("valor_global_manual", v_painel_f)
        try:
            v_manual_default = float(v_manual_default)
        except Exception:
            v_manual_default = float(v_painel_f)

        v_manual = st.number_input(
            "Valor Global (Manual)",
            value=float(v_manual_default),
            min_value=0.0,
            step=1000.0,
            disabled=not editable,
            key=f"val_manual_{id_val}",
        )

        if abs(v_manual - v_painel_f) < 0.005:
            st.success("Igual ao painel")
        else:
            st.warning("Diferente do painel")

        obs = st.text_area(
            "Observações",
            value=_s(edicoes.get("observacoes", "")),
            disabled=not editable,
            key=f"obs_{id_val}",
            height=120,
        )

        if editable and st.button("Salvar", key=f"save_{id_val}"):
            save_edicao(id_val, "valor_global_manual", v_manual)
            save_edicao(id_val, "observacoes", obs)
            st.toast("Salvo!")
            st.rerun()

    st.divider()
    st.write("**Atribuição**")
    st.write(f"Eng. responsável: **{row.get('eng_resp','')}** | Téc. responsável: **{row.get('tec_resp','')}**")


# -----------------------------
# Sidebar: login e navegação
# -----------------------------
st.sidebar.title("Usuário")
user_role = st.sidebar.selectbox("Perfil", ["Engenheiro", "Técnico", "Gestor"], index=0)
user_name = st.sidebar.text_input("Nome", "Samuel Wilber").strip()

st.sidebar.divider()
menu = st.sidebar.radio(
    "Menu",
    ["Geral", "Coordenações", "Cadastros", "Atribuição", "Upload Painel", "Gerenciamento"],
)

# -----------------------------
# Upload Painel
# -----------------------------
if menu == "Upload Painel":
    st.title("Upload Painel")
    st.write("Suba múltiplas planilhas. A chave de junção é `no_instrumento`.")
    files = st.file_uploader("Arquivos XLSX", type=["xlsx"], accept_multiple_files=True)

    if st.button("Processar base", use_container_width=True):
        if not files:
            st.warning("Selecione pelo menos 1 arquivo.")
            st.stop()

        st.session_state.main_df = load_and_merge_all({f.name: f for f in files})
        st.session_state.selected_id = None
        st.session_state.last_search_ran = False
        st.success("Base atualizada.")
    st.stop()

df = st.session_state.main_df
if df is None or df.empty:
    st.warning("Ainda não há base carregada. Vá em **Upload Painel** e envie as planilhas.")
    st.stop()

# -----------------------------
# Geral
# -----------------------------
if menu == "Geral":
    st.title("Geral — Pesquisa")

    # UF options
    uf_opts = sorted(df["uf"].dropna().astype("string").unique().tolist()) if "uf" in df.columns else []

    with st.form("form_geral"):
        st.subheader("Filtros básicos")
        a1, a2, a3, a4 = st.columns(4)
        f_no_inst = a1.text_input("Nº do Instrumento")
        f_ano = a2.text_input("Ano")
        f_no_proc = a3.text_input("Nº do Processo")
        f_uf = a4.multiselect("UF", uf_opts)

        b1, b2, b3, b4 = st.columns(4)
        f_mun = b1.text_input("Município")
        f_obj = b2.text_input("Objeto")
        f_parl = b3.text_input("Parlamentar")
        b4.write("Valor Global (faixa)")
        f_vmin = b4.number_input("Mín", value=0.0, min_value=0.0, step=10000.0, key="vg_min")
        f_vmax = b4.number_input("Máx", value=0.0, min_value=0.0, step=10000.0, key="vg_max")

        st.subheader("Celebração (PB)")
        c1, c2, c3 = st.columns(3)
        f_situacao_pb = c1.text_input("Situação do Projeto Básico")
        f_analista_pb = c2.text_input("Analista do Projeto Básico")
        f_status_analise_pb = c3.text_input("Status da Análise do PB")

        st.subheader("Execução")
        d1, d2, d3, d4 = st.columns(4)
        f_fiscal_exec = d1.text_input("Fiscal de Acompanhamento (Execução)")
        f_status_exec = d2.text_input("Status da Execução")
        f_status_acao = d3.text_input("Status Ação Convenente")
        f_status_obra = d4.text_input("Status da Obra")

        st.subheader("Prestação de Contas")
        e1, e2, e3, e4 = st.columns(4)
        f_fiscal_pc = e1.text_input("Fiscal de Acompanhamento (PC)")
        f_status_exec_pc = e2.text_input("Status de Execução (PC)")
        f_status_obra_pc = e3.text_input("Status da Obra (PC)")
        f_status_pc = e4.text_input("Status Prestação de Contas")

        submitted = st.form_submit_button("Pesquisar", use_container_width=True)

    if submitted:
        st.session_state.last_search_ran = True
        st.session_state.selected_id = None

    # detalhe
    if st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, df, user_name, user_role)
        st.stop()

    # só mostra resultado se pesquisou
    if not st.session_state.last_search_ran:
        st.info("Preencha pelo menos um filtro e clique em **Pesquisar**.")
        st.stop()

    # monta dict de filtros
    filters = {
        "no_instrumento": f_no_inst,
        "ano": f_ano,
        "objeto": f_obj,
        "no_processo": f_no_proc,
        "uf": f_uf,
        "municipio": f_mun,
        "parlamentar": f_parl,
        "valor_global_min": f_vmin if f_vmin and f_vmin > 0 else None,
        "valor_global_max": f_vmax if f_vmax and f_vmax > 0 else None,
        "situacao_pb": f_situacao_pb,
        "analista_pb": f_analista_pb,
        "status_analise_pb": f_status_analise_pb,
        "fiscal_exec": f_fiscal_exec,
        "status_exec": f_status_exec,
        "status_acao_conv": f_status_acao,
        "status_obra": f_status_obra,
        "fiscal_pc": f_fiscal_pc,
        "status_exec_pc": f_status_exec_pc,
        "status_obra_pc": f_status_obra_pc,
        "status_pc": f_status_pc,
    }

    res = apply_filters(df, filters)

    st.write(f"**{len(res)}** resultados encontrados.")
    if res.empty:
        st.warning("Nenhum resultado. Dica: tente remover filtros muito específicos ou use partes do texto (ex.: só um sobrenome).")
        st.stop()

    # lista visual (expansível)
    show_cols = [c for c in ["no_instrumento", "ano", "uf", "municipio", "objeto", "status_exec", "status_obra"] if c in res.columns]
    res_show = res[show_cols].copy() if show_cols else res.copy()

    for i, (_, r) in enumerate(res_show.head(200).iterrows()):
        id_v = _s(r.get("no_instrumento"))
        title = f"{id_v} — {r.get('municipio','')} ({r.get('uf','')})"
        with st.expander(title):
            st.write(f"**Objeto:** {r.get('objeto','')}")
            st.write(f"Ano: **{r.get('ano','')}** | Nº Processo: **{r.get('no_processo','')}**")
            if st.button("Ver/abrir", key=f"open_geral_{i}_{id_v}"):
                st.session_state.selected_id = id_v
                st.rerun()

    st.caption("Mostrando até 200 registros (para performance).")

# -----------------------------
# Coordenações (estrutura mínima por enquanto)
# -----------------------------
elif menu == "Coordenações":
    st.title("Coordenações")

    tab_cel, tab_exe, tab_pc = st.tabs(["Celebração", "Execução", "Prestação de Contas"])

    # casos atribuídos
    if "eng_resp" not in df.columns:
        df["eng_resp"] = pd.NA
    if "tec_resp" not in df.columns:
        df["tec_resp"] = pd.NA

    meus = df[(df["eng_resp"].astype("string").fillna("").str.strip() == user_name) | (df["tec_resp"].astype("string").fillna("").str.strip() == user_name)]

    def coord_filters_form(prefix: str):
        uf_opts2 = sorted(meus["uf"].dropna().astype("string").unique().tolist()) if "uf" in meus.columns else []
        c1, c2, c3, c4 = st.columns(4)
        f_inst = c1.text_input("Nº do Instrumento", key=f"{prefix}_inst")
        f_ano = c2.text_input("Ano", key=f"{prefix}_ano")
        f_uf = c3.multiselect("UF", uf_opts2, key=f"{prefix}_uf")
        f_mun = c4.text_input("Município", key=f"{prefix}_mun")
        f_obj = st.text_input("Objeto", key=f"{prefix}_obj")
        return f_inst, f_ano, f_uf, f_mun, f_obj

    if st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, df, user_name, user_role)
        st.stop()

    with tab_cel:
        st.subheader("Meus casos — Celebração")
        f_inst, f_ano, f_uf, f_mun, f_obj = coord_filters_form("cel")

        filters = {
            "no_instrumento": f_inst,
            "ano": f_ano,
            "uf": f_uf,
            "municipio": f_mun,
            "objeto": f_obj,
            "situacao_pb": st.text_input("Situação do PB", key="cel_sit_pb"),
            "analista_pb": st.text_input("Analista do PB", key="cel_anal_pb"),
            "status_analise_pb": st.text_input("Status da Análise do PB", key="cel_stat_pb"),
        }
        res = apply_filters(meus, filters)

        cols = [c for c in ["no_instrumento", "ano", "uf", "municipio", "objeto", "situacao_pb", "analista_pb", "status_analise_pb"] if c in res.columns]
        for i, (_, r) in enumerate(res.head(200).iterrows()):
            id_v = _s(r.get("no_instrumento"))
            with st.expander(f"{id_v} — {r.get('municipio','')} ({r.get('uf','')})"):
                for c in cols:
                    if c not in ["objeto"]:
                        st.write(f"**{c}**: {r.get(c,'')}")
                st.write(f"**Objeto:** {r.get('objeto','')}")
                if st.button("Ver/Editar", key=f"open_cel_{i}_{id_v}"):
                    st.session_state.selected_id = id_v
                    st.rerun()

    with tab_exe:
        st.subheader("Meus casos — Execução")
        f_inst, f_ano, f_uf, f_mun, f_obj = coord_filters_form("exe")

        filters = {
            "no_instrumento": f_inst,
            "ano": f_ano,
            "uf": f_uf,
            "municipio": f_mun,
            "objeto": f_obj,
            "fiscal_exec": st.text_input("Fiscal (Execução)", key="exe_fisc"),
            "status_exec": st.text_input("Status Execução", key="exe_stat"),
            "status_acao_conv": st.text_input("Status Ação Convenente", key="exe_acao"),
            "status_obra": st.text_input("Status Obra", key="exe_obra"),
        }
        res = apply_filters(meus, filters)

        cols = [c for c in ["no_instrumento", "ano", "uf", "municipio", "objeto", "status_exec", "status_obra"] if c in res.columns]
        for i, (_, r) in enumerate(res.head(200).iterrows()):
            id_v = _s(r.get("no_instrumento"))
            with st.expander(f"{id_v} — {r.get('municipio','')} ({r.get('uf','')})"):
                for c in cols:
                    if c not in ["objeto"]:
                        st.write(f"**{c}**: {r.get(c,'')}")
                st.write(f"**Objeto:** {r.get('objeto','')}")
                if st.button("Ver/Editar", key=f"open_exe_{i}_{id_v}"):
                    st.session_state.selected_id = id_v
                    st.rerun()

    with tab_pc:
        st.subheader("Meus casos — Prestação de Contas")
        f_inst, f_ano, f_uf, f_mun, f_obj = coord_filters_form("pc")

        filters = {
            "no_instrumento": f_inst,
            "ano": f_ano,
            "uf": f_uf,
            "municipio": f_mun,
            "objeto": f_obj,
            "fiscal_pc": st.text_input("Fiscal (PC)", key="pc_fisc"),
            "status_exec_pc": st.text_input("Status Execução (PC)", key="pc_exec"),
            "status_obra_pc": st.text_input("Status Obra (PC)", key="pc_obra"),
            "status_pc": st.text_input("Status Prestação de Contas", key="pc_status"),
        }
        res = apply_filters(meus, filters)

        cols = [c for c in ["no_instrumento", "ano", "uf", "municipio", "objeto", "status_exec_pc", "status_obra_pc", "status_pc"] if c in res.columns]
        for i, (_, r) in enumerate(res.head(200).iterrows()):
            id_v = _s(r.get("no_instrumento"))
            with st.expander(f"{id_v} — {r.get('municipio','')} ({r.get('uf','')})"):
                for c in cols:
                    if c not in ["objeto"]:
                        st.write(f"**{c}**: {r.get(c,'')}")
                st.write(f"**Objeto:** {r.get('objeto','')}")
                if st.button("Ver/Editar", key=f"open_pc_{i}_{id_v}"):
                    st.session_state.selected_id = id_v
                    st.rerun()

# -----------------------------
# Placeholders (manter sem quebrar)
# -----------------------------
elif menu == "Atribuição":
    st.title("Atribuição")
    st.info("Ainda não implementado nesta versão do app.py.")

elif menu == "Cadastros":
    st.title("Cadastros")
    st.info("Ainda não implementado nesta versão do app.py.")

elif menu == "Gerenciamento":
    st.title("Gerenciamento")
    st.info("Ainda não implementado nesta versão do app.py.")
