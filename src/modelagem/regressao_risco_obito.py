# -*- coding: utf-8 -*-
# Arquivo: src/prediction/risco_obito_pneumonia.py

import pandas as pd
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

from pysus.online_data.SIH import download as download_sih
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score, roc_curve
from sklearn.preprocessing import StandardScaler

def analisar_risco_obito(
    ufs: list = ['TO'],
    anos: list = [2022],
    diagnostico_cids: list = ['J12', 'J13', 'J14', 'J15', 'J16', 'J17', 'J18'],
    comorbidade_cids: list = None,
    dir_saida_analises: Path = Path("outputs/analises")
):
    """
    Treina um modelo de Regressão Logística para prever o risco de óbito para um
    diagnóstico específico, incluindo a análise de comorbidades.
    """
    diagnostico_nome = "-".join(diagnostico_cids)
    print(f"\n--- Iniciando Análise de Risco de Óbito por {diagnostico_nome} ---")
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

    # --- 2. Engenharia de Features para EDA ---
    df_modelo_raw['TEM_COMORBIDADE'] = df_modelo_raw['DIAGSEC1'].notna().astype(int)
    df_modelo_raw['RACA_COR'] = df_modelo_raw['RACA_COR'].fillna('9').astype(str)

    # --- 3. Análise Exploratória de Dados (EDA) ---
    print("\n--- Gerando gráficos de Análise Exploratória ---")
    dir_saida_analises.mkdir(parents=True, exist_ok=True)

    # 3.1 Distribuição de Idade por Desfecho
    plt.figure(figsize=(10, 6))
    sns.violinplot(x='MORTE', y='IDADE', data=df_modelo_raw, palette='muted')
    plt.title('Distribuição de Idade por Desfecho (0 = Alta, 1 = Óbito)')
    plt.xlabel('Desfecho')
    plt.ylabel('Idade')
    caminho_idade = dir_saida_analises / f"eda_idade_desfecho_{diagnostico_nome.lower()}.png"
    plt.savefig(caminho_idade)
    plt.close()
    print(f"✅ Gráfico de distribuição de idade salvo em: '{caminho_idade}'")

    # 3.2 Contagem de Desfechos por Sexo
    plt.figure(figsize=(10, 6))
    sns.countplot(x='SEXO', hue='MORTE', data=df_modelo_raw, palette='pastel')
    plt.title('Contagem de Desfechos por Sexo')
    plt.xlabel('Sexo')
    plt.ylabel('Contagem')
    caminho_sexo = dir_saida_analises / f"eda_desfecho_sexo_{diagnostico_nome.lower()}.png"
    plt.savefig(caminho_sexo)
    plt.close()
    print(f"✅ Gráfico de desfecho por sexo salvo em: '{caminho_sexo}'")

    # 3.3 Contagem de Desfechos por Caráter da Internação
    plt.figure(figsize=(10, 6))
    sns.countplot(x='CAR_INT', hue='MORTE', data=df_modelo_raw, palette='deep')
    plt.title('Contagem de Desfechos por Caráter da Internação')
    plt.xlabel('Caráter da Internação')
    plt.ylabel('Contagem')
    caminho_car_int = dir_saida_analises / f"eda_desfecho_car_int_{diagnostico_nome.lower()}.png"
    plt.savefig(caminho_car_int)
    plt.close()
    print(f"✅ Gráfico de desfecho por caráter de internação salvo em: '{caminho_car_int}'")

    # 3.4 Contagem de Desfechos por Raça/Cor
    plt.figure(figsize=(12, 7))
    sns.countplot(x='RACA_COR', hue='MORTE', data=df_modelo_raw, palette='colorblind', order=sorted(df_modelo_raw['RACA_COR'].unique()))
    plt.title('Contagem de Desfechos por Raça/Cor')
    plt.xlabel('Raça/Cor (1:Branca, 2:Preta, 3:Parda, 4:Amarela, 5:Indígena, 9:Ignorado)')
    plt.ylabel('Contagem')
    caminho_raca = dir_saida_analises / f"eda_desfecho_raca_cor_{diagnostico_nome.lower()}.png"
    plt.savefig(caminho_raca)
    plt.close()
    print(f"✅ Gráfico de desfecho por raça/cor salvo em: '{caminho_raca}'")

    # 3.5 Contagem de Desfechos por Presença de Comorbidade
    plt.figure(figsize=(10, 6))
    sns.countplot(x='TEM_COMORBIDADE', hue='MORTE', data=df_modelo_raw, palette='rocket')
    plt.title('Contagem de Desfechos por Presença de Comorbidade')
    plt.xlabel('Tinha Diagnóstico Secundário? (0 = Não, 1 = Sim)')
    plt.ylabel('Contagem')
    caminho_comorb = dir_saida_analises / f"eda_desfecho_comorbidade_{diagnostico_nome.lower()}.png"
    plt.savefig(caminho_comorb)
    plt.close()
    print(f"✅ Gráfico de desfecho por comorbidade salvo em: '{caminho_comorb}'")

    # --- 4. Engenharia de Features para o Modelo ---
    if comorbidade_cids:
        comorbidade_col_name = f"TEM_COMORB_{'-'.join(comorbidade_cids)}"
        df_modelo_raw[comorbidade_col_name] = df_modelo_raw['DIAGSEC1'].str.startswith(tuple(comorbidade_cids)).fillna(False).astype(int)

    df_modelo = pd.get_dummies(df_modelo_raw.drop('DIAGSEC1', axis=1), columns=['SEXO', 'CAR_INT', 'RACA_COR'], drop_first=True)

    X = df_modelo.drop('MORTE', axis=1)
    y = df_modelo['MORTE']

    scaler = StandardScaler()
    X_scaled = X.copy()
    X_scaled['IDADE'] = scaler.fit_transform(X[['IDADE']])

    print("\n[INFO] Features utilizadas no modelo (após transformação):")
    print(X_scaled.head())

    # --- 5. Treinamento do Modelo ---
    X_train, X_test, y_train, y_test = train_test_split(X_scaled, y, test_size=0.3, random_state=42, stratify=y)

    print("\nTreinando o modelo de Regressão Logística...")
    log_reg = LogisticRegression(random_state=42, class_weight='balanced', max_iter=1000)
    log_reg.fit(X_train, y_train)
    print("Modelo treinado com sucesso.")

    # --- 6. Avaliação e Predição ---
    y_pred = log_reg.predict(X_test)
    y_pred_proba = log_reg.predict_proba(X_test)[:, 1]

    print("\n--- Performance do Modelo ---")
    print("\nRelatório de Classificação:")
    print(classification_report(y_test, y_pred))
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"AUC (Área sob a curva ROC): {auc:.4f}")

    # --- 7. Interpretação dos Resultados ---
    print("\n--- Fatores de Risco (Coeficientes do Modelo) ---")
    coefs = pd.DataFrame(log_reg.coef_[0], index=X_train.columns, columns=['Coeficiente'])
    coefs['Chance (Odds Ratio)'] = np.exp(coefs['Coeficiente'])
    print(coefs.sort_values('Chance (Odds Ratio)', ascending=False))

    # --- 8. Geração de Artefatos de Saída ---
    nome_base_arquivo = f"risco_obito_{diagnostico_nome.lower()}"

    # 8.1 Salva o CSV com as predições e dados originais
    df_orig_test = df_modelo_raw.loc[X_test.index].copy()
    df_orig_test.rename(columns={'MORTE': 'MORTE_REAL'}, inplace=True)
    df_orig_test['MORTE_PREDITA'] = y_pred
    df_orig_test['PROBABILIDADE_OBITO'] = y_pred_proba

    caminho_csv = dir_saida_analises / f"predicoes_{nome_base_arquivo}.csv"
    df_orig_test.to_csv(caminho_csv, index=False, sep=';', decimal=',')
    print(f"\n✅ Predições e dados originais salvos em: '{caminho_csv}'")

    # 8.2 Salva a Matriz de Confusão
    plt.figure(figsize=(8, 6))
    sns.heatmap(confusion_matrix(y_test, y_pred), annot=True, fmt='d', cmap='Blues')
    plt.title(f'Matriz de Confusão - Risco de Óbito por {diagnostico_nome}')
    plt.ylabel('Verdadeiro')
    plt.xlabel('Previsto')
    caminho_matriz = dir_saida_analises / f"matriz_confusao_{nome_base_arquivo}.png"
    plt.savefig(caminho_matriz)
    plt.close()
    print(f"✅ Matriz de confusão salva em: '{caminho_matriz}'")

    # 8.3 Salva a Curva ROC
    fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
    plt.figure(figsize=(8, 6))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'Curva ROC (AUC = {auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlabel('Taxa de Falsos Positivos')
    plt.ylabel('Taxa de Verdadeiros Positivos')
    plt.title(f'Curva ROC - Risco de Óbito por {diagnostico_nome}')
    plt.legend(loc="lower right")
    caminho_roc = dir_saida_analises / f"curva_roc_{nome_base_arquivo}.png"
    plt.savefig(caminho_roc)
    plt.close()
    print(f"✅ Curva ROC salva em: '{caminho_roc}'")

    # 8.4 Salva o Gráfico de Fatores de Risco (Odds Ratio)
    plt.figure(figsize=(10, 7))
    coefs_sorted = coefs.sort_values('Chance (Odds Ratio)', ascending=False)
    sns.barplot(x=coefs_sorted['Chance (Odds Ratio)'], y=coefs_sorted.index, palette='vlag')
    plt.axvline(x=1, color='grey', linestyle='--')
    plt.xlabel('Chance (Odds Ratio)')
    plt.ylabel('Fator de Risco')
    plt.title(f'Importância dos Fatores de Risco para Óbito por {diagnostico_nome}')
    caminho_fatores = dir_saida_analises / f"fatores_risco_{nome_base_arquivo}.png"
    plt.savefig(caminho_fatores, bbox_inches='tight')
    plt.close()
    print(f"✅ Gráfico de fatores de risco salvo em: '{caminho_fatores}'")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Treina um modelo de risco de óbito para internações por um diagnóstico específico.")

    RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent

    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos a processar.")

    parser.add_argument("--cids", nargs="+", default=['J12', 'J13', 'J14', 'J15', 'J16', 'J17', 'J18'],
                        help="Lista de prefixos de CID-10 para filtrar o diagnóstico principal.")

    parser.add_argument("--comorbidade_cids", nargs="+", default=None,
                        help="(Opcional) Lista de prefixos de CID-10 para uma comorbidade específica (DIAGSEC1).")

    parser.add_argument("--dir_saida_analises", type=str,
                        default=str(RAIZ_PROJETO / "outputs" / "analises"),
                        help="Diretório de saída para os resultados da análise.")

    args = parser.parse_args()

    analisar_risco_obito(
        ufs=args.ufs,
        anos=args.anos,
        diagnostico_cids=args.cids,
        comorbidade_cids=args.comorbidade_cids,
        dir_saida_analises=Path(args.dir_saida_analises)
    )
