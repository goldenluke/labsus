# -*- coding: utf-8 -*-
"""
======================================================================
  CLASSIFICAÇÃO DE GRAVIDADE A PARTIR DE TEXTO CLÍNICO LIVRE (SINAN/ANIM)
======================================================================
Este script treina um classificador de texto (TF-IDF + SGDClassifier)
para prever, a partir SOMENTE da descrição textual livre do quadro
clínico (campos CLI_LOCA_1/CLI_OUTR_3 da notificação de Acidentes por
Animais Peçonhentos), se o caso terá COMPLICAÇÃO SISTÊMICA (COM_SISTEM:
insuficiência renal, choque, sepse, edema pulmonar — Tabela 5.1 do
dicionário de dados do SINAN/ANIM) — um desfecho clinicamente muito mais
grave do que uma complicação apenas local.

Motivação: complementa `analise_topicos_sintomas_nlp.py` (que descobre
TÓPICOS latentes no texto, sem rótulo) com um modelo SUPERVISIONADO que
aprende a associar padrões de linguagem clínica a um desfecho real —
útil como triagem auxiliar de risco a partir de texto livre digitado
no pronto-socorro, antes mesmo dos exames complementares.
"""

import argparse
import re
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import classification_report, roc_auc_score, roc_curve
import matplotlib.pyplot as plt

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


def preparar_dados(df: pd.DataFrame) -> pd.DataFrame:
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

    if 'COM_SISTEM' not in df.columns:
        raise KeyError("Coluna 'COM_SISTEM' (indicador de complicação sistêmica) não encontrada.")
    df['COM_SISTEM'] = pd.to_numeric(df['COM_SISTEM'], errors='coerce')
    df = df[df['COM_SISTEM'].isin([1, 2])].copy()
    df['GRAVE'] = (df['COM_SISTEM'] == 1).astype(int)

    return df[['TEXTO_LIMPO', 'GRAVE']]


def treinar_classificador(df: pd.DataFrame, dir_saida: Path):
    X_texto = df['TEXTO_LIMPO']
    y = df['GRAVE']

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000, min_df=3)
    X_tfidf = vectorizer.fit_transform(X_texto)

    X_train, X_test, y_train, y_test = train_test_split(X_tfidf, y, test_size=0.3, random_state=42, stratify=y)

    modelo = SGDClassifier(loss='modified_huber', penalty='l2', alpha=1e-4, class_weight='balanced', random_state=42, max_iter=20, tol=None)
    modelo.fit(X_train, y_train)

    y_pred = modelo.predict(X_test)
    y_pred_proba = modelo.predict_proba(X_test)[:, 1]

    print("\n--- Relatório de Classificação (conjunto de teste) ---")
    print(classification_report(y_test, y_pred, zero_division=0, target_names=['Sem complicação sistêmica', 'Complicação sistêmica']))
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"AUC (Área sob a Curva ROC): {auc:.4f}")

    coefs = modelo.coef_[0]
    termos = vectorizer.get_feature_names_out()
    top_positivos = sorted(zip(termos, coefs), key=lambda t: -t[1])[:20]
    top_negativos = sorted(zip(termos, coefs), key=lambda t: t[1])[:20]

    print("\n--- Termos mais associados a COMPLICAÇÃO SISTÊMICA ---")
    for termo, coef in top_positivos:
        print(f"  {termo}: {coef:+.3f}")
    print("\n--- Termos mais associados a EVOLUÇÃO SEM COMPLICAÇÃO ---")
    for termo, coef in top_negativos:
        print(f"  {termo}: {coef:+.3f}")

    fpr, tpr, _ = roc_curve(y_test, y_pred_proba)
    plt.figure(figsize=(8, 8))
    plt.plot(fpr, tpr, color='darkorange', lw=2, label=f'Curva ROC (AUC = {auc:.2f})')
    plt.plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
    plt.xlabel('Taxa de Falsos Positivos')
    plt.ylabel('Taxa de Verdadeiros Positivos')
    plt.title('Classificação de Gravidade a partir de Texto Clínico Livre')
    plt.legend(loc="lower right")
    caminho_fig = dir_saida / "roc_gravidade_texto_clinico.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"\n📈 Curva ROC salva em: {caminho_fig}")

    return pd.DataFrame(top_positivos + top_negativos, columns=['termo', 'coeficiente'])


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando dados do SINAN/ANIM para {args.anos} ---")
    df_raw = carregar_dados_anim(args.anos)
    print(f"✅ {len(df_raw)} notificações carregadas.")

    print(f"\n--- [ETAPA 2] Preparando texto clínico e alvo (COM_SISTEM) ---")
    df = preparar_dados(df_raw)
    print(f"✅ {len(df)} casos com texto e desfecho válidos. Taxa de complicação sistêmica: {df['GRAVE'].mean():.1%}")

    if len(df) < 100 or df['GRAVE'].nunique() < 2:
        print("❌ Dados insuficientes ou sem variação na variável alvo para treinar o classificador (mínimo recomendado: 100 casos com ambas as classes).")
        return

    print(f"\n--- [ETAPA 3] Treinando classificador de gravidade a partir do texto ---")
    df_termos = treinar_classificador(df, dir_saida)

    caminho_csv = dir_saida / "termos_associados_gravidade.csv"
    df_termos.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Termos mais associados à gravidade salvos em: '{caminho_csv}'")

    print("\n" + "=" * 80)
    print("🎉 CLASSIFICAÇÃO DE GRAVIDADE A PARTIR DE TEXTO CLÍNICO CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classifica o risco de complicação sistêmica a partir do texto clínico livre do SINAN/ANIM.")
    parser.add_argument("--anos", nargs="+", type=int, required=True, help="Anos de dados do SINAN/ANIM a usar.")
    parser.add_argument("--dir_saida", type=str, default="outputs/gravidade_texto_clinico", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
