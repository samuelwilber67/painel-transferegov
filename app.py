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
    # Filtros aqui...
    # Ao clicar em um convênio: render_detalhe(id, 'leitura')

elif menu == "Coordenações":
    st.header(f"📑 Meus Convênios - {user_name}")
    # Filtra por eng_resp == user_name
    # Ao clicar: render_detalhe(id, 'convenio')

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
