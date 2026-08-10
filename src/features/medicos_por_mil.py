# src/features/medicos_por_mil.py

import pandas as pd
from pysus.online_data.CNES import CNES
from ..utils.dataloaders import filtrar_populacao
import argparse
from pathlib import Path

def processar_dados(
    ufs=['TO'],
    anos=[2022],
    meses=None,
    arquivo_populacao="estimativa_pop_spline.csv",
    **kwargs # Captura argumentos extras como 'doencas', etc., para ignorá-los
):
    """
    Calcula a taxa de médicos por 1.000 habitantes.
    Se múltiplos meses forem processados, retorna a MÉDIA do período para o ano.
    """
    df_resultados_mensais = []

    try:
        cnes_db = CNES()
        cnes_db.load(groups=['PF'])
    except Exception as e:
        print(f"❌ Erro crítico ao carregar o banco de dados do CNES: {e}")
        return pd.DataFrame()

    processar_por_mes = bool(meses)

    for uf in ufs:
        for ano in anos:
            meses_iterar = meses if processar_por_mes else list(range(1, 13))

            # Carrega a base populacional uma vez por UF/Ano
            df_base_anual = filtrar_populacao(arquivo_populacao=arquivo_populacao, uf=uf, ano=ano)
            if df_base_anual is None:
                print(f"⚠️  Aviso: População para {uf}/{ano} não encontrada. Pulando este ano.")
                continue

            for mes in meses_iterar:
                periodo_str = f"{uf}/{ano}/{mes:02d}"
                print(f"  -> Processando Médicos por Mil: {periodo_str}")

                try:
                    files = cnes_db.get_files(group='PF', uf=uf, year=ano, month=mes)
                    if not files:
                        print(f"⚠️ Nenhum arquivo CNES encontrado para {periodo_str}")
                        continue

                    df_cnes_mes = cnes_db.download(files).to_dataframe()

                    # ⚠️ CORREÇÃO: 'CPFUNICO' no CNES/PF é um indicador binário (branco/'1'),
                    # não um identificador por profissional -- nunique() nessa coluna satura
                    # em no máximo 2 por município, subestimando drasticamente a contagem de
                    # médicos. O identificador real por profissional é 'CPF_PROF' (mascarado
                    # por LGPD, mas estável por pessoa).
                    if 'CBO' not in df_cnes_mes.columns or 'CPF_PROF' not in df_cnes_mes.columns:
                        print(f"⚠️ Colunas CBO ou CPF_PROF ausentes para {periodo_str}")
                        contagem = pd.Series(dtype=int, name='n_medicos')
                    else:
                        df_med = df_cnes_mes[df_cnes_mes['CBO'].astype(str).str.startswith('225')]
                        contagem = df_med.groupby('CODUFMUN')['CPF_PROF'].nunique().rename('n_medicos')
                        contagem.index = contagem.index.astype(str)

                except Exception as e:
                    print(f"❌ Erro ao carregar dados do CNES para {periodo_str}: {e}")
                    contagem = pd.Series(dtype=int, name='n_medicos')

                # Junta os dados mensais e calcula a taxa mensal
                df_mes_calculado = df_base_anual.join(contagem, how='left').fillna({'n_medicos': 0})
                df_mes_calculado['n_medicos'] = df_mes_calculado['n_medicos'].astype(int)
                df_mes_calculado['TAXA_MEDICOS'] = df_mes_calculado.apply(
                    lambda r: (r['n_medicos'] / r['populacao']) * 1000 if r['populacao'] > 0 else 0,
                    axis=1
                )
                df_mes_calculado['MES'] = mes
                df_resultados_mensais.append(df_mes_calculado.reset_index())

    if not df_resultados_mensais:
        print("\n⚠️ Nenhum dado mensal de médicos foi processado.")
        return pd.DataFrame()

    # --- AGREGAÇÃO ANUAL ---
    df_mensal_completo = pd.concat(df_resultados_mensais, ignore_index=True)

    # Chaves para agrupar. Inclui informações do município para mantê-las no resultado.
    chaves_agregacao = ['cod_mun_ibge_6', 'ANO', 'UF', 'municipio', 'cod_mun_ibge_7', 'populacao']
    chaves_presentes = [chave for chave in chaves_agregacao if chave in df_mensal_completo.columns]

    # Agrupa por município/ano e calcula a média das taxas e contagens
    df_anual = df_mensal_completo.groupby(chaves_presentes).agg(
        TAXA_MEDICOS=('TAXA_MEDICOS', 'mean'),
        n_medicos=('n_medicos', 'mean') # Representa a média de médicos ao longo dos meses analisados
    ).reset_index()

    print("✅ Taxa de Médicos (média anual) processada com sucesso.")
    return df_anual


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Calcula a taxa de médicos por mil habitantes.")

    BASE_DIR = Path(__file__).resolve().parent.parent.parent

    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de UFs (ex: TO PA MG)")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos (ex: 2023 2024)")
    parser.add_argument("--meses", nargs="*", type=int, default=None, help="Meses para processar. Se não informado, usa o ano inteiro.")
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"), help="Arquivo CSV com dados populacionais")
    parser.add_argument("--saida", type=str, default=None, help="Caminho completo do arquivo CSV de saída (anualizado).")

    args = parser.parse_args()

    df_resultado = processar_dados(
        ufs=args.ufs,
        anos=args.anos,
        meses=args.meses,
        arquivo_populacao=args.pop
    )

    if not df_resultado.empty:
        caminho_saida = Path(args.saida) if args.saida else BASE_DIR / "outputs" / "indicadores_teste" / "medicos_por_mil_anual.csv"
        caminho_saida.parent.mkdir(parents=True, exist_ok=True)
        df_resultado.to_csv(caminho_saida, index=False, sep=';', encoding='utf-8-sig')
        print(f"\n📄 Resultado anualizado salvo em: '{caminho_saida}'")
    else:
        print("\n⚠️ Nenhum resultado final foi gerado para salvar.")
