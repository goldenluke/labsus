import pandas as pd
import numpy as np
from scipy.interpolate import CubicSpline

ARQUIVO_ENTRADA = "populacao_estimada_completa_spline.csv"
ARQUIVO_SAIDA = "populacao_com_2026.csv"

df = pd.read_csv(
    ARQUIVO_ENTRADA,
    sep=";",
    encoding="utf-8"
)

novas_linhas = []

for cod_mun, grupo in df.groupby("cod_mun_ibge_7"):

    grupo = grupo.sort_values("ano")

    anos = grupo["ano"].values
    pops = grupo["populacao"].values

    # Necessário pelo menos 4 pontos para spline cúbica
    if len(anos) < 4:
        continue

    try:
        spline = CubicSpline(
            anos,
            pops,
            bc_type="natural",
            extrapolate=True
        )

        pop_2026 = int(round(float(spline(2026))))

        # Evita população negativa
        pop_2026 = max(pop_2026, 0)

        ultima = grupo.iloc[-1]

        novas_linhas.append({
            "cod_mun_ibge_7": ultima["cod_mun_ibge_7"],
            "cod_mun_ibge_6": ultima["cod_mun_ibge_6"],
            "municipio": ultima["municipio"],
            "UF": ultima["UF"],
            "ano": 2026,
            "populacao": pop_2026,
            "tipo": "Estimativa (Spline)"
        })

    except Exception as e:
        print(f"Erro em {cod_mun}: {e}")

df_2026 = pd.DataFrame(novas_linhas)

resultado = pd.concat(
    [df, df_2026],
    ignore_index=True
)

resultado = resultado.sort_values(
    ["cod_mun_ibge_7", "ano"]
)

resultado.to_csv(
    ARQUIVO_SAIDA,
    sep=";",
    index=False,
    encoding="utf-8"
)

print(f"{len(df_2026)} estimativas geradas.")
print(f"Arquivo salvo: {ARQUIVO_SAIDA}")
