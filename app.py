import streamlit as st
import pandas as pd
from utils.data import load_and_merge_all, save_edicao_com_historico, get_edicoes, get_historico

st.set_page_config(page_title="Sistema Gerencial", layout="wide")

# --- ESTADO DA SESSÃO ---
if 'main_df' not in st.session_state: st.session_state.main_df = pd.DataFrame()
if 'selected_id' not in st.session_state: st.session_state.selected_id = None

# --- SIDEBAR ---
st.sidebar.title("👤 Perfil")
user_name = st.sidebar.text_input("Seu Nome", "Samuel Wilber")
user_role = st.sidebar.selectbox("Papel", ["Engenheiro", "Gestor"])
st.sidebar.divider()
menu = st.sidebar.radio("Navegação", ["Geral", "Coordenações", "Vistorias", "Upload Painel", "Atribuição"])

df = st.session_state.main_df

# --- AVISOS DINÂMICOS (Baseados em dados reais) ---
if not df.empty:
    st.sidebar.subheader("🔔 Avisos")
    suspensivas = len(df[df['situacao_contratual'].str.contains("SUSPENSIVA", na=False, case=False)])
    if suspensivas > 0:
        st.sidebar.warning(f"⚠️ {suspensivas} convênios em Cláusula Suspensiva")

# --- FUNÇÃO DE DETALHE ---
def render_detalhe(id_val, modo):
    if st.button("⬅️ Voltar"):
        st.session_state.selected_id = None
        st.rerun()

    # Localiza o registro de forma segura
    row = df[(df['no_instrumento'].astype(str) == str(id_val)) | (df['no_proposta'].astype(str) == str(id_val))].iloc[0]
    edicoes = get_edicoes(id_val)
    
    st.header(f"Detalhes: {id_val}")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏛️ Dados Originais")
        st.info(f"**Objeto:** {row.get('objeto', 'N/A')}")
        st.write(f"**Município:** {row.get('municipio', 'N/A')}")
    
    with c2:
        st.subheader("✍️ Dados Manuais")
        obs = st.text_area("Anotações", value=edicoes.get('observacoes', ""), disabled=(modo == 'leitura'))
        if modo != 'leitura' and st.button("Salvar"):
            save_edicao_com_historico(id_val, "observacoes", obs, user_name)
            st.toast("Salvo!")

# --- TELAS ---
if df.empty and menu != "Upload Painel":
    st.info("👋 Bem-vindo! Comece subindo as planilhas na aba **Upload Painel**.")
    st.stop()

if menu == "Upload Painel":
    st.header("📂 Carga de Dados")
    files = st.file_uploader("Suba as planilhas do Transferegov", accept_multiple_files=True)
    if st.button("Processar Base"):
        if files:
            st.session_state.main_df = load_and_merge_all({f.name: f for f in files})
            st.success("Base carregada!")
            st.rerun()

elif menu == "Geral":
    if st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, modo='leitura')
    else:
        st.header("🔍 Consulta Geral")
        # Pesquisa simples e direta
        busca = st.text_input("Pesquisar por Nº Instrumento, Proposta ou Município")
        
        res = df.copy()
        if busca:
            res = res[
                res['no_instrumento'].astype(str).str.contains(busca) | 
                res['no_proposta'].astype(str).str.contains(busca) |
                res['municipio'].str.contains(busca, case=False, na=False)
            ]
        
        st.write(f"Resultados: {len(res)}")
        for idx, r in res.head(30).iterrows():
            id_v = r.get('no_instrumento') if pd.notna(r.get('no_instrumento')) else r.get('no_proposta')
            with st.container(border=True):
                st.write(f"**{id_v}** - {r.get('municipio')}")
                if st.button("Visualizar", key=f"btn_{idx}"):
                    st.session_state.selected_id = id_v
                    st.rerun()

# ... (Repetir lógica similar para Coordenações e Vistorias filtrando por eng_resp/vistoria_resp)
