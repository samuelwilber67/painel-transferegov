from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = [
    "no_instrumento",
    "subsituacao_instrumento",
    "link_externo",
    "possui_obra",
    "valor_global",
    "valor_de_repasse",
    "valor_de_contrapartida",
    "valor_empenhado_acumulado",
    "valor_desembolsado_acumulado",
    "saldo_em_conta",
    "execucao_financeira",
    "objeto",
    "uf",
    "municipio",
    "ano_assinatura",
    "nome_proponente",
    "situacao_instrumento",
    "cnpj",
    "ultimo_pagamento",
    "sem_desembolso",
    "no_processo",
    "sem_pagamento_a_mais_de_150_dias",
    "situacao_inst_contratual",
]

MONEY_COLUMNS = [
    "valor_global",
    "valor_de_repasse",
    "valor_de_contrapartida",
    "valor_empenhado_acumulado",
    "valor_desembolsado_acumulado",
    "saldo_em_conta",
]

NUMERIC_COLUMNS = MONEY_COLUMNS + ["execucao_financeira", "ano_assinatura"]

# Faixas informadas por você
FAIXAS_ATE_90 = "Até 90 dias"
FAIXAS_90_180 = "Acima de 90 até 180 dias"
FAIXAS_180_365 = "Acima de 180 até 365 dias"
FAIXAS_ACIMA_365 = "Acima de 365 dias"
FAIXAS_SEM_DESEMBOLSO = "Sem Desembolso"

FAIXAS_PADRAO = [
    FAIXAS_ATE_90,
    FAIXAS_90_180,
    FAIXAS_180_365,
    FAIXAS_ACIMA_365,
]


def _normalize_str(s: pd.Series) -> pd.Series:
    # Mantém o texto (inclusive acentos), mas padroniza espaços e nulos
    s = s.astype("string")
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    s = s.replace({"": pd.NA, "-": pd.NA, "—": pd.NA})
    return s


def _to_number(s: pd.Series) -> pd.Series:
    # Converte: "2331839.15" -> 2331839.15 ; "-" -> NaN
    # Se vier com vírgula: "1.234,56" -> 1234.56 (tratamento)
    s = s.astype("string")
    s = s.str.strip()
    s = s.replace({"-": pd.NA, "—": pd.NA, "": pd.NA})

    # Remove separador de milhar e ajusta decimal PT-BR, se aparecer
    s = s.str.replace(".", "", regex=False)
    s = s.str.replace(",", ".", regex=False)

    return pd.to_numeric(s, errors="coerce")


def validate_columns(df: pd.DataFrame) -> list[str]:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return missing


def load_xlsx(uploaded_file) -> pd.DataFrame:
    df = pd.read_excel(uploaded_file, engine="openpyxl")
    return df


def clean_and_normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Garantir colunas mínimas (não cria se faltar; validação fica no app)
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = _normalize_str(df[col])

    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = _to_number(df[col])

    # Padronizações úteis
    if "uf" in df.columns:
        df["uf"] = _normalize_str(df["uf"]).str.upper()

    # Normaliza SIM/NÃO quando vier (sem forçar se tiver outros valores)
    for col in ["possui_obra", "sem_pagamento_a_mais_de_150_dias"]:
        if col in df.columns:
            df[col] = _normalize_str(df[col]).str.upper()
            df[col] = df[col].replace({"SIM": "SIM", "NAO": "NÃO", "NAO ": "NÃO"})

    return df


def add_queue_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria as colunas booleanas solicitadas, usando as FAIXAS (texto).
    - sem_desembolso: não tem "Sem Desembolso" (apenas as 4 faixas)
    - ultimo_pagamento: tem as 4 faixas + "Sem Desembolso"
    """
    df = df.copy()

    sd = df.get("sem_desembolso", pd.Series([pd.NA] * len(df), index=df.index, dtype="string"))
    up = df.get("ultimo_pagamento", pd.Series([pd.NA] * len(df), index=df.index, dtype="string"))
    sp150 = df.get("sem_pagamento_a_mais_de_150_dias", pd.Series([pd.NA] * len(df), index=df.index, dtype="string"))

    sd = _normalize_str(sd)
    up = _normalize_str(up)
    sp150 = _normalize_str(sp150).str.upper()

    # Filas equivalentes (por faixa)
    df["fila_sem_exec_90"] = sd.isin([FAIXAS_90_180, FAIXAS_180_365, FAIXAS_ACIMA_365])
    df["fila_sem_exec_180"] = sd.isin([FAIXAS_180_365, FAIXAS_ACIMA_365])
    df["fila_sem_exec_365"] = sd.eq(FAIXAS_ACIMA_365)

    df["fila_ult_pagto_90"] = up.isin([FAIXAS_90_180, FAIXAS_180_365, FAIXAS_ACIMA_365])
    df["fila_ult_pagto_180"] = up.isin([FAIXAS_180_365, FAIXAS_ACIMA_365])

    df["fila_sem_desembolso_ult_pagto"] = up.eq(FAIXAS_SEM_DESEMBOLSO)

    df["fila_sem_pagto_150"] = sp150.eq("SIM")

    return df


def compute_metrics(df: pd.DataFrame) -> dict:
    out = {}
    out["qtd_instrumentos"] = int(df["no_instrumento"].nunique()) if "no_instrumento" in df.columns else int(len(df))

    for col in MONEY_COLUMNS:
        if col in df.columns:
            out[f"soma_{col}"] = float(df[col].fillna(0).sum())
        else:
            out[f"soma_{col}"] = 0.0

    if "execucao_financeira" in df.columns:
        out["media_execucao_financeira"] = float(df["execucao_financeira"].dropna().mean()) if df["execucao_financeira"].notna().any() else 0.0
    else:
        out["media_execucao_financeira"] = 0.0

    return out


def filter_df(
    df: pd.DataFrame,
    uf: list[str],
    municipio: list[str],
    situacao: list[str],
    subsituacao: list[str],
    possui_obra: list[str],
    sem_pagto_150: list[str],
    sem_desembolso: list[str],
    ultimo_pagamento: list[str],
    situacao_inst_contratual: list[str],
    search_text: str | None,
    only_fila_sem_exec_90: bool,
    only_fila_sem_exec_180: bool,
    only_fila_sem_exec_365: bool,
    only_fila_ult_pagto_90: bool,
    only_fila_ult_pagto_180: bool,
    only_fila_sem_desembolso_ult_pagto: bool,
    only_fila_sem_pagto_150: bool,
) -> pd.DataFrame:
    x = df.copy()

    def apply_in(col: str, values: list[str]):
        nonlocal x
        if col in x.columns and values:
            x = x[x[col].isin(values)]

    apply_in("uf", uf)
    apply_in("municipio", municipio)
    apply_in("situacao_instrumento", situacao)
    apply_in("subsituacao_instrumento", subsituacao)
    apply_in("possui_obra", possui_obra)
    apply_in("sem_pagamento_a_mais_de_150_dias", sem_pagto_150)
    apply_in("sem_desembolso", sem_desembolso)
    apply_in("ultimo_pagamento", ultimo_pagamento)
    apply_in("situacao_inst_contratual", situacao_inst_contratual)

    if search_text:
        q = str(search_text).strip()
        if q:
            cols = [c for c in ["no_instrumento", "no_processo", "cnpj", "nome_proponente", "objeto"] if c in x.columns]
            if cols:
                mask = False
                for c in cols:
                    mask = mask | x[c].astype("string").str.contains(q, case=False, na=False)
                x = x[mask]

    # Filas (checkbox)
    def apply_flag(col: str, enabled: bool):
        nonlocal x
        if enabled and col in x.columns:
            x = x[x[col] == True]

    apply_flag("fila_sem_exec_90", only_fila_sem_exec_90)
    apply_flag("fila_sem_exec_180", only_fila_sem_exec_180)
    apply_flag("fila_sem_exec_365", only_fila_sem_exec_365)
    apply_flag("fila_ult_pagto_90", only_fila_ult_pagto_90)
    apply_flag("fila_ult_pagto_180", only_fila_ult_pagto_180)
    apply_flag("fila_sem_desembolso_ult_pagto", only_fila_sem_desembolso_ult_pagto)
    apply_flag("fila_sem_pagto_150", only_fila_sem_pagto_150)

    return x


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")
