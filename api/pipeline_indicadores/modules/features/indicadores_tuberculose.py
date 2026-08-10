# -*- coding: utf-8 -*-
# Arquivo: src/features/indicadores_tuberculose.py

import pandas as pd
import argparse
from pathlib import Path
from typing import List

# Importa as funções de download e utilitários
from pysus.online_data.SINAN import SINAN
from ..utils.dataloaders import filtrar_populacao

# --- CÓDIGOS DE CLASSIFICAÇÃO PARA TUBERCULOSE NO SINAN ---
# TP_NOT (Tipo de Notificação/Entrada): Define se é um caso novo
# 1: Caso Novo, 2: Recidiva, 3: Reingresso após abandono
CODIGOS_CASO_NOVO = ['1', '2', '3']

# SITUA_ENCE (Situação de Encerramento): Define o desfecho do caso
# 1: Cura, 2: Abandono, 3: Óbito por TB, 4: Óbito por outra causa, 5: Transferência, 7: Mudança de esquema
CODIGO_CURA = '1'
CODIGO_ABANDONO = '2'


def processar_dados(ufs, anos, arquivo_populacao, **kwargs):
    """
    Calcula os principais indicadores de Tuberculose (Incidência, Abandono e Cura).
    """
    resultados_finais_por_ano = []

    try:
        sinan_db = SINAN().load()
    except Exception as e:
        print(f"❌ Erro crítico ao carregar o banco de dados do SINAN: {e}")
        return pd.DataFrame()

    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Indicadores de Tuberculose em {uf}/{ano} ===")

            df_ano_base = filtrar_populacao(
                arquivo_populacao=arquivo_populacao,
                uf=uf,
                ano=ano
            )
            if df_ano_base is None:
                continue

            try:
                files = sinan_db.get_files(dis_code='TUBE', year=ano)
                if not files:
                    raise FileNotFoundError(f"Nenhum arquivo SINAN/TUBE encontrado para o ano {ano}")

                downloaded_data = sinan_db.download(files)

                df_sinan = pd.DataFrame()
                if isinstance(downloaded_data, list):
                    df_sinan = pd.concat([p.to_dataframe() for p in downloaded_data], ignore_index=True)
                elif hasattr(downloaded_data, "to_dataframe"):
                    df_sinan = downloaded_data.to_dataframe()

                if df_sinan.empty:
                    raise ValueError("DataFrame do SINAN/TUBE está vazio.")

                # --- LÓGICA DE CÁLCULO DOS INDICADORES (CORRIGIDA) ---

                # Converte colunas de código para numérico para uma filtragem robusta
                df_sinan['TP_NOT_NUM'] = pd.to_numeric(df_sinan['TP_NOT'], errors='coerce').fillna(0).astype(int)
                df_sinan['SITUA_ENCE_NUM'] = pd.to_numeric(df_sinan['SITUA_ENCE'], errors='coerce').fillna(0).astype(int)

                CODIGOS_CASO_NOVO_NUM = [int(c) for c in CODIGOS_CASO_NOVO]
                CODIGO_CURA_NUM = int(CODIGO_CURA)
                CODIGO_ABANDONO_NUM = int(CODIGO_ABANDONO)

                # 1. Filtra por casos novos e pela UF de RESIDÊNCIA
                df_casos_novos = df_sinan[df_sinan['TP_NOT_NUM'].isin(CODIGOS_CASO_NOVO_NUM)]
                uf_code_str = df_ano_base.index.str[:2].unique()[0]
                df_casos_novos_uf = df_casos_novos[df_casos_novos['ID_MN_RESI'].astype(str).str.startswith(uf_code_str)].copy()

                # 2. Agrega o total de casos novos por município de RESIDÊNCIA
                casos_novos_agg = df_casos_novos_uf.groupby('ID_MN_RESI').size().rename("casos_novos_tb")
                casos_novos_agg.index = casos_novos_agg.index.astype(str).str[:6]
                print(f"    -> {casos_novos_agg.sum()} casos novos de Tuberculose encontrados.")

                # 3. Agrega casos de abandono e cura a partir dos casos novos
                casos_abandono_agg = df_casos_novos_uf[df_casos_novos_uf['SITUA_ENCE_NUM'] == CODIGO_ABANDONO_NUM].groupby('ID_MN_RESI').size().rename("casos_abandono_tb")
                casos_abandono_agg.index = casos_abandono_agg.index.astype(str).str[:6]

                casos_cura_agg = df_casos_novos_uf[df_casos_novos_uf['SITUA_ENCE_NUM'] == CODIGO_CURA_NUM].groupby('ID_MN_RESI').size().rename("casos_cura_tb")
                casos_cura_agg.index = casos_cura_agg.index.astype(str).str[:6]

            except Exception as e:
                print(f"⚠️ Erro ao processar Tuberculose para {uf}/{ano}: {e}")
                casos_novos_agg = pd.Series(dtype=int, name="casos_novos_tb")
                casos_abandono_agg = pd.Series(dtype=int, name="casos_abandono_tb")
                casos_cura_agg = pd.Series(dtype=int, name="casos_cura_tb")

            # --- JUNÇÃO E CÁLCULO FINAL ---
            df = df_ano_base.join(casos_novos_agg, how="left")
            df = df.join(casos_abandono_agg, how="left")
            df = df.join(casos_cura_agg, how="left")

            cols_to_fill = ["casos_novos_tb", "casos_abandono_tb", "casos_cura_tb"]
            df[cols_to_fill] = df[cols_to_fill].fillna(0).astype(int)

            # Calcula as taxas
            df['TAXA_INCIDENCIA_TB'] = df.apply(lambda r: (r.casos_novos_tb / r.populacao * 100000) if r.populacao > 0 else 0, axis=1)
            df['TAXA_ABANDONO_TB'] = df.apply(lambda r: (r.casos_abandono_tb / r.casos_novos_tb * 100) if r.casos_novos_tb > 0 else 0, axis=1)
            df['TAXA_CURA_TB'] = df.apply(lambda r: (r.casos_cura_tb / r.casos_novos_tb * 100) if r.casos_novos_tb > 0 else 0, axis=1)

            df['UF'] = uf
            resultados_finais_por_ano.append(df.reset_index())


    if resultados_finais_por_ano:
        df_final = pd.concat(resultados_finais_por_ano, ignore_index=True)
        print("\n✅ Indicadores de Tuberculose processados com sucesso.")
        return df_final
    else:
        print("⚠️ Nenhum dado de Tuberculose foi processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula os principais indicadores de Tuberculose (Incidência, Abandono, Cura).")

    RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent

    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs (ex: TO PA MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos (ex: 2022 2023)")

    caminho_pop_padrao = RAIZ_PROJETO / "dados" / "processados" / "populacao_estimada_completa_spline.csv"
    parser.add_argument("--pop", type=str, default=str(caminho_pop_padrao), help="Arquivo CSV com população municipal")

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
            output_dir = RAIZ_PROJETO / "dados" / "processados" / "indicadores"
            output_dir.mkdir(parents=True, exist_ok=True)

            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            nome_arquivo = f"indicadores_tuberculose_{ufs_str}_{anos_str}.csv"
            caminho_saida_csv = output_dir / nome_arquivo

        df_resultado.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 CSV salvo em: '{caminho_saida_csv}'")
    else:
        print("⚠️ Nenhum resultado para salvar.")
