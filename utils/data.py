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
        # Básicos
        _key("Nº Instrumento"): "no_instrumento",
        _key("Ano Assinatura"): "ano",
        _key("Objeto"): "objeto",
        _key("Nº do Processo"): "no_processo",
        _key("UF"): "uf",
        _key("Município"): "municipio",
        _key("Parlamentar"): "parlamentar",
        _key("Valor Global"): "valor_global_painel",
        
        # Celebração (PB)
        _key("Situação do Projeto Básico"): "situacao_pb",
        _key("Analista do Projeto Básico"): "analista_pb",
        _key("Status da Análise do Projeto Básico"): "status_analise_pb",
        
        # Execução
        _key("Fiscal de Acompanhamento"): "fiscal_exec",
        _key("Status da Execução"): "status_exec",
        _key("Status Ação Convenente"): "status_acao_conv",
        _key("Status da Obra"): "status_obra",
        
        # Prestação de Contas
        _key("Fiscal de Acompanhamento prestação de contas"): "fiscal_pc",
        _key("Status de Execução prestação de contas"): "status_exec_pc",
        _key("Status da obra prestação de contas"): "status_obra_pc",
        _key("Status prestação de contas"): "status_pc",

        # Atribuição (se vier na planilha)
        _key("Engenheiro Responsável"): "eng_resp",
        _key("Técnico Responsável"): "tec_resp",
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
            on_col = "no_instrumento" if "no_instrumento" in df.columns and "no_instrumento" in main_df.columns else None
            if on_col:
                main_df = pd.merge(main_df, df, on=on_col, how="outer", suffixes=('', '_drop'))
                main_df = main_df.loc[:, ~main_df.columns.str.contains('_drop')]

    # Merge Atribuições Locais
    if os.path.exists(DB_ATRIBUICAO):
        attr = pd.read_csv(DB_ATRIBUICAO, dtype={'no_instrumento': str})
        main_df = pd.merge(main_df, attr, on='no_instrumento', how='left', suffixes=('', '_attr'))

    # Garante colunas mínimas para não dar erro de filtro
    cols_check = ['no_instrumento', 'ano', 'objeto', 'no_processo', 'uf', 'municipio', 'parlamentar', 
                  'valor_global_painel', 'situacao_pb', 'analista_pb', 'status_analise_pb', 
                  'fiscal_exec', 'status_exec', 'status_acao_conv', 'status_obra',
                  'fiscal_pc', 'status_exec_pc', 'status_obra_pc', 'status_pc', 'eng_resp', 'tec_resp']
    for c in cols_check:
        if c not in main_df.columns: main_df[c] = pd.NA
        
    return main_df

def save_atribuicao(no_inst, eng, tec):
    new_data = pd.DataFrame([[str(no_inst), eng, tec]], columns=["no_instrumento", "eng_resp", "tec_resp"])
    if os.path.exists(DB_ATRIBUICAO):
        old = pd.read_csv(DB_ATRIBUICAO, dtype={'no_instrumento': str})
        old = old[old['no_instrumento'] != str(no_inst)]
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
