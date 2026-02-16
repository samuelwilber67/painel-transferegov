import streamlit as st
import pandas as pd
from utils.data import load_and_merge_all, save_edicao_com_historico, get_edicoes, get_historico

st.set_page_config(page_title="Plataforma de Convênios", layout="wide")

# --- LOGIN E NAVEGAÇÃO ---
st.sidebar.title("🔐 Acesso")
user_name = st.sidebar.text_input("Seu Nome (Login)", "Samuel Wilber")
user_role = st.sidebar.selectbox("Perfil", ["Engenheiro", "Gestor"])

st.sidebar.divider()
menu = st.sidebar.radio("Navegação", ["Geral", "Coordenações", "Atribuição", "Upload Painel"])

if 'main_df' not in st.session_state: st.session_state.main_df = pd.DataFrame()
if 'selected_id' not in st.session_state: st.session_state.selected_id = None

df = st.session_state.main_df

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
    if st.button("⬅️ Voltar"):
        st.session_state.selected_id = None
        st.rerun()

    row = df[(df['no_instrumento'] == id_val) | (df['no_proposta'] == id_val)].iloc[0]
    fase = identificar_fase(row)
    edicoes = get_edicoes(id_val)
    
    st.header(f"📌 {fase}: {id_val}")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🏛️ Dados Automáticos (Painel)")
        st.info(f"**Objeto:** {row.get('objeto')}")
        st.write(f"**Parlamentar:** {row.get('parlamentar')}")
        val_p = row.get('valor_global_painel', 0)
        st.write(f"**Valor Global (Painel):** R$ {val_p:,.2f}")

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

# --- PÁGINA: GERAL (APENAS LEITURA) ---
if menu == "Geral":
    st.header("🔍 Consulta Geral (Somente Leitura)")
    # Filtros de pesquisa
    with st.expander("Filtros de Busca", expanded=True):
        c1, c2, c3 = st.columns(3)
        f_uf = c1.multiselect("UF", df['uf'].unique()) if not df.empty else []
        f_mun = c2.text_input("Município")
        f_inst = c3.text_input("Nº Instrumento")
    
    if st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, can_edit=False)
    else:
        # Lógica de filtragem e exibição de cards...
        st.write("Resultados da pesquisa aparecem aqui...")
        # Exemplo de card:
        if st.button("Ver Exemplo 909561"):
            st.session_state.selected_id = "909561"
            st.rerun()

# --- PÁGINA: COORDENAÇÕES (EDITÁVEL) ---
elif menu == "Coordenações":
    st.header(f"📑 Meus Convênios - {user_name}")
    
    # Filtra apenas o que é do usuário
    meus_casos = df[(df['eng_resp'] == user_name) | (df['tec_resp'] == user_name)]
    
    if meus_casos.empty:
        st.info("Você não possui convênios atribuídos ao seu nome.")
    elif st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, can_edit=True)
    else:
        tabs = st.tabs(["Celebração", "Execução", "Prestação de Contas"])
        # Lógica para distribuir os casos nas abas conforme a função identificar_fase...
        with tabs[0]:
            st.write("Convênios em Celebração atribuídos a você.")
            for idx, r in meus_casos.iterrows():
                if identificar_fase(r) == "Celebração":
                    st.button(f"Editar {r['no_instrumento']}", key=f"ed_{idx}", 
                              on_click=lambda id=r['no_instrumento']: setattr(st.session_state, 'selected_id', id))

# --- PÁGINA: UPLOAD ---
elif menu == "Upload Painel":
    st.header("📂 Carga de Dados")
    files = st.file_uploader("Suba as planilhas do Transferegov", accept_multiple_files=True)
    if st.button("Atualizar Sistema"):
        st.session_state.main_df = load_and_merge_all({f.name: f for f in files})
        st.success("Base de dados sincronizada!")
