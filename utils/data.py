import pandas as pd
import os
from datetime import datetime

DB_ATRIBUICAO = "db_atribuicao.csv"
DB_EDICOES = "db_edicoes.csv"
DB_HISTORICO = "db_historico.csv"

def load_and_merge_all(files_dict):
    """Processa as planilhas e normaliza as colunas."""
    main_df = pd.DataFrame()
    
    # Mapeamento para padronizar nomes de colunas do Excel
    mapping = {
        'Nº do Instrumento': 'no_instrumento', 'Nº Instrumento': 'no_instrumento',
        'Nº da Proposta': 'no_proposta', 'Nº Proposta': 'no_proposta',
        'UF': 'uf', 'Município': 'municipio', 'Objeto': 'objeto',
        'Situação do Instrumento': 'status_painel',
        'Situação Inst. Contratual': 'situacao_contratual',
        'Valor Global': 'valor_global'
    }

    for name, content in files_dict.items():
        try:
            temp_df = pd.read_excel(content, engine="openpyxl")
            temp_df = temp_df.rename(columns=mapping)
            
            if main_df.empty:
                main_df = temp_df
            else:
                # Merge por Instrumento ou Proposta
                join_col = 'no_instrumento' if 'no_instrumento' in temp_df.columns else 'no_proposta'
                if join_col in main_df.columns:
                    main_df = pd.merge(main_df, temp_df, on=join_col, how='outer', suffixes=('', '_dup'))
        except:
            continue

    # Remove colunas duplicadas
    main_df = main_df.loc[:, ~main_df.columns.str.endswith('_dup')]
    
    # GARANTIA: Cria colunas faltantes para evitar KeyError
    colunas_obrigatorias = [
        'no_instrumento', 'no_proposta', 'uf', 'municipio', 'objeto', 
        'situacao_contratual', 'status_painel', 'valor_global',
        'eng_resp', 'tec_resp', 'vistoria_resp'
    ]
    for col in colunas_obrigatorias:
        if col not in main_df.columns:
            main_df[col] = pd.NA
            
    return main_df

def save_edicao_com_historico(id_val, campo, valor, usuario):
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    # Salva edição atual
    df_ed = pd.DataFrame([[str(id_val), campo, valor]], columns=["id", "campo", "valor"])
    if os.path.exists(DB_EDICOES):
        old = pd.read_csv(DB_EDICOES, dtype={'id': str})
        df_ed = pd.concat([old, df_ed]).drop_duplicates(subset=['id', 'campo'], keep='last')
    df_ed.to_csv(DB_EDICOES, index=False)
    # Registra log
    log = pd.DataFrame([[str(id_val), campo, valor, usuario, data_hora]], columns=["id", "campo", "valor", "usuario", "data_hora"])
    if os.path.exists(DB_HISTORICO):
        log = pd.concat([pd.read_csv(DB_HISTORICO, dtype={'id': str}), log])
    log.to_csv(DB_HISTORICO, index=False)

def get_edicoes(id_val):
    if not os.path.exists(DB_EDICOES): return {}
    df = pd.read_csv(DB_EDICOES, dtype={'id': str})
    return dict(zip(df[df['id'] == str(id_val)]['campo'], df[df['id'] == str(id_val)]['valor']))

def get_historico(id_val):
    if not os.path.exists(DB_HISTORICO): return pd.DataFrame()
    return pd.read_csv(DB_HISTORICO, dtype={'id': str})[lambda d: d['id'] == str(id_val)]
