# -*- coding: utf-8 -*-
# Arquivo: src/features/incidencia_arboviroses.py

import pandas as pd
import argparse
from pathlib import Path
from typing import List, Union

from pysus.online_data.SINAN import SINAN
from ..utils.dataloaders import filtrar_populacao

# --- DICIONÁRIO DE ARBOVIROSES E SEUS CÓDIGOS NO SINAN ---
ARBOVIROSES_SINAN = {
    "dengue": "DENG",
    "chikungunya": "CHIK",
    "zika": "ZIKA"
}

# Códigos de classificação final (CLASSI_FIN) que indicam um caso confirmado
CODIGOS_CONFIRMADOS = {
    "DENG": ['10', '11', '12'],          # Dengue, Dengue com sinais de alarme, Dengue grave
    "CHIK": ['2', '3', '10', '11', '12'], # Laboratorial, Clínico-Epidemiológico, Chikungunya (variantes)
    "ZIKA": ['1']                        # Zika confirmado
}

def processar_dados(ufs, anos, arquivo_populacao, doencas, **kwargs):
    """
    Calcula a taxa de incidência para uma ou mais arboviroses (Dengue, Zika, Chikungunya),
    gerando colunas separadas para cada uma. Versão com guardas defensivas contra
    downloads vazios/ausentes (sincronizada com api/pipeline_indicadores).
    """
    resultados_finais_por_ano = []

    doencas_lista = [doencas] if isinstance(doencas, str) else doencas

    for doenca in doencas_lista:
        if doenca not in ARBOVIROSES_SINAN:
            print(f"❌ Erro: Doença '{doenca}' não reconhecida. Opções válidas: {list(ARBOVIROSES_SINAN.keys())}")
            return pd.DataFrame()

    try:
        sinan_db = SINAN().load()
    except Exception as e:
        print(f"❌ Erro crítico ao carregar o banco de dados do SINAN: {e}")
        return pd.DataFrame()

    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Arboviroses em {uf}/{ano} ===")

            df_ano_base = filtrar_populacao(
                arquivo_populacao=arquivo_populacao,
                uf=uf,
                ano=ano
            )
            if df_ano_base is None or df_ano_base.empty:
                print(f"⚠️ Aviso: Dados de população não encontrados ou vazios para {uf}/{ano}. Pulando este ano/UF.")
                continue

            for doenca in doencas_lista:
                print(f"  -> Calculando para: '{doenca.title()}'")
                dis_code = ARBOVIROSES_SINAN[doenca]

                try:
                    files = sinan_db.get_files(dis_code=dis_code, year=ano)
                    if not files:
                        print(f"⚠️ Aviso: Nenhum arquivo SINAN/{dis_code} encontrado para o ano {ano}. Casos serão zero.")
                        casos_agregados = pd.Series(dtype=int, name=f"casos_{doenca}")

                    else:
                        downloaded_data = sinan_db.download(files)

                        df_sinan = pd.DataFrame()
                        if isinstance(downloaded_data, list):
                            df_sinan = pd.concat([p.to_dataframe() for p in downloaded_data], ignore_index=True)
                        elif hasattr(downloaded_data, "to_dataframe"):
                            df_sinan = downloaded_data.to_dataframe()

                        if df_sinan.empty:
                            print(f"⚠️ Aviso: DataFrame do SINAN/{dis_code} está vazio após download. Casos serão zero.")
                            casos_agregados = pd.Series(dtype=int, name=f"casos_{doenca}")

                        else:
                            codigos_confirmacao_num = [int(c) for c in CODIGOS_CONFIRMADOS.get(dis_code, [])]

                            df_sinan['CLASSI_FIN_NUM'] = pd.to_numeric(df_sinan['CLASSI_FIN'], errors='coerce').fillna(0).astype(int)

                            df_confirmados = df_sinan[df_sinan['CLASSI_FIN_NUM'].isin(codigos_confirmacao_num)]

                            print(f"    -> {len(df_confirmados)} casos confirmados encontrados para {doenca.title()}.")

                            df_confirmados = df_confirmados.copy()
                            df_confirmados['ID_MN_RESI_6'] = df_confirmados['ID_MN_RESI'].astype(str).str[:6]
                            casos_agregados = df_confirmados.groupby('ID_MN_RESI_6').size().rename(f"casos_{doenca}")
                            casos_agregados.index.name = 'cod_mun_ibge_6'

                except Exception as e:
                    print(f"❌ ERRO GRAVE ao processar {doenca} para {uf}/{ano}: {e}")
                    casos_agregados = pd.Series(dtype=int, name=f"casos_{doenca}")

                # Garante que o índice de df_ano_base é 'cod_mun_ibge_6' antes do join
                if df_ano_base.index.name != 'cod_mun_ibge_6':
                    df_ano_base = df_ano_base.reset_index().set_index('cod_mun_ibge_6')

                df_ano_base = df_ano_base.join(casos_agregados, how="left")
                df_ano_base[f"casos_{doenca}"] = df_ano_base[f"casos_{doenca}"].fillna(0).astype(int)

                nome_coluna_taxa = f"TAXA_INCID_{doenca.upper()}"
                df_ano_base[nome_coluna_taxa] = df_ano_base.apply(
                    lambda r: (r[f"casos_{doenca}"] / r.populacao * 100000) if r.populacao > 0 else 0, axis=1)

            df_ano_base['UF'] = uf
            resultados_finais_por_ano.append(df_ano_base.reset_index())

    if resultados_finais_por_ano:
        df_final = pd.concat(resultados_finais_por_ano, ignore_index=True)
        print("\n✅ Processamento de arboviroses concluído com sucesso.")
        return df_final
    else:
        print("⚠️ Nenhum dado de arboviroses foi processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula a Taxa de Incidência para uma ou mais arboviroses.")

    RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent

    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs (ex: TO PA MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos (ex: 2022 2023)")

    parser.add_argument("--doenca", nargs="+", default=list(ARBOVIROSES_SINAN.keys()), choices=list(ARBOVIROSES_SINAN.keys()),
                        help="Uma ou mais arboviroses a serem processadas. Padrão: todas.")

    caminho_pop_padrao = RAIZ_PROJETO / "dados" / "processados" / "populacao_estimada_completa_spline.csv"
    parser.add_argument("--pop", type=str, default=str(caminho_pop_padrao), help="Arquivo CSV com população municipal")

    parser.add_argument("--saida", type=str, default=None, help="Caminho completo do arquivo CSV de saída.")

    args = parser.parse_args()

    df_resultado = processar_dados(
        ufs=args.ufs,
        anos=args.anos,
        doencas=args.doenca,
        arquivo_populacao=args.pop,
    )

    if not df_resultado.empty:
        caminho_saida_csv = args.saida
        if caminho_saida_csv is None:
            output_dir = RAIZ_PROJETO / "dados" / "processados" / "indicadores"
            output_dir.mkdir(parents=True, exist_ok=True)

            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            doenca_str = "-".join(sorted(args.doenca))
            nome_arquivo = f"incidencia_{doenca_str}_{ufs_str}_{anos_str}.csv"
            caminho_saida_csv = output_dir / nome_arquivo

        df_resultado.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 CSV salvo em: '{caminho_saida_csv}'")
    else:
        print("⚠️ Nenhum resultado para salvar.")
