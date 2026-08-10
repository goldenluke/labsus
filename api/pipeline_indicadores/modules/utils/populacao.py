# -*- coding: utf-8 -*-
"""
Script unificado e avançado para processar e estimar dados de população.
Oferece múltiplos métodos de estimativa: Regressão Linear, Polinomial,
Random Forest e Interpolação Spline.
"""
# --- Importações ---
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Modelos e ferramentas do Scikit-learn
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import PolynomialFeatures
from sklearn.pipeline import make_pipeline

# Ferramentas de interpolação do SciPy
from scipy.interpolate import interp1d, PchipInterpolator


def estimar_serie_robusta(anos_originais, valores_originais, anos_alvo):
    """
    Preenche uma série (ano -> população) de um único município para todos
    os anos em `anos_alvo`, usando dois métodos distintos conforme a posição
    do ano faltante em relação ao intervalo de dados reais conhecidos:

    - LACUNA INTERNA (entre o primeiro e o último ano real, ex.: 2007, 2010,
      2022-2023 no caso do IBGE): interpolação PCHIP (Piecewise Cubic
      Hermite), que — ao contrário de uma spline cúbica "pura"
      (scipy.interpolate.interp1d(kind='cubic')) — é shape-preserving: não
      overshoot, não oscila além dos valores vizinhos. Segura porque está
      sempre ancorada por um ponto real de cada lado.

    - EXTRAPOLAÇÃO (além do último ano real, ex.: 2025/2026 neste projeto):
      regressão linear simples sobre os últimos pontos reais disponíveis.
      Uma spline cúbica extrapolada é notoriamente instável (o polinômio do
      último segmento pode divergir sem limite) — foi exatamente isso que
      produziu município com população estimada negativa/zerada em 2026 na
      primeira versão deste arquivo. Extrapolação linear de curto prazo
      (1-2 anos) é a prática padrão para esse tipo de projeção
      populacional quando não há dado real mais recente disponível.

    Retorna um dict {ano: (populacao_estimada, tipo)}, incluindo os
    próprios anos originais (tipo='Original', valor inalterado).
    """
    anos_originais = np.asarray(anos_originais, dtype=int)
    valores_originais = np.asarray(valores_originais, dtype=float)
    ordem = np.argsort(anos_originais)
    anos_originais = anos_originais[ordem]
    valores_originais = valores_originais[ordem]

    mapa_original = dict(zip(anos_originais.tolist(), valores_originais.tolist()))
    min_ano, max_ano = int(anos_originais.min()), int(anos_originais.max())

    # Interpolador PCHIP para lacunas internas — precisa de pelo menos 2 pontos.
    interpolador = PchipInterpolator(anos_originais, valores_originais, extrapolate=False) if len(anos_originais) >= 2 else None

    # Tendência linear recente (últimos até 5 pontos reais) para extrapolar o futuro,
    # e tendência sobre os primeiros até 5 pontos reais para extrapolar o passado
    # (simétrico, embora no dataset atual do IBGE praticamente não haja essa necessidade).
    n_pontos = min(5, len(anos_originais))
    coef_futuro = np.polyfit(anos_originais[-n_pontos:], valores_originais[-n_pontos:], 1) if len(anos_originais) >= 2 else None
    coef_passado = np.polyfit(anos_originais[:n_pontos], valores_originais[:n_pontos], 1) if len(anos_originais) >= 2 else None

    resultado = {}
    for ano in anos_alvo:
        ano = int(ano)
        if ano in mapa_original:
            resultado[ano] = (mapa_original[ano], 'Original')
            continue

        if min_ano < ano < max_ano and interpolador is not None:
            valor = float(interpolador(ano))
            tipo = 'Estimativa (Spline)'
        elif ano > max_ano and coef_futuro is not None:
            valor = float(np.polyval(coef_futuro, ano))
            tipo = 'Estimativa (Linear)'
        elif ano < min_ano and coef_passado is not None:
            valor = float(np.polyval(coef_passado, ano))
            tipo = 'Estimativa (Linear)'
        else:
            # Município com um único ano de dado real: não há como ajustar
            # tendência nem interpolar — mantém o único valor conhecido.
            valor = float(valores_originais[0])
            tipo = 'Estimativa (Linear)'

        # Salvaguarda: população nunca pode ser zero ou negativa.
        resultado[ano] = (max(1.0, valor), tipo)

    return resultado


# --- FUNÇÃO 1: PROCESSAMENTO INICIAL (sem alterações) ---
def processar_dados_brutos(input_filename):
    """Lê um arquivo CSV de população em formato 'wide', limpa, formata e o transforma para o formato 'long'."""
    print(f"--- ETAPA 1: Processando o arquivo bruto: {input_filename} ---")
    try:
        df = pd.read_csv(input_filename, sep=';', header=3, encoding='utf-8')
    except FileNotFoundError:
        print(f"❌ ERRO: O arquivo de entrada '{input_filename}' não foi encontrado.")
        return None
    # ... (o resto da função é idêntico ao script anterior)
    df_long = df.melt(id_vars=['Cód.', 'Município'], var_name='ano', value_name='populacao')
    df_long.rename(columns={'Cód.': 'cod_mun_ibge_7', 'Município': 'municipio_uf'}, inplace=True)
    df_long['populacao'] = pd.to_numeric(df_long['populacao'], errors='coerce')
    df_long.dropna(subset=['populacao'], inplace=True)
    df_long['populacao'] = df_long['populacao'].astype(int)
    df_long['cod_mun_ibge_7'] = df_long['cod_mun_ibge_7'].astype(str)
    df_long['ano'] = df_long['ano'].astype(int)
    df_long['cod_mun_ibge_6'] = df_long['cod_mun_ibge_7'].str[:6]
    df_long['UF'] = df_long['municipio_uf'].str.extract(r'\((\w{2})\)$')
    df_long['municipio'] = df_long['municipio_uf'].str.replace(r'\s\(\w{2}\)$', '', regex=True)
    colunas_finais = ['cod_mun_ibge_7', 'cod_mun_ibge_6', 'municipio', 'UF', 'ano', 'populacao']
    df_final = df_long[colunas_finais]
    print("Processamento inicial concluído.\n")
    return df_final

# --- FUNÇÃO 2: REGRESSÃO E ESTIMATIVA (MODULARIZADA) ---
def estimar_populacao_com_modelo(df_processado, metodo='linear'):
    """
    Recebe um DataFrame limpo e usa o método especificado para preencher
    os valores de população para anos faltantes.
    """
    print(f"--- ETAPA 2: Calculando estimativas com o método '{metodo.replace('_', ' ').title()}' ---")
    if df_processado is None: return None

    lista_dfs_completos = []

    for codigo_municipio, grupo in df_processado.groupby('cod_mun_ibge_7'):
        grupo = grupo.sort_values('ano')
        X = grupo['ano'].values
        y = grupo['populacao'].values
        X_reshaped = X.reshape(-1, 1)

        # --- Seleção e Treinamento do Modelo ---
        modelo = None
        if metodo == 'linear':
            modelo = LinearRegression()
            modelo.fit(X_reshaped, y)
        elif metodo == 'polinomial':
            # Grau 2 é uma boa escolha para curvas simples (parábolas)
            grau = 2
            modelo = make_pipeline(PolynomialFeatures(grau), LinearRegression())
            modelo.fit(X_reshaped, y)
        elif metodo == 'random_forest':
            # n_estimators é o número de árvores na floresta
            modelo = RandomForestRegressor(n_estimators=100, random_state=42, min_samples_leaf=1)
            modelo.fit(X_reshaped, y)
        elif metodo == 'spline':
            # Tratado à parte abaixo: PCHIP para lacunas internas + regressão
            # linear para extrapolação além do último ano real (ver
            # estimar_serie_robusta). Uma spline cúbica pura extrapolada
            # (interp1d(kind='cubic', fill_value='extrapolate')) diverge sem
            # limite fora do intervalo de dados reais — foi essa instabilidade
            # que produzia município com população estimada zerada/negativa.
            modelo = None
        else:
            raise ValueError("Método desconhecido. Escolha entre: 'linear', 'polinomial', 'random_forest', 'spline'.")

        # --- Previsão para os anos faltantes ---
        anos_existentes = set(X)
        min_ano, max_ano = X.min(), 2026 # Estimar até 2023
        anos_completos = set(range(min_ano, max_ano + 1))
        anos_faltantes = sorted(list(anos_completos - anos_existentes))

        if not anos_faltantes:
            grupo['tipo'] = 'Original'
            lista_dfs_completos.append(grupo)
            continue

        anos_faltantes_np = np.array(anos_faltantes)

        if metodo == 'spline':
            estimativas_por_ano = estimar_serie_robusta(X, y, anos_faltantes)
            populacao_estimada = np.array([estimativas_por_ano[a][0] for a in anos_faltantes])
            tipos_estimativa = [estimativas_por_ano[a][1] for a in anos_faltantes]
        else: # Para os modelos sklearn
            populacao_estimada = modelo.predict(anos_faltantes_np.reshape(-1, 1))
            tipos_estimativa = f'Estimativa ({metodo.title()})'

        # --- Consolidação ---
        df_estimativas = pd.DataFrame({
            'cod_mun_ibge_7': codigo_municipio, 'cod_mun_ibge_6': grupo['cod_mun_ibge_6'].iloc[0],
            'municipio': grupo['municipio'].iloc[0], 'UF': grupo['UF'].iloc[0],
            'ano': anos_faltantes, 'populacao': populacao_estimada.astype(int),
            'tipo': tipos_estimativa
        })

        grupo['tipo'] = 'Original'
        df_completo_municipio = pd.concat([grupo, df_estimativas]).sort_values('ano')
        lista_dfs_completos.append(df_completo_municipio)

    df_final = pd.concat(lista_dfs_completos).reset_index(drop=True)
    print("Estimativas para os anos faltantes foram calculadas.")
    return df_final

# --- FUNÇÃO 3: VISUALIZAÇÃO (ADAPTADA) ---
def visualizar_resultado_avancado(df, nome_municipio_exemplo, metodo):
    """Cria e salva um gráfico para visualizar o resultado do método escolhido."""
    print(f"\n--- ETAPA 3: Gerando gráfico para o método '{metodo.title()}' ---")
    df_municipio = df[df['municipio'] == nome_municipio_exemplo]
    if df_municipio.empty: return

    originais = df_municipio[df_municipio['tipo'] == 'Original']
    estimados = df_municipio[df_municipio['tipo'] != 'Original']

    plt.style.use('seaborn-v0_8-whitegrid')
    plt.figure(figsize=(14, 8))

    # Plota os pontos de dados
    sns.scatterplot(x='ano', y='populacao', data=originais, s=100, label='Dados Originais', color='royalblue', zorder=5)
    sns.scatterplot(x='ano', y='populacao', data=estimados, s=120, marker='X', label=f'Estimativas ({metodo.title()})', color='red', zorder=5)

    # Recalcula e plota a linha/curva do modelo
    anos_plot = np.array(range(df_municipio['ano'].min(), df_municipio['ano'].max() + 1))
    X_originais = originais['ano'].values
    y_originais = originais['populacao'].values

    # ... (lógica de modelo duplicada para plotar a curva correta)
    modelo_plot = None
    if metodo == 'linear':
        modelo_plot = LinearRegression().fit(X_originais.reshape(-1,1), y_originais)
    elif metodo == 'polinomial':
        modelo_plot = make_pipeline(PolynomialFeatures(2), LinearRegression()).fit(X_originais.reshape(-1,1), y_originais)
    elif metodo == 'random_forest':
        modelo_plot = RandomForestRegressor(n_estimators=100, random_state=42).fit(X_originais.reshape(-1,1), y_originais)
    elif metodo == 'spline':
        if len(X_originais) > 3:
            modelo_plot = interp1d(X_originais, y_originais, kind='cubic', fill_value="extrapolate")
        else:
            modelo_plot = interp1d(X_originais, y_originais, kind='linear', fill_value="extrapolate")

    if metodo == 'spline':
        populacao_plot = modelo_plot(anos_plot)
    else:
        populacao_plot = modelo_plot.predict(anos_plot.reshape(-1,1))

    plt.plot(anos_plot, populacao_plot, color='darkorange', linestyle='--', label=f'Modelo ({metodo.title()})')

    plt.title(f'Estimativa de População para {nome_municipio_exemplo} - Método: {metodo.title()}', fontsize=16)
    plt.xlabel('Ano', fontsize=12)
    plt.ylabel('População Residente', fontsize=12)
    plt.legend()
    plt.tight_layout()

    output_graph_filename = f"grafico_{metodo}_{nome_municipio_exemplo.replace(' ', '_')}.png"
    plt.savefig(output_graph_filename)
    print(f"📈 Gráfico salvo como '{output_graph_filename}'")
    plt.show()

# --- BLOCO PRINCIPAL DE EXECUÇÃO ---
if __name__ == "__main__":
    ARQUIVO_BRUTO = 'tabela6579(2).csv'
    MUNICIPIO_EXEMPLO = 'Miracema do Tocantins'

    # ================================================================= #
    #   ESCOLHA O MÉTODO AQUI                                           #
    #   Opções: 'linear', 'polinomial', 'random_forest', 'spline'       #
    METODO_ESCOLHIDO = 'spline'
    # ================================================================= #

    ARQUIVO_FINAL_SAIDA = f"estimativa_completa_{METODO_ESCOLHIDO}.csv"

    # Etapa 1: Processar o arquivo bruto
    df_processado = processar_dados_brutos(ARQUIVO_BRUTO)

    # Etapa 2: Aplicar o modelo escolhido e estimar os dados faltantes
    if df_processado is not None:
        df_com_estimativas = estimar_populacao_com_modelo(df_processado, metodo=METODO_ESCOLHIDO)

        if df_com_estimativas is not None:
            df_com_estimativas.to_csv(ARQUIVO_FINAL_SAIDA, sep=';', encoding='utf-8-sig', index=False)
            print(f"\n✅ Arquivo final '{ARQUIVO_FINAL_SAIDA}' salvo com sucesso!")

            # Etapa 3: Visualizar um exemplo
            visualizar_resultado_avancado(df_com_estimativas, MUNICIPIO_EXEMPLO, metodo=METODO_ESCOLHIDO)
