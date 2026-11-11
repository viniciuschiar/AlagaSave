
import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

# Acessa o db 
url = os.getenv("SUPABASE_URL")
chave = os.getenv("SUPABASE_KEY")

# Valida autenticação
if not url or not chave:
    raise ValueError("Configure SUPABASE_URL e SUPABASE_KEY no .env")

endpoint = f"{url}/rest/v1/medicoes"

headers = {
    "apikey": chave,
    "Authorization": f"Bearer {chave}"
}

registros = []
pagina = 0
tamanho_pagina = 1000

# Percorre o db e extrai os registros
while True:
    params = {
        "select": "data_hora,dispositivo,nivel_agua_cm,chuva_percentual",
        "order": "data_hora.asc",
        "limit": tamanho_pagina,
        "offset": pagina * tamanho_pagina
    }

    resposta = requests.get(
        endpoint,
        headers=headers,
        params=params,
        timeout=30
    )
    resposta.raise_for_status()

    dados = resposta.json()
    registros.extend(dados)

    if len(dados) < tamanho_pagina:
        break

    pagina += 1

df = pd.DataFrame(registros)

if df.empty:
    raise ValueError("Nenhuma medição retornada pelo Supabase.")

df["data_hora"] = pd.to_datetime(
    df["data_hora"], utc=True, errors="coerce"
)

df = df.dropna(subset=["data_hora"])
df = df.sort_values(["dispositivo", "data_hora"])

df.to_csv("dados_historicos.csv", index=False)

# Mostra o dataframe coletado
print(f"Extração concluída: {len(df)} registros.")
print(df.head())
