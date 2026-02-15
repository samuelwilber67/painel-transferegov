import streamlit as st
import pandas as pd
from utils.data import load_and_merge_all, save_atribuicao, save_edicao, get_edicoes

st.set_page_config(page_title="Sistema Gerencial de Convênios", layout="wide")

# --- ESTADO DA SESSÃO ---
if 'main_df' not in st.session_state: st.session_state.main_df = pd.DataFrame()
if 'selected_id' not in st.session_state: st.session_state.selected_id = None

# --- SIDEBAR: LOGIN E NAVEGAÇÃO ---
st.sidebar.title("👤 Usuário")
user_role = st.sidebar.selectbox("Perfil", ["Engenheiro", "Técnico", "Gestor"])
user_name = st.sidebar.text_input("Nome", "Samuel Wilber")

st.sidebar.divider()
menu = st.sidebar.radio("Menu Principal", ["Geral", "Coordenações", "Cadastros", "Atribuição", "Upload Painel", "Gerenciamento"])

# --- FUNÇÃO DE DETALHE (EXPANDIDO) ---
def render_detalhe(id_val, can_edit):
    if st.button("⬅️ Voltar para a lista"):
        st.session_state.selected_id = None
        st.rerun()
    
    row = st.session_state.main_df[
        (st.session_state.main_df['no_instrumento'] == id_val) | 
        (st.session_state.main_df['no_proposta'] == id_val)
    ].iloc[0]
    
    edicoes = get_edicoes(id_val)
    
    st.header(f"Convênio: {id_val}")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Dados do Painel")
        st.write(f"**Objeto:** {row.get('objeto')}")
        val_painel = row.get('valor_global_painel', 0)
        st.write(f"**Valor Global (Painel):** R$ {val_painel:,.2f}")
        
    with col2:
        st.subheader("Dados Gerenciais")
        val_manual = st.number_input("Valor Global (Manual)", value=float(edicoes.get('valor_manual', val_painel)), disabled=not can_edit)
        
        if val_manual == val_painel:
            st.success("✅ Igual ao Painel")
        else:
            st.error("⚠️ Diferente do Painel")
            
        obs = st.text_area("Observações", value=edicoes.get('observacoes', ""), disabled=not can_edit)
        
        if can_edit and st.button("Salvar Alterações"):
            save_edicao(id_val, 'valor_manual', val_manual)
            save_edicao(id_val, 'observacoes', obs)
            st.toast("Dados salvos com sucesso!")

# --- PÁGINA: UPLOAD ---
if menu == "Upload Painel":
    st.header("📂 Upload de Planilhas")
    files = st.file_uploader("Suba os 6 arquivos do Painel", accept_multiple_files=True)
    if st.button("Processar Base"):
        st.session_state.main_df = load_and_merge_all({f.name: f for f in files})
        st.success("Base atualizada!")

df = st.session_state.main_df
if df.empty:
    st.warning("Suba os dados na aba 'Upload Painel'.")
    st.stop()

# --- PÁGINA: GERAL ---
if menu == "Geral":
    st.header("🔍 Consulta Geral")
    with st.form("search_geral"):
        c1, c2, c3 = st.columns(3)
        f_uf = c1.multiselect("UF", df['uf'].unique())
        f_mun = c2.text_input("Município")
        f_inst = c3.text_input("Nº Instrumento")
        submitted = st.form_submit_button("Pesquisar")

    if submitted or st.session_state.selected_id:
        res = df.copy()
        if f_uf: res = res[res['uf'].isin(f_uf)]
        if f_mun: res = res[res['municipio'].str.contains(f_mun, case=False, na=False)]
        if f_inst: res = res[(res['no_instrumento'] == f_inst) | (res['no_proposta'] == f_inst)]
        
        if st.session_state.selected_id:
            render_detalhe(st.session_state.selected_id, can_edit=False)
        else:
            st.write(f"{len(res)} resultados encontrados.")
            for idx, r in res.iterrows():
                id_v = r['no_instrumento'] if pd.notna(r['no_instrumento']) else r['no_proposta']
                with st.expander(f"Convênio {id_v} - {r['municipio']} ({r['uf']})"):
                    st.write(f"**Objeto:** {r['objeto']}")
                    if st.button("Ver Detalhes", key=f"btn_{idx}_{id_v}"):
                        st.session_state.selected_id = id_v
                        st.rerun()

# --- PÁGINA: COORDENAÇÕES ---
elif menu == "Coordenações":
    st.header(f"📑 Coordenações - {user_name}")
    
    # Filtro de busca repetido
    with st.expander("🔍 Filtros de Pesquisa"):
        c1, c2 = st.columns(2)
        f_mun = c1.text_input("Município", key="coord_mun")
        f_inst = c2.text_input("Nº Instrumento", key="coord_inst")

    tab_cel, tab_exe, tab_pre = st.tabs(["Celebração", "Execução", "Prestação de Contas"])
    
    # Filtra casos do usuário
    meus_casos = df[(df['eng_resp'] == user_name) | (df['tec_resp'] == user_name)]
    if f_mun: meus_casos = meus_casos[meus_casos['municipio'].str.contains(f_mun, case=False, na=False)]
    if f_inst: meus_casos = meus_casos[(meus_casos['no_instrumento'] == f_inst) | (meus_casos['no_proposta'] == f_inst)]

    if st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, can_edit=True)
    else:
        with tab_cel:
            cols = ["no_instrumento", "ano", "uf", "municipio", "objeto", "status", "status_pb"]
            st.table(meus_casos[[c for c in cols if c in meus_casos.columns]])
            for idx, id_v in enumerate(meus_casos['no_instrumento'].dropna()):
                if st.button(f"Ver/Editar {id_v}", key=f"cel_{idx}_{id_v}"):
                    st.session_state.selected_id = id_v
                    st.rerun()

        with tab_exe:
            cols = ["no_instrumento", "ano", "uf", "municipio", "objeto", "status_execucao", "status_obra"]
            st.table(meus_casos[[c for c in cols if c in meus_casos.columns]])
            for idx, id_v in enumerate(meus_casos['no_instrumento'].dropna()):
                if st.button(f"Ver/Editar {id_v}", key=f"exe_{idx}_{id_v}"):
                    st.session_state.selected_id = id_v
                    st.rerun()

# --- PÁGINA: ATRIBUIÇÃO (GESTORES) ---
elif menu == "Atribuição":
    if user_role != "Gestor":
        st.error("Acesso restrito.")
    else:
        st.header("⚖️ Atribuição de Casos")
        inst = st.selectbox("Selecione o Instrumento/Proposta", df['no_instrumento'].fillna(df['no_proposta']).unique())
        eng = st.text_input("Engenheiro")
        tec = st.text_input("Técnico")
        if st.button("Confirmar Atribuição"):
            save_atribuicao(inst, True, eng, tec)
            st.success("Atribuído!")

# --- PÁGINAS PLACEHOLDER PARA AS OUTRAS ---
elif menu == "Cadastros":
    st.header("📝 Cadastros (Em Desenvolvimento)")
    st.write("Aqui será a atribuição de vistorias.")

elif menu == "Gerenciamento":
    st.header("🏗️ Gerenciamento (Em Desenvolvimento)")
    st.write("Aqui será o gerenciamento de vistorias.")
