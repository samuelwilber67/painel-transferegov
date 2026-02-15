from __future__ import annotations
import pandas as pd
import unicodedata
import os

# Arquivos de "Banco de Dados" local
DB_ATRIBUICAO = "db_atribuicao.csv"
DB_EDICOES = "db_edicoes.csv"

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
        _key("Situação Instrumento"): "status",
        _key("Valor Global"): "valor_global_painel",
        _key("Engenheiro Responsável"): "eng_resp",
        _key("Técnico Responsável"): "tec_resp",
        _key("Status Execução"): "status_execucao",
        _key("Status da Obra"): "status_obra",
        _key("Análise do PB"): "status_pb",
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

    # Merge Atribuições
    if os.path.exists(DB_ATRIBUICAO):
        attr = pd.read_csv(DB_ATRIBUICAO, dtype={'no_instrumento': str, 'no_proposta': str})
        for col in ['no_instrumento', 'no_proposta']:
            if col in main_df.columns and col in attr.columns:
                main_df = pd.merge(main_df, attr, on=col, how="left", suffixes=('', '_attr'))

    # Garante colunas mínimas
    for col in ['eng_resp', 'tec_resp', 'no_instrumento', 'no_proposta']:
        if col not in main_df.columns: main_df[col] = pd.NA
        
    return main_df

def save_atribuicao(id_val, is_inst, eng, tec):
    col = "no_instrumento" if is_inst else "no_proposta"
    new_data = pd.DataFrame([[str(id_val), eng, tec]], columns=[col, "eng_resp", "tec_resp"])
    if os.path.exists(DB_ATRIBUICAO):
        old = pd.read_csv(DB_ATRIBUICAO, dtype={col: str})
        old = old[old[col] != str(id_val)]
        new_data = pd.concat([old, new_data])
    new_data.to_csv(DB_ATRIBUICAO, index=False)

def save_edicao(id_val, campo, valor):
    df = pd.DataFrame([[str(id_val), campo, valor]], columns=["id", "campo", "valor"])
    if os.path.exists(DB_EDICOES):
        old = pd.read_csv(DB_EDICOES, dtype={'id': str})
        df = pd.concat([old, df]).drop_duplicates(subset=['id', 'campo'], keep='last')
    df.to_csv(DB_EDICOES, index=False)

def get_edicoes(id_val):
    if not os.path.exists(DB_EDICOES): return {}
    df = pd.read_csv(DB_EDICOES, dtype={'id': str})
    subset = df[df['id'] == str(id_val)]
    return dict(zip(subset['campo'], subset['valor']))
