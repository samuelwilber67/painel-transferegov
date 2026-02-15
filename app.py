import streamlit as st
import pandas as pd
from utils.data import load_and_merge_all, save_atribuicao, save_edicao_local

st.set_page_config(page_title="Sistema Gerencial de Convênios", layout="wide")

# --- SIMULAÇÃO DE LOGIN ---
st.sidebar.title("🔐 Acesso")
user_role = st.sidebar.selectbox("Perfil", ["Engenheiro", "Técnico", "Gestor"])
user_name = st.sidebar.text_input("Nome do Usuário", "Samuel Wilber")

# --- MENU LATERAL ---
menu = st.sidebar.radio("Navegação", [
    "Geral", 
    "Coordenações", 
    "Cadastros", 
    "Atribuição", 
    "Upload Painel", 
    "Gerenciamento"
])

# --- CARREGAMENTO DE DADOS ---
if 'main_df' not in st.session_state:
    st.session_state.main_df = pd.DataFrame()

# --- PÁGINA: UPLOAD PAINEL ---
if menu == "Upload Painel":
    st.header("📂 Upload de Dados do Painel")
    files = st.file_uploader("Suba as planilhas (Dados Básicos, Acompanhamento, etc)", accept_multiple_files=True)
    if st.button("Processar e Atualizar Base"):
        files_dict = {f.name: f for f in files}
        st.session_state.main_df = load_and_merge_all(files_dict)
        st.success("Base de dados atualizada com sucesso!")

df = st.session_state.main_df

if df.empty:
    st.warning("Aguardando upload dos dados na aba 'Upload Painel'.")
    st.stop()

# --- PÁGINA: GERAL ---
if menu == "Geral":
    st.header("🔍 Consulta Geral")
    search = st.text_input("Pesquisar por Instrumento, Proposta, Município ou Objeto")
    # Lógica de filtro e exibição da tabela global...
    st.dataframe(df)

# --- PÁGINA: ATRIBUIÇÃO (GESTORES) ---
elif menu == "Atribuição":
    if user_role != "Gestor":
        st.error("Acesso restrito a Gestores.")
    else:
        st.header("⚖️ Atribuição de Casos")
        inst = st.selectbox("Instrumento", df['no_instrumento'].unique())
        eng = st.text_input("Engenheiro Responsável")
        tec = st.text_input("Técnico Responsável")
        if st.button("Salvar Atribuição"):
            save_atribuicao(inst, eng, tec)
            st.success("Atribuição salva!")

# --- PÁGINA: COORDENAÇÕES ---
elif menu == "Coordenações":
    st.header(f"📋 Meus Casos - {user_name}")
    sub_tab = st.tabs(["Celebração", "Execução", "Prestação de Contas"])
    
    # Filtra apenas o que é do usuário logado
    meus_casos = df[(df['eng_resp'] == user_name) | (df['tec_resp'] == user_name)]
    
    with sub_tab[0]: # Celebração
        st.dataframe(meus_casos[meus_casos['situacao_instrumento'].str.contains("Proposta|Celebração", na=False)])
    
    with sub_tab[1]: # Execução
        st.subheader("Detalhe da Execução")
        # Aqui implementamos a lógica de "Igual ao Painel" comparando df['valor_global'] com um input
        inst_sel = st.selectbox("Ver detalhe do Instrumento", meus_casos['no_instrumento'].unique())
        # Lógica de edição e alertas...

# --- PÁGINA: GERENCIAMENTO (VISTORIAS) ---
elif menu == "Gerenciamento":
    st.header("🏗️ Gerenciamento de Vistorias")
    # Lógica baseada na imagem 0008...
