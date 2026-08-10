# -*- coding: utf-8 -*-
# Arquivo: src/features/febre_maculosa.py
# Indicador: Febre Maculosa (SINAN/FMAC)

import argparse
from pathlib import Path
from ..utils.dataloaders import processar_agravo_sinan_generico

DIS_CODE = "FMAC"
NOME_INDICADOR = "TAXA_INCIDENCIA_FMAC"


def processar_dados(ufs, anos, arquivo_populacao, **kwargs):
    """Calcula a Taxa de Febre Maculosa (por 100.000 hab.) a partir do SINAN/FMAC."""
    return processar_agravo_sinan_generico(
        ufs, anos, arquivo_populacao,
        dis_code=DIS_CODE,
        nome_indicador=NOME_INDICADOR,
        coluna_filtro='CLASSI_FIN',
        codigos_confirmados=['1'],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calcula a Taxa de Febre Maculosa (SINAN/FMAC).")
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
            caminho_saida_csv = output_dir / f"febre_maculosa_{ufs_str}_{anos_str}.csv"
        df_resultado.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 CSV salvo em: '{caminho_saida_csv}'")
    else:
        print("⚠️ Nenhum resultado para salvar.")
