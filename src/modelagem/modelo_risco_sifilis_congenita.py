# -*- coding: utf-8 -*-
"""
======================================================================
  DETERMINANTES MUNICIPAIS DA TAXA DE SÍFILIS CONGÊNITA
======================================================================
A sífilis congênita é um dos agravos mais evitáveis da saúde pública —
100% evitável com diagnóstico e tratamento da gestante durante o
pré-natal — o que torna sua persistência um marcador direto de FALHA de
acesso/qualidade do pré-natal. Este script treina um modelo LightGBM
(regressão) para prever a TAXA MUNICIPAL de sífilis congênita (SINAN/SIFC)
a partir de indicadores de cobertura e qualidade do pré-natal extraídos
do SINASC (proporção de gestantes com pré-natal adequado, proporção de
mães adolescentes, escolaridade materna) — com SHAP explicando quais
lacunas de pré-natal mais pesam na previsão, para orientar investimento
em atenção primária onde o retorno esperado (em casos evitados) é maior.
"""

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
import numpy as np
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt

from pysus.online_data.SINASC import download as download_sinasc
from pysus.online_data.SINAN import SINAN

UF_PARA_CODIGO_IBGE = {
    'RO': '11', 'AC': '12', 'AM': '13', 'RR': '14', 'PA': '15', 'AP': '16', 'TO': '17',
    'MA': '21', 'PI': '22', 'CE': '23', 'RN': '24', 'PB': '25', 'PE': '26', 'AL': '27',
    'SE': '28', 'BA': '29', 'MG': '31', 'ES': '32', 'RJ': '33', 'SP': '35', 'PR': '41',
    'SC': '42', 'RS': '43', 'MS': '50', 'MT': '51', 'GO': '52', 'DF': '53',
}


def construir_indicadores_prenatal(uf: str, ano: int) -> pd.DataFrame:
    print(f"[LOG] Baixando SINASC para {uf}/{ano}...")
    downloaded = download_sinasc(states=uf, years=ano, groups=['DN'])
    df = pd.concat([f.to_dataframe() for f in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()

    df['CODMUNRES_6DIG'] = df['CODMUNRES'].astype(str).str[:6]
    df['CONSPRENAT'] = pd.to_numeric(df['CONSPRENAT'], errors='coerce')
    df['IDADEMAE'] = pd.to_numeric(df['IDADEMAE'], errors='coerce')
    df['ESCMAE2010'] = pd.to_numeric(df['ESCMAE2010'], errors='coerce')

    grupo = df.groupby('CODMUNRES_6DIG')
    indicadores = pd.DataFrame({
        'N_NASCIMENTOS': grupo.size(),
        'PROP_PRENATAL_ADEQUADO': grupo['CONSPRENAT'].apply(lambda s: (s >= 4).mean()),
        'PROP_MAE_ADOLESCENTE': grupo['IDADEMAE'].apply(lambda s: (s < 20).mean()),
        'PROP_BAIXA_ESCOLARIDADE_MAE': grupo['ESCMAE2010'].apply(lambda s: (s <= 1).mean()),
    }).reset_index().rename(columns={'CODMUNRES_6DIG': 'cod_mun_ibge_6'})
    return indicadores


def carregar_taxa_sifilis_congenita(uf: str, ano: int, arquivo_populacao: Path) -> pd.DataFrame:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
    from src.utils.dataloaders import processar_agravo_sinan_generico

    df = processar_agravo_sinan_generico(
        ufs=[uf], anos=[ano], arquivo_populacao=arquivo_populacao,
        dis_code='SIFC', nome_indicador='TAXA_SIFC', coluna_filtro='CLASSI_FIN', codigos_confirmados=['1'],
    )
    if df is None or df.empty:
        return pd.DataFrame()
    return df[['cod_mun_ibge_6', 'TAXA_SIFC']]


def treinar_modelo(df: pd.DataFrame, dir_saida: Path):
    features = ['PROP_PRENATAL_ADEQUADO', 'PROP_MAE_ADOLESCENTE', 'PROP_BAIXA_ESCOLARIDADE_MAE', 'N_NASCIMENTOS']
    X = df[features]
    y = df['TAXA_SIFC']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
    modelo = lgb.LGBMRegressor(random_state=42, n_estimators=200, max_depth=4, min_child_samples=5)
    modelo.fit(X_train, y_train)

    y_pred = modelo.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    print(f"\n--- Performance do Modelo (conjunto de teste) ---")
    print(f"RMSE: {rmse:.2f} casos por 100 mil hab. | R²: {r2:.3f}")

    explainer = shap.TreeExplainer(modelo)
    shap_values = explainer.shap_values(X)

    plt.figure()
    shap.summary_plot(shap_values, X, show=False)
    plt.title("Determinantes da Taxa Municipal de Sífilis Congênita (SHAP)")
    plt.tight_layout()
    caminho_fig = dir_saida / "shap_sifilis_congenita.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico SHAP salvo em: {caminho_fig}")

    return modelo, r2


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Construindo indicadores de pré-natal (SINASC) para {args.uf}/{args.ano} ---")
    df_prenatal = construir_indicadores_prenatal(args.uf, args.ano)
    print(f"✅ {len(df_prenatal)} municípios com indicadores de pré-natal.")

    print(f"\n--- [ETAPA 2] Carregando taxa de sífilis congênita (SINAN/SIFC) ---")
    df_sifc = carregar_taxa_sifilis_congenita(args.uf, args.ano, Path(args.populacao))
    if df_sifc.empty:
        print("❌ Nenhum dado de sífilis congênita disponível. Abortando.")
        return

    df = pd.merge(df_prenatal, df_sifc, on='cod_mun_ibge_6', how='inner')
    df = df[df['N_NASCIMENTOS'] >= args.min_nascimentos]
    print(f"✅ {len(df)} municípios combinados (com >= {args.min_nascimentos} nascimentos).")

    from src.utils.dataloaders import adicionar_nome_municipio
    df = adicionar_nome_municipio(df, 'cod_mun_ibge_6', args.populacao)

    if len(df) < 20:
        print("❌ Poucos municípios para um modelo confiável (mínimo recomendado: 20). Tente reduzir --min-nascimentos ou incluir mais UFs manualmente.")
        return

    print(f"\n--- [ETAPA 3] Treinando modelo de determinantes ---")
    modelo, r2 = treinar_modelo(df, dir_saida)

    print("\n" + "=" * 80)
    print(f"--- RESULTADO: DETERMINANTES DA SÍFILIS CONGÊNITA EM {args.uf} ---")
    print("=" * 80)
    print(f"R² do modelo: {r2:.3f}")
    correlacao = df[['PROP_PRENATAL_ADEQUADO', 'TAXA_SIFC']].corr().iloc[0, 1]
    print(f"Correlação simples (pré-natal adequado x taxa de SIFC): {correlacao:.3f}")
    print("=" * 80)

    caminho_csv = dir_saida / f"dados_sifilis_congenita_{args.uf.lower()}_{args.ano}.csv"
    df.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Dados municipais salvos em: '{caminho_csv}'")

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE DETERMINANTES DA SÍFILIS CONGÊNITA CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modela os determinantes municipais (pré-natal) da taxa de sífilis congênita.")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano de referência.")
    parser.add_argument("--populacao", type=str, default="referencia/populacao/populacao_estimada_completa_spline.csv", help="Caminho para o CSV de população estimada.")
    parser.add_argument("--min-nascimentos", type=int, default=30, help="Nº mínimo de nascimentos no ano para um município entrar na análise (estabilidade estatística).")
    parser.add_argument("--dir_saida", type=str, default="outputs/sifilis_congenita", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
