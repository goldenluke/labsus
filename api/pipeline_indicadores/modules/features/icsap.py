# src/features/icsap.py

import pandas as pd
from pysus.online_data.SIH import SIH
from ..utils.dataloaders import filtrar_populacao

# Lista Brasileira de Internações por Condições Sensíveis à Atenção Primária
# (Portaria SAS/MS nº 221, de 17/04/2008), 19 grupos de causa. Códigos
# cross-checados com o pacote acadêmico `csapAIH` (Nedel/Alfradique).
#
# A maioria dos grupos casa por BLOCO de 3 caracteres do CID-10 (todo o
# subcódigo conta). Alguns grupos só admitem um subcódigo específico de 4
# caracteres dentro de um bloco maior (ex.: em pneumonias bacterianas, só
# J15.3/J15.4/J15.8/J15.9 entram — não o bloco J15 inteiro) — esses ficam em
# ICSAP_CODIGOS_4CHAR e são checados primeiro.

ICSAP_BLOCOS_3CHAR = {
    # Grupo 01 — Prevenção por imunização e condições evitáveis
    "A15", "A16", "A17", "A18", "A19", "I00", "I01", "I02",
    "A51", "A52", "A53", "B50", "B51", "B52", "B53", "B54", "B55", "B56",
    "B77", "A33", "A34", "A35", "A36", "A37", "A95", "B16", "B26",
    # Grupo 02 — Gastroenterites infecciosas e complicações
    "A00", "A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08", "A09", "E86",
    # Grupo 03 — Anemia
    "D50",
    # Grupo 04 — Deficiências nutricionais
    "E40", "E41", "E42", "E43", "E44", "E45", "E46",
    "E50", "E51", "E52", "E53", "E54", "E55", "E56", "E57", "E58", "E59",
    "E60", "E61", "E62", "E63", "E64",
    # Grupo 05 — Infecções de ouvido, nariz e garganta
    "H66", "J00", "J01", "J02", "J03", "J06", "J31",
    # Grupo 06 — Pneumonias bacterianas (bloco parcial; ver 4-char)
    "J13", "J14",
    # Grupo 07 — Asma
    "J45", "J46",
    # Grupo 08 — Doenças pulmonares
    "J20", "J21", "J40", "J41", "J42", "J43", "J44", "J47",
    # Grupo 09 — Hipertensão
    "I10", "I11",
    # Grupo 10 — Angina
    "I20",
    # Grupo 11 — Insuficiência cardíaca
    "I50", "J81",
    # Grupo 12 — Doenças cerebrovasculares
    "I63", "I64", "I65", "I66", "I67", "I69", "G45", "G46",
    # Grupo 13 — Diabetes mellitus
    "E10", "E11", "E12", "E13", "E14",
    # Grupo 14 — Epilepsias
    "G40", "G41",
    # Grupo 15 — Infecção de rim e trato urinário (bloco parcial; ver 4-char)
    "N10", "N11", "N12", "N30", "N34",
    # Grupo 16 — Infecção de pele e tecido subcutâneo
    "A46", "L01", "L02", "L03", "L04", "L08",
    # Grupo 17 — Doença inflamatória de órgãos pélvicos femininos
    "N70", "N71", "N72", "N73", "N75", "N76",
    # Grupo 18 — Úlcera gastrointestinal (bloco parcial; ver 4-char)
    "K25", "K26", "K27", "K28",
    # Grupo 19 — Doenças relacionadas ao pré-natal e parto
    "O23", "A50",
}

ICSAP_CODIGOS_4CHAR = {
    "G000",  # Grupo 01 — meningite por Haemophilus
    "P350",  # Grupo 01/19 — síndrome da rubéola congênita
    "J153", "J154", "J158", "J159",  # Grupo 06 — outras pneumonias bacterianas
    "J181",  # Grupo 06 — pneumonia lobar não especificada
    "N390",  # Grupo 15 — infecção do trato urinário de localização NE
    "K920", "K921", "K922",  # Grupo 18 — hemorragia gastrointestinal
}


def _classificar_csap(diag_princ: pd.Series) -> pd.Series:
    """Vetorizado: True para linhas cujo DIAG_PRINC está na Lista Brasileira de ICSAP."""
    codigo = diag_princ.astype(str).str.strip().str.upper()
    return codigo.str[:4].isin(ICSAP_CODIGOS_4CHAR) | codigo.str[:3].isin(ICSAP_BLOCOS_3CHAR)


def processar_dados(ufs, anos, arquivo_populacao, meses, **kwargs):
    """
    Calcula a Taxa de Internações por Condições Sensíveis à Atenção Primária
    (ICSAP, por 10.000 habitantes) e a Proporção de Internações CSAP sobre o
    total de internações (%), segundo a Lista Brasileira (Portaria SAS/MS nº
    221/2008), para múltiplas UFs, anos e meses. Agregação por MUNIC_RES
    (município de residência do paciente), que é o padrão da literatura e do
    DATASUS TabNet para medir cobertura de atenção primária.
    """
    df_resultados = []
    processar_por_mes = bool(meses) and len(meses) > 0

    for uf in ufs:
        for ano in anos:
            meses_iterar = meses if processar_por_mes else [None]

            for mes in meses_iterar:
                periodo_str = f"{uf}/{ano}" + (f"/{mes:02d}" if mes else " (ano inteiro)")
                print(f"\n=== Processando ICSAP: {periodo_str} ===")

                df_base = filtrar_populacao(
                    arquivo_populacao=arquivo_populacao,
                    uf=uf,
                    ano=ano
                )
                if df_base is None:
                    continue

                try:
                    sih = SIH()
                    sih.load()
                    files = sih.get_files(group='RD', uf=uf, year=ano, month=mes)

                    if not files:
                        print(f"⚠️  Nenhum arquivo SIH encontrado para {periodo_str}")
                        df_sih = pd.DataFrame()
                    else:
                        parquet_set = sih.download(files)
                        df_sih = pd.concat([p.to_dataframe() for p in parquet_set], ignore_index=True)

                except Exception as e:
                    print(f"❌ Erro ao carregar dados do SIH para {periodo_str}: {e}")
                    df_sih = pd.DataFrame()

                if "DIAG_PRINC" not in df_sih.columns or "MUNIC_RES" not in df_sih.columns:
                    internacoes_csap = pd.Series(dtype=int, name="n_internacoes_csap")
                    internacoes_total = pd.Series(dtype=int, name="n_internacoes_total")
                else:
                    df_sih["MUNIC_RES"] = df_sih["MUNIC_RES"].astype(str).str.zfill(6)
                    is_csap = _classificar_csap(df_sih["DIAG_PRINC"])
                    internacoes_csap = df_sih[is_csap].groupby("MUNIC_RES").size().rename("n_internacoes_csap")
                    internacoes_total = df_sih.groupby("MUNIC_RES").size().rename("n_internacoes_total")

                # Junta os dados e calcula os indicadores
                df_base = df_base.join(internacoes_csap, how="left").join(internacoes_total, how="left")
                df_base["n_internacoes_csap"] = df_base["n_internacoes_csap"].fillna(0).astype(int)
                df_base["n_internacoes_total"] = df_base["n_internacoes_total"].fillna(0).astype(int)

                df_base["ICSAP"] = df_base.apply(
                    lambda row: (row["n_internacoes_csap"] / row["populacao"]) * 10000 if row["populacao"] > 0 else 0,
                    axis=1
                )
                df_base["ICSAP_PROP"] = df_base.apply(
                    lambda row: (row["n_internacoes_csap"] / row["n_internacoes_total"]) * 100 if row["n_internacoes_total"] > 0 else 0,
                    axis=1
                )

                df_base["UF"] = uf
                df_base["MES"] = mes if mes is not None else 0  # 0 para ano inteiro
                df_resultados.append(df_base.reset_index())

    if df_resultados:
        df_final = pd.concat(df_resultados, ignore_index=True)
        print("\n✅ ICSAP processado com sucesso.")
        return df_final
    else:
        print("⚠️ Nenhum dado de internações foi processado.")
        return pd.DataFrame()


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Calcula ICSAP (Internações por Condições Sensíveis à Atenção Primária) por 10 mil habitantes.")

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
            raiz_projeto = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            output_dir = os.path.join(raiz_projeto, "dados", "processados", "indicadores")
            os.makedirs(output_dir, exist_ok=True)

            ufs_str = '-'.join(args.ufs).lower()
            anos_str = '-'.join(map(str, args.anos))
            meses_str = '-'.join(map(str, args.meses)) if args.meses else "anual"
            nome_arquivo = f"icsap_{ufs_str}_{anos_str}_{meses_str}.csv"
            caminho_saida_csv = os.path.join(output_dir, nome_arquivo)

        df_resultado.to_csv(caminho_saida_csv, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado salvo como: '{caminho_saida_csv}'")
    else:
        print("⚠️ Nenhum dado foi retornado.")
