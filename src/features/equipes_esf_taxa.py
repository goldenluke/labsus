# -*- coding: utf-8 -*-
import pandas as pd
import os
import argparse
from pysus.online_data.CNES import CNES
from ..utils.dataloaders import filtrar_populacao

def processar_dados(ufs, anos, arquivo_populacao, meses, **kwargs):
    """
    Calcula a Taxa de Equipes de Saúde da Família (eSF) por 10.000 habitantes
    para múltiplas UFs, anos e meses (opcional).
    """
    df_resultados = []

    try:
        cnes_db = CNES()
        cnes_db.load(groups=['EP'])
    except Exception as e:
        print(f"❌ Erro crítico ao carregar o banco de dados do CNES: {e}")
        return pd.DataFrame()

    processar_por_mes = bool(meses) and len(meses) > 0

    for uf in ufs:
        for ano in anos:
            meses_iterar = meses if processar_por_mes else [None]

            for mes in meses_iterar:
                periodo_str = f"{uf}/{ano}" + (f"/{mes:02d}" if mes else " (ano inteiro)")
                print(f"\n=== Processando Taxa de Equipes ESF: {periodo_str} ===")

                df_base = filtrar_populacao(
                    arquivo_populacao=arquivo_populacao,
                    uf=uf,
                    ano=ano
                )
                if df_base is None:
                    continue

                try:
                    meses_download = [mes] if mes else list(range(1, 13))

                    files = cnes_db.get_files(group='EP', uf=uf, year=ano, month=meses_download)
                    if not files:
                        raise FileNotFoundError(f"Nenhum arquivo CNES/EP encontrado para {periodo_str}")

                    print(f"      -> Baixando {len(files)} arquivo(s) do CNES/EP...")
                    downloaded_files = cnes_db.download(files)

                    df_list = [pd.read_parquet(p.path) for p in downloaded_files]
                    if not df_list:
                        raise ValueError("Nenhum dado pode ser lido dos arquivos baixados.")

                    df_cnes_ep = pd.concat(df_list, ignore_index=True)

                except Exception as e:
                    print(f"❌ Erro ao carregar dados do CNES para {periodo_str}: {e}")
                    df_cnes_ep = pd.DataFrame()

                if df_cnes_ep.empty or 'TIPO_EQP' not in df_cnes_ep.columns or 'CODUFMUN' not in df_cnes_ep.columns:
                    print("      -> [AVISO] DataFrame vazio ou colunas essenciais não encontradas.")
                    contagem_equipes = pd.Series(dtype=int, name="n_equipes_esf")
                else:
                    # ✅ --- CORREÇÃO FINAL E DEFINITIVA ---
                    # O código para Equipe de Saúde da Família (eSF) é '70'.
                    df_esf = df_cnes_ep[df_cnes_ep['TIPO_EQP'].astype(str).str.strip() == '70'].copy()
                    print(f"      -> [INFO] Encontradas {len(df_esf)} entradas de Equipes de Saúde da Família (código 70).")

                    # ⚠️ CORREÇÃO: a coluna do CNES/EP se chama 'IDEQUIPE' (sem underscore),
                    # não 'ID_EQUIPE'. Com o nome errado, o `if` abaixo nunca era verdadeiro
                    # e o código caía sempre no ramo `size()`, contando linhas em vez de
                    # equipes distintas — ao baixar os 12 meses do ano (padrão quando nenhum
                    # mês é informado), a mesma equipe (IDEQUIPE estável mês a mês) era
                    # contada uma vez por mês em que aparecia, inflando a taxa anual em ~12x.
                    if 'IDEQUIPE' in df_esf.columns:
                        contagem_equipes = df_esf.groupby('CODUFMUN')['IDEQUIPE'].nunique().rename('n_equipes_esf')
                    else:
                        contagem_equipes = df_esf.groupby('CODUFMUN').size().rename('n_equipes_esf')

                    contagem_equipes.index = contagem_equipes.index.astype(str)

                # Junta os dados e calcula a taxa
                df = df_base.join(contagem_equipes, how="left")
                df["n_equipes_esf"] = df["n_equipes_esf"].fillna(0).astype(int)
                df["TAXA_EQUIPES_ESF"] = df.apply(
                    lambda row: (row["n_equipes_esf"] / row["populacao"]) * 10000 if row["populacao"] > 0 else 0,
                    axis=1
                )
                df["UF"] = uf
                df["MES"] = mes if mes is not None else 0

                df_resultados.append(df.reset_index())

    if df_resultados:
        df_final = pd.concat(df_resultados, ignore_index=True)
        print("\n✅ Taxa de Equipes de Saúde da Família processada com sucesso.")
        return df_final
    else:
        print("\n⚠️ Nenhum dado de equipes foi processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula a taxa de Equipes de Saúde da Família por 10.000 habitantes.")

    # ... (seus argumentos do parser continuam os mesmos) ...
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs (ex: TO PA MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=[2024], help="Lista de anos (ex: 2023 2024)")
    parser.add_argument("--meses", nargs="*", type=int, default=None, help="Meses para processar. Se não informado, usa o ano inteiro.")
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
            raiz_projeto = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

            output_dir = os.path.join(raiz_projeto, "dados", "processados", "indicadores")
            os.makedirs(output_dir, exist_ok=True)

            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            meses_str = '-'.join(map(str, args.meses)) if args.meses else "anual"

            nome_arquivo = f"taxa_equipes_esf_{ufs_str}_{anos_str}_{meses_str}.csv"
            caminho_saida_csv = os.path.join(output_dir, nome_arquivo)

        df_resultado.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo em: '{caminho_saida_csv}'")
    else:
        print("\n⚠️ Nenhum resultado para salvar.")
