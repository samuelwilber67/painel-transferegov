from __future__ import annotations
import pandas as pd
import unicodedata
import os

# Arquivo onde salvaremos as atribuições e edições locais (nosso "banco de dados")
DB_ATRIBUICAO = "db_atribuicao.csv"
DB_EDICOES = "db_edicoes.csv"

def _key(s: str) -> str:
    if not s: return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return " ".join(s.lower().strip().split())

def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Mapeamento expandido para aceitar as 6 planilhas
    mapping = {
        _key("Nº Instrumento"): "no_instrumento",
        _key("Nº Proposta"): "no_proposta",
        _key("Nº Processo"): "no_processo",
        _key("Objeto"): "objeto",
        _key("UF"): "uf",
        _key("Município"): "municipio",
        _key("Nome do Proponente"): "nome_proponente",
        _key("Situação Instrumento"): "situacao_instrumento",
        _key("Valor Global"): "valor_global",
        _key("Último Pagamento"): "ultimo_pagamento",
        _key("Sem Desembolso"): "sem_desembolso",
        _key("Engenheiro Responsável"): "eng_resp",
        _key("Técnico Responsável"): "tec_resp",
        # Adicione aqui as novas colunas das outras 5 planilhas
    }
    rename_dict = {col: mapping[_key(col)] for col in df.columns if _key(col) in mapping}
    return df.rename(columns=rename_dict)

def load_and_merge_all(files_dict: dict) -> pd.DataFrame:
    """
    Recebe um dicionário de arquivos {nome: bytes} e une todos.
    """
    main_df = pd.DataFrame()
    
    for name, content in files_dict.items():
        df = pd.read_excel(content, engine="openpyxl")
        df = rename_columns(df)
        
        if main_df.empty:
            main_df = df
        else:
            # Une pelo número do instrumento ou proposta
            on_col = "no_instrumento" if "no_instrumento" in df.columns else "no_proposta"
            if on_col in main_df.columns:
                main_df = pd.merge(main_df, df, on=on_col, how="outer", suffixes=('', '_drop'))
                main_df = main_df.loc[:, ~main_df.columns.str.contains('_drop')]
    
    # Carrega Atribuições Locais
    if os.path.exists(DB_ATRIBUICAO):
        attr_df = pd.read_csv(DB_ATRIBUICAO, dtype={'no_instrumento': str})
        main_df = pd.merge(main_df, attr_df, on="no_instrumento", how="left")
        
    return main_df

def save_atribuicao(no_inst, eng, tec):
    df = pd.DataFrame([[str(no_inst), eng, tec]], columns=["no_instrumento", "eng_resp", "tec_resp"])
    if os.path.exists(DB_ATRIBUICAO):
        old = pd.read_csv(DB_ATRIBUICAO, dtype={'no_instrumento': str})
        df = pd.concat([old[old['no_instrumento'] != str(no_inst)], df])
    df.to_csv(DB_ATRIBUICAO, index=False)

def save_edicao_local(no_inst, campo, valor):
    # Salva edições manuais (como as vistorias)
    df = pd.DataFrame([[str(no_inst), campo, valor]], columns=["no_instrumento", "campo", "valor"])
    if os.path.exists(DB_EDICOES):
        old = pd.read_csv(DB_EDICOES, dtype={'no_instrumento': str})
        df = pd.concat([old, df]).drop_duplicates(subset=['no_instrumento', 'campo'], keep='last')
    df.to_csv(DB_EDICOES, index=False)
