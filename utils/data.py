import pandas as pd
import os
import unicodedata
from datetime import datetime

# Bancos de dados locais para salvar o que for manual
DB_ATRIBUICAO = "db_atribuicao.csv"
DB_EDICOES = "db_edicoes.csv"
DB_HISTORICO = "db_historico.csv"

def normalize_col(col):
    """Normaliza nomes de colunas: remove acentos, espaços e põe em minúsculo."""
    nfkd_form = unicodedata.normalize('NFKD', str(col))
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower().strip().replace(" ", "_")

def load_and_merge_all(files_dict):
    """Lê as planilhas e garante que as colunas críticas existam."""
    main_df = pd.DataFrame()
    
    # Mapeamento de possíveis nomes reais para nomes internos
    mapping = {
        'n_instrumento': 'no_instrumento', 'numero_do_instrumento': 'no_instrumento', 'no_instrumento': 'no_instrumento',
        'n_proposta': 'no_proposta', 'numero_da_proposta': 'no_proposta', 'no_proposta': 'no_proposta',
        'uf': 'uf', 'municipio': 'municipio', 'objeto': 'objeto', 'valor_global': 'valor_global',
        'situacao_contratual': 'situacao_contratual', 'status_painel': 'status_painel'
    }

    for name, content in files_dict.items():
        try:
            temp_df = pd.read_excel(content, engine="openpyxl")
            # Normaliza cabeçalhos do Excel
            temp_df.columns = [normalize_col(c) for c in temp_df.columns]
            # Renomeia para o padrão do sistema baseado no mapping
            temp_df = temp_df.rename(columns=mapping)
            
            if main_df.empty:
                main_df = temp_df
            else:
                # Merge inteligente: tenta por instrumento, se não, por proposta
                join_col = 'no_instrumento' if 'no_instrumento' in temp_df.columns and 'no_instrumento' in main_df.columns else 'no_proposta'
                if join_col in temp_df.columns and join_col in main_df.columns:
                    main_df = pd.merge(main_df, temp_df, on=join_col, how='outer', suffixes=('', '_dup'))
                else:
                    main_df = pd.concat([main_df, temp_df], ignore_index=True)
        except Exception as e:
            continue

    # Remove colunas duplicadas do merge
    main_df = main_df.loc[:, ~main_df.columns.str.endswith('_dup')]
    
    # GARANTIA: Se colunas críticas não existem, cria como vazio para não quebrar o site
    for col in ['no_instrumento', 'no_proposta', 'uf', 'municipio', 'objeto', 'eng_resp', 'tec_resp', 'vistoria_resp']:
        if col not in main_df.columns:
            main_df[col] = pd.NA

    # Merge de Atribuições salvas anteriormente
    if os.path.exists(DB_ATRIBUICAO):
        attr = pd.read_csv(DB_ATRIBUICAO, dtype=str)
        main_df = pd.merge(main_df, attr, on='no_instrumento', how='left', suffixes=('', '_new'))
        if 'eng_resp_new' in main_df.columns:
            main_df['eng_resp'] = main_df['eng_resp_new'].combine_first(main_df['eng_resp'])
            main_df['tec_resp'] = main_df['tec_resp_new'].combine_first(main_df['tec_resp'])
            main_df['vistoria_resp'] = main_df['vistoria_resp_new'].combine_first(main_df['vistoria_resp'])
            main_df = main_df.drop(columns=['eng_resp_new', 'tec_resp_new', 'vistoria_resp_new'])

    return main_df

def save_edicao_com_historico(id_val, campo, valor_novo, usuario):
    # Lógica de salvar CSV... (mesma das versões anteriores)
    pass

def get_edicoes(id_val):
    # Lógica de carregar edições...
    pass

def get_historico(id_val):
    # Lógica de carregar histórico...
    pass
