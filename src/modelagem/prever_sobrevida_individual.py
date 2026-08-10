# -*- coding: utf-8 -*-
import pandas as pd
from pathlib import Path
import argparse
import joblib
import matplotlib.pyplot as plt
from lifelines import CoxPHFitter

def aplicar_modelo_sobrevida(dados_paciente: dict, caminho_modelo: Path):
    """
    Carrega o modelo de sobrevivência Cox e o aplica a um novo paciente.
    """
    print("\n--- 🚀 Aplicando Modelo de Risco de Readmissão (Sobrevivência) 🚀 ---")

    try:
        cph = joblib.load(caminho_modelo)
        print(f"[LOG] Modelo '{caminho_modelo.name}' carregado com sucesso.")
    except FileNotFoundError:
        print(f"❌ ERRO: Modelo não encontrado em '{caminho_modelo}'."); return

    # 1. Preparar os dados do novo paciente
    df_paciente = pd.DataFrame([dados_paciente])

    # ==========================================================
    # --- CORREÇÃO APLICADA AQUI ---
    # Manualmente criando as colunas de "Sim/Não" (One-Hot Encoding)
    # ==========================================================

    # Pega a lista de todas as colunas que o modelo espera
    colunas_modelo = cph.params_.index.tolist()

    # Cria um DataFrame com todas as colunas zeradas
    df_paciente_final = pd.DataFrame(0, index=[0], columns=colunas_modelo)

    # Preenche os valores numéricos
    for col in ['IDADE', 'DIAS_PERM', 'UTI_MES_TO', 'LEITHOSP']:
        if col in df_paciente:
            df_paciente_final[col] = df_paciente[col].values

    # Preenche a categoria correta para o diagnóstico
    capitulo_cid = df_paciente['DIAG_PRINC'].iloc[0][0]
    coluna_diag = f"DIAG_PRINC_CAP_{capitulo_cid}"
    if coluna_diag in df_paciente_final.columns:
        df_paciente_final[coluna_diag] = 1

    # Preenche a categoria correta para o sexo
    if df_paciente['SEXO'].iloc[0] == '3': # Feminino
        if 'SEXO_3' in df_paciente_final.columns:
            df_paciente_final['SEXO_3'] = 1

    # Adicione aqui outras lógicas para variáveis categóricas se necessário (ex: ATIVIDAD)
    # ...

    print("\n[LOG] Dados do paciente para previsão (após preparação correta):")
    print(df_paciente_final.transpose())

    # 3. Fazer a Previsão da Curva de Sobrevivência
    curva_sobrevida_individual = cph.predict_survival_function(df_paciente_final)

    # ... (o resto da função permanece o mesmo)
    prob_sobrevida_30d = curva_sobrevida_individual.loc[30].iloc[0]
    prob_sobrevida_90d = curva_sobrevida_individual.loc[90].iloc[0]
    prob_sobrevida_180d = curva_sobrevida_individual.loc[180].iloc[0]

    print("\n" + "="*60)
    print("--- Resultado da Análise de Risco de Readmissão ---")
    print(f"-> Probabilidade de NÃO ser readmitido em 30 dias: {prob_sobrevida_30d:.2%}")
    print(f"-> Probabilidade de NÃO ser readmitido em 90 dias: {prob_sobrevida_90d:.2%}")
    print(f"-> Probabilidade de NÃO ser readmitido em 180 dias: {prob_sobrevida_180d:.2%}")
    print("="*60)

    plt.figure(figsize=(10, 6))
    curva_sobrevida_individual.plot(legend=False)
    plt.title(f"Curva de Risco de Readmissão para o Paciente")
    plt.xlabel("Dias Após a Alta")
    plt.ylabel("Probabilidade de Estar Livre de Readmissão")
    plt.grid(True)
    plt.ylim(0, 1)

    dir_saida = Path("outputs/previsoes_individuais")
    dir_saida.mkdir(parents=True, exist_ok=True)
    caminho_fig = dir_saida / "curva_risco_readmissao_individual.png"
    plt.savefig(caminho_fig)
    plt.close()
    print(f"\n📈 Gráfico com a curva de risco individual salvo em: {caminho_fig}")

if __name__ == "__main__":
    # ... (o bloco main permanece o mesmo)
    parser = argparse.ArgumentParser(description="Calcula a curva de risco de readmissão para um novo paciente.")
    parser.add_argument("--idade", type=int, required=True, help="Idade do paciente.")
    parser.add_argument("--dias-perm", type=int, required=True, help="Dias de permanência na internação.")
    parser.add_argument("--usou-uti", type=int, default=0, help="Total de dias em UTI.")
    parser.add_argument("--sexo", type=str, default='1', choices=['1', '3'], help="Sexo do paciente (1=Masc, 3=Fem).")
    parser.add_argument("--diag-princ", type=str, required=True, help="CID-10 do diagnóstico principal (ex: I50).")
    parser.add_argument("--leitos-hosp", type=int, default=150, help="Nº de leitos do hospital.")
    parser.add_argument("--hosp-ensino", type=int, default=0, choices=[0, 1], help="Se o hospital é de ensino (1=Sim, 0=Não).")
    parser.add_argument("--modelo", type=str, default="outputs/analise_sobrevida_readmissao/modelo_cox_readmissao.joblib", help="Caminho para o modelo treinado.")
    args = parser.parse_args()

    dados_pac = {
        'IDADE': args.idade, 'DIAS_PERM': args.dias_perm, 'UTI_MES_TO': args.usou_uti,
        'SEXO': args.sexo, 'DIAG_PRINC': args.diag_princ, 'LEITHOSP': args.leitos_hosp,
        'ATIVIDAD': str(args.hosp_ensino)
    }

    aplicar_modelo_sobrevida(dados_pac, Path(args.modelo))
