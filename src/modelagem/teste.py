# -*- coding: utf-8 -*-
"""
Script para construir um modelo preditivo de surtos de Infecção Hospitalar (HAI).

Este script realiza os seguintes passos:
1.  Baixa dados de internações (SIH) e de cadastro de estabelecimentos (CNES) para um período histórico.
2.  Agrega os dados em uma base trimestral por hospital (CNES).
3.  Realiza a engenharia de features, calculando taxas, médias e variáveis de lag temporal.
4.  Define uma variável alvo (SURTO) para identificar um aumento significativo na taxa de infecção.
5.  Junta os dados do SIH e CNES para criar o dataset final de modelagem.
6.  Treina um modelo de classificação (Random Forest) para prever a ocorrência de um surto no próximo trimestre.
7.  Avalia o modelo e exibe os fatores de risco mais importantes.
"""
import pandas as pd
import numpy as np
from pathlib import Path
import argparse
from datetime import datetime

# --- Dependências de ML ---
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# --- Dependência de Dados do SUS ---
from pysus.online_data import SIH, CNES

# --- Funções Auxiliares ---

def carregar_dados_sih(anos: list) -> pd.DataFrame:
    """Baixa e consolida dados do SIH para os anos especificados."""
    print(f"\n--- Carregando dados do SIH para os anos: {anos} ---")
    sih_db = SIH()
    all_dfs = []
    for ano in anos:
        try:
            # Baixando para todos os estados (a base nacional é mais robusta)
            files = sih_db.get_files(group='RD', year=ano)
            if not files:
                print(f"Aviso: Nenhum arquivo SIH encontrado para o ano {ano}.")
                continue

            print(f"Baixando e processando {len(files)} arquivos para o ano {ano}...")
            # Limitar a quantidade de arquivos para um exemplo mais rápido: pega
            # 1 arquivo por estado (mês de dezembro) em vez dos 12 primeiros da
            # lista, que ficariam concentrados em 1-2 estados (ordem alfabética
            # do nome do arquivo, ex: RDAC*.dbc, RDAL*.dbc, ...).
            # Em um cenário real, remova este filtro para usar todos os meses/estados.
            files_to_process = [f for f in files if f.name[-2:] == '12']

            downloaded = sih_db.download(files_to_process)

            if isinstance(downloaded, list):
                 dfs_ano = [p.to_dataframe() for p in downloaded if hasattr(p, 'to_dataframe')]
            elif hasattr(downloaded, "to_dataframe"):
                 dfs_ano = [downloaded.to_dataframe()]
            else:
                 dfs_ano = []

            if dfs_ano:
                df_ano = pd.concat(dfs_ano, ignore_index=True)
                all_dfs.append(df_ano)
                print(f"Ano {ano} processado. Registros: {len(df_ano)}")

        except Exception as e:
            print(f"Erro ao processar o ano {ano} do SIH: {e}")

    if not all_dfs:
        return pd.DataFrame()

    return pd.concat(all_dfs, ignore_index=True)

def carregar_dados_cnes(anos: list) -> pd.DataFrame:
    """Baixa e consolida dados de estabelecimentos do CNES."""
    print(f"\n--- Carregando dados do CNES para os anos: {anos} ---")
    cnes_db = CNES()
    all_dfs = []
    for ano in anos:
        try:
            # Usar os dados de Dezembro como a "foto" do final do ano
            files = cnes_db.get_files(group='ST', year=ano, month=12)
            if not files:
                print(f"Aviso: Nenhum arquivo CNES encontrado para {ano}-12.")
                continue

            print(f"Baixando e processando dados de {ano}-12...")
            df_ano = cnes_db.download(files).to_dataframe()
            # Adiciona a coluna de ano para facilitar o join
            df_ano['ANO'] = ano
            all_dfs.append(df_ano)
        except Exception as e:
            print(f"Erro ao processar o ano {ano} do CNES: {e}")

    if not all_dfs:
        return pd.DataFrame()

    return pd.concat(all_dfs, ignore_index=True)

def criar_features_trimestrais_sih(df_sih: pd.DataFrame) -> pd.DataFrame:
    """Agrega dados do SIH e cria features em uma base trimestral por hospital."""
    print("\n--- Criando features trimestrais a partir dos dados do SIH ---")

    # 1. Limpeza e conversão de tipos
    df_sih['DT_INTER'] = pd.to_datetime(df_sih['DT_INTER'], errors='coerce')
    df_sih.dropna(subset=['DT_INTER', 'CNES'], inplace=True)

    df_sih['INFEHOSP'] = pd.to_numeric(df_sih['INFEHOSP'], errors='coerce').fillna(0)
    df_sih['DIAS_PERM'] = pd.to_numeric(df_sih['DIAS_PERM'], errors='coerce')

    # 2. Criar a coluna de trimestre
    df_sih['trimestre'] = pd.to_datetime(df_sih['DT_INTER']).dt.to_period('Q')

    # 3. Agregação por hospital e trimestre
    # Definindo cirurgias complexas (exemplo simplificado: procedimentos cirúrgicos principais)
    # Em um projeto real, esta lista seria validada com especialistas.
    df_sih['is_cirurgia'] = df_sih['PROC_REA'].str.startswith('04').astype(int)

    df_trimestral = df_sih.groupby(['CNES', 'trimestre']).agg(
        total_internacoes=('N_AIH', 'nunique'),
        total_infeccoes=('INFEHOSP', lambda x: x[x == 1].count()),
        media_dias_perm=('DIAS_PERM', 'mean'),
        total_cirurgias=('is_cirurgia', 'sum')
    ).reset_index()

    # 4. Cálculo de taxas e indicadores
    df_trimestral['taxa_infeccao'] = (df_trimestral['total_infeccoes'] / df_trimestral['total_internacoes'] * 100).fillna(0)
    df_trimestral['perc_cirurgias'] = (df_trimestral['total_cirurgias'] / df_trimestral['total_internacoes'] * 100).fillna(0)

    # 5. Criação de features de lag (dados do trimestre anterior)
    df_trimestral = df_trimestral.sort_values(by=['CNES', 'trimestre'])
    for col in ['taxa_infeccao', 'media_dias_perm', 'total_internacoes', 'perc_cirurgias']:
        df_trimestral[f'{col}_lag1'] = df_trimestral.groupby('CNES')[col].shift(1)

    print("Features trimestrais do SIH criadas com sucesso.")
    return df_trimestral

def definir_variavel_alvo(df_trimestral: pd.DataFrame) -> pd.DataFrame:
    """Define a variável alvo 'SURTO' com base no aumento da taxa de infecção."""
    print("\n--- Definindo a variável alvo (SURTO) ---")

    # 1. Calcular a mudança na taxa de infecção em relação ao trimestre anterior
    df_trimestral['delta_taxa_infeccao'] = df_trimestral['taxa_infeccao'] - df_trimestral['taxa_infeccao_lag1']

    # 2. Definir o limiar para "aumento significativo"
    # Usaremos o 75º percentil de todos os aumentos positivos
    aumentos = df_trimestral[df_trimestral['delta_taxa_infeccao'] > 0]['delta_taxa_infeccao']
    if len(aumentos) > 0:
        limiar_surto = aumentos.quantile(0.75)
    else:
        limiar_surto = 1 # Um valor padrão caso não haja aumentos

    print(f"Limiar para definir 'SURTO' (aumento acima de): {limiar_surto:.2f} pontos percentuais na taxa.")

    # 3. Criar a variável alvo
    df_trimestral['SURTO'] = (df_trimestral['delta_taxa_infeccao'] > limiar_surto).astype(int)

    # 4. Alinhar o alvo para a predição
    # Queremos prever o surto no PRÓXIMO trimestre usando dados do trimestre ATUAL.
    df_trimestral['SURTO_PROX_TRIMESTRE'] = df_trimestral.groupby('CNES')['SURTO'].shift(-1)

    # Remover linhas onde o alvo é nulo (o último trimestre de cada hospital)
    df_final = df_trimestral.dropna(subset=['SURTO_PROX_TRIMESTRE', 'taxa_infeccao_lag1']).copy()
    df_final['SURTO_PROX_TRIMESTRE'] = df_final['SURTO_PROX_TRIMESTRE'].astype(int)

    print("Variável alvo definida e alinhada para previsão.")
    return df_final

def treinar_e_avaliar_modelo(df_modelo: pd.DataFrame, dir_saida: Path):
    """Treina, avalia e interpreta o modelo de classificação."""
    print("\n--- Treinando e avaliando o modelo preditivo ---")

    # 1. Seleção de features e alvo
    features = [
        # Features do trimestre anterior (lag 1)
        'taxa_infeccao_lag1', 'media_dias_perm_lag1', 'total_internacoes_lag1', 'perc_cirurgias_lag1',
        # Features do CNES (características estruturais)
        'COMISS04', 'LEITHOSP', 'ATIVIDAD_ensino', 'tem_urgencia', 'is_filantropico'
    ]

    # Garante que todas as features existem no dataframe
    features_existentes = [f for f in features if f in df_modelo.columns]
    if len(features_existentes) != len(features):
        print(f"Aviso: features faltando. Usando apenas: {features_existentes}")

    X = df_modelo[features_existentes]
    y = df_modelo['SURTO_PROX_TRIMESTRE']

    # 2. Divisão treino/teste
    # Usar um split estratificado para garantir proporção de surtos em ambos os sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)

    print(f"Tamanho do dataset: {len(df_modelo)} hospitais-trimestres.")
    print(f"Distribuição da classe 'SURTO':\n{y.value_counts(normalize=True)}")

    # 3. Treinamento do Modelo
    # RandomForest é uma boa escolha pela robustez e interpretabilidade
    # class_weight='balanced' é crucial para lidar com o desbalanceamento de classes
    modelo = RandomForestClassifier(n_estimators=100, random_state=42, class_weight='balanced', n_jobs=-1)
    modelo.fit(X_train, y_train)

    # 4. Avaliação
    y_pred = modelo.predict(X_test)
    y_pred_proba = modelo.predict_proba(X_test)[:, 1]

    print("\n--- Relatório de Classificação ---")
    print(classification_report(y_test, y_pred))

    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"Área sob a Curva ROC (AUC): {auc:.4f}")

    # 5. Análise de Fatores de Risco (Feature Importances)
    importances = pd.DataFrame({
        'feature': X_train.columns,
        'importance': modelo.feature_importances_
    }).sort_values('importance', ascending=False)

    print("\n--- Fatores de Risco Mais Importantes ---")
    print(importances)

    # 6. Salvar artefatos
    dir_saida.mkdir(parents=True, exist_ok=True)

    # Salvar feature importances
    plt.figure(figsize=(12, 8))
    sns.barplot(x='importance', y='feature', data=importances)
    plt.title('Importância das Features para Previsão de Surtos de Infecção Hospitalar')
    plt.tight_layout()
    caminho_fig = dir_saida / "feature_importance.png"
    plt.savefig(caminho_fig)
    plt.close()
    print(f"\nGráfico de importância das features salvo em: {caminho_fig}")

    # Salvar matriz de confusão
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(8, 6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=['Não Surto', 'Surto'], yticklabels=['Não Surto', 'Surto'])
    plt.xlabel('Predito')
    plt.ylabel('Real')
    plt.title('Matriz de Confusão')
    caminho_cm = dir_saida / "confusion_matrix.png"
    plt.savefig(caminho_cm)
    plt.close()
    print(f"Matriz de confusão salva em: {caminho_cm}")


# --- Função Principal ---
def main(args):
    """Orquestra a execução do pipeline de predição de surtos."""
    # 1. Carregar dados brutos
    df_sih = carregar_dados_sih(args.anos_historico)
    df_cnes = carregar_dados_cnes(args.anos_historico)

    if df_sih.empty or df_cnes.empty:
        print("\nERRO CRÍTICO: Não foi possível carregar os dados. Abortando.")
        return

    # 2. Engenharia de features do SIH
    df_sih_trimestral = criar_features_trimestrais_sih(df_sih)

    # 3. Definir variável alvo
    df_sih_com_alvo = definir_variavel_alvo(df_sih_trimestral)

    # 4. Preparar dados do CNES e juntar
    print("\n--- Preparando e juntando dados do CNES ---")
    df_cnes_features = df_cnes[['CNES', 'ANO', 'COMISS04', 'LEITHOSP', 'ATIVIDAD', 'URGEMERG', 'TP_PREST']].copy()
    df_cnes_features.drop_duplicates(subset=['CNES', 'ANO'], inplace=True)

    # Criando features binárias a partir de categóricas
    df_cnes_features['COMISS04'] = pd.to_numeric(df_cnes_features['COMISS04'], errors='coerce').fillna(0).astype(int)
    df_cnes_features['ATIVIDAD_ensino'] = df_cnes_features['ATIVIDAD'].isin(['1', '2']).astype(int)
    df_cnes_features['tem_urgencia'] = pd.to_numeric(df_cnes_features['URGEMERG'], errors='coerce').fillna(0).astype(int)
    df_cnes_features['is_filantropico'] = (df_cnes_features['TP_PREST'] == '61').astype(int)

    # Adicionar ano ao dataframe do SIH para o merge
    df_sih_com_alvo['ANO'] = df_sih_com_alvo['trimestre'].dt.year

    # Merge
    df_modelo = pd.merge(
        df_sih_com_alvo,
        df_cnes_features,
        on=['CNES', 'ANO'],
        how='left'
    )

    # Limpeza final
    df_modelo.dropna(subset=['LEITHOSP'], inplace=True)

    print(f"Dataset final para modelagem criado com {len(df_modelo)} registros.")

    # 5. Treinar e avaliar o modelo
    treinar_e_avaliar_modelo(df_modelo, Path(args.dir_saida))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Modelo Preditivo de Surtos de Infecção Hospitalar (HAI).")

    current_year = datetime.now().year

    parser.add_argument(
        "--anos-historico",
        nargs="+",
        type=int,
        default=[current_year - 2, current_year - 1],
        help="Anos de dados históricos a serem baixados para treinar o modelo."
    )
    parser.add_argument(
        "--dir-saida",
        type=str,
        default="outputs/analise_surtos_hai",
        help="Diretório para salvar os resultados (gráficos, etc.)."
    )

    args = parser.parse_args()

    main(args)
