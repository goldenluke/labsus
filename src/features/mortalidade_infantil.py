# -*- coding: utf-8 -*-
import pandas as pd
from pysus.online_data.SIM import download as download_sim
from pysus.online_data.SINASC import download as download_sinasc
from ..utils.dataloaders import filtrar_populacao

def processar_dados(ufs, anos, arquivo_populacao, **kwargs):
    """
    Calcula a Taxa de Mortalidade Infantil (TMI) para múltiplos estados e anos,
    gerando também mapas por UF/ano.
    """
    resultados = []
    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando TMI: {uf} / {ano} ===")

            df_base = filtrar_populacao(
                arquivo_populacao=arquivo_populacao,
                uf=uf,
                ano=ano
            )
            if df_base is None:
                continue

            # --- SIM: óbitos infantis ---
            try:
                sim_files = download_sim(states=uf, years=ano, groups=["CID10"])
                # download_sim pode retornar um único ParquetSet, uma lista deles ou uma
                # lista vazia quando a competência ainda não foi publicada pelo DATASUS.
                if isinstance(sim_files, list):
                    if not sim_files:
                        raise FileNotFoundError(f"Nenhum arquivo SIM disponível para {ano} (dado ainda não publicado).")
                    df_sim = pd.concat([p.to_dataframe() for p in sim_files], ignore_index=True)
                else:
                    df_sim = sim_files.to_dataframe()
                df_sim["IDADE"] = pd.to_numeric(df_sim["IDADE"], errors="coerce")
                df_inf = df_sim[df_sim["IDADE"] < 401]
                obitos = df_inf.groupby("CODMUNRES").size().rename("obitos_infantis")
                obitos.index = obitos.index.astype(str).str[:6]
            except Exception as e:
                print(f"⚠️ Erro SIM {uf}/{ano}: {e}")
                # ✅ CORREÇÃO: Garante que a Série vazia tenha um nome
                obitos = pd.Series(dtype=int, name="obitos_infantis")

            # --- SINASC: nascidos vivos ---
            try:
                sinasc_files = download_sinasc(states=uf, years=ano, groups=["DN"])
                if isinstance(sinasc_files, list) and len(sinasc_files) > 0:
                    df_sin = pd.concat([f.to_dataframe() for f in sinasc_files], ignore_index=True)
                elif hasattr(sinasc_files, "to_dataframe"):
                    df_sin = sinasc_files.to_dataframe()
                else: # Caso de não encontrar arquivos
                    raise ValueError("Nenhum arquivo SINASC encontrado.")

                nascidos = df_sin.groupby("CODMUNRES").size().rename("nascidos_vivos")
                nascidos.index = nascidos.index.astype(str).str[:6]
            except Exception as e:
                print(f"⚠️ Erro SINASC {uf}/{ano}: {e}")
                # ✅ CORREÇÃO: Garante que a Série vazia tenha um nome
                nascidos = pd.Series(dtype=int, name="nascidos_vivos")

            # junta e calcula TMI
            df_base = df_base.join(obitos, how="left").join(nascidos, how="left").fillna(0)
            df_base['obitos_infantis'] = df_base['obitos_infantis'].astype(int)
            df_base['nascidos_vivos']  = df_base['nascidos_vivos'].astype(int)
            df_base['TMI'] = df_base.apply(
                lambda r: (r['obitos_infantis']/r['nascidos_vivos']*1000) if r['nascidos_vivos']>0 else 0,
                axis=1
            )

            df_base['UF']  = uf

            resultados.append(df_base.reset_index())

    if resultados:
        df_final = pd.concat(resultados, ignore_index=True)
        print("\n✅ TMI (por mil nascidos vivos) processada com sucesso.")
        return df_final
    else:
        print("⚠️ Nenhum dado processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Calcula a Taxa de Mortalidade Infantil (TMI) por UF e ano.")
    parser.add_argument("--ufs", nargs="+", default=["TO", "GO"], help="Lista de UFs, ex: TO GO MG")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022, 2023], help="Lista de anos (ex: 2022 2023)")
    parser.add_argument("--pop", type=str, default="estimativa_pop_spline.csv", help="Arquivo CSV com população municipal")
    parser.add_argument("--saida", type=str, default=None, help="Caminho completo do arquivo CSV de saída.")

    args = parser.parse_args()

    df_tmi = processar_dados(args.ufs, args.anos, args.pop)

    if not df_tmi.empty:
        caminho_saida_csv = args.saida

        if caminho_saida_csv is None:
            # Caminho para a raiz do projeto
            dir_atual = os.path.dirname(__file__)

            # ✅ CORREÇÃO: Sobe DOIS NÍVEIS para chegar à raiz do projeto
            raiz_projeto = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

            # Caminho final em dados/processados
            output_dir = os.path.join(raiz_projeto, "dados", "processados", "indicadores")
            os.makedirs(output_dir, exist_ok=True)

            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            nome_arquivo = f"mortalidade_infantil_{ufs_str}_{anos_str}.csv"
            caminho_saida_csv = os.path.join(output_dir, nome_arquivo)

        df_tmi.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 CSV salvo em: '{caminho_saida_csv}'")
    else:
        print("⚠️ Nenhum resultado para salvar.")
