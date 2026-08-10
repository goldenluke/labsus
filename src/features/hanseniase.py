# -*- coding: utf-8 -*-
import pandas as pd
import os
import argparse
from pysus.online_data.SINAN import SINAN
from ..utils.dataloaders import filtrar_populacao

def processar_dados(ufs, anos, arquivo_populacao, **kwargs):
    """
    Calcula a Taxa de Detecção de Casos Novos de Hanseníase por 100.000 habitantes,
    utilizando uma lógica de processamento de dados robusta e à prova de falhas.
    """
    resultados = []

    try:
        sinan_db = SINAN()
        sinan_db.load()
    except Exception as e:
        print(f"❌ Erro crítico ao carregar o banco de dados do SINAN: {e}")
        return pd.DataFrame()

    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Taxa de Detecção de Hanseníase: {uf}/{ano} ===")

            df_base = filtrar_populacao(
                arquivo_populacao=arquivo_populacao,
                uf=uf,
                ano=ano
            )
            if df_base is None:
                continue

            try:
                files = sinan_db.get_files(dis_code='HANS', year=ano)
                if not files:
                    raise FileNotFoundError(f"Nenhum arquivo SINAN/HANS encontrado para o ano {ano}")

                downloaded_data = sinan_db.download(files)

                # ✅ --- CORREÇÃO FINAL: Lógica completa para tratar todos os retornos possíveis ---
                df_sinan = pd.DataFrame()
                if isinstance(downloaded_data, list):
                    # Caso 1: Retorna uma lista de Parquets
                    df_sinan = pd.concat([p.to_dataframe() for p in downloaded_data], ignore_index=True)
                elif hasattr(downloaded_data, "_parquets"):
                    # Caso 2: Retorna um objeto que contém a lista no atributo _parquets
                    df_sinan = pd.concat([p.to_dataframe() for p in downloaded_data._parquets], ignore_index=True)
                elif hasattr(downloaded_data, "to_dataframe"):
                    # Caso 3: Retorna um único objeto com método to_dataframe()
                    df_sinan = downloaded_data.to_dataframe()
                else:
                    raise TypeError("O objeto baixado do SINAN não é de um tipo esperado e não pôde ser convertido para DataFrame.")
                # --- FIM DA CORREÇÃO ---

                if df_sinan.empty:
                    raise ValueError("DataFrame do SINAN/HANS está vazio após o download.")

                # Filtros epidemiológicos (ano do diagnóstico e casos novos)
                df_sinan['DT_DIAG'] = pd.to_datetime(df_sinan['DT_DIAG'], errors='coerce')
                df_sinan.dropna(subset=['DT_DIAG'], inplace=True)
                df_sinan_ano = df_sinan[df_sinan['DT_DIAG'].dt.year == ano].copy()

                df_casos_novos = df_sinan_ano
                if 'MODOENTR' in df_sinan_ano.columns:
                    df_casos_novos = df_sinan_ano[df_sinan_ano['MODOENTR'].astype(str) == '1'].copy()

                # Filtro por UF de residência
                uf_code_str = df_base.index.str[:2].unique()[0]
                df_casos_novos_uf = df_casos_novos[df_casos_novos['ID_MN_RESI'].astype(str).str.startswith(uf_code_str)]

                # Contagem dos casos
                casos = df_casos_novos_uf.groupby('ID_MN_RESI').size().rename("casos_novos_hanseniase")
                casos.index = casos.index.astype(str).str[:6]

            except Exception as e:
                print(f"⚠️ Erro ao baixar ou processar dados do SINAN para {uf}/{ano}: {e}")
                casos = pd.Series(dtype=int, name="casos_novos_hanseniase")

            # --- Junção e Cálculo do Indicador ---
            df = df_base.join(casos, how="left").fillna(0)
            df['casos_novos_hanseniase'] = df['casos_novos_hanseniase'].astype(int)
            df['TAXA_DETECCAO_HANSENIASE'] = df.apply(
                lambda r: (r.casos_novos_hanseniase / r.populacao * 100000) if r.populacao > 0 else 0,
                axis=1
            )
            df['UF'] = uf
            if 'ano' in df.columns:
                df.rename(columns={'ano': 'ANO'}, inplace=True)
            else:
                 df['ANO'] = ano

            resultados.append(df.reset_index())


    if resultados:
        df_final = pd.concat(resultados, ignore_index=True)
        print("\n✅ Taxa de Detecção de Hanseníase processada com sucesso.")
        return df_final
    else:
        print("\n⚠️ Nenhum dado de Hanseníase foi processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Calcula a Taxa de Detecção de Hanseníase para múltiplos estados e anos.")
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs (ex: TO PA MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos (ex: 2021 2022)")
    parser.add_argument("--pop", type=str, default="outputs/csv/populacao_estimada_completa_spline.csv", help="Caminho para o arquivo CSV com dados populacionais.")
    parser.add_argument("--saida", type=str, default=None, help="Caminho do arquivo CSV de saída.")

    args = parser.parse_args()

    df_resultado = processar_dados(
        ufs=args.ufs,
        anos=args.anos,
        arquivo_populacao=args.pop,
    )

    if not df_resultado.empty:
        caminho_saida_csv = args.saida

        if caminho_saida_csv is None:
            # Caminho para a raiz do projeto
            raiz_projeto = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

            # Caminho final em dados/processados
            output_dir = os.path.join(raiz_projeto, "dados", "processados", "indicadores")
            os.makedirs(output_dir, exist_ok=True)

            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            nome_arquivo = f"taxa_hanseniase_{ufs_str}_{anos_str}.csv"
            caminho_saida_csv = os.path.join(output_dir, nome_arquivo)

        df_resultado.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 CSV com os resultados salvo em: '{caminho_saida_csv}'")
    else:
        print("\n⚠️ Nenhum resultado final foi gerado para salvar.")

