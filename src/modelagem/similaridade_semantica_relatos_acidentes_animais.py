# -*- coding: utf-8 -*-
"""
======================================================================
  SIMILARIDADE SEMÂNTICA DE RELATOS CLÍNICOS (SINAN/ANIM)
======================================================================
Este script vetoriza (TF-IDF) os relatos de texto livre do quadro clínico
de Acidentes por Animais Peçonhentos, calcula a SIMILARIDADE DE COSSENO
entre todos os pares de relatos e agrupa (KMeans) os relatos mais
parecidos entre si em clusters narrativos — por exemplo, um cluster pode
capturar relatos dominados por "dor local, edema, equimose" (típico de
picada de serpente peçonhenta) enquanto outro captura "dor intensa,
sudorese, taquicardia" (típico de picada de escorpião).

Diferente da Modelagem de Tópicos (LDA, em `analise_topicos_sintomas_nlp.py`,
que descobre TEMAS latentes que se misturam em cada documento), aqui cada
relato é atribuído a UM cluster (partição rígida), o que facilita
comparar diretamente a frequência e a distribuição geográfica de cada
"padrão narrativo" de acidente.
"""

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import KMeans
from sklearn.decomposition import TruncatedSVD

import nltk
from nltk.corpus import stopwords

from pysus.online_data.SINAN import SINAN


def carregar_dados_anim(anos: list) -> pd.DataFrame:
    sinan_db = SINAN().load()
    files = sinan_db.get_files(dis_code='ANIM', year=anos)
    if not files:
        raise FileNotFoundError(f"Nenhum arquivo SINAN/ANIM encontrado para {anos}.")
    downloaded = sinan_db.download(files)
    df = pd.concat([p.to_dataframe() for p in downloaded], ignore_index=True) if isinstance(downloaded, list) else downloaded.to_dataframe()
    return df


def limpar_texto(texto: str, stop_words: set) -> str:
    texto = str(texto).lower()
    texto = re.sub(r'\d+', '', texto)
    texto = re.sub(r'[^\w\s]', '', texto)
    palavras = [p for p in texto.split() if p not in stop_words and len(p) > 2]
    return " ".join(palavras)


def preparar_textos(df: pd.DataFrame) -> pd.DataFrame:
    try:
        stop_words = set(stopwords.words('portuguese'))
    except LookupError:
        nltk.download('stopwords', quiet=True)
        stop_words = set(stopwords.words('portuguese'))

    text_cols = [c for c in ['CLI_LOCA_1', 'CLI_OUTR_3'] if c in df.columns]
    if not text_cols:
        raise KeyError("Nenhum campo de texto clínico (CLI_LOCA_1/CLI_OUTR_3) encontrado nos dados.")

    df['TEXTO_BRUTO'] = df[text_cols].fillna('').astype(str).agg(' '.join, axis=1)
    df = df[df['TEXTO_BRUTO'].str.strip() != ''].copy()
    df['TEXTO_LIMPO'] = df['TEXTO_BRUTO'].apply(lambda t: limpar_texto(t, stop_words))
    df = df[df['TEXTO_LIMPO'].str.strip() != '']
    return df


def agrupar_por_similaridade(df: pd.DataFrame, n_clusters: int, seed: int = 42):
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=3000, min_df=3)
    X_tfidf = vectorizer.fit_transform(df['TEXTO_LIMPO'])

    kmeans = KMeans(n_clusters=n_clusters, random_state=seed, n_init=10)
    df['CLUSTER_NARRATIVO'] = kmeans.fit_predict(X_tfidf)

    termos = np.array(vectorizer.get_feature_names_out())
    centros_ordenados = kmeans.cluster_centers_.argsort()[:, ::-1]
    termos_por_cluster = {c: termos[centros_ordenados[c, :12]].tolist() for c in range(n_clusters)}

    svd = TruncatedSVD(n_components=2, random_state=seed)
    coords_2d = svd.fit_transform(X_tfidf)
    df['SVD_1'], df['SVD_2'] = coords_2d[:, 0], coords_2d[:, 1]

    # cosine_similarity(sub) devolve uma matriz DENSA n x n — com dados
    # nacionais multi-ano um único cluster pode ter dezenas de milhares de
    # relatos, o que estoura a memória (ex.: 87746x87746 floats ~= 61 GB).
    # A média de similaridade intra-cluster é só uma estatística-resumo,
    # então uma amostra já é representativa; não precisa da matriz inteira.
    AMOSTRA_MAXIMA_SIMILARIDADE = 500
    rng = np.random.default_rng(seed)

    similaridade_media_intra = []
    X_denso = X_tfidf
    for c in range(n_clusters):
        indices_cluster = np.where(df['CLUSTER_NARRATIVO'].values == c)[0]
        if len(indices_cluster) < 2:
            similaridade_media_intra.append(np.nan)
            continue
        if len(indices_cluster) > AMOSTRA_MAXIMA_SIMILARIDADE:
            indices_cluster = rng.choice(indices_cluster, size=AMOSTRA_MAXIMA_SIMILARIDADE, replace=False)
        sub = X_denso[indices_cluster]
        sim = cosine_similarity(sub)
        n = sub.shape[0]
        media = (sim.sum() - n) / (n * (n - 1))  # exclui a diagonal (similaridade consigo mesmo)
        similaridade_media_intra.append(media)

    return df, termos_por_cluster, similaridade_media_intra


def gerar_grafico(df: pd.DataFrame, dir_saida: Path):
    import matplotlib.pyplot as plt
    import matplotlib.cm as cm

    plt.figure(figsize=(10, 9))
    scatter = plt.scatter(df['SVD_1'], df['SVD_2'], c=df['CLUSTER_NARRATIVO'], cmap=cm.tab10, alpha=0.6, s=15)
    plt.legend(*scatter.legend_elements(), title="Cluster", loc='best')
    plt.title("Clusters de Relatos Clínicos por Similaridade Semântica (SINAN/ANIM)")
    plt.xlabel('Componente semântica 1 (SVD/LSA)')
    plt.ylabel('Componente semântica 2 (SVD/LSA)')
    caminho_fig = dir_saida / "clusters_relatos_animais_peconhentos.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Mapa de clusters semânticos salvo em: {caminho_fig}")


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando dados do SINAN/ANIM para {args.anos} ---")
    df_raw = carregar_dados_anim(args.anos)
    print(f"✅ {len(df_raw)} notificações carregadas.")

    print(f"\n--- [ETAPA 2] Preparando textos clínicos ---")
    df = preparar_textos(df_raw)
    print(f"✅ {len(df)} relatos com texto válido.")

    if len(df) < 50:
        print("❌ Poucos relatos de texto para uma análise de similaridade confiável (mínimo recomendado: 50).")
        return

    print(f"\n--- [ETAPA 3] Agrupando relatos por similaridade semântica (k={args.n_clusters}) ---")
    df, termos_por_cluster, similaridade_intra = agrupar_por_similaridade(df, args.n_clusters, args.seed)

    print("\n" + "=" * 80)
    print("--- RESULTADO: CLUSTERS DE RELATOS CLÍNICOS POR SIMILARIDADE SEMÂNTICA ---")
    print("=" * 80)
    for c in range(args.n_clusters):
        n_relatos = (df['CLUSTER_NARRATIVO'] == c).sum()
        sim = similaridade_intra[c]
        print(f"\nCluster {c} ({n_relatos} relatos, similaridade média intra-cluster={sim:.3f} se calculável):")
        print(f"  Termos característicos: {', '.join(termos_por_cluster[c])}")
        exemplo = df[df['CLUSTER_NARRATIVO'] == c]['TEXTO_BRUTO'].iloc[0]
        print(f"  Exemplo de relato: '{exemplo[:150]}...'")
    print("=" * 80)

    caminho_csv = dir_saida / "relatos_com_cluster_semantico.csv"
    df[['TEXTO_BRUTO', 'CLUSTER_NARRATIVO', 'SVD_1', 'SVD_2']].to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Relatos com cluster atribuído salvos em: '{caminho_csv}'")

    gerar_grafico(df, dir_saida)

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE SIMILARIDADE SEMÂNTICA CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agrupa relatos clínicos do SINAN/ANIM por similaridade semântica (TF-IDF + KMeans).")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Anos de dados do SINAN/ANIM a usar.")
    parser.add_argument("--n-clusters", type=int, default=6, help="Número de clusters narrativos a formar.")
    parser.add_argument("--seed", type=int, default=42, help="Semente aleatória.")
    parser.add_argument("--dir_saida", type=str, default="outputs/similaridade_relatos_animais", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
