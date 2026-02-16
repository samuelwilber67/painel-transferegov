from __future__ import annotations

import os
import unicodedata
from datetime import datetime

import pandas as pd

# "Banco" local simples (CSV) para testes
DB_ATRIBUICAO = "db_atribuicao.csv"
DB_EDICOES = "db_edicoes.csv"
DB_HISTORICO = "db_historico.csv"


def _key(s: str) -> str:
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower().strip()
    s = " ".join(s.split())
    return s


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renomeia colunas do Excel para nomes internos.
    Adicione aqui variações reais dos seus cabeçalhos quando aparecerem.
    """
    mapping = {
        # IDs
        _key("Nº do Instrumento"): "no_instrumento",
        _key("Nº Instrumento"): "no_instrumento",
        _key("No Instrumento"): "no_instrumento",
        _key("Número do Instrumento"): "no_instrumento",
        _key("Numero do Instrumento"): "no_instrumento",

        _key("Nº da Proposta"): "no_proposta",
        _key("Nº Proposta"): "no_proposta",
        _key("No Proposta"): "no_proposta",
        _key("Número da Proposta"): "no_proposta",
        _key("Numero da Proposta"): "no_proposta",

        # Básicos
        _key("Ano"): "ano",
        _key("Ano Assinatura"): "ano",
        _key("Objeto"): "objeto",
        _key("UF"): "uf",
        _key("Município"): "municipio",
        _key("Municipio"): "municipio",
        _key("Parlamentar"): "parlamentar",
        _key("Valor Global"): "valor_global_painel",
        _key("Valor Global do Instrumento"): "valor_global_painel",

        # Processo (NUP)
        _key("Nº do Processo"): "no_processo",
        _key("Nº Processo"): "no_processo",
        _key("NUP"): "no_processo",
        _key("Processo"): "no_processo",

        # Status (Painel)
        _key("Situação do Instrumento"): "status_painel",
        _key("Situação Instrumento"): "status_painel",
        _key("Situacao Instrumento"): "status_painel",
        _key("Situação Inst. Contratual"): "situacao_contratual",
        _key("Situacao Inst. Contratual"): "situacao_contratual",
        _key("Situação Inst Contratual"): "situacao_contratual",
        _key("Situacao Inst Contratual"): "situacao_contratual",

        # Campos "coordenações" (se vierem do painel)
        _key("Situação do Projeto Básico"): "situacao_pb",
        _key("Analista do Projeto Básico"): "analista_pb",
        _key("Status da Análise do Projeto Básico"): "status_analise_pb",

        _key("Fiscal de Acompanhamento"): "fiscal_exec",
        _key("Status da Execução"): "status_exec",
        _key("Status Ação Convenente"): "status_acao_convenente",
        _key("Status da Obra"): "status_obra",

        _key("Fiscal de Acompanhamento prestação de contas"): "fiscal_pc",
        _key("Status de Execução prestação de contas"): "status_exec_pc",
        _key("Status da obra prestação de contas"): "status_obra_pc",
        _key("Status prestação de contas"): "status_pc",

        # Caso venha atribuído do painel (ou de uma planilha própria)
        _key("Engenheiro Responsável"): "eng_resp",
        _key("Eng. Responsável"): "eng_resp",
        _key("Técnico Responsável"): "tec_resp",
        _key("Tec. Responsável"): "tec_resp",
    }

    rename_dict = {}
    for col in df.columns:
        k = _key(col)
        if k in mapping:
            rename_dict[col] = mapping[k]
    return df.rename(columns=rename_dict)


def _ensure_columns(main_df: pd.DataFrame) -> pd.DataFrame:
    """
    Garante colunas mínimas para o app não quebrar.
    """
    cols = [
        "no_instrumento",
        "no_proposta",
        "ano",
        "objeto",
        "no_processo",
        "uf",
        "municipio",
        "parlamentar",
        "valor_global_painel",
        "status_painel",
        "situacao_contratual",
        "eng_resp",
        "tec_resp",
        # coordenações (se não vierem, ficam vazias e poderão ser preenchidas manualmente no futuro)
        "situacao_pb",
        "analista_pb",
        "status_analise_pb",
        "fiscal_exec",
        "status_exec",
        "status_acao_convenente",
        "status_obra",
        "fiscal_pc",
        "status_exec_pc",
        "status_obra_pc",
        "status_pc",
    ]
    for c in cols:
        if c not in main_df.columns:
            main_df[c] = pd.NA
    return main_df


def load_and_merge_all(files_dict: dict) -> pd.DataFrame:
    """
    Lê múltiplos XLSX e faz merge por no_instrumento quando possível.
    Se não houver instrumento, tenta por no_proposta.
    """
    main_df = pd.DataFrame()

    for _, content in files_dict.items():
        df = pd.read_excel(content, engine="openpyxl")
        df = rename_columns(df)

        # normaliza IDs como string (evita 909561 virar 909561.0)
        for id_col in ["no_instrumento", "no_proposta"]:
            if id_col in df.columns:
                df[id_col] = df[id_col].astype("string").str.strip()

        if main_df.empty:
            main_df = df
            continue

        # define chave de merge
        if "no_instrumento" in df.columns and "no_instrumento" in main_df.columns:
            on_col = "no_instrumento"
        elif "no_proposta" in df.columns and "no_proposta" in main_df.columns:
            on_col = "no_proposta"
        else:
            # sem chave compatível: concat como fallback
            main_df = pd.concat([main_df, df], ignore_index=True)
            continue

        main_df = pd.merge(main_df, df, on=on_col, how="outer", suffixes=("", "_drop"))
        main_df = main_df.loc[:, ~main_df.columns.str.endswith("_drop")]

    main_df = _ensure_columns(main_df)

    # aplica atribuições gravadas localmente
    if os.path.exists(DB_ATRIBUICAO):
        attr = pd.read_csv(DB_ATRIBUICAO, dtype={"id": "string"})
        # attr tem: id, eng_resp, tec_resp
        main_df = main_df.copy()
        main_df["id_merge"] = main_df["no_instrumento"].fillna(main_df["no_proposta"]).astype("string")
        main_df = main_df.merge(attr, left_on="id_merge", right_on="id", how="left", suffixes=("", "_attr"))
        # se tiver atribuição no CSV, sobrescreve
        main_df["eng_resp"] = main_df["eng_resp_attr"].combine_first(main_df["eng_resp"])
        main_df["tec_resp"] = main_df["tec_resp_attr"].combine_first(main_df["tec_resp"])
        main_df = main_df.drop(columns=[c for c in ["id_merge", "id", "eng_resp_attr", "tec_resp_attr"] if c in main_df.columns])

    return main_df


def save_atribuicao(id_val: str, eng: str, tec: str) -> None:
    """
    Salva atribuição por ID (instrumento ou proposta).
    """
    id_val = str(id_val).strip()
    df = pd.DataFrame([[id_val, eng, tec]], columns=["id", "eng_resp", "tec_resp"])

    if os.path.exists(DB_ATRIBUICAO):
        old = pd.read_csv(DB_ATRIBUICAO, dtype={"id": "string"})
        old = old[old["id"] != id_val]
        df = pd.concat([old, df], ignore_index=True)

    df.to_csv(DB_ATRIBUICAO, index=False)


def get_edicoes(id_val: str) -> dict:
    """
    Retorna o último valor por campo para um ID.
    """
    id_val = str(id_val).strip()
    if not os.path.exists(DB_EDICOES):
        return {}

    df = pd.read_csv(DB_EDICOES, dtype={"id": "string", "campo": "string"})
    subset = df[df["id"] == id_val]
    if subset.empty:
        return {}
    # garante último por campo
    subset = subset.sort_values("data_hora")
    last = subset.drop_duplicates(subset=["campo"], keep="last")
    return dict(zip(last["campo"], last["valor"]))


def save_edicao_com_historico(id_val: str, campo: str, valor_novo, usuario: str) -> None:
    """
    Salva a edição e registra histórico (audit trail).
    """
    id_val = str(id_val).strip()
    campo = str(campo).strip()
    usuario = str(usuario).strip()
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # DB_EDICOES (estado atual por campo)
    row_ed = pd.DataFrame([[id_val, campo, str(valor_novo), data_hora]], columns=["id", "campo", "valor", "data_hora"])
    if os.path.exists(DB_EDICOES):
        old = pd.read_csv(DB_EDICOES, dtype={"id": "string", "campo": "string"})
        old = old[~((old["id"] == id_val) & (old["campo"] == campo))]
        row_ed = pd.concat([old, row_ed], ignore_index=True)
    row_ed.to_csv(DB_EDICOES, index=False)

    # DB_HISTORICO (linha a linha)
    row_hist = pd.DataFrame([[id_val, campo, str(valor_novo), usuario, data_hora]],
                            columns=["id", "campo", "valor", "usuario", "data_hora"])
    if os.path.exists(DB_HISTORICO):
        hist = pd.read_csv(DB_HISTORICO, dtype={"id": "string"})
        row_hist = pd.concat([hist, row_hist], ignore_index=True)
    row_hist.to_csv(DB_HISTORICO, index=False)


def get_historico(id_val: str) -> pd.DataFrame:
    id_val = str(id_val).strip()
    if not os.path.exists(DB_HISTORICO):
        return pd.DataFrame(columns=["id", "campo", "valor", "usuario", "data_hora"])
    df = pd.read_csv(DB_HISTORICO, dtype={"id": "string"})
    df = df[df["id"] == id_val].copy()
    if "data_hora" in df.columns:
        df = df.sort_values("data_hora", ascending=False)
    return df
