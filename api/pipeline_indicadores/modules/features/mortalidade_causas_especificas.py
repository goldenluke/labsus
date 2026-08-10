# -*- coding: utf-8 -*-
# Arquivo: src/features/mortalidade_causas_especificas.py

import pandas as pd
import argparse
from pathlib import Path
from typing import List, Union

# Importa as funções de download e utilitários
from pysus.online_data.SIM import download as download_sim
from ..utils.dataloaders import filtrar_populacao

# --- DICIONÁRIO DE GRUPOS DE CAUSAS ESPECÍFICAS (CID-10) ---
GRUPOS_CID10 = {
    "circulatorio": ['I'],
    "neoplasias": ['C'],
    "respiratorias": ['J'],
    "diabetes": ['E10', 'E11', 'E12', 'E13', 'E14'],
    "externas": ['V', 'W', 'X', 'Y'],
    "covid19": ['U071', 'U072', 'B342']
}

def processar_dados(ufs, anos, arquivo_populacao, causa_grupo, **kwargs):
    """
    Calcula a taxa de mortalidade para um ou mais grupos de causas específicas.
    """
    resultados_finais = []
    causa_grupo_lista = [causa_grupo] if isinstance(causa_grupo, str) else causa_grupo

    for grupo in causa_grupo_lista:
        if grupo not in GRUPOS_CID10:
            print(f"❌ Erro: Grupo de causa '{grupo}' não reconhecido.")
            return pd.DataFrame()

    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando UF: {uf} / Ano: {ano} ===")

            df_ano_base = filtrar_populacao(
                arquivo_populacao=arquivo_populacao, uf=uf, ano=ano
            )
            if df_ano_base is None:
                continue

            try:
                print("[LOG] Baixando dados do SIM...")
                sim_raw = download_sim(states=uf, years=ano, groups=["CID10"])
                # download_sim pode retornar um único ParquetSet, uma lista deles ou uma
                # lista vazia quando a competência ainda não foi publicada pelo DATASUS.
                if isinstance(sim_raw, list):
                    if not sim_raw:
                        raise FileNotFoundError(f"Nenhum arquivo SIM disponível para {ano} (dado ainda não publicado).")
                    df_sim = pd.concat([p.to_dataframe() for p in sim_raw], ignore_index=True)
                else:
                    df_sim = sim_raw.to_dataframe()
                print("[LOG] Dados do SIM baixados com sucesso.")
            except Exception as e:
                # Mantém o UF/ano no resultado final (com contagens zeradas) em vez de
                # descartá-lo silenciosamente — falha de download não deve virar "0
                # municípios processados", e sim "0 óbitos processados".
                print(f"⚠️ Erro ao baixar ou processar SIM para {uf}/{ano}: {e}.")
                df_sim = pd.DataFrame(columns=["CAUSABAS", "CODMUNRES"])

            # --- CORREÇÃO NA LÓGICA DE AGREGAÇÃO ---
            # Inicia o DataFrame com os dados base de população
            df_ano_com_causas = df_ano_base.copy()

            # Itera sobre cada grupo de causa e adiciona as colunas ao mesmo DataFrame
            for grupo in causa_grupo_lista:
                print(f"  -> Calculando para o grupo: '{grupo.title()}'")
                codigos_cid = GRUPOS_CID10[grupo]

                # Normaliza a coluna CAUSABAS para uma comparação robusta
                df_sim['CAUSABAS_NORM'] = df_sim['CAUSABAS'].str.replace('.', '', regex=False).str.strip()

                if grupo == 'covid19':
                    df_causa_especifica = df_sim[df_sim['CAUSABAS_NORM'].isin(codigos_cid)].copy()
                else:
                    prefixos = tuple(codigos_cid)
                    df_causa_especifica = df_sim[df_sim['CAUSABAS_NORM'].str.startswith(prefixos, na=False)].copy()

                print(f"[DEBUG] Grupo '{grupo}': {len(df_causa_especifica)} óbitos encontrados.")

                nome_coluna_obitos = f"obitos_{grupo}"
                obitos_especificos = df_causa_especifica.groupby("CODMUNRES").size().rename(nome_coluna_obitos)
                obitos_especificos.index = obitos_especificos.index.astype(str).str[:6]

                df_ano_com_causas = df_ano_com_causas.join(obitos_especificos, how="left")
                df_ano_com_causas[nome_coluna_obitos] = df_ano_com_causas[nome_coluna_obitos].fillna(0).astype(int)

                nome_coluna_taxa = f"TAXA_MORT_{grupo.upper()}"
                df_ano_com_causas[nome_coluna_taxa] = df_ano_com_causas.apply(
                    lambda r: (r[nome_coluna_obitos] / r.populacao * 100000) if r.populacao > 0 else 0, axis=1)


            df_ano_com_causas['UF'] = uf
            resultados_finais.append(df_ano_com_causas.reset_index())

    if resultados_finais:
        df_final = pd.concat(resultados_finais, ignore_index=True)
        print("\n✅ Processamento de todas as causas e anos concluído com sucesso.")
        return df_final
    else:
        print("⚠️ Nenhum dado foi processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula a Taxa de Mortalidade por Causas Específicas.")
    RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs (ex: TO PA MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos (ex: 2022 2023)")
    parser.add_argument("--causa", nargs="+", default=list(GRUPOS_CID10.keys()), choices=list(GRUPOS_CID10.keys()),
                        help="Um ou mais grupos de causa específica a serem processados. Padrão: todos os grupos.")
    caminho_pop_padrao = RAIZ_PROJETO / "dados" / "processados" / "populacao_estimada_completa_spline.csv"
    parser.add_argument("--pop", type=str, default=str(caminho_pop_padrao), help="Arquivo CSV com população municipal")
    parser.add_argument("--saida", type=str, default=None, help="Caminho completo do arquivo CSV de saída.")
    caminho_mapas_padrao = RAIZ_PROJETO / "outputs" / "figures"
    args = parser.parse_args()

    df_resultado = processar_dados(
        ufs=args.ufs,
        anos=args.anos,
        causa_grupo=args.causa,
        arquivo_populacao=args.pop,
    )

    if not df_resultado.empty:
        caminho_saida_csv = args.saida
        if caminho_saida_csv is None:
            output_dir = RAIZ_PROJETO / "dados" / "processados" / "indicadores"
            output_dir.mkdir(parents=True, exist_ok=True)
            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            causa_str = "-".join(sorted(args.causa))
            nome_arquivo = f"mortalidade_{causa_str}_{ufs_str}_{anos_str}.csv"
            caminho_saida_csv = output_dir / nome_arquivo

        df_resultado.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 CSV salvo em: '{caminho_saida_csv}'")
    else:
        print("⚠️ Nenhum resultado para salvar.")
