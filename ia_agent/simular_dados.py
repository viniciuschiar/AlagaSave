"""Gera medições simuladas contínuas (em janelas de 5 min) para treinar a IA do AlagaSave.

Insere os registros diretamente na tabela `medicoes` do Supabase e também
atualiza o arquivo local `dados_historicos.csv`.

Para rodar no terminal:
    python3 ia_agent/simular_dados.py
"""

import argparse
import csv
import json
import math
import os
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ALTURA_REFERENCIA_CM = 100.0
DISPOSITIVO_PADRAO = "ESP32-AlagaSave"


def carregar_env(caminho_env: Path) -> dict[str, str]:
    """Lê variáveis de um arquivo .env sem depender de bibliotecas externas."""
    env = {}
    if caminho_env.exists():
        for linha in caminho_env.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if not linha or linha.startswith("#") or "=" not in linha:
                continue
            chave, valor = linha.split("=", 1)
            env[chave.strip()] = valor.strip().strip('"').strip("'")
    return env


def classificar_nivel(nivel_pct: float) -> str:
    if nivel_pct >= 90.0:
        return "CRITICO"
    if nivel_pct >= 70.0:
        return "ALERTA"
    if nivel_pct >= 30.0:
        return "ATENCAO"
    return "NORMAL"


def classificar_chuva(chuva_pct: float) -> str:
    if chuva_pct >= 60.0:
        return "CHUVA_FORTE"
    if chuva_pct >= 20.0:
        return "CHUVA_MODERADA"
    return "SEM_CHUVA"


def gerar_serie_simulada(
    inicio_utc: datetime,
    quantidade_janelas: int = 300,
    dispositivo: str = DISPOSITIVO_PADRAO,
) -> list[dict]:
    """Gera uma série contínua de medições a cada 5 minutos (padrão: 300 janelas = 25h).

    Simula múltiplos episódios de chuva (seca -> moderada -> forte -> estiagem)
    onde o nível da água responde gradualmente à intensidade da chuva acumulada
    e escoa quando a chuva diminui, permitindo que a regressão linear aprenda a
    prever o nível 30 minutos à frente.
    """
    registros = []
    nivel_atual = 18.0

    for passo in range(quantidade_janelas):
        instante = inicio_utc + timedelta(minutes=5 * passo)

        # Combina ondas de diferentes períodos para simular frentes de chuva variadas
        onda_principal = math.sin(2.0 * math.pi * passo / 72.0 - 0.8)
        onda_secundaria = 0.6 * math.sin(2.0 * math.pi * passo / 36.0 + 0.4)
        onda_curta = 0.25 * math.cos(2.0 * math.pi * passo / 18.0)

        chuva_bruta = 42.0 + 32.0 * onda_principal + 18.0 * onda_secundaria + 8.0 * onda_curta
        chuva_pct = round(max(0.0, min(100.0, chuva_bruta)), 2)

        # Dinâmica física simplificada: chuva > 25% faz o nível subir; drenagem natural faz descer
        equilibrio_alvo = 8.0 + 0.85 * chuva_pct
        taxa_resposta = 0.16 if equilibrio_alvo > nivel_atual else 0.10
        variacao = taxa_resposta * (equilibrio_alvo - nivel_atual) + 0.035 * (chuva_pct - 35.0)
        nivel_atual = max(0.0, min(ALTURA_REFERENCIA_CM, nivel_atual + variacao))

        nivel_cm = round(nivel_atual, 2)
        distancia_cm = round(ALTURA_REFERENCIA_CM - nivel_cm, 2)
        nivel_pct = round((nivel_cm / ALTURA_REFERENCIA_CM) * 100.0, 2)
        chuva_adc = int(round((chuva_pct / 100.0) * 4095))

        registros.append(
            {
                "data_hora": instante.isoformat(),
                "dispositivo": dispositivo,
                "distancia_cm": distancia_cm,
                "nivel_agua_cm": nivel_cm,
                "nivel_agua_percentual": nivel_pct,
                "chuva_adc": chuva_adc,
                "chuva_percentual": chuva_pct,
                "situacao_chuva": classificar_chuva(chuva_pct),
                "status_nivel": classificar_nivel(nivel_pct),
            }
        )

    return registros


def enviar_para_supabase(url: str, chave: str, registros: list[dict], tamanho_lote: int = 100) -> int:
    """Envia os registros simulados em lotes para a tabela `medicoes` do Supabase."""
    endpoint = f"{url.rstrip('/')}/rest/v1/medicoes"
    headers = {
        "Content-Type": "application/json",
        "apikey": chave,
        "Authorization": f"Bearer {chave}",
        "Prefer": "return=minimal",
    }

    total_enviado = 0
    for i in range(0, len(registros), tamanho_lote):
        lote = registros[i : i + tamanho_lote]
        corpo = json.dumps(lote).encode("utf-8")
        req = urllib.request.Request(endpoint, data=corpo, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status not in (200, 201, 204):
                raise RuntimeError(f"Status inesperado do Supabase: {resp.status}")
        total_enviado += len(lote)

    return total_enviado


def atualizar_csv_local(caminho_csv: Path, novos_registros: list[dict]) -> int:
    """Mescla os registros simulados com os registros já existentes em dados_historicos.csv."""
    linhas_existentes = []
    if caminho_csv.exists():
        with caminho_csv.open("r", encoding="utf-8-sig", newline="") as f:
            leitor = csv.DictReader(f)
            for linha in leitor:
                chuva = linha.get("milimetragem_chuva") or linha.get("chuva_percentual")
                if linha.get("data_hora") and linha.get("dispositivo") and chuva is not None:
                    linhas_existentes.append(
                        {
                            "data_hora": linha["data_hora"].strip(),
                            "dispositivo": linha["dispositivo"].strip(),
                            "nivel_agua_cm": linha["nivel_agua_cm"].strip(),
                            "milimetragem_chuva": str(chuva).strip(),
                        }
                    )

    mapa = {}
    for item in linhas_existentes:
        mapa[(item["dispositivo"], item["data_hora"])] = item

    for reg in novos_registros:
        data_formatada = reg["data_hora"].replace("T", " ")
        chave = (reg["dispositivo"], data_formatada)
        mapa[chave] = {
            "data_hora": data_formatada,
            "dispositivo": reg["dispositivo"],
            "nivel_agua_cm": reg["nivel_agua_cm"],
            "milimetragem_chuva": reg["chuva_percentual"],
        }

    todas = sorted(mapa.values(), key=lambda x: (x["dispositivo"], x["data_hora"]))

    with caminho_csv.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(
            f,
            fieldnames=["data_hora", "dispositivo", "nivel_agua_cm", "milimetragem_chuva"],
        )
        escritor.writeheader()
        escritor.writerows(todas)

    return len(todas)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--janelas",
        type=int,
        default=300,
        help="Quantidade de medições de 5 em 5 minutos (padrão: 300 = 25 horas).",
    )
    parser.add_argument(
        "--inicio",
        default="2026-11-08T00:00:00+00:00",
        help="Data/hora inicial em UTC (ISO 8601).",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=Path("dados_historicos.csv"),
        help="Caminho do CSV histórico local.",
    )
    parser.add_argument(
        "--apenas-local",
        action="store_true",
        help="Apenas atualiza o CSV local sem enviar para o Supabase.",
    )
    args = parser.parse_args()

    inicio_utc = datetime.fromisoformat(args.inicio).astimezone(timezone.utc)
    registros = gerar_serie_simulada(inicio_utc, args.janelas)

    raiz = Path(__file__).resolve().parent
    env = carregar_env(raiz / ".env")
    url = os.getenv("SUPABASE_URL") or env.get("SUPABASE_URL")
    chave = os.getenv("SUPABASE_KEY") or env.get("SUPABASE_KEY")

    if not args.apenas_local:
        if not url or not chave:
            print("Aviso: SUPABASE_URL/SUPABASE_KEY não encontrados. Salvando apenas no CSV local.")
        else:
            try:
                enviados = enviar_para_supabase(url, chave, registros)
                print(f"Supabase: {enviados} medições simuladas inseridas com sucesso na tabela 'medicoes'.")
            except urllib.error.HTTPError as erro:
                detalhe = erro.read().decode("utf-8", errors="replace")
                print(f"Erro HTTP ao inserir no Supabase ({erro.code}): {detalhe}")
            except Exception as erro:
                print(f"Não foi possível conectar ao Supabase ({erro}). Salvando no CSV local...")

    total_csv = atualizar_csv_local(args.csv, registros)
    print(f"CSV local atualizado ({args.csv}): {total_csv} registros no total.")


if __name__ == "__main__":
    main()
