"""Audita o CSV do AlagaSave e cria exemplos com horizonte de 30 minutos."""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

TEMPO = "data_hora"
DISPOSITIVO = "dispositivo"
NIVEL = "nivel_agua_cm"
CHUVA = "chuva_percentual"
ALVO = "nivel_agua_30min_cm"
TEMPO_ALVO = "data_hora_alvo"
HORIZONTE = pd.Timedelta(minutes=30)
VARIAVEIS = [NIVEL, CHUVA, "variacao_nivel_5min_cm", "variacao_nivel_15min_cm"]
COLUNAS = [TEMPO, DISPOSITIVO, *VARIAVEIS, TEMPO_ALVO, ALVO]


def preparar(caminho, fuso):
    dados = pd.read_csv(caminho, sep=None, engine="python", encoding="utf-8-sig",
                        dtype=str)
    dados.columns = dados.columns.str.strip()
    exigidas = [TEMPO, DISPOSITIVO, NIVEL, CHUVA]
    faltantes = sorted(set(exigidas) - set(dados))

    if faltantes:
        raise ValueError(f"Colunas ausentes: {faltantes}. Encontradas: {list(dados)}")
    auditoria = {"linhas_brutas": len(dados), "colunas": list(dados)}
    dados = dados[exigidas].copy()
    datas = dados[TEMPO].str.strip()
    # Datas sem offset usam o fuso informado. Datas com offset preservam o instante.
    explicitas = datas.str.contains(r"(?:Z|[+-]\d{2}(?::?\d{2})?)$", case=False,
                                   na=False) & datas.str.contains(r"\d:\d", na=False)
    datas_utc = pd.to_datetime(datas.where(explicitas), utc=True, errors="coerce",
                              format="mixed")
    locais = pd.to_datetime(datas.where(~explicitas), errors="coerce", format="mixed")
    locais = locais.dt.tz_localize(fuso, ambiguous="NaT", nonexistent="NaT")
    dados[TEMPO] = datas_utc.fillna(locais.dt.tz_convert("UTC"))
    dados[DISPOSITIVO] = dados[DISPOSITIVO].str.strip().replace("", pd.NA)

    for coluna in (NIVEL, CHUVA):
        valores = dados[coluna].str.strip().str.replace(",", ".", regex=False)
        dados[coluna] = pd.to_numeric(valores, errors="coerce")
        dados[coluna] = dados[coluna].replace([np.inf, -np.inf], np.nan)

    auditoria["ausentes_ou_invalidos"] = dados.isna().sum().to_dict()
    auditoria["datas_sem_offset"] = int((datas.notna() & ~explicitas).sum())
    nivel_negativo = dados[NIVEL].lt(0)
    chuva_fora = dados[CHUVA].notna() & ~dados[CHUVA].between(0, 100)
    auditoria["nivel_negativo"] = int(nivel_negativo.sum())
    auditoria["chuva_fora_0_a_100"] = int(chuva_fora.sum())
    dados = dados.dropna(subset=exigidas)
    dados = dados.loc[~(nivel_negativo | chuva_fora).reindex(dados.index)]
    chaves = [DISPOSITIVO, TEMPO]
    unicas = dados.drop_duplicates()
    auditoria["duplicatas_identicas_validas"] = len(dados) - len(unicas)
    conflitos = unicas.duplicated(chaves, keep=False)
    auditoria["linhas_com_horario_conflitante"] = int(conflitos.sum())
    dados = unicas.loc[~conflitos].sort_values(chaves)
    auditoria["linhas_validas"] = len(dados)
    auditoria["dispositivos"] = {}
    exemplos = []

    for dispositivo, grupo in dados.groupby(DISPOSITIVO):
        leituras = grupo.set_index(TEMPO)[[NIVEL, CHUVA]]
        tempos = leituras.index
        intervalos = tempos.to_series().diff().dt.total_seconds().dropna()
        # Cada janela contém somente leituras em (t - 5 min, t].

        janelas = leituras.groupby(tempos.ceil("5min")).median()
        janelas.index.name = TEMPO
        horarios = janelas.index
        linha = janelas.copy()

        for minutos in (5, 15):
            anterior = janelas[NIVEL].reindex(horarios - pd.Timedelta(minutes=minutos))
            linha[f"variacao_nivel_{minutos}min_cm"] = linha[NIVEL] - anterior.to_numpy()

        linha[TEMPO_ALVO] = horarios + HORIZONTE
        linha[ALVO] = janelas[NIVEL].reindex(linha[TEMPO_ALVO]).to_numpy()
        linha[DISPOSITIVO] = dispositivo
        pares_horizonte = int(linha[ALVO].notna().sum())
        linha = linha.dropna().reset_index()[COLUNAS]
        exemplos.append(linha)
        auditoria["dispositivos"][str(dispositivo)] = {
            "linhas_validas": len(leituras),
            "inicio_utc": tempos.min().isoformat(),
            "fim_utc": tempos.max().isoformat(),
            "duracao_horas": (tempos.max() - tempos.min()).total_seconds() / 3600,
            "intervalo_mediano_segundos": float(intervalos.median()) if len(intervalos) else None,
            "maior_intervalo_segundos": float(intervalos.max()) if len(intervalos) else None,
            "janelas_observadas": len(janelas),
            "janelas_vazias": int((horarios.max() - horarios.min()) / pd.Timedelta(minutes=5))
            + 1 - len(janelas),
            "nivel_min_cm": float(leituras[NIVEL].min()),
            "nivel_max_cm": float(leituras[NIVEL].max()),
            "chuva_min_percentual": float(leituras[CHUVA].min()),
            "chuva_max_percentual": float(leituras[CHUVA].max()),
            "pares_30min": pares_horizonte,
            "exemplos_com_historico_e_alvo": len(linha),
        }

    base = pd.concat(exemplos, ignore_index=True) if exemplos else pd.DataFrame(columns=COLUNAS)
    base = base.sort_values([TEMPO, DISPOSITIVO])
    auditoria["exemplos_finais"] = len(base)
    auditoria["fuso_para_datas_sem_offset"] = fuso

    return base, auditoria


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--fuso", default="UTC", help="Fuso das datas sem offset.")
    parser.add_argument("--saida", type=Path, default=Path("dados_tratados.csv"))
    parser.add_argument("--auditoria", type=Path, default=Path("auditoria.json"))
    args = parser.parse_args()
    destinos = {args.csv.resolve(), args.saida.resolve(), args.auditoria.resolve()}

    if len(destinos) != 3:
        parser.error("Use caminhos diferentes para entrada, saída e auditoria.")
    try:
        base, auditoria = preparar(args.csv, args.fuso)
    except (ValueError, OSError, KeyError) as erro:
        parser.exit(1, f"Falha no tratamento: {erro}\n")
        
    base.to_csv(args.saida, index=False)
    relatorio = json.dumps(auditoria, ensure_ascii=False, indent=2, allow_nan=False)
    args.auditoria.write_text(relatorio + "\n", encoding="utf-8")
    print(relatorio)


if __name__ == "__main__":
    main()
