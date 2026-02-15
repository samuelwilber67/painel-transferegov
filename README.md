# Base de instrumentos (Transferegov) - Streamlit

App Streamlit para analisar um XLSX exportado do Transferegov (painel com filtros/dimensões/métricas).

## O que o app faz
- Upload do XLSX
- Normaliza dados (troca "-" por nulo, converte colunas numéricas)
- Cria filas (booleans) com base nas faixas exportadas:
  - sem_desembolso: Até 90 / 90-180 / 180-365 / >365
  - ultimo_pagamento: as mesmas + "Sem Desembolso"
  - sem_pagamento_a_mais_de_150_dias: SIM/NÃO
- Permite filtros e busca
- Mostra tabela e detalhe do instrumento
- Exporta CSV do resultado filtrado

## Rodar localmente
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/Mac: source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
