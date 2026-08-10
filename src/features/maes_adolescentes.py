# -*- coding: utf-8 -*-
import pandas as pd
import os
import argparse
from pysus.online_data.SINASC import download as download_sinasc
from ..utils.dataloaders import filtrar_populacao

# --- ALTERAÇÃO: Adicionado 'dir_mapas' para flexibilidade ---
def processar_dados(ufs, anos, arquivo_populacao, **kwargs):

    """
    Calcula a proporção de mães adolescentes (<20 anos) por município,
    UF e ano, com geração de mapas automáticos.
    """
    resultados = []

    for uf in ufs:
        for ano in anos:
            print(f"\n=== Processando Mães Adolescentes: {uf} / {ano} ===")

            df_base = filtrar_populacao(
                arquivo_populacao=arquivo_populacao,
                uf=uf,
                ano=ano
            )
            if df_base is None:
                continue

            # ✅ CORREÇÃO: Lógica de download mais robusta
            try:
                sinasc = download_sinasc(states=uf, years=ano, groups=["DN"])
                if isinstance(sinasc, list) and len(sinasc) > 0:
                    df_sin = pd.concat([f.to_dataframe() for f in sinasc], ignore_index=True)
                elif hasattr(sinasc, "to_dataframe"):
                    df_sin = sinasc.to_dataframe()
                else: # Caso de não encontrar arquivos
                    raise ValueError("Nenhum arquivo SINASC encontrado.")

                if df_sin.empty:
                    raise ValueError("DataFrame do SINASC está vazio após o download.")

                # total de nascimentos
                tot = df_sin.groupby("CODMUNRES").size().rename("total_nascimentos")
                tot.index = tot.index.astype(str).str[:6]

                # mães com idade < 20 (IDADEMAE não numérica/ausente é descartada, não derruba o UF/ano)
                idademae_num = pd.to_numeric(df_sin["IDADEMAE"].astype(str).str[:2], errors="coerce")
                mae_adol = df_sin[idademae_num < 20].groupby("CODMUNRES").size().rename("maes_adolescentes")
                mae_adol.index = mae_adol.index.astype(str).str[:6]

            except Exception as e:
                print(f"⚠️ Erro ao baixar ou processar SINASC para {uf}/{ano}: {e}")
                # Cria Series vazias com os nomes corretos para evitar erro no join
                tot = pd.Series(dtype=int, name="total_nascimentos")
                mae_adol = pd.Series(dtype=int, name="maes_adolescentes")

            # junta e calcula
            df = df_base.join(tot, how="left").join(mae_adol, how="left").fillna(0)
            df['total_nascimentos'] = df['total_nascimentos'].astype(int)
            df['maes_adolescentes'] = df['maes_adolescentes'].astype(int)
            df['PROP_MAE_ADOL'] = df.apply(
                lambda r: (r.maes_adolescentes / r.total_nascimentos * 100) if r.total_nascimentos > 0 else 0,
                axis=1
            )

            df['UF'] = uf

            resultados.append(df.reset_index())



    if resultados:
        df_final = pd.concat(resultados, ignore_index=True)
        print("\n✅ Proporção de mães adolescentes (%) processada com sucesso.")
        return df_final
    else:
        print("⚠️ Nenhum dado processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Calcula a proporção de mães adolescentes (<20 anos) por UF e ano.")

    # ✅ CORREÇÃO: Parser aprimorado
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs (ex: TO GO MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022, 2023], help="Lista de anos")
    parser.add_argument("--pop", type=str, default="estimativa_pop_spline.csv", help="Arquivo CSV com população municipal")

    parser.add_argument("--saida", type=str, default=None, help="Caminho completo do arquivo CSV de saída. Se não informado, um nome será gerado.")

    args = parser.parse_args()

    df_prop = processar_dados(
        ufs=args.ufs,
        anos=args.anos,
        arquivo_populacao=args.pop,
    )

    if not df_prop.empty:
        caminho_saida_csv = args.saida

        if caminho_saida_csv is None:
            # Caminho absoluto para a raiz do projeto
            dir_atual = os.path.dirname(__file__)

            raiz_projeto = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

            # Caminho final em dados/processados
            output_dir = os.path.join(raiz_projeto, "dados", "processados", "indicadores")
            os.makedirs(output_dir, exist_ok=True)

            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            nome_arquivo = f"prop_maes_adolescentes_{ufs_str}_{anos_str}.csv"
            caminho_saida_csv = os.path.join(output_dir, nome_arquivo)

        df_prop.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 CSV salvo em: '{caminho_saida_csv}'")
    else:
        print("⚠️ Nenhum resultado para salvar.")
