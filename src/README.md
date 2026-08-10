# Diagnóstico Situacional em Saúde Pública por Clusterização K-Means

![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

Este projeto apresenta um **framework completo e reutilizável** para análise de dados de saúde pública no Brasil. A arquitetura modular vai desde a coleta automatizada de dados brutos de fontes governamentais até a aplicação de técnicas de machine learning para agrupar municípios segundo seus perfis de saúde.

O objetivo é transformar dados públicos do DATASUS e IBGE em inteligência acionável. Embora o estudo de caso apresentado foque no estado do Tocantins para o ano de 2022, a arquitetura do projeto foi desenhada para ser **facilmente adaptável a qualquer estado ou ano**, bastando a alteração de parâmetros nos scripts.

---

## 🚀 Principais Funcionalidades

- **Coleta Automatizada de Dados:** Scripts para baixar dados diretamente dos sistemas do SUS (SIM, SINASC, CNES, SIH, SINAN).
- **Cálculo de Indicadores:** Automatiza o cálculo de 6 indicadores de saúde fundamentais.
- **Consolidação de Dados:** Integra indicadores em um arquivo único CSV indexado por município para o estado e ano selecionados.
- **Análise de Cluster (K-Means):** Agrupa municípios em perfis de vulnerabilidade/eficiência por meio de K-Means.
- **Visualização:** Gera mapas de calor, "Snake Plots" e outros gráficos para análise e apresentação dos resultados.

---

## 📊 Estudo de Caso: Visualização dos Resultados para o Tocantins (2022)

A análise gera uma série de visualizações que permitem um diagnóstico completo da situação de saúde no estado.

### Mapas de Calor por Indicador

A análise inicial envolve a geração de mapas de calor (coropléticos) para cada indicador individual, permitindo uma visualização direta da distribuição geográfica de cada métrica.

| Taxa de Mortalidade Infantil | Cobertura de Pré-Natal Adequado |
| :---: | :---: |
| ![TMI](mapa_tmi_to_2022.png) | ![Pré-Natal](mapa_cobertura_prenatal_to_2022.png) |
| **Taxa de Médicos por 1.000 Habitantes** | **Proporção de Partos Cesáreos** |
| ![Médicos](mapa_taxa_medicos_to_2022.png) | ![Cesáreas](mapa_prop_cesareos_to_2022.png) |
| **Óbitos Mal Definidos por 10.000 Habitantes** | **Internações por Doenças Crônicas por 10.000 Habitantes** |
| ![Causas Mal Definidas](mapa_taxa_mal_definidas_to_2022.png) | ![Internações Crônicas](mapa_internacoes_cronicas_to_2022.png) |

### Análise de Cluster (K-Means)

Aplicando o algoritmo K-Means, os municípios foram segmentados em grupos distintos com base em seus perfis de saúde. O mapa abaixo mostra a distribuição geográfica desses clusters, revelando "bolsões" de municípios com desafios e potencialidades semelhantes.

![Mapa de Clusters K=4](kmeans_maps_k3_vs_k4.png)

O "Snake Plot" a seguir detalha a "personalidade" de cada cluster, mostrando como a média de seus indicadores se desvia da média estadual, o que permite uma interpretação clara dos desafios e pontos fortes de cada grupo.

![Comparação dos Perfis de Cluster](kmeans_snake_plot_k3_vs_k4.png)

---

## 📚 Fontes de Dados

- SIM (Sistema de Informações sobre Mortalidade)
- SINASC (Sistema de Informações sobre Nascidos Vivos)
- CNES (Cadastro Nacional de Estabelecimentos de Saúde)
- SIH (Sistema de Informações Hospitalares)
- SINAN (Sistema de Informação de Agravos de Notificação)
- FTP do IBGE (Censo Demográfico 2022)

Todos os dados são públicos e obtidos via DATASUS e IBGE.

---

## ⚙️ Como Usar

1.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Baixe os Shapefiles:** Baixe os shapefiles dos municípios brasileiros (ano 2022) diretamente do [portal do IBGE](https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/34774-malhas-digitais-2022.html?=&t=downloads) e coloque os arquivos na pasta `shapefiles/`.

3.  **Gere a Base Populacional:**
    ```bash
    python populacao.py
    ```
    > **Obs:** Este passo cria o arquivo `populacao_brasil_censo_2022_com_estado.csv`, que é essencial para os próximos scripts.

### 🌎 Adaptando para Outros Estados e Anos

O principal poder deste projeto é sua flexibilidade. Para analisar um estado ou ano diferente, basta abrir os scripts de cálculo (ex: `mortalidade_infantil.py`, `medicos.py`, etc.) e **modificar as variáveis no topo do arquivo**:

```python
# Exemplo dentro de um dos scripts de indicador
UF_SIGLA = 'SP'  # Altere de 'TO' para a sigla do estado desejado (ex: 'SP', 'BA', 'MG')
ANO = 2021       # Altere para o ano desejado
```

### Execução do Fluxo de Análise

4.  **Execute o Orquestrador:**
    ```bash
    python orquestrador.py
    ```
    > Este script irá calcular todos os indicadores para a UF e ano definidos e gerar o arquivo `indicadores_integrados_[uf]_[ano].csv`.

5.  **Execute a Análise de Cluster:**
    Antes de executar, certifique-se de que o nome do arquivo CSV no script `analise_cluster.py` corresponde ao arquivo gerado pelo orquestrador.
    ```bash
    python analise_cluster.py
    ```
    > Este script lê o arquivo consolidado e gera as visualizações de análise.

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Abra uma issue ou envie um pull request para sugestões, correções ou melhorias.

---

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para detalhes.
