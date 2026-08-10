# -*- coding: utf-8 -*-
import pandas as pd
import os
import argparse
from pysus.online_data.SIH import SIH
from ..utils.dataloaders import filtrar_populacao

def processar_dados(ufs, anos, arquivo_populacao, meses, **kwargs):
    """
    Calcula a Taxa de Internações Gerais por 1.000 habitantes para múltiplas UFs,
    anos e meses (opcional).
    """
    df_resultados = [] # A variável foi declarada como 'df_resultados'

    try:
        sih_db = SIH()
        sih_db.load()
    except Exception as e:
        print(f"❌ Erro crítico ao carregar o banco de dados do SIH: {e}")
        return pd.DataFrame()

    processar_por_mes = bool(meses) and len(meses) > 0

    for uf in ufs:
        for ano in anos:
            meses_iterar = meses if processar_por_mes else [None]

            for mes in meses_iterar:
                periodo_str = f"{uf}/{ano}" + (f"/{mes:02d}" if mes else " (ano inteiro)")
                print(f"\n=== Processando Internações Gerais: {periodo_str} ===")

                df_base = filtrar_populacao(
                    arquivo_populacao=arquivo_populacao,
                    uf=uf,
                    ano=ano
                )
                if df_base is None:
                    continue

                try:
                    files = sih_db.get_files(group='RD', uf=uf, year=ano, month=mes)

                    if not files:
                        print(f"⚠️  Nenhum arquivo SIH encontrado para {periodo_str}")
                        df_sih = pd.DataFrame()
                    else:
                        parquet_set = sih_db.download(files)
                        if isinstance(parquet_set, list):
                            df_sih = pd.concat([p.to_dataframe() for p in parquet_set], ignore_index=True)
                        elif hasattr(parquet_set, "to_dataframe"):
                            df_sih = parquet_set.to_dataframe()
                        else:
                            df_sih = pd.DataFrame()

                except Exception as e:
                    print(f"❌ Erro ao carregar dados do SIH para {periodo_str}: {e}")
                    df_sih = pd.DataFrame()

                if df_sih.empty or 'MUNIC_RES' not in df_sih.columns:
                    internacoes = pd.Series(dtype=int, name="total_internacoes")
                else:
                    df_sih['MUNIC_RES'] = df_sih['MUNIC_RES'].astype(str).str.zfill(6)
                    internacoes = df_sih.groupby("MUNIC_RES").size().rename("total_internacoes")

                df = df_base.join(internacoes, how="left")
                df["total_internacoes"] = df["total_internacoes"].fillna(0).astype(int)

                df["TAXA_INTERNACAO_GERAL"] = df.apply(
                    lambda row: (row["total_internacoes"] / row["populacao"]) * 1000 if row["populacao"] > 0 else 0,
                    axis=1
                )

                df["UF"] = uf
                df["MES"] = mes if mes is not None else 0

                # ✅ --- CORREÇÃO APLICADA AQUI ---
                # O nome da variável foi corrigido de 'resultados' para 'df_resultados'.
                df_resultados.append(df.reset_index())
                # --- FIM DA CORREÇÃO ---

    if df_resultados:
        df_final = pd.concat(df_resultados, ignore_index=True)
        print("\n✅ Taxa de Internações Gerais processada com sucesso.")
        return df_final
    else:
        print("\n⚠️ Nenhum dado de internações foi processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Calcula a taxa de internações gerais por 1.000 habitantes.")

    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs (ex: TO PA MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=[2024], help="Lista de anos (ex: 2023 2024)")
    parser.add_argument("--meses", nargs="*", type=int, default=None, help="Lista de meses (ex: 1 2 12). Se não informado, processa o ano inteiro.")
    parser.add_argument("--pop", type=str, default="outputs/csv/populacao_estimada_completa_spline.csv", help="Arquivo CSV com dados populacionais")
    parser.add_argument("--saida", type=str, default=None, help="Caminho completo do arquivo CSV de saída.")

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
            dir_atual = os.path.dirname(__file__)

            # ✅ CORREÇÃO: Sobe DOIS NÍVEIS para chegar à raiz do projeto
            raiz_projeto = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

            # Caminho final em dados/processados
            output_dir = os.path.join(raiz_projeto, "dados", "processados", "indicadores")
            os.makedirs(output_dir, exist_ok=True)

            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            meses_str = '-'.join(map(str, args.meses)) if args.meses else "anual"
            nome_arquivo = f"taxa_internacoes_gerais_{ufs_str}_{anos_str}_{meses_str}.csv"
            caminho_saida_csv = os.path.join(output_dir, nome_arquivo)

        df_resultado.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida_csv}'")
    else:
        print("\n⚠️ Nenhum resultado foi gerado para salvar.")

