import streamlit as st
import pandas as pd
from utils.data import load_and_merge_all, save_edicao_com_historico, get_edicoes, get_historico

st.set_page_config(page_title="Sistema Gerencial de Convênios", layout="wide")

# --- ESTADO DA SESSÃO (ESTABILIDADE) ---
if 'main_df' not in st.session_state:
    st.session_state.main_df = pd.DataFrame()
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

# --- SIDEBAR: LOGIN E NAVEGAÇÃO ---
st.sidebar.title("👤 Usuário")
user_name = st.sidebar.text_input("Nome", "Samuel Wilber")
user_role = st.sidebar.selectbox("Perfil", ["Engenheiro", "Técnico", "Gestor"])

st.sidebar.divider()
menu = st.sidebar.radio("Navegação", ["Geral", "Coordenações", "Vistorias", "Upload Painel", "Atribuição"])

df = st.session_state.main_df

# --- FUNÇÕES DE APOIO ---
def identificar_fase(row):
    status = str(row.get('status_painel', '') or '').upper()
    sit_contratual = str(row.get('situacao_contratual', '') or '').upper()
    ni = row.get('no_instrumento')
    if pd.isna(ni) or str(ni).strip() == "" or "SUSPENSIVA" in sit_contratual:
        return "Celebração"
    return "Execução"

def render_detalhe(id_val, modo):
    """
    id_val: ID do convênio selecionado
    modo: 'leitura' (Geral), 'convenio' (Coordenações), 'vistoria' (Vistorias)
    """
    # Busca o registro
    mask = (df['no_instrumento'].astype(str) == str(id_val)) | (df['no_proposta'].astype(str) == str(id_val))
    filtered = df[mask]
    
    if filtered.empty:
        st.error("Registro não encontrado.")
        if st.button("Voltar"):
            st.session_state.selected_id = None
            st.rerun()
        return

    row = filtered.iloc[0]
    fase = identificar_fase(row)
    edicoes = get_edicoes(id_val)
    
    if st.button("⬅️ Voltar para a lista"):
        st.session_state.selected_id = None
        st.rerun()

    st.header(f"📌 {fase}: {id_val}")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏛️ Dados do Painel")
        st.info(f"**Objeto:** {row.get('objeto', 'N/A')}")
        st.write(f"**UF/Município:** {row.get('uf', 'N/A')} / {row.get('municipio', 'N/A')}")
        st.write(f"**Status Painel:** {row.get('status_painel', 'N/A')}")
        
    with c2:
        st.subheader("✍️ Gestão Manual")
        # Exemplo de Alerta de Valor
        val_p = row.get('valor_global', 0)
        val_m = st.number_input("Valor Global Gerencial", value=float(edicoes.get('valor_manual', val_p)), 
                                disabled=(modo == 'leitura'))
        
        if float(val_m) == float(val_p): st.success("✅ Valor igual ao Painel")
        else: st.error("⚠️ Valor diferente do Painel")

        obs = st.text_area("Observações", value=edicoes.get('observacoes', ""), disabled=(modo == 'leitura'))
        
        if modo != 'leitura' and st.button("Salvar Alterações"):
            save_edicao_com_historico(id_val, "valor_manual", val_m, user_name)
            save_edicao_com_historico(id_val, "observacoes", obs, user_name)
            st.toast("Salvo com sucesso!")

    st.divider()
    st.subheader("📜 Histórico")
    hist = get_historico(id_val)
    if not hist.empty:
        st.dataframe(hist[['data_hora', 'usuario', 'campo', 'valor']], use_container_width=True)

# --- LÓGICA DE TELAS ---

# Se não há base, força Upload (exceto se for o menu de Upload)
if df.empty and menu != "Upload Painel":
    st.warning("⚠️ Por favor, suba sua base de dados na aba **Upload Painel** para começar.")
    st.stop()

if menu == "Upload Painel":
    st.header("📂 Upload de Dados")
    files = st.file_uploader("Arraste os arquivos do Transferegov", accept_multiple_files=True)
    if st.button("Processar Base"):
        if files:
            st.session_state.main_df = load_and_merge_all({f.name: f for f in files})
            st.success("Base carregada com sucesso!")
            st.rerun()

elif menu == "Geral":
    if st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, modo='leitura')
    else:
        st.header("🔍 Consulta Geral")
        # Filtros fora de formulário para evitar travamento
        c1, c2, c3 = st.columns(3)
        f_inst = c1.text_input("Nº Instrumento / Proposta")
        f_uf = c2.multiselect("UF", sorted(df['uf'].dropna().unique())) if 'uf' in df.columns else []
        f_mun = c3.text_input("Município")

        # Aplicar filtros
        res = df.copy()
        if f_inst:
            res = res[(res['no_instrumento'].astype(str).str.contains(f_inst)) | (res['no_proposta'].astype(str).str.contains(f_inst))]
        if f_uf:
            res = res[res['uf'].isin(f_uf)]
        if f_mun:
            res = res[res['municipio'].str.contains(f_mun, case=False, na=False)]

        st.write(f"Exibindo {len(res)} resultados:")
        for idx, r in res.head(50).iterrows(): # Limitado a 50 para performance
            id_v = r.get('no_instrumento') if pd.notna(r.get('no_instrumento')) else r.get('no_proposta')
            with st.container(border=True):
                st.write(f"**{id_v}** - {r.get('municipio')} ({r.get('uf')})")
                if st.button("Visualizar Detalhes", key=f"btn_geral_{idx}"):
                    st.session_state.selected_id = id_v
                    st.rerun()

elif menu == "Coordenações":
    if st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, modo='convenio')
    else:
        st.header(f"📑 Meus Convênios - {user_name}")
        # Filtra apenas o que é do usuário
        meus = df[(df['eng_resp'] == user_name) | (df['tec_resp'] == user_name)]
        
        if meus.empty:
            st.info("Nenhum convênio atribuído a você.")
        else:
            tab1, tab2 = st.tabs(["Celebração", "Execução"])
            with tab1:
                for idx, r in meus.iterrows():
                    if identificar_fase(r) == "Celebração":
                        st.write(f"ID: {r.get('no_instrumento') or r.get('no_proposta')}")
                        if st.button("Editar", key=f"ed_cel_{idx}"):
                            st.session_state.selected_id = r.get('no_instrumento') or r.get('no_proposta')
                            st.rerun()
            with tab2:
                for idx, r in meus.iterrows():
                    if identificar_fase(r) == "Execução":
                        st.write(f"ID: {r.get('no_instrumento')}")
                        if st.button("Editar", key=f"ed_exe_{idx}"):
                            st.session_state.selected_id = r.get('no_instrumento')
                            st.rerun()

elif menu == "Atribuição":
    st.header("⚖️ Atribuição de Responsáveis")
    if user_role != "Gestor":
        st.error("Acesso restrito a Gestores.")
    else:
        # Interface simples para atribuir
        id_atrib = st.selectbox("Selecione o Convênio", df['no_instrumento'].dropna().unique())
        eng = st.text_input("Nome do Engenheiro")
        if st.button("Confirmar Atribuição"):
            # Aqui chamaria a função de salvar atribuição do data.py
            st.success(f"Convênio {id_atrib} atribuído a {eng}")
