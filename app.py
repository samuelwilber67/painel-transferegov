import streamlit as st
import pandas as pd
from utils.data import load_and_merge_all, save_edicao_com_historico, get_edicoes, get_historico

st.set_page_config(page_title="Gestão de Convênios", layout="wide")

# --- LOGIN E PERFIS ---
st.sidebar.title("👤 Usuário")
user_name = st.sidebar.text_input("Nome", "Samuel Wilber")
user_role = st.sidebar.selectbox("Perfil", ["Engenheiro", "Técnico", "Gestor"])

# --- NOTIFICAÇÕES (AVISOS NO CANTO ESQUERDO) ---
st.sidebar.divider()
st.sidebar.subheader("🔔 Avisos")
# Exemplo de lógica de contagem (seria baseada no df real)
st.sidebar.warning("⚠️ 10 convênios precisam de notificação")
st.sidebar.error("🚨 5 casos sem pagamento > 90 dias")

# --- NAVEGAÇÃO ---
menu_options = ["Geral", "Coordenações", "Vistorias", "Upload Painel"]  # Agora "Upload Painel" aparece para todos
if user_role == "Gestor":
    menu_options += ["Atribuição"]
menu = st.sidebar.radio("Menu Principal", menu_options)

if 'main_df' not in st.session_state:
    # Dados de teste iniciais (para você testar sem subir nada)
    st.session_state.main_df = pd.DataFrame({
        'no_instrumento': ['909561', '909562', pd.NA],
        'no_proposta': [pd.NA, pd.NA, 'PROP001'],
        'ano': [2023, 2023, 2024],
        'objeto': ['Construção de escola', 'Reforma de hospital', 'Aquisição de equipamentos'],
        'uf': ['SP', 'RJ', 'MG'],
        'municipio': ['São Paulo', 'Rio de Janeiro', 'Belo Horizonte'],
        'parlamentar': ['Dep. Silva', 'Dep. Santos', 'Dep. Oliveira'],
        'valor_global': [1000000.0, 500000.0, 200000.0],
        'status_painel': ['Em Execução', 'Prestação de Contas', 'Em Análise'],
        'situacao_contratual': ['Celebrado', 'Celebrado', 'Cláusula Suspensiva'],
        'eng_resp': [pd.NA, 'Samuel Wilber', pd.NA],
        'tec_resp': [pd.NA, pd.NA, 'Samuel Wilber'],
        'vistoria_resp': [pd.NA, pd.NA, 'Samuel Wilber'],  # Novo campo para responsável da vistoria
    })
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

df = st.session_state.main_df

# --- LÓGICA DE EDIÇÃO (O CORAÇÃO DO SISTEMA) ---
def render_detalhe(id_val, modo):
    """
    modo: 'leitura' (Geral), 'convenio' (Coordenações), 'vistoria' (Vistorias)
    """
    row = df[(df['no_instrumento'] == id_val) | (df['no_proposta'] == id_val)].iloc[0]
    edicoes = get_edicoes(id_val)
    fase = "Celebração" if pd.isna(row.get('no_instrumento')) or "SUSPENSIVA" in str(row.get('situacao_contratual')) else "Execução"
    
    st.title(f"Convênio {id_val} - {fase}")
    
    # 1. CELEBRAÇÃO (Campos Azuis da Imagem)
    if fase == "Celebração":
        st.subheader("🔹 Etapa de Celebração")
        c1, c2 = st.columns(2)
        with c1:
            notif_data = st.date_input("Data Última Notificação", disabled=(modo == 'leitura' or modo == 'vistoria'))
            notif_qtd = st.number_input("Qtd Notificações", disabled=(modo == 'leitura' or modo == 'vistoria'))
        with c2:
            reit_data = st.date_input("Data Última Reiteração", disabled=(modo == 'leitura' or modo == 'vistoria'))
            reit_qtd = st.number_input("Qtd Reiterações", disabled=(modo == 'leitura' or modo == 'vistoria'))

    # 2. EXECUÇÃO (Campos Verdes/Roxos da Imagem)
    elif fase == "Execução":
        st.subheader("🟢 Etapa de Execução")
        c1, c2 = st.columns(2)
        with c1:
            # ALERTA DE VALOR (Comparação manual vs painel)
            val_painel = row.get('valor_global', 0)
            val_manual = st.number_input("Valor do Contrato (Manual)", value=float(edicoes.get('valor_contrato', val_painel)), 
                                        disabled=(modo == 'leitura' or modo == 'vistoria'))
            if val_manual == val_painel:
                st.success("✅ Igual ao Painel")
            else:
                st.error("⚠️ Diferente do Painel")
            
            st.date_input("Data Aceite Plataforma", disabled=(modo == 'leitura' or modo == 'vistoria'))
        
        with c2:
            st.selectbox("Status da Obra", ["Não Iniciada", "Em Andamento", "Parada", "Finalizada"], 
                         disabled=(modo == 'leitura' or modo == 'vistoria'))

    # 3. QUADRO DE VISTORIAS (Editável apenas na aba Vistorias ou pelo Gestor)
    st.divider()
    st.subheader("🟣 Quadro de Vistorias")
    can_edit_vistoria = (modo == 'vistoria' or user_role == "Gestor")
    st.text_input("Tipo de Vistoria", disabled=not can_edit_vistoria)
    st.date_input("Data da Vistoria", disabled=not can_edit_vistoria)
    st.slider("% Execução", 0, 100, disabled=not can_edit_vistoria)

    # 4. OBSERVAÇÕES COM HISTÓRICO
    st.subheader("📝 Observações")
    nova_obs = st.text_area("Adicionar Anotação", disabled=(modo == 'leitura'))
    if st.button("Salvar Anotação", disabled=(modo == 'leitura')):
        save_edicao_com_historico(id_val, "obs", nova_obs, user_name)
        st.rerun()
    
    hist = get_historico(id_val)
    if not hist.empty:
        st.table(hist[['data_hora', 'usuario', 'valor']])

# --- RENDERIZAÇÃO DAS ABAS ---
if menu == "Geral":
    st.header("🔍 Pesquisa Geral (Leitura)")
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
        with cc1:  # Celebração
            f_pb_sit = st.text_input("Situação do Projeto Básico")
            f_pb_ana = st.text_input("Analista do Projeto Básico (Eng. Atribuído - Celebração)")
            f_pb_stat = st.text_input("Status da Análise do Projeto Básico")
        with cc2:  # Execução
            f_ex_fisc = st.text_input("Fiscal de Acompanhamento (Eng. Atribuído - Execução)")
            f_ex_stat = st.text_input("Status da Execução")
            f_ex_acao = st.text_input("Status Ação Convenente")
            f_ex_obra = st.text_input("Status da Obra")
        with cc3:  # Prestação de Contas
            f_pc_fisc = st.text_input("Fiscal de Acompanhamento prestação de contas (Eng. Atribuído - Prestação de contas)")
            f_pc_exec = st.text_input("Status de Execução prestação de contas")
            f_pc_obra = st.text_input("Status da obra prestação de contas")
            f_pc_stat = st.text_input("Status prestação de contas")

        submitted = st.form_submit_button("🔍 Pesquisar")

    if submitted or st.session_state.selected_id:
        res = df.copy()
        # Aplicação dos filtros
        if f_inst:
            res = res[res['no_instrumento'] == f_inst]
        if f_ano:
            res = res[res['ano'] == int(f_ano)]
        if f_obj:
            res = res[res['objeto'].str.contains(f_obj, case=False, na=False)]
        if f_proc:
            res = res[res['no_processo'].str.contains(f_proc, case=False, na=False)]
        if f_uf:
            res = res[res['uf'].isin(f_uf)]
        if f_mun:
            res = res[res['municipio'].str.contains(f_mun, case=False, na=False)]
        if f_parl:
            res = res[res['parlamentar'].str.contains(f_parl, case=False, na=False)]
        if f_val > 0:
            res = res[res['valor_global'] >= f_val]
        # Adicione filtros por coordenação conforme necessário (exemplo simplificado)
        if f_pb_sit:
            res = res[res['situacao_pb'].str.contains(f_pb_sit, case=False, na=False)]
        # ... (adicione os outros filtros de coordenação aqui)

        if st.session_state.selected_id:
            render_detalhe(st.session_state.selected_id, 'leitura')
        else:
            st.write(f"{len(res)} resultados encontrados.")
            for idx, r in res.iterrows():
                id_v = r['no_instrumento'] if pd.notna(r['no_instrumento']) else r['no_proposta']
                with st.expander(f"Convênio {id_v} - {r['municipio']} ({r['uf']})"):
                    st.write(f"**Objeto:** {r['objeto']}")
                    if st.button("Ver Detalhes", key=f"btn_{idx}_{id_v}"):
                        st.session_state.selected_id = id_v
                        st.rerun()

elif menu == "Coordenações":
    st.header(f"📑 Coordenações - {user_name}")
    
    # Filtro de busca repetido
    with st.expander("🔍 Filtros de Pesquisa"):
        c1, c2 = st.columns(2)
        f_mun = c1.text_input("Município", key="coord_mun")
        f_inst = c2.text_input("Nº Instrumento", key="coord_inst")

    tab_cel, tab_exe = st.tabs(["Celebração", "Execução"])
    
    # Filtra casos do usuário
    meus_casos = df[(df['eng_resp'] == user_name) | (df['tec_resp'] == user_name)]
    if f_mun:
        meus_casos = meus_casos[meus_casos['municipio'].str.contains(f_mun, case=False, na=False)]
    if f_inst:
        meus_casos = meus_casos[(meus_casos['no_instrumento'] == f_inst) | (meus_casos['no_proposta'] == f_inst)]

    if st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, 'convenio')
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

elif menu == "Vistorias":
    st.header(f"🏗️ Minhas Vistorias - {user_name}")
    # Filtra por vistoria_resp == user_name
    # Ao clicar: render_detalhe(id, 'vistoria')

elif menu == "Upload Painel":
    st.header("📂 Upload de Planilhas")
    files = st.file_uploader("Suba os 6 arquivos do Painel", accept_multiple_files=True)
    if st.button("Processar Base"):
        st.session_state.main_df = load_and_merge_all({f.name: f for f in files})
        st.success("Base atualizada!")

elif menu == "Atribuição":
    st.header("⚖️ Atribuição (Gestor)")
    inst = st.text_input("Nº Instrumento")
    eng = st.text_input("Engenheiro Responsável")
    vis = st.text_input("Engenheiro da Vistoria")
    if st.button("Atribuir"):
        # Salva eng_resp e vistoria_resp no db_atribuicao
        st.success("Atribuído com sucesso!")
