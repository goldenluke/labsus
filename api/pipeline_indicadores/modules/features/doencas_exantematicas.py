# -*- coding: utf-8 -*-
# Arquivo: src/features/doencas_exantematicas.py
# Indicadores: Sarampo e Rubéola (SINAN/EXAN) — mesmo agravo (ficha compartilhada),
# CLASSI_FIN distingue as duas doenças (1=Sarampo, 2=Rubéola, 3=Descartado), por
# isso os dois indicadores são calculados a partir de um único download.

import argparse
from pathlib import Path
from ..utils.dataloaders import processar_agravo_sinan_generico

DIS_CODE = "EXAN"


def processar_dados(ufs, anos, arquivo_populacao, **kwargs):
    """
    Calcula a Taxa de Incidência de Sarampo e de Rubéola (por 100.000 hab.)
    a partir do SINAN/EXAN. As duas doenças compartilham a mesma ficha de
    notificação; CLASSI_FIN='1' confirma Sarampo e CLASSI_FIN='2' confirma
    Rubéola.
    """
    df_sarampo = processar_agravo_sinan_generico(
        ufs, anos, arquivo_populacao,
        dis_code=DIS_CODE,
        nome_indicador="TAXA_INCIDENCIA_SARAMPO",
        coluna_filtro="CLASSI_FIN",
        codigos_confirmados=["1"],
    )
    if df_sarampo.empty:
        return df_sarampo

    df_rubeola = processar_agravo_sinan_generico(
        ufs, anos, arquivo_populacao,
        dis_code=DIS_CODE,
        nome_indicador="TAXA_INCIDENCIA_RUBEOLA",
        coluna_filtro="CLASSI_FIN",
        codigos_confirmados=["2"],
    )

    chaves = [c for c in ["cod_mun_ibge_6", "ANO", "UF"] if c in df_sarampo.columns and c in df_rubeola.columns]
    if not chaves or df_rubeola.empty:
        return df_sarampo

    df = df_sarampo.merge(
        df_rubeola[chaves + ["TAXA_INCIDENCIA_RUBEOLA"]],
        on=chaves, how="left",
    )
    df["TAXA_INCIDENCIA_RUBEOLA"] = df["TAXA_INCIDENCIA_RUBEOLA"].fillna(0)
    return df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula as Taxas de Incidência de Sarampo e Rubéola (SINAN/EXAN).")
    RAIZ_PROJETO = Path(__file__).resolve().parent.parent.parent
    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs (ex: TO PA MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos (ex: 2022 2023)")
    caminho_pop_padrao = RAIZ_PROJETO / "dados" / "processados" / "populacao_estimada_completa_spline.csv"
    parser.add_argument("--pop", type=str, default=str(caminho_pop_padrao), help="Arquivo CSV com população municipal")
    parser.add_argument("--saida", type=str, default=None, help="Caminho completo do arquivo CSV de saída.")
    args = parser.parse_args()

    df_resultado = processar_dados(ufs=args.ufs, anos=args.anos, arquivo_populacao=args.pop)

    if not df_resultado.empty:
        caminho_saida_csv = args.saida
        if caminho_saida_csv is None:
            output_dir = RAIZ_PROJETO / "dados" / "processados" / "indicadores"
            output_dir.mkdir(parents=True, exist_ok=True)
            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            caminho_saida_csv = output_dir / f"doencas_exantematicas_{ufs_str}_{anos_str}.csv"
        df_resultado.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 CSV salvo em: '{caminho_saida_csv}'")
    else:
        print("⚠️ Nenhum resultado para salvar.")
