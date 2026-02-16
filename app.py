import streamlit as st
import pandas as pd

from utils.data import (
    load_and_merge_all,
    save_edicao_com_historico,
    get_edicoes,
    get_historico,
)

st.set_page_config(page_title="Sistema Gerencial de Convênios", layout="wide")


# =========================
# Helpers (sem “dados inventados”)
# =========================
def _ensure_session_state():
    if "main_df" not in st.session_state:
        st.session_state.main_df = pd.DataFrame()
    if "selected_id" not in st.session_state:
        st.session_state.selected_id = None


def _has_cols(df: pd.DataFrame, cols: list[str]) -> bool:
    return all(c in df.columns for c in cols)


def _safe_str_series(df: pd.DataFrame, col: str) -> pd.Series:
    if col not in df.columns:
        return pd.Series([""] * len(df), index=df.index, dtype="string")
    return df[col].astype("string")


def _get_case_id(row: pd.Series) -> str:
    """
    Retorna um ID “único” para abrir o detalhe:
    prioriza no_instrumento; se vazio, usa no_proposta.
    """
    ni = row.get("no_instrumento", pd.NA)
    np = row.get("no_proposta", pd.NA)
    if pd.notna(ni) and str(ni).strip():
        return str(ni).strip()
    if pd.notna(np) and str(np).strip():
        return str(np).strip()
    # fallback: nunca deveria acontecer se a base estiver bem formada
    return f"row_{row.name}"


def identificar_fase(row: pd.Series) -> str:
    """
    Regra atual (sem Prestação por enquanto, mas já previsto):
    - Se NÃO tem no_instrumento -> Celebração (proposta)
    - Se tem "suspensiva" na situação contratual -> Celebração
    - Se status contém "PRESTA" -> Prestação de Contas (deixa pronto)
    - Senão -> Execução
    """
    status = str(row.get("status_painel", "") or "").upper()
    sit_contratual = str(row.get("situacao_contratual", "") or "").upper()

    no_instrumento = row.get("no_instrumento", pd.NA)
    if pd.isna(no_instrumento) or str(no_instrumento).strip() == "":
        return "Celebração"

    if "SUSPENSIVA" in sit_contratual:
        return "Celebração"

    if "PRESTA" in status:
        return "Prestação de Contas"

    return "Execução"


def _can_edit_convenio(row: pd.Series, user_name: str, user_role: str) -> bool:
    """
    Edita convênio apenas:
    - Gestor sempre
    - Eng/Téc se for responsável do convênio (eng_resp ou tec_resp)
    """
    if user_role == "Gestor":
        return True

    eng = str(row.get("eng_resp", "") or "").strip()
    tec = str(row.get("tec_resp", "") or "").strip()
    u = str(user_name or "").strip()
    return (eng == u) or (tec == u)


def _can_edit_vistoria(row: pd.Series, user_name: str, user_role: str) -> bool:
    """
    Edita vistoria apenas:
    - Gestor sempre
    - usuário se for responsável da vistoria (vistoria_resp)
    """
    if user_role == "Gestor":
        return True

    vis = str(row.get("vistoria_resp", "") or "").strip()
    u = str(user_name or "").strip()
    return vis == u


def render_detalhe(df: pd.DataFrame, id_val: str, modo: str, user_name: str, user_role: str):
    """
    modo:
      - 'leitura'  -> Geral (somente leitura total)
      - 'convenio' -> Coordenações (edita só se for responsável convênio/gestor)
      - 'vistoria' -> Vistorias (edita somente campos de vistoria se for responsável vistoria/gestor)
    """
    if st.button("⬅️ Voltar para a lista"):
        st.session_state.selected_id = None
        st.rerun()

    # encontra linha (instrumento ou proposta)
    if not _has_cols(df, ["no_instrumento"]) and not _has_cols(df, ["no_proposta"]):
        st.error("Sua base não tem 'no_instrumento' nem 'no_proposta' (após normalização). Verifique o utils/data.py.")
        return

    mask = pd.Series([False] * len(df), index=df.index)
    if "no_instrumento" in df.columns:
        mask = mask | (df["no_instrumento"].astype("string") == str(id_val))
    if "no_proposta" in df.columns:
        mask = mask | (df["no_proposta"].astype("string") == str(id_val))

    filtered = df[mask]
    if filtered.empty:
        st.error(f"Registro '{id_val}' não encontrado na base.")
        return

    row = filtered.iloc[0]
    fase = identificar_fase(row)

    can_edit_conv = _can_edit_convenio(row, user_name, user_role)
    can_edit_vis = _can_edit_vistoria(row, user_name, user_role)

    # trava conforme modo
    if modo == "leitura":
        allow_conv_edit = False
        allow_vis_edit = False
    elif modo == "convenio":
        allow_conv_edit = can_edit_conv
        allow_vis_edit = False
    elif modo == "vistoria":
        allow_conv_edit = False
        allow_vis_edit = can_edit_vis
    else:
        allow_conv_edit = False
        allow_vis_edit = False

    st.header(f"📌 {fase}: {id_val}")

    # ========= Dados automáticos (painel)
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏛️ Dados Automáticos (Painel) — Leitura")
        st.write(f"**Objeto:** {row.get('objeto', '')}")
        st.write(f"**UF:** {row.get('uf', '')}")
        st.write(f"**Município:** {row.get('municipio', '')}")
        st.write(f"**Parlamentar:** {row.get('parlamentar', '')}")
        st.write(f"**Status (Painel):** {row.get('status_painel', '')}")
        st.write(f"**Situação Contratual:** {row.get('situacao_contratual', '')}")
        st.write(f"**Nº Processo/NUP:** {row.get('no_processo', '')}")

        if "valor_global" in df.columns:
            try:
                st.write(f"**Valor Global (Painel):** {float(row.get('valor_global', 0) or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
            except Exception:
                st.write(f"**Valor Global (Painel):** {row.get('valor_global', '')}")

    # ========= Dados manuais (gerencial) + alertas
    with c2:
        st.subheader("✍️ Dados Manuais (Gerencial)")
        edicoes = get_edicoes(id_val)

        # exemplo 1: valor manual vs painel
        val_painel = row.get("valor_global", 0)
        try:
            val_painel_num = float(val_painel) if pd.notna(val_painel) and str(val_painel).strip() != "" else 0.0
        except Exception:
            val_painel_num = 0.0

        valor_manual = st.number_input(
            "Valor Global (Manual)",
            value=float(edicoes.get("valor_manual", val_painel_num) or 0.0),
            disabled=not allow_conv_edit,
        )

        if pd.notna(val_painel) and str(val_painel).strip() != "":
            if float(valor_manual) == float(val_painel_num):
                st.success("Igual ao Painel")
            else:
                st.error("Diferente do Painel")

        observacoes = st.text_area(
            "Observações / Anotações",
            value=str(edicoes.get("observacoes", "") or ""),
            disabled=(modo == "leitura") or (not allow_conv_edit and modo == "convenio"),
        )

        if st.button("Salvar (Convênio)", disabled=not allow_conv_edit):
            save_edicao_com_historico(id_val, "valor_manual", valor_manual, user_name)
            save_edicao_com_historico(id_val, "observacoes", observacoes, user_name)
            st.toast("Alterações do convênio salvas.")
            st.rerun()

    # ========= Bloco de Vistoria (editável só no modo vistoria)
    st.divider()
    st.subheader("🟣 Vistoria (somente responsável da vistoria ou gestor)")
    edicoes = get_edicoes(id_val)

    tipo_vistoria = st.text_input(
        "Tipo de Vistoria",
        value=str(edicoes.get("vistoria_tipo", "") or ""),
        disabled=not allow_vis_edit,
    )
    data_vistoria = st.date_input(
        "Data da Vistoria",
        value=pd.to_datetime(edicoes.get("vistoria_data", pd.Timestamp.today())).date()
        if edicoes.get("vistoria_data") else pd.Timestamp.today().date(),
        disabled=not allow_vis_edit,
    )
    perc_exec = st.slider(
        "% Execução (Vistoria)",
        0, 100,
        int(float(edicoes.get("vistoria_perc", 0) or 0)),
        disabled=not allow_vis_edit,
    )
    obs_vistoria = st.text_area(
        "Observações da Vistoria",
        value=str(edicoes.get("vistoria_obs", "") or ""),
        disabled=not allow_vis_edit,
    )

    if st.button("Salvar (Vistoria)", disabled=not allow_vis_edit):
        save_edicao_com_historico(id_val, "vistoria_tipo", tipo_vistoria, user_name)
        save_edicao_com_historico(id_val, "vistoria_data", str(data_vistoria), user_name)
        save_edicao_com_historico(id_val, "vistoria_perc", perc_exec, user_name)
        save_edicao_com_historico(id_val, "vistoria_obs", obs_vistoria, user_name)
        st.toast("Alterações de vistoria salvas.")
        st.rerun()

    # ========= Histórico
    st.divider()
    st.subheader("📜 Histórico de Alterações")
    hist = get_historico(id_val)
    if hist is None or (hasattr(hist, "empty") and hist.empty):
        st.write("Sem registros ainda.")
    else:
        cols = [c for c in ["data_hora", "usuario", "campo", "valor"] if c in hist.columns]
        st.dataframe(hist[cols], use_container_width=True)


# =========================
# UI principal
# =========================
_ensure_session_state()

# Sidebar: login e menu
st.sidebar.title("👤 Usuário")
user_name = st.sidebar.text_input("Nome", "Samuel Wilber")
user_role = st.sidebar.selectbox("Perfil", ["Engenheiro", "Técnico", "Gestor"])

# Avisos (placeholder — sem inventar contagens)
st.sidebar.divider()
st.sidebar.subheader("🔔 Avisos")
st.sidebar.info("Os avisos serão calculados com base na sua base após o upload.")

# Menu
menu_options = ["Geral", "Coordenações", "Vistorias", "Upload Painel"]
if user_role == "Gestor":
    menu_options += ["Atribuição"]
menu = st.sidebar.radio("Menu Principal", menu_options)

df = st.session_state.main_df

# Se não tem base, só libera Upload
if df.empty and menu != "Upload Painel":
    st.warning("Nenhuma base carregada. Vá em **Upload Painel**, envie os arquivos e clique em **Processar Base**.")
    st.stop()


# =========================
# Aba: Upload Painel
# =========================
if menu == "Upload Painel":
    st.header("📂 Upload de Planilhas (Base de Dados)")

    st.write(
        "Envie suas planilhas do painel. Após clicar em **Processar Base**, "
        "a base será carregada em memória e as pesquisas começarão a fazer sentido."
    )

    files = st.file_uploader(
        "Suba os arquivos (pode ser 1 ou vários).",
        accept_multiple_files=True,
        type=["xlsx", "xls", "csv"],
    )

    if st.button("Processar Base"):
        if not files:
            st.error("Nenhum arquivo enviado.")
        else:
            # Passa {nome: arquivo} para o loader
            st.session_state.main_df = load_and_merge_all({f.name: f for f in files})
            st.session_state.selected_id = None
            st.success("Base carregada.")
            st.write("Colunas detectadas:")
            st.code(", ".join(list(st.session_state.main_df.columns)))
            st.rerun()


# =========================
# Aba: Geral (somente leitura + filtros completos)
# =========================
elif menu == "Geral":
    st.header("🔍 Geral — Consulta (Somente leitura)")

    with st.form("search_geral"):
        st.write("### Filtros de Pesquisa")

        c1, c2, c3, c4 = st.columns(4)
        f_inst = c1.text_input("Nº do Instrumento")
        f_ano = c2.text_input("Ano")
        f_obj = c3.text_input("Objeto")
        f_proc = c4.text_input("Nº do Processo (NUP)")

        c5, c6, c7, c8 = st.columns(4)
        uf_options = sorted([x for x in _safe_str_series(df, "uf").dropna().unique().tolist() if x])
        f_uf = c5.multiselect("UF", uf_options)
        f_mun = c6.text_input("Município")
        f_parl = c7.text_input("Parlamentar")
        f_val_min = c8.number_input("Valor Global (mín.)", min_value=0.0, value=0.0)

        st.write("---")
        st.write("#### Filtros por Coordenações (campos internos/gerenciais, se existirem na base)")
        cc1, cc2, cc3 = st.columns(3)
        with cc1:
            f_sit_pb = st.text_input("Situação do Projeto Básico")
            f_analista_pb = st.text_input("Analista do Projeto Básico")
            f_status_analise_pb = st.text_input("Status da Análise do Projeto Básico")
        with cc2:
            f_fiscal_exec = st.text_input("Fiscal de Acompanhamento (Execução)")
            f_status_exec = st.text_input("Status da Execução")
            f_status_acao = st.text_input("Status Ação Convenente")
            f_status_obra = st.text_input("Status da Obra")
        with cc3:
            f_fiscal_pc = st.text_input("Fiscal de Acompanhamento (Prestação de contas)")
            f_status_exec_pc = st.text_input("Status Execução (Prestação de contas)")
            f_status_obra_pc = st.text_input("Status Obra (Prestação de contas)")
            f_status_pc = st.text_input("Status Prestação de contas")

        submitted = st.form_submit_button("Pesquisar")

    # Detalhe (quando clica)
    if st.session_state.selected_id:
        render_detalhe(df, st.session_state.selected_id, modo="leitura", user_name=user_name, user_role=user_role)
    else:
        res = df.copy()

        # filtros base (sempre checando existência)
        if f_inst and "no_instrumento" in res.columns:
            res = res[res["no_instrumento"].astype("string") == f_inst.strip()]

        if f_ano and "ano" in res.columns:
            try:
                res = res[res["ano"].astype("Int64") == int(f_ano)]
            except Exception:
                pass

        if f_obj and "objeto" in res.columns:
            res = res[_safe_str_series(res, "objeto").str.contains(f_obj, case=False, na=False)]

        if f_proc and "no_processo" in res.columns:
            res = res[_safe_str_series(res, "no_processo").str.contains(f_proc, case=False, na=False)]

        if f_uf and "uf" in res.columns:
            res = res[_safe_str_series(res, "uf").isin(f_uf)]

        if f_mun and "municipio" in res.columns:
            res = res[_safe_str_series(res, "municipio").str.contains(f_mun, case=False, na=False)]

        if f_parl and "parlamentar" in res.columns:
            res = res[_safe_str_series(res, "parlamentar").str.contains(f_parl, case=False, na=False)]

        if f_val_min > 0 and "valor_global" in res.columns:
            try:
                res = res[pd.to_numeric(res["valor_global"], errors="coerce").fillna(0) >= f_val_min]
            except Exception:
                pass

        # filtros coordenações (se existirem)
        if f_sit_pb and "situacao_pb" in res.columns:
            res = res[_safe_str_series(res, "situacao_pb").str.contains(f_sit_pb, case=False, na=False)]
        if f_analista_pb and "analista_pb" in res.columns:
            res = res[_safe_str_series(res, "analista_pb").str.contains(f_analista_pb, case=False, na=False)]
        if f_status_analise_pb and "status_analise_pb" in res.columns:
            res = res[_safe_str_series(res, "status_analise_pb").str.contains(f_status_analise_pb, case=False, na=False)]

        if f_fiscal_exec and "fiscal_exec" in res.columns:
            res = res[_safe_str_series(res, "fiscal_exec").str.contains(f_fiscal_exec, case=False, na=False)]
        if f_status_exec and "status_exec" in res.columns:
            res = res[_safe_str_series(res, "status_exec").str.contains(f_status_exec, case=False, na=False)]
        if f_status_acao and "status_acao_convenente" in res.columns:
            res = res[_safe_str_series(res, "status_acao_convenente").str.contains(f_status_acao, case=False, na=False)]
        if f_status_obra and "status_obra" in res.columns:
            res = res[_safe_str_series(res, "status_obra").str.contains(f_status_obra, case=False, na=False)]

        if f_fiscal_pc and "fiscal_pc" in res.columns:
            res = res[_safe_str_series(res, "fiscal_pc").str.contains(f_fiscal_pc, case=False, na=False)]
        if f_status_exec_pc and "status_exec_pc" in res.columns:
            res = res[_safe_str_series(res, "status_exec_pc").str.contains(f_status_exec_pc, case=False, na=False)]
        if f_status_obra_pc and "status_obra_pc" in res.columns:
            res = res[_safe_str_series(res, "status_obra_pc").str.contains(f_status_obra_pc, case=False, na=False)]
        if f_status_pc and "status_pc" in res.columns:
            res = res[_safe_str_series(res, "status_pc").str.contains(f_status_pc, case=False, na=False)]

        # Só mostra lista após clicar em "Pesquisar" OU se não quiser exigir isso, remova o "if submitted"
        if not submitted:
            st.info("Use os filtros e clique em **Pesquisar**.")
        else:
            st.write(f"**{len(res)}** resultados encontrados.")
            for idx, r in res.iterrows():
                case_id = _get_case_id(r)
                municipio = r.get("municipio", "")
                uf = r.get("uf", "")
                objeto = r.get("objeto", "")
                status = r.get("status_painel", "")

                with st.container(border=True):
                    st.write(f"**Convênio/Proposta:** {case_id}  |  **UF/Município:** {uf}/{municipio}")
                    st.write(f"**Status:** {status}")
                    st.write(f"**Objeto:** {objeto}")

                    if st.button("Abrir", key=f"abrir_geral_{case_id}_{idx}"):
                        st.session_state.selected_id = case_id
                        st.rerun()


# =========================
# Aba: Coordenações (meus casos + filtros)
# =========================
elif menu == "Coordenações":
    st.header(f"📑 Coordenações — Meus convênios ({user_name})")

    # filtra "meus casos"
    meus = df.copy()
    if "eng_resp" in meus.columns or "tec_resp" in meus.columns:
        eng = _safe_str_series(meus, "eng_resp")
        tec = _safe_str_series(meus, "tec_resp")
        u = str(user_name or "").strip()
        meus = meus[(eng == u) | (tec == u)]
    else:
        st.error("Sua base não tem colunas de atribuição (eng_resp/tec_resp). Verifique a aba Atribuição e o utils/data.py.")
        st.stop()

    # filtros (mesmos 3 principais que você pediu para coordenações: UF, município, nº instrumento)
    with st.form("search_coord"):
        c1, c2, c3 = st.columns(3)
        f_uf = c1.multiselect("UF", sorted([x for x in _safe_str_series(meus, "uf").dropna().unique().tolist() if x]))
        f_mun = c2.text_input("Município")
        f_inst = c3.text_input("Nº do Instrumento / Proposta")
        submitted = st.form_submit_button("Pesquisar")

    if st.session_state.selected_id:
        render_detalhe(df, st.session_state.selected_id, modo="convenio", user_name=user_name, user_role=user_role)
    else:
        if not submitted:
            st.info("Use os filtros e clique em **Pesquisar**.")
            st.stop()

        res = meus.copy()
        if f_uf and "uf" in res.columns:
            res = res[_safe_str_series(res, "uf").isin(f_uf)]
        if f_mun and "municipio" in res.columns:
            res = res[_safe_str_series(res, "municipio").str.contains(f_mun, case=False, na=False)]
        if f_inst:
            # procura em instrumento OU proposta
            mask = pd.Series([False] * len(res), index=res.index)
            if "no_instrumento" in res.columns:
                mask = mask | (_safe_str_series(res, "no_instrumento") == f_inst.strip())
            if "no_proposta" in res.columns:
                mask = mask | (_safe_str_series(res, "no_proposta") == f_inst.strip())
            res = res[mask]

        # separa em Celebração e Execução (PC fica pronto, mas você pediu “deixar de lado”)
        res = res.copy()
        res["fase_calc"] = res.apply(identificar_fase, axis=1)

        tab_cel, tab_exe = st.tabs(["Celebração", "Execução"])

        with tab_cel:
            cel = res[res["fase_calc"] == "Celebração"]
            st.write(f"**{len(cel)}** casos.")
            for idx, r in cel.iterrows():
                case_id = _get_case_id(r)
                with st.container(border=True):
                    st.write(f"**{case_id}** — {r.get('municipio','')} ({r.get('uf','')})")
                    st.write(f"**Objeto:** {r.get('objeto','')}")
                    if st.button("Abrir", key=f"abrir_coord_cel_{case_id}_{idx}"):
                        st.session_state.selected_id = case_id
                        st.rerun()

        with tab_exe:
            exe = res[res["fase_calc"] == "Execução"]
            st.write(f"**{len(exe)}** casos.")
            for idx, r in exe.iterrows():
                case_id = _get_case_id(r)
                with st.container(border=True):
                    st.write(f"**{case_id}** — {r.get('municipio','')} ({r.get('uf','')})")
                    st.write(f"**Objeto:** {r.get('objeto','')}")
                    if st.button("Abrir", key=f"abrir_coord_exe_{case_id}_{idx}"):
                        st.session_state.selected_id = case_id
                        st.rerun()


# =========================
# Aba: Vistorias (meus casos por vistoria_resp + filtros)
# =========================
elif menu == "Vistorias":
    st.header(f"🏗️ Vistorias — Minhas vistorias ({user_name})")

    if "vistoria_resp" not in df.columns:
        st.error("Sua base não tem coluna 'vistoria_resp'. Verifique o utils/data.py e/ou a base de atribuição de vistorias.")
        st.stop()

    vis = df[_safe_str_series(df, "vistoria_resp") == str(user_name or "").strip()].copy()

    with st.form("search_vis"):
        c1, c2, c3 = st.columns(3)
        f_uf = c1.multiselect("UF", sorted([x for x in _safe_str_series(vis, "uf").dropna().unique().tolist() if x]))
        f_mun = c2.text_input("Município")
        f_inst = c3.text_input("Nº do Instrumento / Proposta")
        submitted = st.form_submit_button("Pesquisar")

    if st.session_state.selected_id:
        render_detalhe(df, st.session_state.selected_id, modo="vistoria", user_name=user_name, user_role=user_role)
    else:
        if not submitted:
            st.info("Use os filtros e clique em **Pesquisar**.")
            st.stop()

        res = vis.copy()
        if f_uf and "uf" in res.columns:
            res = res[_safe_str_series(res, "uf").isin(f_uf)]
        if f_mun and "municipio" in res.columns:
            res = res[_safe_str_series(res, "municipio").str.contains(f_mun, case=False, na=False)]
        if f_inst:
            mask = pd.Series([False] * len(res), index=res.index)
            if "no_instrumento" in res.columns:
                mask = mask | (_safe_str_series(res, "no_instrumento") == f_inst.strip())
            if "no_proposta" in res.columns:
                mask = mask | (_safe_str_series(res, "no_proposta") == f_inst.strip())
            res = res[mask]

        st.write(f"**{len(res)}** vistorias encontradas.")
        for idx, r in res.iterrows():
            case_id = _get_case_id(r)
            with st.container(border=True):
                st.write(f"**{case_id}** — {r.get('municipio','')} ({r.get('uf','')})")
                st.write(f"**Objeto:** {r.get('objeto','')}")
                if st.button("Abrir", key=f"abrir_vis_{case_id}_{idx}"):
                    st.session_state.selected_id = case_id
                    st.rerun()


# =========================
# Aba: Atribuição (somente gestor) — mantém a aba, mas sem inventar dados
# =========================
elif menu == "Atribuição":
    st.header("⚖️ Atribuição (Somente Gestor)")

    if user_role != "Gestor":
        st.error("Acesso restrito: somente Gestor.")
        st.stop()

    st.info(
        "Esta aba depende de funções de atribuição no backend (utils/data.py). "
        "Se você já implementou save_atribuicao, eu conecto aqui. "
        "Por enquanto, mantenho a aba sem quebrar o app."
    )

    st.write("Defina aqui: responsável do convênio (eng_resp/tec_resp) e responsável da vistoria (vistoria_resp).")
    st.write("Se você me disser o formato da sua planilha de atribuição, eu amarro isso 100% com o loader.")
