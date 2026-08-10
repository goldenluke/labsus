# -*- coding: utf-8 -*-
"""
======================================================================
  REQUALIFICADOR DE CAUSA DE ÓBITO COM PROCESSAMENTO DE LINGUAGEM NATURAL (NLP)
======================================================================
Este script treina um modelo de classificação de texto para requalificar
óbitos registrados com "Causas Mal Definidas" (Capítulo XVIII da CID-10,
códigos R00-R99).
"""

import pandas as pd
from pathlib import Path
import argparse
import re

# Importações do PySUS
from pysus.online_data.SIM import SIM

# Ferramentas de NLP e Machine Learning do Scikit-learn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import classification_report


def carregar_dados_sim(anos: list, ufs: list):
    """Carrega múltiplos anos de dados do SIM com tratamento robusto de retorno."""
    print(f"\n--- [ETAPA 1] Carregando dados do SIM para {ufs}/{anos} ---")

    try:
        sim_db = SIM().load()
        files = sim_db.get_files(group='CID10', uf=ufs, year=anos)
        if not files:
            print("⚠️ Nenhum arquivo do SIM encontrado para os filtros fornecidos.")
            return pd.DataFrame()

        print(f"[LOG] Baixando e processando {len(files)} arquivo(s)...")

        downloaded = sim_db.download(files)

        if isinstance(downloaded, list):
            df = pd.concat([p.to_dataframe() for p in downloaded if hasattr(p, 'to_dataframe')], ignore_index=True)
        elif hasattr(downloaded, "to_dataframe"):
            df = downloaded.to_dataframe()
        else:
            df = pd.DataFrame()

        print(f"✅ Dados do SIM carregados com sucesso. Total de {len(df)} registros.")
        return df

    except Exception as e:
        print(f"❌ Erro crítico durante o carregamento de dados: {e}")
        return pd.DataFrame()


def preparar_dados_para_nlp(df: pd.DataFrame):
    """Prepara os dados para a análise de texto, criando o documento e o alvo."""
    print("\n--- [ETAPA 2] Preparando dados para a modelagem NLP ---")

    text_cols = ['LINHAA', 'LINHAB', 'LINHAC', 'LINHAD', 'LINHAII']
    df['TEXTO_DO'] = df[text_cols].fillna('').astype(str).agg(' '.join, axis=1)
    df['TEXTO_DO'] = df['TEXTO_DO'].str.lower().apply(lambda x: re.sub(r'\s+', ' ', x).strip())
    df['CAPITULO_CID'] = df['CAUSABAS'].astype(str).str[0]

    df_treino = df[~df['CAPITULO_CID'].isin(['R', 'n', 'N'])].copy()
    df_predicao = df[df['CAPITULO_CID'] == 'R'].copy()

    df_treino.dropna(subset=['TEXTO_DO'], inplace=True)
    df_treino = df_treino[df_treino['TEXTO_DO'] != '']

    print(f"✅ Dados preparados:")
    print(f"  -> {len(df_treino)} registros para treinamento (causas bem definidas).")
    print(f"  -> {len(df_predicao)} registros para requalificação (causas mal definidas).")

    return df_treino, df_predicao

def treinar_e_aplicar_modelo_nlp(df_treino: pd.DataFrame, df_predicao: pd.DataFrame):
    """
    Treina um modelo de classificação de texto e o aplica para requalificar
    os óbitos mal definidos.
    """
    print("\n--- [ETAPA 3] Treinamento e Aplicação do Modelo NLP ---")

    print("[LOG] Vetorizando o texto com TF-IDF...")
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=15000)

    X_text = df_treino['TEXTO_DO']
    y = df_treino['CAPITULO_CID']

    X_tfidf = vectorizer.fit_transform(X_text)

    X_train, X_test, y_train, y_test = train_test_split(X_tfidf, y, test_size=0.3, random_state=42, stratify=y)

    # Usamos loss='modified_huber' que é bom para obter scores de confiança
    modelo = SGDClassifier(loss='modified_huber', penalty='l2', alpha=1e-4, random_state=42, max_iter=20, tol=None)

    print("[LOG] Treinando o modelo de classificação de texto...")
    modelo.fit(X_train, y_train)
    print("✅ Modelo treinado com sucesso.")

    print("\n--- Performance do Modelo de Requalificação (em dados de teste) ---")
    y_pred = modelo.predict(X_test)
    print(classification_report(y_test, y_pred, zero_division=0))

    print(f"\n[LOG] Requalificando {len(df_predicao)} óbitos com causa mal definida...")
    if not df_predicao.empty:
        X_mal_definidos_text = df_predicao['TEXTO_DO']
        X_mal_definidos_tfidf = vectorizer.transform(X_mal_definidos_text)

        df_predicao['CAPITULO_PREVISTO'] = modelo.predict(X_mal_definidos_tfidf)

        # O decision_function com modified_huber retorna um score que pode ser interpretado como confiança
        scores = modelo.decision_function(X_mal_definidos_tfidf)
        df_predicao['CONFIANCA_PREVISAO'] = scores.max(axis=1)

        print("✅ Requalificação concluída.")
        return df_predicao
    else:
        print("  -> Nenhum óbito mal definido encontrado para requalificar.")
        return pd.DataFrame()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Requalifica óbitos com causa mal definida usando NLP.")
    parser.add_argument("--ufs", nargs="+", required=True, help="Lista de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Anos de dados do SIM a usar.")
    parser.add_argument("--dir_saida", type=str, default="outputs/requalificacao_obitos", help="Diretório para salvar o relatório.")

    # ==========================================================
    # --- NOVO ARGUMENTO ADICIONADO AQUI ---
    # ==========================================================
    parser.add_argument(
        "--limiar-confianca",
        type=float,
        default=0.0,
        help="Limiar mínimo de confiança para incluir uma previsão no relatório final. Scores mais altos indicam maior confiança."
    )
    # ==========================================================

    args = parser.parse_args()

    # Pipeline
    df_raw = carregar_dados_sim(anos=args.anos, ufs=args.ufs)

    if df_raw is not None and not df_raw.empty:
        df_treino, df_predicao = preparar_dados_para_nlp(df_raw)

        if not df_treino.empty:
            df_requalificado = treinar_e_aplicar_modelo_nlp(df_treino, df_predicao)

            if not df_requalificado.empty:
                # ==========================================================
                # --- LÓGICA DE FILTRAGEM ADICIONADA AQUI ---
                # ==========================================================
                print(f"\n[LOG] Filtrando resultados com confiança >= {args.limiar_confianca}...")

                total_antes_filtro = len(df_requalificado)
                df_filtrado = df_requalificado[df_requalificado['CONFIANCA_PREVISAO'] >= args.limiar_confianca].copy()
                total_depois_filtro = len(df_filtrado)

                print(f"  -> {total_depois_filtro} de {total_antes_filtro} previsões ({total_depois_filtro/total_antes_filtro:.2%}) foram mantidas.")
                # ==========================================================

                output_dir = Path(args.dir_saida)
                output_dir.mkdir(parents=True, exist_ok=True)

                ufs_str = '-'.join(args.ufs).lower()
                anos_str = '-'.join(map(str, args.anos))
                nome_arquivo = f"obitos_requalificados_confianca_{str(args.limiar_confianca).replace('.', 'p')}_{ufs_str}_{anos_str}.csv"
                caminho_csv = output_dir / nome_arquivo

                colunas_relatorio = [
                    'CODMUNRES', 'DTOBITO', 'IDADE', 'SEXO',
                    'CAUSABAS', 'TEXTO_DO', 'CAPITULO_PREVISTO', 'CONFIANCA_PREVISAO'
                ]
                df_filtrado[colunas_relatorio].to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')

                print(f"\n📄 Relatório de óbitos requalificados salvo em: '{caminho_csv}'")
                print("\n--- Amostra do Relatório de Requalificação (Alta Confiança) ---")
                print(df_filtrado[colunas_relatorio].head())

                print("\n" + "="*80)
                print("🎉 PIPELINE DE REQUALIFICAÇÃO DE CAUSA DE ÓBITO CONCLUÍDO! 🎉")
                print("="*80)
