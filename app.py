import streamlit as st
import pandas as pd

from utils.data import (
    load_and_merge_all,
    save_edicao_com_historico,
    get_edicoes,
    get_historico,
    save_atribuicao,   # <- agora importado (antes estava faltando)
)

st.set_page_config(page_title="Sistema Gerencial de Convênios", layout="wide")

# -----------------------------
# Helpers
# -----------------------------
def _s(x):
    """String safe (para comparar IDs)."""
    if x is None or (isinstance(x, float) and pd.isna(x)) or pd.isna(x):
        return ""
    return str(x).strip()

def _col(df, name):
    """Garante coluna no DF."""
    if name not in df.columns:
        df[name] = pd.NA
    return df

def identificar_fase(row: pd.Series) -> str:
    """
    Regra:
    - Celebração: sem nº instrumento OU contém 'SUSPENSIVA' na situação contratual
    - Prestação de Contas: status contém 'PRESTA' (ajuste se necessário)
    - Execução: caso contrário
    """
    no_inst = _s(row.get("no_instrumento"))
    status = _s(row.get("status_painel")).upper()
    sit_contratual = _s(row.get("situacao_contratual")).upper()

    if (not no_inst) or ("SUSPENSIVA" in sit_contratual):
        return "Celebração"
    if "PRESTA" in status:
        return "Prestação de Contas"
    return "Execução"

def get_id_from_row(r: pd.Series) -> str:
    """Preferência: nº instrumento; se não tiver, nº proposta."""
    ni = _s(r.get("no_instrumento"))
    np = _s(r.get("no_proposta"))
    return ni if ni else np

def filter_by_id(df: pd.DataFrame, id_val: str) -> pd.DataFrame:
    id_val = _s(id_val)
    if not id_val:
        return df.iloc[0:0]

    df = _col(df, "no_instrumento")
    df = _col(df, "no_proposta")

    a = df["no_instrumento"].astype("string").fillna("").str.strip()
    b = df["no_proposta"].astype("string").fillna("").str.strip()

    return df[(a == id_val) | (b == id_val)]

def apply_contains(df: pd.DataFrame, col: str, value: str) -> pd.DataFrame:
    value = _s(value)
    if not value:
        return df
    if col not in df.columns:
        return df.iloc[0:0]
    return df[df[col].astype("string").fillna("").str.contains(value, case=False, na=False)]


# -----------------------------
# Session State
# -----------------------------
if "main_df" not in st.session_state:
    st.session_state.main_df = pd.DataFrame()

if "selected_id" not in st.session_state:
    st.session_state.selected_id = None

if "test_records" not in st.session_state:
    # DF local para registros manuais (teste)
    st.session_state.test_records = pd.DataFrame(
        columns=[
            "no_instrumento", "no_proposta", "ano", "uf", "municipio", "objeto",
            "no_processo", "parlamentar", "valor_global_painel",
            "status_painel", "situacao_contratual",
            "eng_resp", "tec_resp",
        ]
    )

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("👤 Usuário")
user_role = st.sidebar.selectbox("Perfil", ["Engenheiro", "Técnico", "Gestor"])
user_name = st.sidebar.text_input("Nome (login)", "Samuel Wilber")

st.sidebar.divider()
menu = st.sidebar.radio(
    "Menu",
    ["Geral", "Coordenações", "Cadastro Manual (Teste)", "Atribuição", "Upload"],
)

# -----------------------------
# Fonte de dados consolidada:
# planilhas (main_df) + registros manuais de teste
# -----------------------------
df_files = st.session_state.main_df.copy()
df_test = st.session_state.test_records.copy()

# padroniza colunas mínimas pra não quebrar filtros
for base in (df_files, df_test):
    for c in [
        "no_instrumento", "no_proposta", "ano", "objeto", "no_processo",
        "uf", "municipio", "parlamentar", "valor_global_painel",
        "status_painel", "situacao_contratual", "eng_resp", "tec_resp",
        "situacao_pb", "analista_pb", "status_analise_pb",
        "fiscal_exec", "status_exec", "status_acao_conv", "status_obra",
        "fiscal_pc", "status_exec_pc", "status_obra_pc", "status_pc",
    ]:
        _col(base, c)

df = pd.concat([df_files, df_test], ignore_index=True)

# força ids como string (evita 909561 virar float)
for c in ["no_instrumento", "no_proposta", "no_processo"]:
    if c in df.columns:
        df[c] = df[c].astype("string")

# -----------------------------
# Detalhe (Geral/Coordenações)
# -----------------------------
def render_detalhe(id_val: str, can_edit: bool):
    if st.button("⬅️ Voltar para a lista"):
        st.session_state.selected_id = None
        st.rerun()

    filtered = filter_by_id(df, id_val)

    if filtered.empty:
        st.error(f"Registro {id_val} não encontrado na base. (Pode ser ID antigo ou filtro/seleção incorreta.)")
        return

    row = filtered.iloc[0]
    fase = identificar_fase(row)
    real_id = get_id_from_row(row)

    st.header(f"📌 {fase}: {real_id}")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Dados automáticos (Painel)")
        st.write(f"**Instrumento:** {_s(row.get('no_instrumento')) or '-'}")
        st.write(f"**Proposta:** {_s(row.get('no_proposta')) or '-'}")
        st.write(f"**Processo:** {_s(row.get('no_processo')) or '-'}")
        st.write(f"**Ano:** {_s(row.get('ano')) or '-'}")
        st.write(f"**UF/Município:** {_s(row.get('uf'))} / {_s(row.get('municipio'))}")
        st.write(f"**Parlamentar:** {_s(row.get('parlamentar')) or '-'}")
        st.write(f"**Objeto:** {_s(row.get('objeto')) or '-'}")
        st.write(f"**Status (Painel):** {_s(row.get('status_painel')) or '-'}")
        st.write(f"**Situação contratual:** {_s(row.get('situacao_contratual')) or '-'}")

        val_p = row.get("valor_global_painel")
        try:
            val_p_num = float(val_p) if pd.notna(val_p) and _s(val_p) else 0.0
        except Exception:
            val_p_num = 0.0
        st.write(f"**Valor Global (Painel):** R$ {val_p_num:,.2f}")

    with col2:
        st.subheader("Dados manuais (interno)")
        ed = get_edicoes(real_id)

        val_m = st.number_input(
            "Valor Global Gerencial",
            value=float(ed.get("valor_manual", val_p_num)),
            disabled=not can_edit,
        )

        if abs(val_m - val_p_num) < 0.000001:
            st.success("Igual ao Painel")
        else:
            st.warning("Diferente do Painel")

        obs = st.text_area(
            "Observações / Anotações",
            value=_s(ed.get("observacoes", "")),
            disabled=not can_edit,
            height=140,
        )

        if can_edit and st.button("Salvar alterações"):
            save_edicao_com_historico(real_id, "valor_manual", val_m, user_name)
            save_edicao_com_historico(real_id, "observacoes", obs, user_name)
            st.toast("Salvo com histórico.")

    st.divider()
    st.subheader("Histórico de alterações")
    hist = get_historico(real_id)
    if hist is None or (hasattr(hist, "empty") and hist.empty):
        st.write("Sem histórico ainda.")
    else:
        st.dataframe(hist, use_container_width=True)


# -----------------------------
# Upload
# -----------------------------
if menu == "Upload":
    st.header("📂 Upload das planilhas")
    files = st.file_uploader("Suba os arquivos do Painel/TransferGov", accept_multiple_files=True)
    if st.button("Processar base"):
        if not files:
            st.warning("Anexe pelo menos 1 arquivo.")
        else:
            st.session_state.main_df = load_and_merge_all({f.name: f for f in files})
            st.success("Base carregada.")
            st.rerun()


# -----------------------------
# Cadastro manual para teste
# -----------------------------
elif menu == "Cadastro Manual (Teste)":
    st.header("🧪 Cadastro Manual (apenas para testes)")

    with st.form("form_cad_manual"):
        c1, c2 = st.columns(2)
        no_instrumento = c1.text_input("Nº Instrumento (se já celebrado)")
        no_proposta = c2.text_input("Nº Proposta (se ainda em celebração)")

        c3, c4, c5 = st.columns(3)
        ano = c3.text_input("Ano")
        uf = c4.text_input("UF")
        municipio = c5.text_input("Município")

        objeto = st.text_input("Objeto")
        no_processo = st.text_input("Nº Processo")
        parlamentar = st.text_input("Parlamentar")
        valor_global = st.number_input("Valor Global (Painel)", value=0.0)

        c6, c7 = st.columns(2)
        status_painel = c6.text_input("Status (Painel)", value="EM ANDAMENTO")
        situacao_contratual = c7.text_input("Situação contratual", value="")

        c8, c9 = st.columns(2)
        eng_resp = c8.text_input("Eng. Responsável (para cair em Coordenações)", value=user_name)
        tec_resp = c9.text_input("Tec. Responsável", value="")

        submitted = st.form_submit_button("Cadastrar")
        if submitted:
            if not _s(no_instrumento) and not _s(no_proposta):
                st.error("Informe pelo menos Nº Instrumento ou Nº Proposta.")
            else:
                new_row = {
                    "no_instrumento": _s(no_instrumento) or pd.NA,
                    "no_proposta": _s(no_proposta) or pd.NA,
                    "ano": _s(ano) or pd.NA,
                    "uf": _s(uf) or pd.NA,
                    "municipio": _s(municipio) or pd.NA,
                    "objeto": _s(objeto) or pd.NA,
                    "no_processo": _s(no_processo) or pd.NA,
                    "parlamentar": _s(parlamentar) or pd.NA,
                    "valor_global_painel": float(valor_global),
                    "status_painel": _s(status_painel) or pd.NA,
                    "situacao_contratual": _s(situacao_contratual) or pd.NA,
                    "eng_resp": _s(eng_resp) or pd.NA,
                    "tec_resp": _s(tec_resp) or pd.NA,
                }
                st.session_state.test_records = pd.concat(
                    [st.session_state.test_records, pd.DataFrame([new_row])],
                    ignore_index=True
                )
                st.success("Registro criado. Vá em Geral ou Coordenações para testar.")
                st.rerun()


# -----------------------------
# Geral (somente leitura) com filtros "de ontem"
# -----------------------------
elif menu == "Geral":
    st.header("🔎 Geral (consulta — somente leitura)")

    with st.form("search_geral"):
        st.write("### Filtros gerais")
        c1, c2, c3, c4 = st.columns(4)
        f_inst = c1.text_input("Nº do Instrumento")
        f_ano = c2.text_input("Ano")
        f_obj = c3.text_input("Objeto")
        f_proc = c4.text_input("Nº do processo")

        c5, c6, c7, c8 = st.columns(4)
        f_uf = c5.multiselect("UF", sorted([_s(x) for x in df["uf"].dropna().unique() if _s(x)]))
        f_mun = c6.text_input("Município")
        f_parl = c7.text_input("Parlamentar")
        f_val_min = c8.number_input("Valor Global (mín.)", value=0.0)

        st.write("### Filtros por coordenação (aparecem no Geral, mas só consulta)")
        d1, d2, d3 = st.columns(3)
        with d1:
            f_pb_sit = st.text_input("Situação do Projeto Básico")
            f_pb_ana = st.text_input("Analista do Projeto Básico (Celebração)")
            f_pb_stat = st.text_input("Status da Análise do Projeto Básico")
        with d2:
            f_ex_fisc = st.text_input("Fiscal Execução")
            f_ex_stat = st.text_input("Status da Execução")
            f_ex_acao = st.text_input("Status Ação Convenente")
            f_ex_obra = st.text_input("Status da Obra")
        with d3:
            f_pc_fisc = st.text_input("Fiscal Prestação de Contas")
            f_pc_exec = st.text_input("Status Execução (PC)")
            f_pc_obra = st.text_input("Status Obra (PC)")
            f_pc_stat = st.text_input("Status Prestação de Contas")

        # Extra útil (você comentou): pesquisar pelo responsável
        st.write("### Responsáveis (consulta)")
        r1, r2 = st.columns(2)
        f_eng = r1.text_input("Eng. atribuído")
        f_tec = r2.text_input("Tec. atribuído")

        submitted = st.form_submit_button("Pesquisar")

    if st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, can_edit=False)
    elif submitted:
        res = df.copy()

        # filtros gerais
        if _s(f_inst):
            res = res[res["no_instrumento"].astype("string").fillna("").str.strip() == _s(f_inst)]
        if _s(f_ano):
            res = apply_contains(res, "ano", f_ano)
        if _s(f_obj):
            res = apply_contains(res, "objeto", f_obj)
        if _s(f_proc):
            res = apply_contains(res, "no_processo", f_proc)
        if f_uf:
            res = res[res["uf"].astype("string").fillna("").isin(f_uf)]
        if _s(f_mun):
            res = apply_contains(res, "municipio", f_mun)
        if _s(f_parl):
            res = apply_contains(res, "parlamentar", f_parl)
        if f_val_min and "valor_global_painel" in res.columns:
            res = res[pd.to_numeric(res["valor_global_painel"], errors="coerce").fillna(0) >= float(f_val_min)]

        # filtros por coordenação
        res = apply_contains(res, "situacao_pb", f_pb_sit)
        res = apply_contains(res, "analista_pb", f_pb_ana)
        res = apply_contains(res, "status_analise_pb", f_pb_stat)

        res = apply_contains(res, "fiscal_exec", f_ex_fisc)
        res = apply_contains(res, "status_exec", f_ex_stat)
        res = apply_contains(res, "status_acao_conv", f_ex_acao)
        res = apply_contains(res, "status_obra", f_ex_obra)

        res = apply_contains(res, "fiscal_pc", f_pc_fisc)
        res = apply_contains(res, "status_exec_pc", f_pc_exec)
        res = apply_contains(res, "status_obra_pc", f_pc_obra)
        res = apply_contains(res, "status_pc", f_pc_stat)

        # responsáveis
        res = apply_contains(res, "eng_resp", f_eng)
        res = apply_contains(res, "tec_resp", f_tec)

        st.write(f"**{len(res)}** resultado(s).")

        for idx, r in res.iterrows():
            id_v = get_id_from_row(r)
            fase = identificar_fase(r)
            titulo = f"{id_v} — {fase} — {_s(r.get('municipio'))} ({_s(r.get('uf'))})"
            with st.expander(titulo):
                st.write(f"**Objeto:** {_s(r.get('objeto'))}")
                st.write(f"**Responsável:** {_s(r.get('eng_resp')) or '-'}")
                if st.button("Abrir", key=f"abrir_geral_{idx}_{id_v}"):
                    st.session_state.selected_id = id_v
                    st.rerun()
    else:
        st.info("Use os filtros acima e clique em **Pesquisar**.")


# -----------------------------
# Coordenações (editável)
# -----------------------------
elif menu == "Coordenações":
    st.header(f"📑 Coordenações — {user_name}")

    # Meus casos: usuário é eng ou tec, ou gestor (gestor vê tudo mas edita dependendo regra)
    if user_role == "Gestor":
        meus = df.copy()
    else:
        meus = df[(df["eng_resp"].astype("string").fillna("").str.strip() == _s(user_name)) |
                  (df["tec_resp"].astype("string").fillna("").str.strip() == _s(user_name))].copy()

    # filtros rápidos
    with st.expander("Filtros", expanded=True):
        c1, c2 = st.columns(2)
        f_mun = c1.text_input("Município", key="coord_mun")
        f_inst = c2.text_input("Nº Instrumento/Proposta", key="coord_id")
    if _s(f_mun):
        meus = apply_contains(meus, "municipio", f_mun)
    if _s(f_inst):
        # tenta filtrar por instrumento OU proposta
        idq = _s(f_inst)
        a = meus["no_instrumento"].astype("string").fillna("").str.strip()
        b = meus["no_proposta"].astype("string").fillna("").str.strip()
        meus = meus[(a == idq) | (b == idq)]

    if st.session_state.selected_id:
        # Permissão: edita se (é gestor) OU (é responsável)
        if user_role == "Gestor":
            can_edit = True
        else:
            rec = filter_by_id(df, st.session_state.selected_id)
            if rec.empty:
                can_edit = False
            else:
                rr = rec.iloc[0]
                can_edit = (_s(rr.get("eng_resp")) == _s(user_name)) or (_s(rr.get("tec_resp")) == _s(user_name))
        render_detalhe(st.session_state.selected_id, can_edit=can_edit)
    else:
        tabs = st.tabs(["Celebração", "Execução", "Prestação de Contas"])

        for tab, fase_nome in zip(tabs, ["Celebração", "Execução", "Prestação de Contas"]):
            with tab:
                subset = meus[meus.apply(identificar_fase, axis=1) == fase_nome].copy()
                st.write(f"**{len(subset)}** caso(s) em {fase_nome}.")

                for idx, r in subset.iterrows():
                    id_v = get_id_from_row(r)
                    titulo = f"{id_v} — {_s(r.get('municipio'))} ({_s(r.get('uf'))})"
                    with st.expander(titulo):
                        st.write(f"**Objeto:** {_s(r.get('objeto'))}")
                        if st.button("Abrir / Editar", key=f"abrir_coord_{fase_nome}_{idx}_{id_v}"):
                            st.session_state.selected_id = id_v
                            st.rerun()


# -----------------------------
# Atribuição (para gestor)
# -----------------------------
elif menu == "Atribuição":
    st.header("⚖️ Atribuição de casos")

    if user_role != "Gestor":
        st.error("Acesso restrito (apenas Gestor).")
    else:
        # lista de IDs possíveis (instrumento ou proposta)
        df_ids = df.copy()
        df_ids["id_case"] = df_ids.apply(get_id_from_row, axis=1)
        options = sorted([x for x in df_ids["id_case"].unique() if _s(x)])

        if not options:
            st.warning("Não há registros na base ainda. Use Upload ou Cadastro Manual (Teste).")
        else:
            id_case = st.selectbox("Selecione o Instrumento/Proposta", options)
            eng = st.text_input("Engenheiro responsável")
            tec = st.text_input("Técnico responsável")

            if st.button("Salvar atribuição"):
                # O save_atribuicao precisa saber se é instrumento ou proposta
                is_inst = bool(filter_by_id(df[df["no_instrumento"].notna()], id_case).shape[0])
                save_atribuicao(id_case, is_inst, eng, tec)
                st.success("Atribuição salva. Vá em Coordenações para ver.")
