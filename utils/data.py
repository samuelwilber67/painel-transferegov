from __future__ import annotations
import pandas as pd
import os
from datetime import datetime

# Bancos de dados locais (CSV)
DB_ATRIBUICAO = "db_atribuicao.csv"
DB_EDICOES = "db_edicoes.csv"
DB_HISTORICO = "db_historico.csv"

def load_and_merge_all(files_dict: dict) -> pd.DataFrame:
    # Lógica de merge das 6 planilhas (simplificada para o exemplo)
    main_df = pd.DataFrame()
    for name, content in files_dict.items():
        df = pd.read_excel(content, engine="openpyxl")
        # ... (renomeação de colunas conforme conversas anteriores)
        if main_df.empty: main_df = df
        else: main_df = pd.merge(main_df, df, on="no_instrumento", how="outer")
    
    # Merge Atribuições (Convênio e Vistoria)
    if os.path.exists(DB_ATRIBUICAO):
        attr = pd.read_csv(DB_ATRIBUICAO, dtype={'no_instrumento': str})
        main_df = pd.merge(main_df, attr, on='no_instrumento', how='left')
    
    return main_df

def save_edicao_com_historico(id_val, campo, valor_novo, usuario):
    data_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
    # Salva estado atual
    df_ed = pd.DataFrame([[str(id_val), campo, valor_novo]], columns=["id", "campo", "valor"])
    if os.path.exists(DB_EDICOES):
        old = pd.read_csv(DB_EDICOES, dtype={'id': str})
        df_ed = pd.concat([old, df_ed]).drop_duplicates(subset=['id', 'campo'], keep='last')
    df_ed.to_csv(DB_EDICOES, index=False)

    # Registra Log
    log = pd.DataFrame([[str(id_val), campo, valor_novo, usuario, data_hora]], 
                       columns=["id", "campo", "valor", "usuario", "data_hora"])
    if os.path.exists(DB_HISTORICO):
        log = pd.concat([pd.read_csv(DB_HISTORICO, dtype={'id': str}), log])
    log.to_csv(DB_HISTORICO, index=False)

def get_edicoes(id_val):
    if not os.path.exists(DB_EDICOES): return {}
    df = pd.read_csv(DB_EDICOES, dtype={'id': str})
    subset = df[df['id'] == str(id_val)]
    return dict(zip(subset['campo'], subset['valor']))

def get_historico(id_val):
    if not os.path.exists(DB_HISTORICO): return pd.DataFrame()
    df = pd.read_csv(DB_HISTORICO, dtype={'id': str})
    return df[df['id'] == str(id_val)].sort_values("data_hora", ascending=False)
