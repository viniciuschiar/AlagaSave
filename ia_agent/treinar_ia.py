"""Valida e treina uma regressão linear múltipla para o AlagaSave."""
'''

Para rodar a aplicação execute:
"python .\ia_agent\treinar_ia.py .\ia_agent\.csv\dados_tratados.csv"
no terminal Python.

''' 
import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import TimeSeriesSplit

from tratar_dados import ALVO, COLUNAS, DISPOSITIVO, HORIZONTE, NIVEL, TEMPO, TEMPO_ALVO, VARIAVEIS

def metricas(real, previsto):
    return {
        "mae_cm": float(mean_absolute_error(real, previsto)),
        "rmse_cm": float(np.sqrt(mean_squared_error(real, previsto))),
        "r2": float(r2_score(real, previsto)) if real.nunique() > 1 else None,
    }


def avaliar(treino, teste):
    modelo = LinearRegression().fit(treino[VARIAVEIS], treino[ALVO])

    return modelo, {
        "linhas_treino": len(treino),
        "linhas_validacao": len(teste),
        "ultimo_alvo_treino_utc": treino[TEMPO_ALVO].max().isoformat(),
        "inicio_validacao_utc": teste[TEMPO].min().isoformat(),
        "fim_validacao_utc": teste[TEMPO].max().isoformat(),
        "regressao": metricas(teste[ALVO], modelo.predict(teste[VARIAVEIS])),
        "persistencia": metricas(teste[ALVO], teste[NIVEL]),
    }


def treinar(caminho):
    base = pd.read_csv(caminho, dtype={DISPOSITIVO: str})

    if not set(COLUNAS).issubset(base):
        raise ValueError("O arquivo deve ser gerado por tratar_dados.py.")
    
    for coluna in (TEMPO, TEMPO_ALVO):
        base[coluna] = pd.to_datetime(base[coluna], utc=True, errors="raise", format="mixed")
    if (base[COLUNAS].isna().any().any()
            or not np.isfinite(base[[*VARIAVEIS, ALVO]].to_numpy(dtype=float)).all()
            or not (base[TEMPO_ALVO] - base[TEMPO]).eq(HORIZONTE).all()
            or base.duplicated([TEMPO, DISPOSITIVO]).any()):
        
        raise ValueError("Base tratada inválida. Gere-a novamente com tratar_dados.py.")
    
    base = base.sort_values(TEMPO)
    horarios = pd.DatetimeIndex(base[TEMPO].unique())

    if len(horarios) < 6:
        raise ValueError(f"Apenas {len(horarios)} horários elegíveis para treino e validação.")
    corte = horarios[int(len(horarios) * 0.8)]
    desenvolvimento = base.loc[base[TEMPO_ALVO] < corte]
    teste = base.loc[base[TEMPO] >= corte]
    horas_desenv = pd.DatetimeIndex(desenvolvimento[TEMPO].unique())
    minimo_treino = len(VARIAVEIS) + 2

    if len(horas_desenv) < minimo_treino or teste[TEMPO].nunique() < 2:
        raise ValueError("Histórico insuficiente após reservar o teste e excluir "
                         "os alvos que alcançam o período de teste.")

    # Todos os dispositivos compartilham os cortes. As janelas crescem no tempo.
    validacoes = []

    for _, indices in TimeSeriesSplit(n_splits=3).split(horas_desenv):
        horas_validacao = horas_desenv[indices]
        treino = desenvolvimento.loc[desenvolvimento[TEMPO_ALVO] < horas_validacao[0]]
        validacao = desenvolvimento.loc[desenvolvimento[TEMPO].isin(horas_validacao)]
        if treino[TEMPO].nunique() < minimo_treino or validacao[TEMPO].nunique() < 2:
            continue
        _, resultado = avaliar(treino, validacao)
        validacoes.append(resultado)

    if not validacoes:
        raise ValueError("Histórico insuficiente para uma dobra temporal com "
                         "treino e validação após excluir os alvos sobrepostos.")
    
    if desenvolvimento[ALVO].nunique() < 2:
        raise ValueError("O nível futuro é constante no conjunto de treino.")
    modelo, resultado_teste = avaliar(desenvolvimento, teste)
    relatorio = {
        "horizonte_minutos": 30,
        "validacao_temporal": validacoes,
        "dobras_previstas": 3,
        "teste_final": resultado_teste,
        "linhas_excluidas_no_corte_final": len(base) - len(desenvolvimento) - len(teste),
        "posto_da_matriz": int(modelo.rank_),
        "coeficientes": dict(zip(VARIAVEIS, modelo.coef_.tolist())),
        "intercepto_cm": float(modelo.intercept_),
    }
    return modelo, relatorio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv", type=Path)
    parser.add_argument("--modelo", type=Path, default=Path("modelo_alagasave.joblib"))
    parser.add_argument("--metricas", type=Path, default=Path("metricas.json"))
    args = parser.parse_args()

    if len({args.csv.resolve(), args.modelo.resolve(), args.metricas.resolve()}) != 3:
        parser.error("Use caminhos diferentes para entrada, modelo e métricas.")
    try:
        modelo, relatorio = treinar(args.csv)

    except (ValueError, OSError, TypeError) as erro:
        parser.exit(1, f"Treino interrompido: {erro}\n")

    joblib.dump({"modelo": modelo, "variaveis": VARIAVEIS, "horizonte_minutos": 30},
                args.modelo)
    
    resultado = json.dumps(relatorio, ensure_ascii=False, indent=2, allow_nan=False)
    args.metricas.write_text(resultado + "\n", encoding="utf-8")
    print(resultado)

if __name__ == "__main__":
    main()
