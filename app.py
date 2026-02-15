import streamlit as st
import pandas as pd
from utils.data import load_and_merge_all, save_atribuicao, save_edicao, get_edicoes

st.set_page_config(page_title="Sistema Gerencial de Convênios", layout="wide")

if 'main_df' not in st.session_state: st.session_state.main_df = pd.DataFrame()
if 'selected_id' not in st.session_state: st.session_state.selected_id = None

# Sidebar
st.sidebar.title("👤 Usuário")
user_role = st.sidebar.selectbox("Perfil", ["Engenheiro", "Técnico", "Gestor"])
user_name = st.sidebar.text_input("Nome", "Samuel Wilber")
menu = st.sidebar.radio("Menu Principal", ["Geral", "Coordenações", "Atribuição", "Upload Painel"])

# Função de Detalhe Expandido
def render_detalhe(id_val, can_edit):
    if st.button("⬅️ Voltar para a lista"):
        st.session_state.selected_id = None
        st.rerun()
    
    row = st.session_state.main_df[st.session_state.main_df['no_instrumento'] == id_val].iloc[0]
    edicoes = get_edicoes(id_val)
    
    st.header(f"Convênio: {id_val}")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("Dados do Painel")
        st.write(f"**Objeto:** {row.get('objeto')}")
        val_p = row.get('valor_global_painel', 0)
        st.write(f"**Valor Global (Painel):** R$ {val_p:,.2f}")
        st.write(f"**UF/Município:** {row.get('uf')} / {row.get('municipio')}")
        
    with c2:
        st.subheader("Dados Gerenciais (Editável)")
        val_m = st.number_input("Valor Global (Manual)", value=float(edicoes.get('valor_manual', val_p)), disabled=not can_edit)
        if val_m == val_p: st.success("✅ Igual ao Painel")
        else: st.error("⚠️ Diferente do Painel")
        
        obs = st.text_area("Observações", value=edicoes.get('observacoes', ""), disabled=not can_edit)
        if can_edit and st.button("Salvar Alterações"):
            save_edicao(id_val, 'valor_manual', val_m)
            save_edicao(id_val, 'observacoes', obs)
            st.toast("Salvo!")

# --- PÁGINA: GERAL ---
if menu == "Geral":
    st.header("🔍 Consulta Geral")
    with st.form("search_geral"):
        st.write("### Filtros de Pesquisa")
        c1, c2, c3, c4 = st.columns(4)
        f_inst = c1.text_input("Nº Instrumento")
        f_ano = c2.text_input("Ano")
        f_obj = c3.text_input("Objeto")
        f_proc = c4.text_input("Nº Processo")
        
        c5, c6, c7, c8 = st.columns(4)
        f_uf = c5.multiselect("UF", st.session_state.main_df['uf'].unique())
        f_mun = c6.text_input("Município")
        f_parl = c7.text_input("Parlamentar")
        f_val = c8.number_input("Valor Global", value=0.0)

        st.write("---")
        st.write("#### Filtros por Coordenação")
        cc1, cc2, cc3 = st.columns(3)
        with cc1: # Celebração
            f_pb_sit = st.text_input("Situação PB")
            f_pb_ana = st.text_input("Analista PB")
            f_pb_stat = st.text_input("Status Análise PB")
        with cc2: # Execução
            f_ex_fisc = st.text_input("Fiscal Execução")
            f_ex_stat = st.text_input("Status Execução")
            f_ex_obra = st.text_input("Status Obra")
        with cc3: # PC
            f_pc_fisc = st.text_input("Fiscal PC")
            f_pc_stat = st.text_input("Status PC")
            f_pc_obra = st.text_input("Status Obra PC")

        submitted = st.form_submit_button("🔍 Pesquisar")

    if submitted or st.session_state.selected_id:
        if st.session_state.selected_id:
            render_detalhe(st.session_state.selected_id, can_edit=False)
        else:
            res = st.session_state.main_df.copy()
            # Aplicação dos filtros (Lógica simplificada para exemplo)
            if f_inst: res = res[res['no_instrumento'] == f_inst]
            if f_uf: res = res[res['uf'].isin(f_uf)]
            if f_mun: res = res[res['municipio'].str.contains(f_mun, case=False, na=False)]
            
            st.write(f"**{len(res)} resultados encontrados.**")
            for idx, r in res.iterrows():
                with st.expander(f"Convênio {r['no_instrumento']} - {r['municipio']} ({r['uf']})"):
                    st.write(f"**Objeto:** {r['objeto']}")
                    if st.button("Ver Detalhes", key=f"btn_geral_{idx}"):
                        st.session_state.selected_id = r['no_instrumento']
                        st.rerun()

# --- PÁGINA: COORDENAÇÕES ---
elif menu == "Coordenações":
    st.header(f"📑 Coordenações - {user_name}")
    tab_cel, tab_exe, tab_pre = st.tabs(["Celebração", "Execução", "Prestação de Contas"])
    
    meus_casos = st.session_state.main_df[
        (st.session_state.main_df['eng_resp'] == user_name) | 
        (st.session_state.main_df['tec_resp'] == user_name)
    ]

    with tab_cel:
        st.subheader("Filtros Celebração")
        c1, c2, c3 = st.columns(3)
        fc_pb_sit = c1.text_input("Situação PB", key="c_pb_sit")
        fc_pb_ana = c2.text_input("Analista PB", key="c_pb_ana")
        fc_pb_stat = c3.text_input("Status Análise PB", key="c_pb_stat")
        
        st.table(meus_casos[['no_instrumento', 'ano', 'uf', 'municipio', 'objeto', 'status_analise_pb']])
        for idx, r in meus_casos.iterrows():
            if st.button(f"Ver/Editar {r['no_instrumento']}", key=f"btn_cel_{idx}"):
                st.session_state.selected_id = r['no_instrumento']
                st.rerun()

    # Repetir lógica similar para Execução e PC...

# --- PÁGINA: UPLOAD ---
elif menu == "Upload Painel":
    st.header("📂 Upload de Planilhas")
    files = st.file_uploader("Suba os arquivos do Painel", accept_multiple_files=True)
    if st.button("Processar Base"):
        st.session_state.main_df = load_and_merge_all({f.name: f for f in files})
        st.success("Base atualizada!")
