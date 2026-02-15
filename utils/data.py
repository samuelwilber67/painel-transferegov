from __future__ import annotations

import unicodedata
import pandas as pd


# Colunas obrigatórias para o MVP funcionar
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
    "sem_pagamento_a_mais_de_150_dias",
    "situacao_inst_contratual",
]

# Colunas opcionais (se vierem, o app usa; se não vierem, não quebra)
OPTIONAL_COLUMNS = [
    "no_processo",  # NUP / Nº Processo
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


def _normalize_str(s: pd.Series) -> pd.Series:
    s = s.astype("string")
    s = s.str.replace(r"\s+", " ", regex=True).str.strip()
    s = s.replace({"": pd.NA, "-": pd.NA, "—": pd.NA})
    return s


def _to_number(s: pd.Series) -> pd.Series:
    """
    Converte texto numérico para número, lidando com:
      - "1.234,56" (PT-BR)
      - "1234,56"  (PT-BR sem milhar)
      - "1234.56"  (ponto decimal)
      - "1,234.56"  (milhar com vírgula e decimal com ponto)
      - "-" -> NaN

    Regra:
      - Se tiver vírgula, assume vírgula como decimal (PT-BR) quando também houver pontos.
        (ex.: "1.234,56" -> 1234.56)
      - Se não tiver vírgula, assume ponto como decimal (ex.: "1234.56" -> 1234.56)
      - Se tiver "1,234.56" (vírgula e ponto), trata vírgula como milhar e ponto como decimal.
    """
    s = s.astype("string")
    s = s.str.strip()
    s = s.replace({"-": pd.NA, "—": pd.NA, "": pd.NA})

    has_comma = s.str.contains(",", na=False)
    has_dot = s.str.contains(r"\.", na=False)

    # Caso 1: tem vírgula e ponto -> pode ser PT-BR (1.234,56) OU US (1,234.56)
    # Vamos decidir pela posição: se a vírgula vem depois do último ponto, é PT-BR; caso contrário, é US.
    both = has_comma & has_dot
    s_both = s.where(both, other=pd.NA)

    last_dot_pos = s_both.str.rfind(".")
    last_comma_pos = s_both.str.rfind(",")

    is_ptbr = last_comma_pos > last_dot_pos  # "1.234,56"
    s_ptbr_both = s_both.where(is_ptbr, other=pd.NA)
    s_us_both = s_both.where(~is_ptbr, other=pd.NA)

    # PT-BR: remove milhares "." e troca decimal "," por "."
    s_ptbr_both = s_ptbr_both.str.replace(".", "", regex=False)
    s_ptbr_both = s_ptbr_both.str.replace(",", ".", regex=False)

    # US: remove milhares "," e mantém "." como decimal
    s_us_both = s_us_both.str.replace(",", "", regex=False)

    # Caso 2: só vírgula (sem ponto) -> assume vírgula decimal ("1234,56")
    only_comma = has_comma & ~has_dot
    s_only_comma = s.where(only_comma, other=pd.NA)
    s_only_comma = s_only_comma.str.replace(",", ".", regex=False)

    # Caso 3: só ponto (sem vírgula) -> assume ponto decimal ("1234.56")
    only_dot = has_dot & ~has_comma
    s_only_dot = s.where(only_dot, other=pd.NA)
    # se vier com separador de milhar por vírgula aqui não entra; então só mantém.

    # Caso 4: nem vírgula nem ponto -> número inteiro como texto
    neither = ~has_comma & ~has_dot
    s_neither = s.where(neither, other=pd.NA)

    combined = s_ptbr_both.fillna(s_us_both).fillna(s_only_comma).fillna(s_only_dot).fillna(s_neither)
    return pd.to_numeric(combined, errors="coerce")


def _key(s: str) -> str:
    """
    Normaliza nomes de colunas para comparação:
    - remove acentos
    - deixa minúsculo
    - remove caracteres não alfanuméricos (vira espaço)
    - colapsa espaços
    """
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = "".join(ch if ch.isalnum() else " " for ch in s)
    s = " ".join(s.split())
    return s


def rename_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renomeia colunas do XLSX exportado (com espaços/acentos/maiúsculas) para snake_case interno.
    Usa matching por chave normalizada para tolerar variações do painel.
    """
    normalized_map = {
        # Identificação
        _key("Nº Instrumento"): "no_instrumento",
        _key("No Instrumento"): "no_instrumento",
        _key("Número Instrumento"): "no_instrumento",
        _key("Numero Instrumento"): "no_instrumento",

        _key("SubSituação Instrumento"): "subsituacao_instrumento",
        _key("Subsituação Instrumento"): "subsituacao_instrumento",
        _key("Sub Situacao Instrumento"): "subsituacao_instrumento",

        _key("Link Externo"): "link_externo",

        _key("Possui Obra"): "possui_obra",

        # Financeiro
        _key("Valor Global"): "valor_global",
        _key("Valor de Repasse"): "valor_de_repasse",
        _key("Valor de Contrapartida"): "valor_de_contrapartida",
        _key("Valor Empenhado Acumulado"): "valor_empenhado_acumulado",
        _key("Valor Desembolsado Acumulado"): "valor_desembolsado_acumulado",
        _key("Saldo em Conta"): "saldo_em_conta",
        _key("Execução Financeira"): "execucao_financeira",
        _key("Execucao Financeira"): "execucao_financeira",

        # Conteúdo e localização
        _key("Objeto"): "objeto",
        _key("UF"): "uf",
        _key("Município"): "municipio",
        _key("Municipio"): "municipio",
        _key("Ano Assinatura"): "ano_assinatura",

        # Proponente e status
        _key("Nome do Proponente"): "nome_proponente",
        _key("Nome Proponente"): "nome_proponente",
        _key("Situação Instrumento"): "situacao_instrumento",
        _key("Situacao Instrumento"): "situacao_instrumento",
        _key("CNPJ"): "cnpj",
        _key("CNPJ Proponente"): "cnpj",

        # Indicadores/faixas
        _key("Último Pagamento"): "ultimo_pagamento",
        _key("Ultimo Pagamento"): "ultimo_pagamento",
        _key("Sem Desembolso"): "sem_desembolso",
        _key("Sem Pagamento a Mais de 150 Dias"): "sem_pagamento_a_mais_de_150_dias",
        _key("Sem Pagamento mais de 150 dias"): "sem_pagamento_a_mais_de_150_dias",
        _key("Sem Pagamento +150 dias"): "sem_pagamento_a_mais_de_150_dias",

        _key("Situação Inst. Contratual"): "situacao_inst_contratual",
        _key("Situacao Inst Contratual"): "situacao_inst_contratual",
        _key("Situação Inst Contratual"): "situacao_inst_contratual",

        # Processo (NUP) - opcional
        _key("Nº Processo"): "no_processo",
        _key("Nº do Processo"): "no_processo",
        _key("No Processo"): "no_processo",
        _key("No do Processo"): "no_processo",
        _key("Número do Processo"): "no_processo",
        _key("Numero do Processo"): "no_processo",
        _key("NUP"): "no_processo",
        _key("NUP do Processo"): "no_processo",
        _key("Processo"): "no_processo",
    }

    rename_dict = {}
    for col in df.columns:
        k = _key(col)
        if k in normalized_map:
            rename_dict[col] = normalized_map[k]

    return df.rename(columns=rename_dict)


def validate_columns(df: pd.DataFrame) -> list[str]:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    return missing


def load_xlsx(uploaded_file) -> pd.DataFrame:
    return pd.read_excel(uploaded_file, engine="openpyxl")


def clean_and_normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Normaliza strings
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = _normalize_str(df[col])

    # Converte numéricos
    for col in NUMERIC_COLUMNS:
        if col in df.columns:
            df[col] = _to_number(df[col])

    # UF em caixa alta
    if "uf" in df.columns:
        df["uf"] = _normalize_str(df["uf"]).str.upper()

    # Normaliza SIM/NÃO (quando aplicável)
    for col in ["possui_obra", "sem_pagamento_a_mais_de_150_dias"]:
        if col in df.columns:
            df[col] = _normalize_str(df[col]).str.upper()
            df[col] = df[col].replace({"SIM": "SIM", "NAO": "NÃO", "NAO ": "NÃO"})

    return df


def add_queue_flags(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cria colunas booleanas para filas, usando as FAIXAS (texto).
    """
    df = df.copy()

    sd = df.get("sem_desembolso", pd.Series([pd.NA] * len(df), index=df.index, dtype="string"))
    up = df.get("ultimo_pagamento", pd.Series([pd.NA] * len(df), index=df.index, dtype="string"))
    sp150 = df.get("sem_pagamento_a_mais_de_150_dias", pd.Series([pd.NA] * len(df), index=df.index, dtype="string"))

    sd = _normalize_str(sd)
    up = _normalize_str(up)
    sp150 = _normalize_str(sp150).str.upper()

    # Sem execução financeira (por faixa de "Sem Desembolso")
    df["fila_sem_exec_90"] = sd.isin([FAIXAS_90_180, FAIXAS_180_365, FAIXAS_ACIMA_365])
    df["fila_sem_exec_180"] = sd.isin([FAIXAS_180_365, FAIXAS_ACIMA_365])
    df["fila_sem_exec_365"] = sd.eq(FAIXAS_ACIMA_365)

    # Último pagamento (por faixa)
    df["fila_ult_pagto_90"] = up.isin([FAIXAS_90_180, FAIXAS_180_365, FAIXAS_ACIMA_365])
    df["fila_ult_pagto_180"] = up.isin([FAIXAS_180_365, FAIXAS_ACIMA_365])

    # Último pagamento = Sem Desembolso (categoria específica do painel)
    df["fila_sem_desembolso_ult_pagto"] = up.eq(FAIXAS_SEM_DESEMBOLSO)

    # Indicador direto do painel
    df["fila_sem_pagto_150"] = sp150.eq("SIM")

    return df


def compute_metrics(df: pd.DataFrame) -> dict:
    out = {}
    out["qtd_instrumentos"] = int(df["no_instrumento"].nunique()) if "no_instrumento" in df.columns else int(len(df))

    for col in MONEY_COLUMNS:
        out[f"soma_{col}"] = float(df[col].fillna(0).sum()) if col in df.columns else 0.0

    if "execucao_financeira" in df.columns and df["execucao_financeira"].notna().any():
        out["media_execucao_financeira"] = float(df["execucao_financeira"].dropna().mean())
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
            candidates = ["no_instrumento", "cnpj", "nome_proponente", "objeto", "no_processo"]
            cols = [c for c in candidates if c in x.columns]
            if cols:
                mask = False
                for c in cols:
                    mask = mask | x[c].astype("string").str.contains(q, case=False, na=False)
                x = x[mask]

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
