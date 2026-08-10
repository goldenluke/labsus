# -*- coding: utf-8 -*-
# Arquivo: src/features/mortalidade_prematura_dcnt.py

import pandas as pd
import os
import argparse
from pathlib import Path

# Importa as funções de download e utilitários
from pysus.online_data.SIM import download as download_sim
from ..utils.dataloaders import filtrar_populacao

# --- LISTA DE CIDs PARA DOENÇAS CRÔNICAS NÃO TRANSMISSÍVEIS (DCNT) ---
# Baseado nas definições da OMS para monitoramento de mortalidade prematura.
DCNT_CID10 = [
    # Neoplasias Malignas (Câncer)
    'C00', 'C01', 'C02', 'C03', 'C04', 'C05', 'C06', 'C07', 'C08', 'C09',
    'C10', 'C11', 'C12', 'C13', 'C14', 'C15', 'C16', 'C17', 'C18', 'C19',
    'C20', 'C21', 'C22', 'C23', 'C24', 'C25', 'C26', 'C30', 'C31', 'C32',
    'C33', 'C34', 'C37', 'C38', 'C39', 'C40', 'C41', 'C43', 'C44', 'C45',
    'C46', 'C47', 'C48', 'C49', 'C50', 'C51', 'C52', 'C53', 'C54', 'C55',
    'C56', 'C57', 'C58', 'C60', 'C61', 'C62', 'C63', 'C64', 'C65', 'C66',
    'C67', 'C68', 'C69', 'C70', 'C71', 'C72', 'C73', 'C74', 'C75', 'C76',
    'C77', 'C78', 'C79', 'C80', 'C81', 'C82', 'C83', 'C84', 'C85', 'C88',
    'C90', 'C91', 'C92', 'C93', 'C94', 'C95', 'C96', 'C97',
    # Diabetes Mellitus
    'E10', 'E11', 'E12', 'E13', 'E14',
    # Doenças do Aparelho Circulatório
    'I00', 'I01', 'I02', 'I05', 'I06', 'I07', 'I08', 'I09', 'I10', 'I11',
    'I12', 'I13', 'I15', 'I20', 'I21', 'I22', 'I23', 'I24', 'I25', 'I26',
    'I27', 'I28', 'I30', 'I31', 'I32', 'I33', 'I34', 'I35', 'I36', 'I37',
    'I38', 'I39', 'I40', 'I41', 'I42', 'I43', 'I44', 'I45', 'I46', 'I47',
    'I48', 'I49', 'I50', 'I51', 'I60', 'I61', 'I62', 'I63', 'I64', 'I65',
    'I66', 'I67', 'I68', 'I69', 'I70', 'I71', 'I72', 'I73', 'I74', 'I77',
    'I78', 'I80', 'I81', 'I82', 'I83', 'I84', 'I85', 'I86', 'I87', 'I88',
    'I89', 'I95', 'I96', 'I97', 'I98', 'I99',
    # Doenças Respiratórias Crônicas
    'J30', 'J31', 'J32', 'J33', 'J34', 'J35', 'J36', 'J37', 'J38', 'J39',
    'J40', 'J41', 'J42', 'J43', 'J44', 'J45', 'J46', 'J47', 'J60', 'J61',
    'J62', 'J63', 'J64', 'J65', 'J66', 'J67', 'J68', 'J69', 'J70', 'J80',
    'J81', 'J82', 'J84', 'J85', 'J86', 'J90', 'J91', 'J92', 'J93', 'J94',
    'J95', 'J96', 'J98'
]

def processar_dados(ufs, anos, arquivo_populacao, **kwargs):
    """
    Calcula a taxa de mortalidade prematura (30 a 69 anos) por Doenças Crônicas
    Não Transmissíveis (DCNT) para múltiplas UFs e anos.
    """
    resultados = []

    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Mortalidade Prematura por DCNT: {uf}/{ano} ===")

            df_base = filtrar_populacao(
                arquivo_populacao=arquivo_populacao,
                uf=uf,
                ano=ano
            )
            if df_base is None:
                continue

            try:
                sim_raw = download_sim(states=uf, years=ano, groups=["CID10"])
                # download_sim pode retornar um único ParquetSet, uma lista deles ou uma
                # lista vazia quando a competência ainda não foi publicada pelo DATASUS.
                if isinstance(sim_raw, list):
                    if not sim_raw:
                        raise FileNotFoundError(f"Nenhum arquivo SIM disponível para {ano} (dado ainda não publicado).")
                    df_sim = pd.concat([p.to_dataframe() for p in sim_raw], ignore_index=True)
                else:
                    df_sim = sim_raw.to_dataframe()

                # --- FILTROS ESPECÍFICOS PARA O INDICADOR ---

                # 1. Filtra por faixa etária prematura (30 a 69 anos)
                # O campo IDADE no SIM é codificado. '4' indica anos.
                df_sim['IDADE'] = pd.to_numeric(df_sim['IDADE'], errors='coerce')
                df_prem = df_sim[(df_sim['IDADE'] >= 430) & (df_sim['IDADE'] <= 469)].copy()

                # 2. Filtra pelas causas básicas que são DCNT
                # Usamos os 3 primeiros caracteres do CID para abranger as subcategorias
                dcnt_prefixos = list(set([cid[:3] for cid in DCNT_CID10]))
                df_prem_dcnt = df_prem[df_prem['CAUSABAS'].str[:3].isin(dcnt_prefixos)]

                # 3. Agrega os óbitos por município de residência
                obitos_dcnt = df_prem_dcnt.groupby("CODMUNRES").size().rename("obitos_prem_dcnt")
                obitos_dcnt.index = obitos_dcnt.index.astype(str).str[:6]

            except Exception as e:
                print(f"⚠️ Erro ao baixar ou processar SIM para {uf}/{ano}: {e}")
                obitos_dcnt = pd.Series(dtype=int, name="obitos_prem_dcnt")

            # --- JUNÇÃO E CÁLCULO DO INDICADOR ---
            df = df_base.join(obitos_dcnt, how="left").fillna(0)
            df['obitos_prem_dcnt'] = df['obitos_prem_dcnt'].astype(int)

            # Calcula a taxa por 100.000 habitantes
            df['TAXA_MORT_PREM_DCNT'] = df.apply(
                lambda r: (r.obitos_prem_dcnt / r.populacao * 100000) if r.populacao > 0 else 0, axis=1)

            df['UF'] = uf
            resultados.append(df.reset_index())


    if resultados:
        df_final = pd.concat(resultados, ignore_index=True)
        print("\n✅ Mortalidade Prematura por DCNT processada com sucesso.")
        return df_final
    else:
        print("⚠️ Nenhum dado de mortalidade prematura por DCNT foi processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula a Taxa de Mortalidade Prematura por DCNT.")

    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs (ex: TO PA MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos (ex: 2022 2023)")
    parser.add_argument("--pop", type=str, default="estimativa_pop_spline.csv", help="Arquivo CSV com população municipal")
    parser.add_argument("--saida", type=str, default=None, help="Caminho completo do arquivo CSV de saída.")

    args = parser.parse_args()

    df_resultado = processar_dados(
        ufs=args.ufs,
        anos=args.anos,
        arquivo_populacao=args.pop,
    )

    if not df_resultado.empty:
        caminho_saida_csv = args.saida
        if caminho_saida_csv is None:
            # Lógica para salvar o arquivo na estrutura correta do projeto
            raiz_projeto = Path(__file__).resolve().parent.parent.parent
            output_dir = raiz_projeto / "dados" / "processados" / "indicadores"
            output_dir.mkdir(parents=True, exist_ok=True)

            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            nome_arquivo = f"mortalidade_prematura_dcnt_{ufs_str}_{anos_str}.csv"
            caminho_saida_csv = output_dir / nome_arquivo

        df_resultado.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 CSV salvo em: '{caminho_saida_csv}'")
    else:
        print("⚠️ Nenhum resultado para salvar.")
