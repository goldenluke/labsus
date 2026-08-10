# -*- coding: utf-8 -*-
"""
Helpers compartilhados pelos índices compostos de src/features/ (Capacidade
Assistencial, Complexidade Hospitalar, Cobertura Assistencial, Diversidade
Assistencial etc.) — evita reimplementar a mesma matemática (diversidade de
Shannon/Simpson, combinação de componentes num índice 0-100) em cada módulo.
"""
import numpy as np
import pandas as pd


def calcular_diversidade(contagens: pd.Series) -> dict:
    """Dado um vetor de contagens (ex.: nº de casos por CID num município),
    retorna o índice de Shannon (H'), o índice de Simpson (1-D, "probabilidade
    de dois casos aleatórios serem de causas diferentes") e a riqueza
    (nº de categorias distintas com pelo menos 1 caso)."""
    contagens = contagens[contagens > 0]
    total = contagens.sum()
    riqueza = int((contagens > 0).sum())
    if total == 0 or riqueza == 0:
        return {'shannon': 0.0, 'simpson': 0.0, 'riqueza': 0}

    proporcoes = contagens / total
    shannon = float(-(proporcoes * np.log(proporcoes)).sum())
    simpson = float(1 - (proporcoes ** 2).sum())
    return {'shannon': shannon, 'simpson': simpson, 'riqueza': riqueza}


def combinar_indice_composto(df: pd.DataFrame, colunas: list, metodo: str = 'pca') -> pd.Series:
    """Combina várias colunas numéricas (ex.: leitos/mil, médicos/mil,
    enfermeiros/mil) num único índice 0-100. Por padrão usa a 1ª componente
    principal (PCA) sobre as colunas padronizadas (mesma abordagem de
    `analise_fatorial_indicadores_saude.py`) — cai para média simples de
    z-scores se houver poucas linhas/variância nula (PCA não converge ou não
    tem sentido com muito poucos municípios)."""
    from sklearn.preprocessing import StandardScaler

    dados = df[colunas].fillna(0)
    if len(dados) < 3 or dados.std().eq(0).all():
        metodo = 'media_zscore'

    scaler = StandardScaler()
    padronizado = scaler.fit_transform(dados)

    if metodo == 'pca':
        try:
            from sklearn.decomposition import PCA
            pca = PCA(n_components=1)
            componente = pca.fit_transform(padronizado).flatten()
            # Garante que o sinal do componente seja "quanto maior, melhor" —
            # PCA não garante isso sozinho, então alinhamos pelo sinal da
            # correlação com a média simples dos componentes de entrada.
            media_simples = padronizado.mean(axis=1)
            if np.corrcoef(componente, media_simples)[0, 1] < 0:
                componente = -componente
        except Exception:
            componente = padronizado.mean(axis=1)
    else:
        componente = padronizado.mean(axis=1)

    minimo, maximo = componente.min(), componente.max()
    if maximo - minimo == 0:
        return pd.Series(50.0, index=df.index)
    indice_0_100 = (componente - minimo) / (maximo - minimo) * 100
    return pd.Series(indice_0_100, index=df.index)


def normalizar_0_1(serie: pd.Series, epsilon: float = 1e-6) -> pd.Series:
    """Min-max simples para [epsilon, 1] — usado nas fórmulas de razão dos
    índices de 2ª camada (ex.: HSRI = Capacidade / (Demanda × Mortalidade)),
    onde um componente no denominador não pode ser exatamente 0."""
    minimo, maximo = serie.min(), serie.max()
    if maximo - minimo == 0:
        return pd.Series(0.5, index=serie.index)
    return epsilon + (serie - minimo) / (maximo - minimo) * (1 - epsilon)


def indice_gini(valores: pd.Series) -> float:
    """Coeficiente de Gini (0 = distribuição perfeitamente igual, 1 = toda a
    grandeza concentrada num único município)."""
    x = np.sort(valores.dropna().values.astype(float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return 0.0
    indice = np.arange(1, n + 1)
    return float((2 * (indice * x).sum() - (n + 1) * x.sum()) / (n * x.sum()))


def indice_theil(valores: pd.Series) -> float:
    """Índice T de Theil (0 = igualdade perfeita; cresce sem limite superior
    fixo com a concentração — decompõe-se em componentes intra/entre grupos,
    o que o Gini não faz, mas aqui usamos só o valor agregado)."""
    x = valores.dropna().values.astype(float)
    x = x[x > 0]
    if len(x) == 0:
        return 0.0
    media = x.mean()
    if media == 0:
        return 0.0
    razao = x / media
    return float((razao * np.log(razao)).mean())


def indice_hoover(valores: pd.Series) -> float:
    """Índice de Hoover/Robin Hood: proporção da grandeza total que teria de
    ser redistribuída para atingir igualdade perfeita entre os municípios."""
    x = valores.dropna().values.astype(float)
    total = x.sum()
    n = len(x)
    if total == 0 or n == 0:
        return 0.0
    media = total / n
    return float(np.abs(x - media).sum() / (2 * total))


def indice_palma(valores: pd.Series) -> float:
    """Razão de Palma: soma do decil mais rico (top 10%) sobre a soma dos 4
    decis mais pobres (bottom 40%) — mais sensível às extremidades da
    distribuição do que Gini/Theil."""
    x = np.sort(valores.dropna().values.astype(float))
    n = len(x)
    if n < 10:
        return 0.0
    corte_40 = max(1, int(np.floor(n * 0.4)))
    corte_90 = int(np.ceil(n * 0.9))
    soma_bottom40 = x[:corte_40].sum()
    soma_top10 = x[corte_90:].sum()
    if soma_bottom40 == 0:
        return 0.0
    return float(soma_top10 / soma_bottom40)


def metricas_estabilidade_serie(serie: pd.Series) -> dict:
    """Métricas de estabilidade dinâmica de uma série temporal (por município,
    um valor por ano): variância, autocorrelação lag-1 (memória/"critical
    slowing down" — quanto mais perto de 1, mais lenta a série volta ao
    equilíbrio após um choque, sinal precoce de transição crítica),
    assimetria (skewness), curtose (kurtosis) e coeficiente de variação."""
    x = serie.dropna().astype(float)
    if len(x) < 4:
        return {'variancia': 0.0, 'autocorrelacao_lag1': 0.0, 'skewness': 0.0, 'kurtosis': 0.0, 'coef_variacao': 0.0}

    variancia = float(x.var())
    media = float(x.mean())
    autocorrelacao_lag1 = float(x.autocorr(lag=1)) if len(x) > 1 else 0.0
    if np.isnan(autocorrelacao_lag1):
        autocorrelacao_lag1 = 0.0
    skewness = float(x.skew())
    kurtosis = float(x.kurt())
    coef_variacao = float(x.std() / media) if media != 0 else 0.0

    return {
        'variancia': variancia,
        'autocorrelacao_lag1': autocorrelacao_lag1,
        'skewness': 0.0 if np.isnan(skewness) else skewness,
        'kurtosis': 0.0 if np.isnan(kurtosis) else kurtosis,
        'coef_variacao': coef_variacao,
    }


def metricas_pico_recuperacao(serie: pd.Series, limiar_recuperacao: float = 1.1) -> dict:
    """Proxy estrutural (sem ajuste de modelo) para tempo-até-pico e
    tempo-até-recuperação de uma série temporal anual: localiza o ano de
    valor máximo e mede quantos anos depois a série volta a ficar abaixo de
    `limiar_recuperacao` vezes o valor do primeiro ano (baseline). Se nunca
    recupera dentro da janela, tempo_recuperacao fica em branco (NaN)."""
    x = serie.dropna().astype(float)
    if len(x) < 3:
        return {'tempo_ate_pico': np.nan, 'tempo_ate_recuperacao': np.nan, 'velocidade_recuperacao': np.nan}

    anos_idx = list(range(len(x)))
    valores = x.values
    baseline = valores[0]
    idx_pico = int(np.argmax(valores))
    tempo_ate_pico = anos_idx[idx_pico] - anos_idx[0]

    tempo_ate_recuperacao = np.nan
    for i in range(idx_pico + 1, len(valores)):
        if baseline == 0 or valores[i] <= baseline * limiar_recuperacao:
            tempo_ate_recuperacao = anos_idx[i] - anos_idx[idx_pico]
            break

    velocidade_recuperacao = (
        (valores[idx_pico] - baseline) / tempo_ate_recuperacao
        if tempo_ate_recuperacao and tempo_ate_recuperacao > 0 else np.nan
    )

    return {
        'tempo_ate_pico': float(tempo_ate_pico),
        'tempo_ate_recuperacao': float(tempo_ate_recuperacao) if not np.isnan(tempo_ate_recuperacao) else np.nan,
        'velocidade_recuperacao': float(velocidade_recuperacao) if not np.isnan(velocidade_recuperacao) else np.nan,
    }
