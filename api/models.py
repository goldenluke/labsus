# api/models.py
from django.db import models
from django.conf import settings

# Define as escolhas para o tipo de arquivo
class FileType(models.TextChoices):
    INDICATORS = 'INDICATORS', 'Indicadores de Saúde'
    K_MEANS = 'K_MEANS', 'K-means de Perfis de Saúde'
    ARCHETYPE = 'ARCHETYPE', 'Definição de Arquétipo'
    PREDICTION = 'PREDICTION', 'Previsão de Internações'
    PATIENT_FLOW = 'PATIENT_FLOW', 'Fluxo de Pacientes' # ⭐ ADICIONE ESTA LINHA
    RISK_PREDICTION = 'RISK_PREDICTION', 'Previsão de Risco (Individual)'
    # ⭐ ADICIONE A NOVA LINHA AQUI ⭐
    LOGISTIC_REGRESSION = 'LOGISTIC_REGRESSION', 'Regressão Logística'
    COST_PREDICTION = 'COST_PREDICTION', 'Previsão de Custo'
    DETECCAO_SURTOS = 'DETECCAO_SURTOS', 'Detecção de Surtos'
    CHART_DATA = 'CHART_DATA', 'Dados Internos de Gráfico'
    LOS_HIBRIDO = 'LOS_HIBRIDO', 'LOS Híbrido'
    RISK_PRENATAL = 'RISK_PRENATAL', 'Risco Perinatal'
    INFANT_SURVIVAL = 'INFANT_SURVIVAL', 'Sobrevida Infantil'
    COX_READMISSION = 'COX_READMISSION', 'Cox Readmissão'
    DOENCAS_CRONICAS = 'DOENCAS_CRONICAS', 'Doenças Crônicas'
    HOSPITALIZACAO_RDF = 'HOSPITALIZACAO_RDF', 'Hospitalização (BPHO/RDF)'
    POPULATION_SPACE = 'POPULATION_SPACE', 'PopulationSpace (BioSpace)'
    POP_COMPARE = 'POP_COMPARE', 'PopulationSpace: Comparação'
    POP_CAUSAL = 'POP_CAUSAL', 'PopulationSpace: Análise Causal'
    POP_ANOMALY = 'POP_ANOMALY', 'PopulationSpace: Anomalias'
    POP_RISK = 'POP_RISK', 'PopulationSpace: Score de Risco'
    POP_UNCERTAINTY = 'POP_UNCERTAINTY', 'PopulationSpace: Previsão com Incerteza'
    POP_CLASSIFY = 'POP_CLASSIFY', 'PopulationSpace: Classificador'
    POP_TRANSITIONS = 'POP_TRANSITIONS', 'PopulationSpace: Transições de Fenótipo'
    POP_SURVIVAL = 'POP_SURVIVAL', 'PopulationSpace: Sobrevida (Fenótipo)'
    POP_INTERVENE = 'POP_INTERVENE', 'PopulationSpace: Intervenção (Contrafactual)'
    POP_GRAPH = 'POP_GRAPH', 'PopulationSpace: Grafo de Similaridade'
    POP_FACTOR = 'POP_FACTOR', 'PopulationSpace: Fatores Latentes'
    POP_TOPOLOGY = 'POP_TOPOLOGY', 'PopulationSpace: Topologia'
    POP_EARLY_WARNING = 'POP_EARLY_WARNING', 'PopulationSpace: Alerta Precoce'
    POP_GNN = 'POP_GNN', 'PopulationSpace: GNN (Classificação de Nós)'
    POP_DYNAMICS = 'POP_DYNAMICS', 'PopulationSpace: Dinâmica & Estabilidade'
    POP_PER_CAPITA = 'POP_PER_CAPITA', 'PopulationSpace: Per Capita (Taxa Populacional)'
    POP_MUNICIPIO = 'POP_MUNICIPIO', 'PopulationSpace: Município'
    POP_NOTIFICACAO = 'POP_NOTIFICACAO', 'PopulationSpace: Caso de Notificação'
    POP_FAMILIA = 'POP_FAMILIA', 'PopulationSpace: Família'

    # --- Modelagem Avançada (30 novos modelos de src/modelagem) ---
    MORAN_MORTALIDADE = 'MORAN_MORTALIDADE', 'Moran Global: Mortalidade Infantil'
    LISA_SINAN = 'LISA_SINAN', 'LISA: Clusters de Agravo SINAN'
    HOTSPOTS_INTERNACAO = 'HOTSPOTS_INTERNACAO', 'Getis-Ord: Hotspots de Internação'
    MORAN_BIVARIADO = 'MORAN_BIVARIADO', 'Moran Bivariado: IVS x Mortalidade'
    BAYES_PEQUENAS_AREAS = 'BAYES_PEQUENAS_AREAS', 'Bayesiano: Pequenas Áreas'
    CHANGEPOINT_BAYESIANO = 'CHANGEPOINT_BAYESIANO', 'Bayesiano: Changepoint de Surto'
    BINOMIAL_NEGATIVA = 'BINOMIAL_NEGATIVA', 'GLM Binomial Negativa'
    STL_SARIMA_ARBOVIROSES = 'STL_SARIMA_ARBOVIROSES', 'STL+SARIMA: Arboviroses'
    QUEBRA_ESTRUTURAL = 'QUEBRA_ESTRUTURAL', 'Quebra Estrutural: Óbitos'
    EXCESSO_MORTALIDADE = 'EXCESSO_MORTALIDADE', 'Excesso de Mortalidade'
    SOBREVIDA_TB = 'SOBREVIDA_TB', 'Sobrevida: Tratamento de TB'
    SOBREVIDA_PERMANENCIA = 'SOBREVIDA_PERMANENCIA', 'Sobrevida: Permanência Hospitalar'
    SOBREVIDA_REINCIDENCIA = 'SOBREVIDA_REINCIDENCIA', 'Sobrevida: Reincidência Causa Externa'
    REDE_COMORBIDADES = 'REDE_COMORBIDADES', 'Rede: Coocorrência de Comorbidades'
    REDE_ESPECIALIZACAO = 'REDE_ESPECIALIZACAO', 'Rede: Especialização de Estabelecimentos'
    DIFF_IN_DIFF = 'DIFF_IN_DIFF', 'Diferenças-em-Diferenças'
    RDD_PESO_NASCER = 'RDD_PESO_NASCER', 'RDD: Limiar de Peso ao Nascer'
    GRAVIDADE_TEXTO = 'GRAVIDADE_TEXTO', 'NLP: Gravidade por Texto Clínico'
    SIMILARIDADE_RELATOS = 'SIMILARIDADE_RELATOS', 'NLP: Similaridade de Relatos'
    ISOLATION_FOREST = 'ISOLATION_FOREST', 'Isolation Forest: Auditoria Financeira'
    HDBSCAN_ESTABELECIMENTOS = 'HDBSCAN_ESTABELECIMENTOS', 'HDBSCAN: Estabelecimentos Atípicos'
    UMAP_PERFIS = 'UMAP_PERFIS', 'UMAP+HDBSCAN: Perfis Municipais'
    ANALISE_FATORIAL = 'ANALISE_FATORIAL', 'Análise Fatorial: Indicadores'
    OBITO_MATERNO = 'OBITO_MATERNO', 'Triagem: Óbito Materno'
    SIFILIS_CONGENITA = 'SIFILIS_CONGENITA', 'Determinantes: Sífilis Congênita'
    OBITO_NEONATAL = 'OBITO_NEONATAL', 'Óbito Neonatal: Precoce vs Tardio'
    UTI_NEONATAL = 'UTI_NEONATAL', 'Score: Demanda de UTI Neonatal'
    ROBSON = 'ROBSON', 'Classificação de Robson'
    KOTELCHUCK = 'KOTELCHUCK', 'Índice de Kotelchuck'
    ABANDONO_HANSENIASE = 'ABANDONO_HANSENIASE', 'Risco de Abandono: Hanseníase'
    PAINEL_GEOGRAFICO_IVS = 'PAINEL_GEOGRAFICO_IVS', 'Painel Geográfico (IVS + CNES)'

    FLUXO_PARTOS = 'FLUXO_PARTOS', 'Mapa de Fluxo de Partos'
    FLUXO_ALTA_COMPLEXIDADE = 'FLUXO_ALTA_COMPLEXIDADE', 'Mapa de Fluxo de Alta Complexidade'
    DIFUSAO_ESPACIAL_SURTO = 'DIFUSAO_ESPACIAL_SURTO', 'Difusão Espacial de Surto'
    DESERTOS_ASSISTENCIAIS = 'DESERTOS_ASSISTENCIAIS', 'Mapa de Desertos Assistenciais'
    PREVISAO_OBITOS = 'PREVISAO_OBITOS', 'Previsão de Óbitos (Prophet)'
    PREVISAO_NASCIMENTOS = 'PREVISAO_NASCIMENTOS', 'Previsão de Nascimentos (Prophet)'
    PREVISAO_PROD_AMB = 'PREVISAO_PROD_AMB', 'Previsão de Produção Ambulatorial (Prophet)'
    INDICE_COMPOSTO = 'INDICE_COMPOSTO', 'Índice Composto (HSRI/HNFI/MECI/CCI/HAE/HVS/TERI/PHSI/HSSI/HEI)'
    OTHER = 'OTHER', 'Outro' # Tipo genérico para outros CSVs

# GARANTA QUE O NOME DA CLASSE É ESTE
class ManagedFile(models.Model):
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/csvs/')
    filename = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    task_id = models.UUIDField(null=True, blank=True, help_text="ID da tarefa Celery que gerou este arquivo.")

    file_type = models.CharField(
        max_length=25, # Aumentado para acomodar o novo nome
        choices=FileType.choices,
        default=FileType.INDICATORS,
        help_text="Classificação do conteúdo do arquivo CSV para visualização."
    )

    def __str__(self):
        return f"{self.filename} (por: {self.uploader.username}, Tipo: {self.get_file_type_display()})"


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    has_bpho_access = models.BooleanField(
        default=False,
        help_text="Libera acesso à BPHO/PopulationSpace e demais pipelines que consultam a ontologia (alto custo computacional).",
    )

    def __str__(self):
        return f"{self.user.username} (BPHO: {'sim' if self.has_bpho_access else 'não'})"
