import streamlit as st
import pandas as pd
from utils.data import load_and_merge_all, save_edicao_com_historico, get_edicoes, get_historico

st.set_page_config(page_title="Painel Transferegov", layout="wide")

# --- ESTADO DA SESSÃO ---
if 'main_df' not in st.session_state: st.session_state.main_df = pd.DataFrame()
if 'selected_id' not in st.session_state: st.session_state.selected_id = None

# --- SIDEBAR ---
st.sidebar.title("👤 Perfil")
user_name = st.sidebar.text_input("Nome", "Samuel Wilber")
user_role = st.sidebar.selectbox("Papel", ["Engenheiro", "Gestor"])
st.sidebar.divider()
menu = st.sidebar.radio("Navegação", ["Geral", "Coordenações", "Vistorias", "Upload", "Atribuição"])

df = st.session_state.main_df

# --- AVISOS (SIDEBAR) ---
if not df.empty:
    st.sidebar.subheader("🔔 Avisos")
    susp = len(df[df['situacao_contratual'].astype(str).str.contains("SUSPENSIVA", na=False, case=False)])
    if susp > 0: st.sidebar.warning(f"{susp} convênios em Cláusula Suspensiva")

# --- TELA DE DETALHE ---
def render_detalhe(id_val, modo):
    if st.button("⬅️ Voltar"):
        st.session_state.selected_id = None
        st.rerun()

    row = df[(df['no_instrumento'].astype(str) == str(id_val)) | (df['no_proposta'].astype(str) == str(id_val))].iloc[0]
    edicoes = get_edicoes(id_val)
    fase = "Celebração" if pd.isna(row.get('no_instrumento')) or "SUSPENSIVA" in str(row.get('situacao_contratual')).upper() else "Execução"
    
    st.header(f"📌 {fase}: {id_val}")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏛️ Dados Oficiais")
        st.info(f"**Objeto:** {row.get('objeto', 'N/A')}")
        st.write(f"**Município:** {row.get('municipio', 'N/A')} ({row.get('uf', 'N/A')})")
        st.write(f"**Status:** {row.get('status_painel', 'N/A')}")
    
    with c2:
        st.subheader("✍️ Gestão Manual")
        val_p = row.get('valor_global', 0)
        val_m = st.number_input("Valor Global (Manual)", value=float(edicoes.get('valor_manual', val_p)), disabled=(modo == 'leitura' or modo == 'vistoria'))
        if float(val_m) == float(val_p): st.success("✅ Igual ao Painel")
        else: st.error("⚠️ Diferente do Painel")

        obs = st.text_area("Observações", value=edicoes.get('observacoes', ""), disabled=(modo == 'leitura'))
        if st.button("Salvar") and modo != 'leitura':
            save_edicao_com_historico(id_val, "valor_manual", val_m, user_name)
            save_edicao_com_historico(id_val, "observacoes", obs, user_name)
            st.toast("Salvo!")

# --- NAVEGAÇÃO ---
if df.empty and menu != "Upload":
    st.info("Suba as planilhas na aba **Upload** para começar.")
    st.stop()

if menu == "Upload":
    st.header("📂 Upload de Dados")
    files = st.file_uploader("Arraste seus arquivos Excel aqui", accept_multiple_files=True)
    if st.button("Processar Base"):
        st.session_state.main_df = load_and_merge_all({f.name: f for f in files})
        st.success("Base carregada!")
        st.rerun()

elif menu == "Geral":
    if st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, 'leitura')
    else:
        st.header("🔍 Consulta Geral")
        busca = st.text_input("Filtrar por ID ou Município")
        res = df[df['no_instrumento'].astype(str).str.contains(busca) | df['municipio'].str.contains(busca, case=False, na=False)]
        for idx, r in res.head(50).iterrows():
            id_v = r.get('no_instrumento') if pd.notna(r.get('no_instrumento')) else r.get('no_proposta')
            if st.button(f"Abrir {id_v} - {r.get('municipio')}", key=f"gen_{idx}"):
                st.session_state.selected_id = id_v
                st.rerun()

elif menu == "Coordenações":
    if st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, 'convenio')
    else:
        st.header(f"📑 Meus Convênios - {user_name}")
        meus = df[(df['eng_resp'] == user_name) | (df['tec_resp'] == user_name)]
        for idx, r in meus.iterrows():
            id_v = r.get('no_instrumento') or r.get('no_proposta')
            if st.button(f"Ver {id_v}", key=f"coor_{idx}"):
                st.session_state.selected_id = id_v
                st.rerun()
