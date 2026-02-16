import streamlit as st
import pandas as pd
from utils.data import load_and_merge_all, save_edicao_com_historico, get_edicoes, get_historico

st.set_page_config(page_title="Sistema Gerencial de Convênios", layout="wide")

# --- ESTADO DA SESSÃO ---
if 'main_df' not in st.session_state: st.session_state.main_df = pd.DataFrame()
if 'selected_id' not in st.session_state: st.session_state.selected_id = None

# --- SIDEBAR: LOGIN E NAVEGAÇÃO ---
st.sidebar.title("👤 Usuário")
user_role = st.sidebar.selectbox("Perfil", ["Engenheiro", "Técnico", "Gestor"])
user_name = st.sidebar.text_input("Nome", "Samuel Wilber")

st.sidebar.divider()
menu = st.sidebar.radio("Menu Principal", ["Geral", "Coordenações", "Cadastros", "Atribuição", "Upload", "Painel", "Gerenciamento"])

df = st.session_state.main_df
if df.empty:
    st.warning("Suba os dados na aba 'Upload'.")
    st.stop()

# --- FUNÇÃO DE IDENTIFICAÇÃO DE FASE ---
def identificar_fase(row):
    status = str(row.get('status_painel', '')).upper()
    sit_contratual = str(row.get('situacao_contratual', '')).upper()
    if pd.isna(row.get('no_instrumento')) or "SUSPENSIVA" in sit_contratual:
        return "Celebração"
    elif "PRESTAÇÃO" in status:
        return "Prestação de Contas"
    else:
        return "Execução"

# --- VISÃO EXPANDIDA (DETALHE) ---
def render_detalhe(id_val, can_edit):
    if st.button("⬅️ Voltar para a lista"):
        st.session_state.selected_id = None
        st.rerun()
    
    # Verificação se o convênio existe
    filtered_df = df[(df['no_instrumento'] == id_val) | (df['no_proposta'] == id_val)]
    if filtered_df.empty:
        st.error(f"Convênio {id_val} não encontrado na base de dados.")
        return
    
    row = filtered_df.iloc[0]
    fase = identificar_fase(row)
    edicoes = get_edicoes(id_val)
    
    st.header(f"📌 {fase}: {id_val}")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏛️ Dados Automáticos (Painel)")
        st.info(f"**Objeto:** {row.get('objeto')}")
        val_p = row.get('valor_global_painel', 0)
        st.write(f"**Valor Global (Painel):** R$ {val_p:,.2f}")
        st.write(f"**UF/Município:** {row.get('uf')} / {row.get('municipio')}")
        
    with c2:
        st.subheader("✍️ Dados Manuais (Gerencial)")
        val_m = st.number_input("Valor Global Gerencial", value=float(edicoes.get('valor_manual', val_p)), disabled=not can_edit)
        
        if val_m == val_p: st.success("✅ Igual ao Painel")
        else: st.error("⚠️ Diferente do Painel")
        
        obs = st.text_area("Observações/Anotações", value=edicoes.get('observacoes', ""), disabled=not can_edit)
        
        if can_edit and st.button("Salvar Alterações"):
            save_edicao_com_historico(id_val, "valor_manual", val_m, user_name)
            save_edicao_com_historico(id_val, "observacoes", obs, user_name)
            st.toast("Dados salvos e histórico registrado!")

    st.divider()
    st.subheader("📜 Histórico de Alterações")
    hist = get_historico(id_val)
    if not hist.empty:
        st.dataframe(hist[['data_hora', 'usuario', 'campo', 'valor']], use_container_width=True)
    else:
        st.write("Sem registros anteriores.")

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
        f_uf = c5.multiselect("UF", df['uf'].unique())
        f_mun = c6.text_input("Município")
        f_parl = c7.text_input("Parlamentar")
        f_val = c8.number_input("Valor Global", value=0.0)

        st.write("---")
        st.write("#### Filtros por Coordenação")
        cc1, cc2, cc3 = st.columns(3)
        with cc1: # Celebração
            f_pb_sit = st.text_input("Situação do Projeto Básico")
            f_pb_ana = st.text_input("Analista do Projeto Básico (Eng. Atribuído - Celebração)")
            f_pb_stat = st.text_input("Status da Análise do Projeto Básico")
        with cc2: # Execução
            f_ex_fisc = st.text_input("Fiscal de Acompanhamento (Eng. Atribuído - Execução)")
            f_ex_stat = st.text_input("Status da Execução")
            f_ex_acao = st.text_input("Status Ação Convenente")
            f_ex_obra = st.text_input("Status da Obra")
        with cc3: # Prestação de Contas
            f_pc_fisc = st.text_input("Fiscal de Acompanhamento prestação de contas (Eng. Atribuído - Prestação de contas)")
            f_pc_exec = st.text_input("Status de Execução prestação de contas")
            f_pc_obra = st.text_input("Status da obra prestação de contas")
            f_pc_stat = st.text_input("Status prestação de contas")

        submitted = st.form_submit_button("🔍 Pesquisar")

    if submitted or st.session_state.selected_id:
        res = df.copy()
        # Aplicação dos filtros (lógica simplificada para exemplo)
        if f_inst: res = res[res['no_instrumento'] == f_inst]
        if f_uf: res = res[res['uf'].isin(f_uf)]
        if f_mun: res = res[res['municipio'].str.contains(f_mun, case=False, na=False)]
        # Adicione mais filtros conforme necessário...
        
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
            cols = ["no_instrumento", "ano", "uf", "municipio", "objeto", "status_exec", "status_obra"]
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

elif menu == "Upload":
    st.header("📂 Upload de Planilhas")
    files = st.file_uploader("Suba os 6 arquivos do Painel", accept_multiple_files=True)
    if st.button("Processar Base"):
        st.session_state.main_df = load_and_merge_all({f.name: f for f in files})
        st.success("Base atualizada!")

elif menu == "Painel":
    st.header("📊 Painel (Em Desenvolvimento)")
    st.write("Aqui será o painel de métricas.")

elif menu == "Gerenciamento":
    st.header("🏗️ Gerenciamento (Em Desenvolvimento)")
    st.write("Aqui será o gerenciamento de vistorias.")
