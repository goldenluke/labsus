# -*- coding: utf-8 -*-
import pandas as pd
import os
import argparse
from pysus.online_data.SIH import SIH
from ..utils.dataloaders import filtrar_populacao

# --- ALTERAÇÃO: Adicionado 'dir_mapas' para flexibilidade ---
def processar_dados(ufs, anos, arquivo_populacao, meses, **kwargs):
    """
    Calcula o indicador de internações por doenças crônicas para múltiplas UFs, anos e meses.
    """
    DOENCAS_CID10 = ["I10", "I11", "I12", "I13", "I15", "E10", "E11", "E12", "E13", "E14", "J45", "J46"]
    df_resultados = []

    processar_por_mes = bool(meses) and len(meses) > 0

    for uf in ufs:
        for ano in anos:
            meses_iterar = meses if processar_por_mes else [None]

            for mes in meses_iterar:
                periodo_str = f"{uf}/{ano}" + (f"/{mes:02d}" if mes else " (ano inteiro)")
                print(f"\n=== Processando Internações por Doenças Crônicas: {periodo_str} ===")

                df_base = filtrar_populacao(
                    arquivo_populacao=arquivo_populacao,
                    uf=uf,
                    ano=ano
                )
                if df_base is None:
                    continue

                # ✅ CORREÇÃO: Lógica de download mais robusta
                try:
                    sih = SIH()
                    sih.load()
                    files = sih.get_files(group='RD', uf=uf, year=ano, month=mes)

                    if not files:
                        print(f"⚠️  Nenhum arquivo SIH encontrado para {periodo_str}")
                        df_sih = pd.DataFrame() # Cria um DataFrame vazio para continuar
                    else:
                        parquet_set = sih.download(files)
                        df_sih = pd.concat([p.to_dataframe() for p in parquet_set], ignore_index=True)

                except Exception as e:
                    print(f"❌ Erro ao carregar dados do SIH para {periodo_str}: {e}")
                    df_sih = pd.DataFrame() # Cria um DataFrame vazio em caso de erro

                # Se o DataFrame estiver vazio ou sem a coluna, cria uma Série de internações vazia
                if "DIAG_PRINC" not in df_sih.columns:
                    internacoes = pd.Series(dtype=int, name="n_internacoes")
                else:
                    df_cronicas = df_sih[df_sih["DIAG_PRINC"].astype(str).str[:3].isin([cid[:3] for cid in DOENCAS_CID10])].copy()
                    df_cronicas["MUNIC_RES"] = df_cronicas["MUNIC_RES"].astype(str).str.zfill(6)
                    internacoes = df_cronicas.groupby("MUNIC_RES").size().rename("n_internacoes")

                # Junta os dados e calcula os indicadores
                df_base = df_base.join(internacoes, how="left")
                df_base["n_internacoes"] = df_base["n_internacoes"].fillna(0).astype(int)
                df_base["DOENCAS_CRONICAS"] = df_base.apply(
                    lambda row: (row["n_internacoes"] / row["populacao"]) * 10000 if row["populacao"] > 0 else 0,
                    axis=1
                )

                df_base["UF"] = uf
                df_base["MES"] = mes if mes is not None else 0 # 0 para ano inteiro
                df_resultados.append(df_base.reset_index())

    if df_resultados:
        df_final = pd.concat(df_resultados, ignore_index=True)
        print("\n✅ Internações por Doenças Crônicas processada com sucesso.")
        return df_final
    else:
        print("⚠️ Nenhum dado de internações foi processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Calcula internações por doenças crônicas por 10 mil habitantes.")

    # ✅ CORREÇÃO: Parser aprimorado
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs (ex: TO PA MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=[2024], help="Lista de anos (ex: 2023 2024)")
    parser.add_argument("--meses", nargs="*", type=int, default=None, help="Lista de meses (ex: 1 2 12). Se não informado, processa o ano inteiro.")
    parser.add_argument("--pop", type=str, default="estimativa_pop_spline.csv", help="Arquivo CSV com dados populacionais")
    parser.add_argument("--saida", type=str, default=None, help="Caminho completo do arquivo CSV de saída. Se não informado, um nome será gerado automaticamente.")

    args = parser.parse_args()

    df_resultado = processar_dados(
        ufs=args.ufs,
        anos=args.anos,
        meses=args.meses,
        arquivo_populacao=args.pop,
    )

    if not df_resultado.empty:
        caminho_saida_csv = args.saida

        if caminho_saida_csv is None:
            # Caminho absoluto para a raiz do projeto
            raiz_projeto = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

            # Caminho final em dados/processados
            output_dir = os.path.join(raiz_projeto, "dados", "processados", "indicadores")
            os.makedirs(output_dir, exist_ok=True)

            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            meses_str = '-'.join(map(str, args.meses)) if args.meses else "anual"
            nome_arquivo = f"internacoes_cronicas_{ufs_str}_{anos_str}_{meses_str}.csv"
            caminho_saida_csv = os.path.join(output_dir, nome_arquivo)

        df_resultado.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo como: '{caminho_saida_csv}'")
    else:
        print("⚠️ Nenhum dado foi retornado.")

