# -*- coding: utf-8 -*-
# Arquivo: src/prediction/risco_obito_task.py
# Versão otimizada para ser executada como uma background task (ex: em tasks.py do Django/Celery)

import pandas as pd
import argparse
from pathlib import Path
import numpy as np

from pysus.online_data.SIH import download as download_sih
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import StandardScaler

def analisar_risco_obito_task(
    ufs: list = ['TO'],
    anos: list = [2022],
    diagnostico_cids: list = ['J12', 'J13', 'J14', 'J15', 'J16', 'J17', 'J18'],
    comorbidade_cids: list = None,
    dir_saida_csv: Path = Path("dados/processados/analises")
):
    """
    Treina um modelo de Regressão Logística para prever o risco de óbito para um
    diagnóstico específico e salva os resultados em um CSV.
    Esta versão não gera gráficos.
    """
    diagnostico_nome = "-".join(diagnostico_cids)
    print(f"\n--- Iniciando Task: Análise de Risco de Óbito por {diagnostico_nome} ---")
    if comorbidade_cids:
        print(f"    -> Analisando o impacto da comorbidade: {'-'.join(comorbidade_cids)}")

    # --- 1. Coleta e Preparação dos Dados ---
    df_list = []
    for uf in ufs:
        for ano in anos:
            try:
                print(f"  -> Baixando dados do SIH para {uf}/{ano}...")
                downloaded_files = download_sih(states=uf, years=ano, months=list(range(1, 13)), groups='RD')

                if isinstance(downloaded_files, list):
                    df_sih = pd.concat([f.to_dataframe() for f in downloaded_files], ignore_index=True)
                elif hasattr(downloaded_files, "to_dataframe"):
                    df_sih = downloaded_files.to_dataframe()
                else:
                    df_sih = pd.DataFrame()

                df_list.append(df_sih)
            except Exception as e:
                print(f"⚠️ Erro ao baixar dados para {uf}/{ano}: {e}")

    if not df_list:
        print("❌ Nenhum dado do SIH pôde ser baixado. Análise abortada.")
        return

    df_total = pd.concat(df_list, ignore_index=True)
    print(f"Total de {len(df_total)} registos de internação baixados.")

    # Filtra para o diagnóstico principal especificado
    df_diagnostico = df_total[df_total['DIAG_PRINC'].str.startswith(tuple(diagnostico_cids))].copy()
    print(f"  -> {len(df_diagnostico)} registos de {diagnostico_nome} encontrados.")

    features = ['IDADE', 'SEXO', 'CAR_INT', 'RACA_COR', 'DIAGSEC1', 'MORTE']
    df_modelo_raw = df_diagnostico[features].copy()
    df_modelo_raw['MORTE'] = pd.to_numeric(df_modelo_raw['MORTE'], errors='coerce')
    df_modelo_raw.dropna(subset=['MORTE'], inplace=True)

    if len(df_modelo_raw) < 50:
        print(f"❌ Análise abortada: Número de amostras ({len(df_modelo_raw)}) é muito baixo.")
        return

    if df_modelo_raw['MORTE'].nunique() < 2:
        print(f"❌ Análise abortada: O conjunto de dados contém apenas uma classe de desfecho.")
        return

    # --- 2. Engenharia de Features para o Modelo ---
    df_modelo_raw['TEM_COMORBIDADE'] = df_modelo_raw['DIAGSEC1'].notna().astype(int)

    if comorbidade_cids:
        comorbidade_col_name = f"TEM_COMORB_{'-'.join(comorbidade_cids)}"
        df_modelo_raw[comorbidade_col_name] = df_modelo_raw['DIAGSEC1'].str.startswith(tuple(comorbidade_cids)).fillna(False).astype(int)

    df_modelo_raw['RACA_COR'] = df_modelo_raw['RACA_COR'].fillna('9').astype(str)

    df_modelo = pd.get_dummies(df_modelo_raw.drop('DIAGSEC1', axis=1), columns=['SEXO', 'CAR_INT', 'RACA_COR'], drop_first=True)

    X = df_modelo.drop('MORTE', axis=1)
    y = df_modelo['MORTE']

    scaler = StandardScaler()
    X_scaled = X.copy()
    X_scaled['IDADE'] = scaler.fit_transform(X[['IDADE']])

    # --- 3. Treinamento do Modelo ---
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.3, random_state=42, stratify=y)

    print("\nTreinando o modelo de Regressão Logística...")
    log_reg = LogisticRegression(random_state=42, class_weight='balanced', max_iter=1000)
    log_reg.fit(X_train, y_train)
    print("Modelo treinado com sucesso.")

    # --- 4. Avaliação e Predição ---
    y_pred = log_reg.predict(X_test)
    y_pred_proba = log_reg.predict_proba(X_test)[:, 1]

    print("\n--- Performance do Modelo ---")
    print("\nRelatório de Classificação:")
    print(classification_report(y_test, y_pred))
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"AUC (Área sob a curva ROC): {auc:.4f}")

    # --- 5. Interpretação dos Resultados ---
    print("\n--- Fatores de Risco (Coeficientes do Modelo) ---")
    coefs = pd.DataFrame(log_reg.coef_[0], index=X_train.columns, columns=['Coeficiente'])
    coefs['Chance (Odds Ratio)'] = np.exp(coefs['Coeficiente'])
    print(coefs.sort_values('Chance (Odds Ratio)', ascending=False))

    # --- 6. Geração do CSV de Saída ---
    dir_saida_csv.mkdir(parents=True, exist_ok=True)
    nome_base_arquivo = f"risco_obito_{diagnostico_nome.lower()}"

    df_orig_test = df_modelo_raw.loc[X_test.index].copy()
    df_orig_test.rename(columns={'MORTE': 'MORTE_REAL'}, inplace=True)
    df_orig_test['MORTE_PREDITA'] = y_pred
    df_orig_test['PROBABILIDADE_OBITO'] = y_pred_proba

    caminho_csv = dir_saida_csv / f"predicoes_{nome_base_arquivo}.csv"
    df_orig_test.to_csv(caminho_csv, index=False, sep=';', decimal=',')
    print(f"\n✅ Predições e dados originais salvos em: '{caminho_csv}'")
    print(f"--- Task Finalizada: Análise de Risco de Óbito por {diagnostico_nome} ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Treina um modelo de risco de óbito para internações por um diagnóstico específico.")

    RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent

    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos a processar.")

    parser.add_argument("--cids", nargs="+", default=['J12', 'J13', 'J14', 'J15', 'J16', 'J17', 'J18'],
                        help="Lista de prefixos de CID-10 para filtrar o diagnóstico principal.")

    parser.add_argument("--comorbidade_cids", nargs="+", default=None,
                        help="(Opcional) Lista de prefixos de CID-10 para uma comorbidade específica (DIAGSEC1).")

    parser.add_argument("--dir_saida_csv", type=str,
                        help="Diretório de saída para os resultados da análise em CSV.")

    args = parser.parse_args()

    analisar_risco_obito_task(
        ufs=args.ufs,
        anos=args.anos,
        diagnostico_cids=args.cids,
        comorbidade_cids=args.comorbidade_cids,
        dir_saida_csv=Path(args.dir_saida_csv)
    )
