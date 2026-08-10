# -*- coding: utf-8 -*-
import pandas as pd
import os
import argparse
from pysus.online_data.SIM import download as download_sim
from ..utils.dataloaders import filtrar_populacao

# --- ALTERAÇÃO: Adicionado 'dir_mapas' para flexibilidade ---
def processar_dados(ufs, anos, arquivo_populacao, **kwargs):
    """
    Calcula proporção e taxa de óbitos por causas mal definidas para múltiplas UFs e anos.
    """
    resultados = []

    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Causas Mal Definidas: {uf}/{ano} ===")

            df_base = filtrar_populacao(
                arquivo_populacao=arquivo_populacao,
                uf=uf,
                ano=ano
            )
            if df_base is None:
                continue

            # ✅ CORREÇÃO: Lógica de download mais robusta
            try:
                sim = download_sim(states=uf, years=ano, groups=["CID10"])
                # download_sim pode retornar um único ParquetSet, uma lista deles
                # (ex.: quando o SIM particiona o ano em mais de um arquivo) ou uma
                # lista vazia quando a competência ainda não foi publicada pelo DATASUS.
                if isinstance(sim, list):
                    if not sim:
                        raise FileNotFoundError(f"Nenhum arquivo SIM disponível para {ano} (dado ainda não publicado).")
                    df_sim = pd.concat([p.to_dataframe() for p in sim], ignore_index=True)
                else:
                    df_sim = sim.to_dataframe()

                # total de óbitos
                total = df_sim.groupby("CODMUNRES").size().rename("total_obitos")
                total.index = total.index.astype(str).str[:6]

                # óbitos por causas mal definidas (CID R00–R99)
                mal = df_sim[df_sim['CAUSABAS'].astype(str).str.startswith('R')]
                mal_def = mal.groupby("CODMUNRES").size().rename("obitos_mal_definidas")
                mal_def.index = mal_def.index.astype(str).str[:6]
            except Exception as e:
                print(f"⚠️ Erro ao baixar ou processar SIM para {uf}/{ano}: {e}")
                # Cria Series vazias com os nomes corretos para evitar erro no join
                total = pd.Series(dtype=int, name="total_obitos")
                mal_def = pd.Series(dtype=int, name="obitos_mal_definidas")

            # --- Junta e calcula indicadores ---
            df = df_base.join(total, how="left").join(mal_def, how="left").fillna(0)
            df['total_obitos']         = df['total_obitos'].astype(int)
            df['obitos_mal_definidas']  = df['obitos_mal_definidas'].astype(int)
            df['PROP_MAL_DEFINIDAS']    = df.apply(
                lambda r: (r.obitos_mal_definidas/r.total_obitos*100) if r.total_obitos>0 else 0, axis=1)
            df['TX_MAL_DEFINIDAS_P10K'] = df.apply(
                lambda r: (r.obitos_mal_definidas/r.populacao*10000) if r.populacao>0 else 0, axis=1)

            df['UF'] = uf

            resultados.append(df.reset_index())


    if resultados:
        df_final = pd.concat(resultados, ignore_index=True)
        print("\n✅ Óbitos por Causas Mal Definidas processado com sucesso.")
        return df_final
    else:
        print("⚠️ Nenhum dado processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Calcula óbitos por causas mal definidas para múltiplos estados e anos.")

    # ✅ CORREÇÃO: Parser aprimorado
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs, ex: TO PA MG")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022, 2023], help="Lista de anos")
    parser.add_argument("--pop", type=str, default="estimativa_pop_spline.csv", help="Arquivo CSV com população municipal")
    parser.add_argument("--saida", type=str, default=None, help="Caminho completo do arquivo CSV de saída. Se não informado, um nome será gerado.")

    args = parser.parse_args()

    df = processar_dados(
        ufs=args.ufs,
        anos=args.anos,
        arquivo_populacao=args.pop,
    )

    if not df.empty:
        caminho_saida_csv = args.saida

        if caminho_saida_csv is None:
            # Caminho absoluto para a raiz do projeto
            raiz_projeto = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

            # Caminho final em dados/processados
            output_dir = os.path.join(raiz_projeto, "dados", "processados", "indicadores")
            os.makedirs(output_dir, exist_ok=True)

            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            nome_arquivo = f"obitos_causas_mal_definidas_{ufs_str}_{anos_str}.csv"
            caminho_saida_csv = os.path.join(output_dir, nome_arquivo)

        df.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 CSV salvo em: '{caminho_saida_csv}'")
    else:
        print("⚠️ Nenhum resultado para salvar.")

