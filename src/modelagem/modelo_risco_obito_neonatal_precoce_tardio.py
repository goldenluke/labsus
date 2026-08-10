# -*- coding: utf-8 -*-
"""
======================================================================
  ÓBITO NEONATAL PRECOCE (0-6 DIAS) vs. TARDIO (7-27 DIAS): FATORES
======================================================================
A mortalidade neonatal precoce (0-6 dias de vida) e a tardia (7-27 dias)
têm mecanismos causais clinicamente distintos e bem documentados na
literatura: óbitos PRECOCES concentram-se em prematuridade extrema,
malformações congênitas e complicações do parto; óbitos TARDIOS
concentram-se mais em infecções adquiridas, problemas de continuidade do
cuidado pós-alta e acesso a serviços. Tratar os dois como um único
"óbito neonatal" (como em `analise_sobrevida_infantil.py`) mistura essas
duas histórias diferentes.

Este script vincula nascimentos (SINASC) a óbitos (SIM) como em
`analise_sobrevida_infantil.py`, mas retém a DATA exata do óbito para
calcular a idade precisa em dias e treina um classificador
(LightGBM + SHAP) que distingue PRECOCE de TARDIO entre os óbitos
neonatais observados — apontando quais fatores clínicos/assistenciais
diferenciam os dois padrões.
"""

import argparse
from pathlib import Path

import pandas as pd
import recordlinkage
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
import lightgbm as lgb
import shap
import matplotlib.pyplot as plt

from src.modelagem.analise_sobrevida_infantil import carregar_dados


def vincular_com_data_obito(df_sinasc: pd.DataFrame, df_sim: pd.DataFrame) -> pd.DataFrame:
    """Vincula nascimentos a óbitos neonatais (0-27 dias) preservando DTOBITO,
    para calcular a idade exata em dias no momento do óbito."""
    if df_sim is None or df_sim.empty:
        return pd.DataFrame()

    df_sim_infantil = df_sim[pd.to_numeric(df_sim['IDADE'], errors='coerce') < 401].copy()
    if df_sim_infantil.empty:
        return pd.DataFrame()

    df_nasc = df_sinasc[['CODMUNRES', 'DTNASC']].reset_index().rename(columns={'index': 'rec_id_nasc'})
    df_obit = df_sim_infantil[['CODMUNRES', 'DTNASC', 'DTOBITO']].reset_index().rename(columns={'index': 'rec_id_obit'})
    df_nasc.set_index('rec_id_nasc', inplace=True)
    df_obit_idx = df_obit.set_index('rec_id_obit')

    indexer = recordlinkage.Index()
    indexer.block('CODMUNRES')
    candidate_links = indexer.index(df_nasc, df_obit_idx)
    if len(candidate_links) == 0:
        return pd.DataFrame()

    compare_cls = recordlinkage.Compare()
    compare_cls.exact('DTNASC', 'DTNASC', label='DTNASC')
    features = compare_cls.compute(candidate_links, df_nasc, df_obit_idx)
    matches = features[features.sum(axis=1) >= 1]

    pares = matches.index.to_frame(index=False)
    pares.columns = ['rec_id_nasc', 'rec_id_obit']
    df_vinculado = df_sinasc.loc[pares['rec_id_nasc']].reset_index(drop=True)
    df_vinculado['DTOBITO'] = df_obit.set_index('rec_id_obit').loc[pares['rec_id_obit'], 'DTOBITO'].values
    return df_vinculado


def preparar_dados(df_vinculado: pd.DataFrame) -> pd.DataFrame:
    df = df_vinculado.copy()
    df['DTNASC_DT'] = pd.to_datetime(df['DTNASC'], format='%d%m%Y', errors='coerce')
    df['DTOBITO_DT'] = pd.to_datetime(df['DTOBITO'], format='%d%m%Y', errors='coerce')
    df['IDADE_OBITO_DIAS'] = (df['DTOBITO_DT'] - df['DTNASC_DT']).dt.days

    df = df[(df['IDADE_OBITO_DIAS'] >= 0) & (df['IDADE_OBITO_DIAS'] <= 27)].copy()
    df['OBITO_PRECOCE'] = (df['IDADE_OBITO_DIAS'] <= 6).astype(int)

    features = ['PESO', 'GESTACAO', 'APGAR5', 'IDADEMAE', 'ESCMAE2010', 'CONSPRENAT', 'QTDFILVIVO', 'QTDFILMORT', 'PARTO', 'RACACORMAE']
    features_presentes = [c for c in features if c in df.columns]
    df_modelo = df[features_presentes + ['OBITO_PRECOCE']].copy()
    for col in features_presentes:
        df_modelo[col] = pd.to_numeric(df_modelo[col], errors='coerce')
    df_modelo = df_modelo.dropna(subset=features_presentes)
    return df_modelo


def treinar_modelo(df: pd.DataFrame, dir_saida: Path):
    y = df['OBITO_PRECOCE']
    X = df.drop(columns=['OBITO_PRECOCE'])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42, stratify=y)
    ratio = y_train.value_counts().get(0, 1) / max(y_train.value_counts().get(1, 1), 1)
    modelo = lgb.LGBMClassifier(objective='binary', random_state=42, scale_pos_weight=ratio)
    modelo.fit(X_train, y_train)

    y_pred = modelo.predict(X_test)
    y_pred_proba = modelo.predict_proba(X_test)[:, 1]
    print("\n--- Relatório de Classificação (Precoce vs. Tardio) ---")
    print(classification_report(y_test, y_pred, zero_division=0, target_names=['Tardio (7-27 dias)', 'Precoce (0-6 dias)']))
    auc = roc_auc_score(y_test, y_pred_proba)
    print(f"AUC: {auc:.4f}")

    feature_name_map = {
        'PESO': 'Peso ao Nascer (g)', 'GESTACAO': 'Semanas de Gestação (Faixa)', 'APGAR5': 'Apgar (5º Min)',
        'IDADEMAE': 'Idade da Mãe', 'ESCMAE2010': 'Escolaridade da Mãe', 'CONSPRENAT': 'Nº Consultas Pré-Natal',
        'QTDFILVIVO': 'Nº Filhos Vivos', 'QTDFILMORT': 'Nº Filhos Mortos', 'PARTO': 'Tipo de Parto', 'RACACORMAE': 'Raça/Cor da Mãe',
    }
    X_test_renomeado = X_test.rename(columns=feature_name_map)

    explainer = shap.TreeExplainer(modelo)
    shap_values = explainer.shap_values(X_test)
    shap_values_risco = shap_values[1] if isinstance(shap_values, list) else shap_values

    plt.figure()
    shap.summary_plot(shap_values_risco, X_test_renomeado, plot_type="bar", show=False)
    plt.title("Fatores que Diferenciam Óbito Neonatal Precoce de Tardio (SHAP)")
    plt.tight_layout()
    caminho_fig = dir_saida / "shap_precoce_vs_tardio.png"
    plt.savefig(caminho_fig, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Gráfico SHAP salvo em: {caminho_fig}")

    return modelo, auc


def main(args):
    dir_saida = Path(args.dir_saida)
    dir_saida.mkdir(parents=True, exist_ok=True)

    print(f"\n--- [ETAPA 1] Carregando SINASC/SIM para {args.uf}/{args.ano} ---")
    df_sinasc, df_sim, _ = carregar_dados(ufs=[args.uf], ano_coorte=args.ano)
    if df_sinasc is None or df_sinasc.empty:
        print("❌ Não foi possível carregar dados do SINASC.")
        return

    print(f"\n--- [ETAPA 2] Vinculando nascimentos a óbitos neonatais (preservando data do óbito) ---")
    df_vinculado = vincular_com_data_obito(df_sinasc, df_sim)
    if df_vinculado.empty:
        print("❌ Nenhum óbito neonatal vinculado. Abortando.")
        return
    print(f"✅ {len(df_vinculado)} óbitos neonatais vinculados.")

    print(f"\n--- [ETAPA 3] Classificando idade exata ao óbito (Precoce 0-6d / Tardio 7-27d) ---")
    df = preparar_dados(df_vinculado)
    print(f"✅ {len(df)} casos válidos. Proporção precoce: {df['OBITO_PRECOCE'].mean():.1%}")

    if len(df) < 50 or df['OBITO_PRECOCE'].nunique() < 2:
        print("❌ Dados insuficientes para treinar o modelo (mínimo recomendado: 50 óbitos, com ambos os tipos).")
        return

    print(f"\n--- [ETAPA 4] Treinando classificador ---")
    treinar_modelo(df, dir_saida)

    # Município é recuperado de df_vinculado (via o índice preservado por preparar_dados)
    # só para a saída — não entra em df/treinar_modelo para não virar feature do modelo.
    from src.utils.dataloaders import adicionar_nome_municipio
    df_saida = df.copy()
    df_saida.insert(0, 'CODMUNRES', df_vinculado.loc[df_saida.index, 'CODMUNRES'].astype(str).str[:6])
    df_saida = adicionar_nome_municipio(df_saida, 'CODMUNRES', args.populacao)

    caminho_csv = dir_saida / f"obitos_neonatais_precoce_tardio_{args.uf.lower()}_{args.ano}.csv"
    df_saida.to_csv(caminho_csv, index=False, sep=';', encoding='utf-8-sig')
    print(f"\n📄 Dados salvos em: '{caminho_csv}'")

    print("\n" + "=" * 80)
    print("🎉 ANÁLISE DE ÓBITO NEONATAL PRECOCE vs. TARDIO CONCLUÍDA! 🎉")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Diferencia fatores de risco de óbito neonatal precoce (0-6d) vs. tardio (7-27d).")
    parser.add_argument("--uf", type=str, required=True, help="UF a analisar.")
    parser.add_argument("--ano", type=int, required=True, help="Ano da coorte de nascimentos.")
    parser.add_argument("--populacao", type=str, default="referencia/populacao/populacao_estimada_completa_spline.csv", help="Caminho para o CSV de população estimada (usado para mapear nomes de município).")
    parser.add_argument("--dir_saida", type=str, default="outputs/obito_neonatal_precoce_tardio", help="Diretório para salvar os resultados.")
    args = parser.parse_args()
    main(args)
