# -*- coding: utf-8 -*-
"""
======================================================================
  ANÁLISE DE TÓPICOS EM SINTOMAS COM PROCESSAMENTO DE LINGUAGEM NATURAL (NLP)
======================================================================
Este script utiliza a técnica de Modelagem de Tópicos (Topic Modeling)
para analisar os campos de texto livre da ficha de notificação de
Acidentes por Animais Peçonhentos e identificar "clusters" de sinais
e sintomas que ocorrem com frequência juntos.
"""

import pandas as pd
from pathlib import Path
import argparse
import re

# Importações do PySUS
from pysus.online_data.SINAN import SINAN

# Ferramentas de NLP do Scikit-learn
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation

# Ferramentas de pré-processamento de texto do NLTK
import nltk
from nltk.corpus import stopwords


# Mapeamento de Sigla de UF para código IBGE (o SINAN não expõe filtro de UF
# em get_files(); os arquivos são nacionais por agravo/ano, então o filtro
# precisa ser aplicado no DataFrame já baixado).
UF_PARA_CODIGO_IBGE = {
    'RO': '11', 'AC': '12', 'AM': '13', 'RR': '14', 'PA': '15', 'AP': '16', 'TO': '17',
    'MA': '21', 'PI': '22', 'CE': '23', 'RN': '24', 'PB': '25', 'PE': '26', 'AL': '27',
    'SE': '28', 'BA': '29', 'MG': '31', 'ES': '32', 'RJ': '33', 'SP': '35', 'PR': '41',
    'SC': '42', 'RS': '43', 'MS': '50', 'MT': '51', 'GO': '52', 'DF': '53',
}


def carregar_dados_sinan(anos: list, ufs: list):
    """Carrega múltiplos anos de dados do SINAN para Acidentes por Animais Peçonhentos."""
    print(f"\n--- [ETAPA 1] Carregando dados do SINAN-ANIM para {ufs}/{anos} ---")

    try:
        sinan_db = SINAN().load()
        # O SINAN distribui os arquivos por agravo/ano em nível nacional — não
        # há parâmetro de UF em get_files(). O filtro por UF é aplicado abaixo,
        # após o download, pelo município de residência (ID_MN_RESI).
        files = sinan_db.get_files(dis_code='ANIM', year=anos)

        if not files:
            print("⚠️ Nenhum arquivo SINAN/ANIM encontrado para os filtros fornecidos.")
            return pd.DataFrame()

        print(f"[LOG] Baixando e processando {len(files)} arquivo(s)...")
        downloaded = sinan_db.download(files)

        if isinstance(downloaded, list):
            df = pd.concat([p.to_dataframe() for p in downloaded if hasattr(p, 'to_dataframe')], ignore_index=True)
        elif hasattr(downloaded, "to_dataframe"):
            df = downloaded.to_dataframe()
        else:
            df = pd.DataFrame()

        if df.empty:
            print("⚠️ Nenhum registro retornado pelo SINAN/ANIM.")
            return df

        if ufs and 'ID_MN_RESI' in df.columns:
            codigos_uf = [UF_PARA_CODIGO_IBGE[uf.upper()] for uf in ufs if uf.upper() in UF_PARA_CODIGO_IBGE]
            if codigos_uf:
                df = df[df['ID_MN_RESI'].astype(str).str[:2].isin(codigos_uf)].copy()
            else:
                print(f"⚠️ Nenhuma das UFs informadas ({ufs}) é reconhecida; nenhum filtro de UF aplicado.")

        print(f"✅ Dados de Acidentes por Animais Peçonhentos carregados para {ufs}. Total de {len(df)} registros.")
        return df

    except Exception as e:
        print(f"❌ Erro crítico durante o carregamento de dados: {e}")
        return pd.DataFrame()


def preparar_texto_para_analise(df: pd.DataFrame):
    """Cria o documento de análise e realiza a limpeza do texto."""
    print("\n--- [ETAPA 2] Preparando e limpando os dados de texto ---")

    # 1. Concatenar os campos de texto livre
    text_cols = ['CLI_LOCA_1', 'CLI_OUTR_3']
    df['NOTA_CLINICA'] = df[text_cols].fillna('').astype(str).agg(' '.join, axis=1)

    # 2. Filtrar apenas os registros que contêm algum texto
    df_texto = df[df['NOTA_CLINICA'].str.strip() != ''].copy()

    if df_texto.empty:
        print("❌ Nenhum dado de texto livre encontrado para análise.")
        return pd.DataFrame()

    # 3. Limpeza e Pré-processamento do Texto
    print("[LOG] Realizando limpeza do texto (lowercase, remoção de stopwords)...")
    stop_words = stopwords.words('portuguese')

    def limpar_texto(texto):
        texto = texto.lower() # Converte para minúsculas
        texto = re.sub(r'\d+', '', texto) # Remove números
        texto = re.sub(r'[^\w\s]', '', texto) # Remove pontuação
        palavras = texto.split()
        palavras_sem_stopwords = [palavra for palavra in palavras if palavra not in stop_words and len(palavra) > 2]
        return " ".join(palavras_sem_stopwords)

    df_texto['TEXTO_LIMPO'] = df_texto['NOTA_CLINICA'].apply(limpar_texto)

    # Remove registros que ficaram sem texto após a limpeza
    df_texto_final = df_texto[df_texto['TEXTO_LIMPO'].str.strip() != ''].copy()

    print(f"✅ Preparação de texto concluída. {len(df_texto_final)} registros com texto válido para análise.")
    return df_texto_final


def modelar_e_interpretar_topicos(df: pd.DataFrame, n_topicos: int, n_palavras_top: int):
    """
    Vetoriza o texto e aplica o modelo LDA para descobrir tópicos.
    """
    print("\n--- [ETAPA 3] Modelagem de Tópicos com LDA ---")

    # 1. Vetorização (Bag of Words)
    print("[LOG] Vetorizando o texto com CountVectorizer...")
    # Considera apenas palavras que aparecem em no mínimo 5 documentos
    vectorizer = CountVectorizer(max_df=0.95, min_df=5, ngram_range=(1,2))
    X_counts = vectorizer.fit_transform(df['TEXTO_LIMPO'])

    # 2. Treinamento do Modelo LDA
    print(f"[LOG] Treinando o modelo LDA para encontrar {n_topicos} tópicos...")
    lda = LatentDirichletAllocation(n_components=n_topicos, random_state=42)
    lda.fit(X_counts)

    # 3. Interpretação e Geração do Relatório
    print("\n" + "="*80)
    print("--- RESULTADOS: TÓPICOS DE SINTOMAS DESCOBERTOS ---")
    print("="*80)

    feature_names = vectorizer.get_feature_names_out()

    for topico_idx, topic in enumerate(lda.components_):
        # Pega as N palavras mais importantes para o tópico
        top_words = [feature_names[i] for i in topic.argsort()[:-n_palavras_top - 1:-1]]
        print(f"\nTópico #{topico_idx + 1}:")
        print("  -> Palavras-chave: ", ", ".join(top_words))

        # Opcional: Mostrar um exemplo de relato para este tópico
        df['TOPICO_DOMINANTE'] = lda.transform(X_counts).argmax(axis=1)
        # Garante que haja pelo menos um exemplo antes de tentar acessá-lo
        exemplos = df[df['TOPICO_DOMINANTE'] == topico_idx]['NOTA_CLINICA']
        if not exemplos.empty:
            print(f"  -> Exemplo de relato: '{exemplos.head(1).iloc[0]}'")

    print("\n" + "="*80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Executa uma análise de modelagem de tópicos em campos de texto do SINAN.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument("--ufs", nargs="+", required=True, help="Lista de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Anos de dados do SINAN-ANIM a usar.")
    parser.add_argument("--n-topicos", type=int, default=5, help="Número de tópicos (clusters de sintomas) a serem descobertos.")
    parser.add_argument("--n-palavras", type=int, default=10, help="Número de palavras-chave para exibir por tópico.")

    args = parser.parse_args()

    # Pipeline
    df_raw = carregar_dados_sinan(anos=args.anos, ufs=args.ufs)

    if df_raw is not None and not df_raw.empty:
        df_preparado = preparar_texto_para_analise(df_raw)

        if not df_preparado.empty:
            modelar_e_interpretar_topicos(df_preparado, args.n_topicos, args.n_palavras)
            print("🎉 PIPELINE DE MODELAGEM DE TÓPICOS CONCLUÍDO! 🎉")
            print("="*80)
