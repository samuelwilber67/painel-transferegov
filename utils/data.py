from __future__ import annotations
import pandas as pd
import unicodedata
import os
from datetime import datetime

# Arquivos de "Banco de Dados" local
DB_ATRIBUICAO = "db_atribuicao.csv"
DB_EDICOES = "db_edicoes.csv"
DB_HISTORICO = "db_historico.csv"

def _key(s: str) -> str:
    if not s: return ""
    s = unicodedata.normalize("NFKD", str(s))
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.lower().strip().split())

def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    mapping = {
        _key("Nº Instrumento"): "no_instrumento",
        _key("Nº Proposta"): "no_proposta",
        _key("Ano Assinatura"): "ano",
        _key("UF"): "uf",
        _key("Município"): "municipio",
        _key("Objeto"): "objeto",
        _key("Parlamentar"): "parlamentar",
        _key("Situação Instrumento"): "status_painel",
        _key("Situação Inst. Contratual"): "situacao_contratual",
        _key("Valor Global"): "valor_global_painel",
        _key("Engenheiro Responsável"): "eng_resp",
        _key("Técnico Responsável"): "tec_resp",
        _key("Status da Obra"): "status_obra_painel",
        _key("Analista do Projeto Básico"): "analista_pb",
    }
    rename_dict = {col: mapping[_key(col)] for col in df.columns if _key(col) in mapping}
    return df.rename(columns=rename_dict)

def load_and_merge_all(files_dict: dict) -> pd.DataFrame:
    main_df = pd.DataFrame()
    for name, content in files_dict.items():
        df = pd.read_excel(content, engine="openpyxl")
        df = rename_columns(df)
        if main_df.empty:
            main_df = df
        else:
            on_col = "no_instrumento" if "no_instrumento" in df.columns and "no_instrumento" in main_df.columns else "no_proposta"
            if on_col in main_df.columns:
                main_df = pd.merge(main_df, df, on=on_col, how="outer", suffixes=('', '_drop'))
                main_df = main_df.loc[:, ~main_df.columns.str.contains('_drop')]

    # Merge Atribuições Locais
    if os.path.exists(DB_ATRIBUICAO):
        attr = pd.read_csv(DB_ATRIBUICAO, dtype={'no_instrumento': str, 'no_proposta': str})
        main_df = pd.merge(main_df, attr, on='no_instrumento', how='left', suffixes=('', '_attr'))

    # Garante colunas mínimas
    cols_check = ['no_instrumento', 'no_proposta', 'eng_resp', 'tec_resp', 'status_painel', 'situacao_contratual']
    for c in cols_check:
        if c not in main_df.columns: main_df[c] = pd.NA
        
    return main_df

def save_edicao_com_historico(id_val, campo, valor_novo, usuario):
    # Salva valor atual
    df_ed = pd.DataFrame([[str(id_val), campo, valor_novo]], columns=["id", "campo", "valor"])
    if os.path.exists(DB_EDICOES):
        old_ed = pd.read_csv(DB_EDICOES, dtype={'id': str})
        df_ed = pd.concat([old_ed, df_ed]).drop_duplicates(subset=['id', 'campo'], keep='last')
    df_ed.to_csv(DB_EDICOES, index=False)

    # Log de Histórico
    log = pd.DataFrame([[str(id_val), campo, valor_novo, usuario, datetime.now().strftime("%d/%m/%Y %H:%M")]], 
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
