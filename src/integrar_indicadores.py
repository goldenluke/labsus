# src/integrar_indicadores.py

import pandas as pd
from pathlib import Path
import argparse
import importlib
import traceback
from functools import reduce

# Assumindo que o script é executado a partir do diretório raiz do projeto Django
# ou que o PYTHONPATH está configurado corretamente.
# Para execução standalone, podemos precisar ajustar o caminho.
try:
    from .utils.dataloaders import filtrar_populacao
except ImportError:
    from utils.dataloaders import filtrar_populacao


def discover_feature_functions(features_dir: Path) -> dict:
    """
    Escaneia o diretório de features, importa cada módulo e retorna um dicionário
    mapeando o nome do arquivo para sua função 'processar_dados'.
    """
    print("--- Descobrindo módulos de features disponíveis ---")
    feature_functions = {}
    for f in features_dir.glob('*.py'):
        # Ignora arquivos que não são módulos de features, como __init__.py
        if f.name.startswith(('__init__', '.')):
            continue

        module_name = f.stem
        # O caminho para importação precisa ser relativo ao pacote 'src'
        module_path = f'src.features.{module_name}'
        try:
            module = importlib.import_module(module_path)
            if hasattr(module, 'processar_dados'):
                feature_functions[module_name] = getattr(module, 'processar_dados')
                print(f"  -> Módulo '{module_name}' carregado com sucesso.")
            else:
                print(f"⚠️ Aviso: Módulo '{module_path}' não possui uma função 'processar_dados'.")
        except Exception as e:
            print(f"❌ Erro ao importar o módulo '{module_path}': {e}")

    return feature_functions

def main(args):
    """Função principal que orquestra todo o fluxo de trabalho de integração."""

    features_dir = Path(__file__).parent / "features"
    funcoes_disponiveis = discover_feature_functions(features_dir)

    if not funcoes_disponiveis:
        print("❌ ERRO CRÍTICO: Nenhuma função de feature foi encontrada. Encerrando.")
        return

    # --- Configuração Inicial ---
    ARQUIVO_POP = Path(args.pop)
    ARQUIVO_INDICADORES_INTEGRADOS = Path(args.output_csv_path)
    ARQUIVO_INDICADORES_INTEGRADOS.parent.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print("🚀 INICIANDO O PIPELINE DE INTEGRAÇÃO DE INDICADORES 🚀")
    print(f"  Estados Alvo: {args.ufs}")
    print(f"  Anos Alvo:    {args.anos}")

    indicadores_a_processar = args.indicadores if args.indicadores else list(funcoes_disponiveis.keys())
    print(f"  Indicadores a processar: {indicadores_a_processar}")
    print("="*60)

    if not ARQUIVO_POP.exists():
        print(f"❌ ERRO CRÍTICO: Arquivo de população não encontrado em '{ARQUIVO_POP}'.")
        return
    print("✅ Arquivo de população validado.")

    # --- ETAPA 1: Criar o DataFrame Base ---
    print("\n--- ETAPA 1: Criando DataFrame base com população e chaves ---")
    df_base_list = []
    for uf in args.ufs:
        for ano in args.anos:
            df_temp = filtrar_populacao(arquivo_populacao=ARQUIVO_POP, uf=uf, ano=ano)
            if df_temp is not None:
                df_base_list.append(df_temp.reset_index())

    if not df_base_list:
        print("❌ ERRO CRÍTICO: Não foi possível carregar dados de população para nenhuma combinação de UF/Ano.")
        return

    df_final = pd.concat(df_base_list, ignore_index=True)
    chaves_base = ['cod_mun_ibge_6', 'ANO', 'UF', 'municipio', 'cod_mun_ibge_7', 'populacao']
    df_final = df_final[[col for col in chaves_base if col in df_final.columns]].copy()
    print(f"✅ DataFrame base criado com {len(df_final)} registros.")

    # --- ETAPA 2: Calcular e Mesclar Indicadores ---
    print("\n--- ETAPA 2: Calculando e mesclando indicadores ---")

    for nome_indicador_modulo in indicadores_a_processar:
        if nome_indicador_modulo in funcoes_disponiveis:
            print(f"\n-> Processando feature: {nome_indicador_modulo}...")
            funcao_a_chamar = funcoes_disponiveis[nome_indicador_modulo]
            try:
                params = {
                    "ufs": args.ufs, "anos": args.anos, "arquivo_populacao": ARQUIVO_POP,
                    "doencas": args.arboviroses, "causa_grupo": args.mortalidade
                }

                df_feature = funcao_a_chamar(**params, meses=None)

                if df_feature is not None and not df_feature.empty:
                    chaves_juncao = ['cod_mun_ibge_6', 'ANO', 'UF']
                    cols_indicadores = [col for col in df_feature.columns if col.isupper() and col not in chaves_juncao]

                    if not cols_indicadores:
                        print(f"  -> Aviso: Nenhum indicador (coluna em maiúsculas) encontrado no resultado de '{nome_indicador_modulo}'.")
                        continue

                    cols_para_manter = chaves_juncao + cols_indicadores
                    df_feature_limpo = df_feature[cols_para_manter].drop_duplicates(subset=chaves_juncao)

                    df_final = pd.merge(df_final, df_feature_limpo, on=chaves_juncao, how='left')
                    print(f"  -> Indicador(es) de '{nome_indicador_modulo}' mesclado(s) com sucesso.")

            except Exception:
                print(f"❌ Erro grave ao processar o grupo '{nome_indicador_modulo}':")
                traceback.print_exc()
        else:
            print(f"⚠️ Aviso: Indicador '{nome_indicador_modulo}' solicitado não foi encontrado nos módulos. Pulando.")

    # --- ETAPA 3: Limpeza Final e Salvamento ---
    print("\n--- ETAPA 3: Limpeza final e salvamento ---")

    cols_indicadores_final = [c for c in df_final.columns if c.isupper() and c not in ['UF', 'ANO']]
    df_final[cols_indicadores_final] = df_final[cols_indicadores_final].fillna(0)

    df_final.to_csv(ARQUIVO_INDICADORES_INTEGRADOS, sep=';', encoding='utf-8-sig', index=False)
    print(f"✅ Painel de dados integrado salvo em: '{ARQUIVO_INDICADORES_INTEGRADOS}'")

    print("\n=================================================")
    print("🎉 FLUXO DE INTEGRAÇÃO DE INDICADORES CONCLUÍDO! 🎉")
    print("=================================================")

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    try:
        discovered_features = discover_feature_functions(script_dir / "features")
        available_indicators_help = f"Indicadores específicos. Disponíveis: {list(discovered_features.keys())}"
    except Exception:
        available_indicators_help = "Indicadores específicos. Falha ao descobrir módulos."

    parser = argparse.ArgumentParser(
        description="Orquestrador para integração de Indicadores de Saúde.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    BASE_DIR = Path(__file__).resolve().parent.parent

    parser.add_argument("--ufs", nargs="+", default=["TO"], help="Lista de siglas de UFs a processar.")
    parser.add_argument("--anos", nargs="+", type=int, default=[2022], help="Lista de anos a processar.")
    parser.add_argument("--arboviroses", nargs="+", default=['chikungunya', 'zika'], help="Arboviroses a processar.")
    parser.add_argument("--mortalidade", nargs="+", default=['circulatorio', 'neoplasias', 'respiratorias', 'diabetes', 'externas', 'covid19'], help="Grupos de mortalidade a processar.")
    parser.add_argument("--indicadores", nargs="+", help=available_indicators_help)

    default_output_path = BASE_DIR / "outputs" / "integrados" / "indicadores_integrados_default.csv"
    parser.add_argument("--output_csv_path", type=str, default=str(default_output_path), help="Caminho completo para o arquivo CSV de saída.")
    parser.add_argument("--pop", type=str, default=str(BASE_DIR / "referencia/populacao/populacao_estimada_completa_spline.csv"), help="Caminho para o arquivo CSV de população.")

    args = parser.parse_args()

    # Adiciona 'meses' ao objeto args com valor None, já que foi removido do parser
    # mas a função main ainda o passa para as features.
    args.meses = None

    main(args)
