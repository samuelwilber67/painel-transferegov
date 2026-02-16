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
st.sidebar.warning("⚠️ 10 convênios precisam de notificação")
st.sidebar.error("🚨 5 casos sem pagamento > 90 dias")

# --- NAVEGAÇÃO ---
menu_options = ["Geral", "Coordenações", "Vistorias", "Upload Painel"]
if user_role == "Gestor":
    menu_options += ["Atribuição"]
menu = st.sidebar.radio("Menu Principal", menu_options)

# --- ESTADO DA SESSÃO ---
if 'main_df' not in st.session_state:
    # Dados de teste iniciais (com todas as colunas necessárias para evitar KeyError)
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
        'vistoria_resp': [pd.NA, pd.NA, 'Samuel Wilber'],
        'no_processo': [pd.NA, 'NUP123', pd.NA],  # Adicionado para filtros
        'situacao_pb': [pd.NA, 'Aprovado', pd.NA],  # Adicionado para filtros
        'status_exec': [pd.NA, 'Em Andamento', pd.NA],
        'status_obra': [pd.NA, 'Em Andamento', pd.NA],
    })
if 'selected_id' not in st.session_state:
    st.session_state.selected_id = None

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
def render_detalhe(id_val, modo):
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
        val_p = row.get('valor_global', 0)
        st.write(f"**Valor Global (Painel):** R$ {val_p:,.2f}")
        st.write(f"**UF/Município:** {row.get('uf')} / {row.get('municipio')}")
        
    with c2:
        st.subheader("✍️ Dados Manuais (Gerencial)")
        val_m = st.number_input("Valor Global Gerencial", value=float(edicoes.get('valor_manual', val_p)), disabled=(modo == 'leitura' or modo == 'vistoria'))
        
        if val_m == val_p:
            st.success("✅ Igual ao Painel")
        else:
            st.error("⚠️ Diferente do Painel")
        
        obs = st.text_area("Observações/Anotações", value=edicoes.get('observacoes', ""), disabled=(modo == 'leitura'))
        
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
        uf_options = df['uf'].unique() if 'uf' in df.columns else []
        f_uf = c5.multiselect("UF", uf_options)
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
        # Aplicação dos filtros com verificação de coluna
        if f_inst and 'no_instrumento' in res.columns:
            res = res[res['no_instrumento'] == f_inst]
        if f_ano and 'ano' in res.columns:
            try:
                res = res[res['ano'] == int(f_ano)]
            except ValueError:
                pass
        if f_obj and 'objeto' in res.columns:
            res = res[res['objeto'].str.contains(f_obj, case=False, na=False)]
        if f_proc and 'no_processo' in res.columns:
            res = res[res['no_processo'].str.contains(f_proc, case=False, na=False)]
        if f_uf and 'uf' in res.columns:
            res = res[res['uf'].isin(f_uf)]
        if f_mun and 'municipio' in res.columns:
            res = res[res['municipio'].str.contains(f_mun, case=False, na=False)]
        if f_parl and 'parlamentar' in res.columns:
            res = res[res['parlamentar'].str.contains(f_parl, case=False, na=False)]
        if f_val > 0 and 'valor_global' in res.columns:
            res = res[res['valor_global'] >= f_val]
        # Filtros por coordenação
        if f_pb_sit and 'situacao_pb' in res.columns:
            res = res[res['situacao_pb'].str.contains(f_pb_sit, case=False, na=False)]
        # Adicione outros filtros similares aqui

        if st.session_state.selected_id:
            render_detalhe(st.session_state.selected_id, 'leitura')
        else:
            st.write(f"{len(res)} resultados encontrados.")
            for idx, r in res.iterrows():
                id_v = r.get('no_instrumento') if pd.notna(r.get('no_instrumento')) else r.get('no_proposta', f"idx_{idx}")
                municipio = r.get('municipio', 'N/A')
                uf = r.get('uf', 'N/A')
                objeto = r.get('objeto', 'N/A')
                with st.expander(f"Convênio {id_v} - {municipio} ({uf})"):
                    st.write(f"**Objeto:** {objeto}")
                    if st.button("Ver Detalhes", key=f"btn_{idx}_{id_v}"):
                        st.session_state.selected_id = id_v
                        st.rerun()

elif menu == "Coordenações":
    st.header(f"📑 Coordenações - {user_name}")
    
    # Filtro de busca
    with st.expander("🔍 Filtros de Pesquisa"):
        c1, c2 = st.columns(2)
        f_mun = c1.text_input("Município", key="coord_mun")
        f_inst = c2.text_input("Nº Instrumento", key="coord_inst")

    tab_cel, tab_exe = st.tabs(["Celebração", "Execução"])
    
    # Filtra casos do usuário
    meus_casos = df[(df['eng_resp'] == user_name) | (df['tec_resp'] == user_name)]
    if f_mun and 'municipio' in meus_casos.columns:
        meus_casos = meus_casos[meus_casos['municipio'].str.contains(f_mun, case=False, na=False)]
    if f_inst and 'no_instrumento' in meus_casos.columns and 'no_proposta' in meus_casos.columns:
        meus_casos = meus_casos[(meus_casos['no_instrumento'] == f_inst) | (meus_casos['no_proposta'] == f_inst)]

    if st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, 'convenio')
    else:
        with tab_cel:
            cols = ["no_instrumento", "ano", "uf", "municipio", "objeto", "status_painel", "situacao_pb"]
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
    vistorias = df[df['vistoria_resp'] == user_name]
    if vistorias.empty:
        st.info("Você não possui vistorias atribuídas.")
    else:
        for idx, r in vistorias.iterrows():
            id_v = r.get('no_instrumento') if pd.notna(r.get('no_instrumento')) else r.get('no_proposta', f"idx_{idx}")
            with st.expander(f"Vistoria {id_v} - {r.get('municipio', 'N/A')} ({r.get('uf', 'N/A')})"):
                st.write(f"**Objeto:** {r.get('objeto', 'N/A')}")
                if st.button("Ver/Editar Vistoria", key=f"vis_{idx}_{id_v}"):
                    st.session_state.selected_id = id_v
                    st.rerun()
    
    if st.session_state.selected_id:
        render_detalhe(st.session_state.selected_id, 'vistoria')

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
        # Salva no CSV
        df_attr = pd.DataFrame([[inst, eng, vis]], columns=["no_instrumento", "eng_resp", "vistoria_resp"])
        if os.path.exists("db_atribuicao.csv"):
            old = pd.read_csv("db_atribuicao.csv", dtype={'no_instrumento': str})
            old = old[old['no_instrumento'] != inst]
            df_attr = pd.concat([old, df_attr], ignore_index=True)
        df_attr.to_csv("db_atribuicao.csv", index=False)
        st.success("Atribuído com sucesso!")
