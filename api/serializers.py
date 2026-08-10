# api/serializers.py

from rest_framework import serializers
from .models import ManagedFile, Profile
from dj_rest_auth.registration.serializers import RegisterSerializer
from dj_rest_auth.serializers import UserDetailsSerializer as DjRestAuthUserDetailsSerializer

# Importar os modelos de TaskStatus das suas pipelines
from api.pipeline_indicadores.models import IntegracaoTaskStatus
from api.pipeline_kmeans.models import KMeansTaskStatus
from api.pipeline_predicao_internacoes.models import PredictionTaskStatus
from .pipeline_regressao_obitos.models import RegressaoObitosTaskStatus
from .pipeline_fluxo_pacientes.models import FluxoPacientesTaskStatus
from .pipeline_fluxo_pacientes.models import FluxoPacientesTaskStatus
from .pipeline_risco_readmissao.models import ReadmissaoTaskStatus
from .pipeline_custo_internacao.models import CustoInternacaoTaskStatus
from .pipeline_deteccao_surtos.models import DeteccaoSurtosTaskStatus
from .pipeline_los_hibrido.models import LosHibridoTaskStatus
from .pipeline_risco_perinatal.models import PerinatalTaskStatus
from .pipeline_sobrevida_infantil.models import SobrevidaInfantilTaskStatus
from .pipeline_doencas_cronicas.models import DoencasCronicasTaskStatus
from .pipeline_hospitalizacao_rdf.models import HospitalizacaoRDFTaskStatus
from .pipeline_population_space.models import PopulationSpaceTaskStatus
from .pipeline_fluxo_partos.models import FluxoPartosTaskStatus
from .pipeline_previsao_obitos.models import PrevisaoObitosTaskStatus
from .pipeline_previsao_nascimentos.models import PrevisaoNascimentosTaskStatus
from .pipeline_previsao_producao_ambulatorial.models import PrevisaoProducaoAmbulatorialTaskStatus
from .pipeline_indices_compostos.models import IndiceCompostoTaskStatus
from .pipeline_fluxo_alta_complexidade.models import FluxoAltaComplexidadeTaskStatus
from .pipeline_difusao_espacial_surto.models import DifusaoEspacialSurtoTaskStatus
from .pipeline_desertos_assistenciais.models import DesertosAssistenciaisTaskStatus
from .pipeline_moran_mortalidade.models import MoranMortalidadeTaskStatus
from .pipeline_lisa_sinan.models import LisaSinanTaskStatus
from .pipeline_hotspots_internacao.models import HotspotsInternacaoTaskStatus
from .pipeline_moran_bivariado.models import MoranBivariadoTaskStatus
from .pipeline_painel_geografico.models import PainelGeograficoTaskStatus
from .pipeline_bayes_pequenas_areas.models import BayesPequenasAreasTaskStatus
from .pipeline_changepoint_bayesiano.models import ChangepointBayesianoTaskStatus
from .pipeline_binomial_negativa.models import BinomialNegativaTaskStatus
from .pipeline_stl_sarima_arboviroses.models import StlSarimaArbovirosesTaskStatus
from .pipeline_quebra_estrutural.models import QuebraEstruturalTaskStatus
from .pipeline_excesso_mortalidade.models import ExcessoMortalidadeTaskStatus
from .pipeline_sobrevida_tb.models import SobrevidaTbTaskStatus
from .pipeline_sobrevida_permanencia.models import SobrevidaPermanenciaTaskStatus
from .pipeline_sobrevida_reincidencia.models import SobrevidaReincidenciaTaskStatus
from .pipeline_rede_comorbidades.models import RedeComorbidadesTaskStatus
from .pipeline_rede_especializacao.models import RedeEspecializacaoTaskStatus
from .pipeline_diff_in_diff.models import DiffInDiffTaskStatus
from .pipeline_rdd_peso_nascer.models import RddPesoNascerTaskStatus
from .pipeline_gravidade_texto.models import GravidadeTextoTaskStatus
from .pipeline_similaridade_relatos.models import SimilaridadeRelatosTaskStatus
from .pipeline_isolation_forest.models import IsolationForestTaskStatus
from .pipeline_hdbscan_estabelecimentos.models import HdbscanEstabelecimentosTaskStatus
from .pipeline_umap_perfis.models import UmapPerfisTaskStatus
from .pipeline_analise_fatorial.models import AnaliseFatorialTaskStatus
from .pipeline_obito_materno.models import ObitoMaternoTaskStatus
from .pipeline_sifilis_congenita.models import SifilisCongenitaTaskStatus
from .pipeline_obito_neonatal.models import ObitoNeonatalTaskStatus
from .pipeline_uti_neonatal.models import UtiNeonatalTaskStatus
from .pipeline_robson.models import RobsonTaskStatus
from .pipeline_kotelchuck.models import KotelchuckTaskStatus
from .pipeline_abandono_hanseniase.models import AbandonoHanseniaseTaskStatus

# ⭐ 2. ADICIONE ESTA NOVA CLASSE AO FINAL DO FICHEIRO ⭐
class ReadmissaoTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    # Adiciona um campo para obter o URL da imagem de resultado
    output_image_url = serializers.ImageField(source='output_image_file.file', read_only=True)

    class Meta:
        model = ReadmissaoTaskStatus
        fields = '__all__'


class FluxoPacientesTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = FluxoPacientesTaskStatus
        fields = '__all__'

class RegressaoObitosTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = RegressaoObitosTaskStatus
        fields = '__all__'

class HospitalizacaoRDFTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = HospitalizacaoRDFTaskStatus
        fields = '__all__'


class PopulationSpaceTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = PopulationSpaceTaskStatus
        fields = '__all__'


class CustomRegisterSerializer(RegisterSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._has_phone_field = False


class CustomUserDetailsSerializer(DjRestAuthUserDetailsSerializer):
    """
    Estende o serializer padrão do dj-rest-auth para expor has_bpho_access,
    permitindo que o frontend saiba, logo após o login, se o usuário pode
    acessar a BPHO/PopulationSpace.
    """
    has_bpho_access = serializers.SerializerMethodField()

    class Meta(DjRestAuthUserDetailsSerializer.Meta):
        fields = DjRestAuthUserDetailsSerializer.Meta.fields + ('has_bpho_access',)

    def get_has_bpho_access(self, obj):
        profile, _ = Profile.objects.get_or_create(user=obj)
        return profile.has_bpho_access


class ManagedFileSerializer(serializers.ModelSerializer):
    uploader_username = serializers.CharField(source='uploader.username', read_only=True)

    class Meta:
        model = ManagedFile
        fields = ['id', 'file', 'filename', 'description', 'uploaded_at', 'uploader_username', 'file_type', 'task_id']


class ArchetypeDataSerializer(serializers.Serializer):
    filename = serializers.CharField(max_length=255, required=True)
    data_rows = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
        required=True
    )
    indicator_columns = serializers.ListField(child=serializers.CharField(), min_length=1, required=True)
    profile_column_name = serializers.CharField(max_length=100, required=True)
    color_column_name = serializers.CharField(max_length=100, required=False, allow_blank=True)


# ⭐ NOVOS SERIALIZERS PARA TASK STATUS ⭐

class IntegracaoTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True) # Nome do arquivo de saída

    class Meta:
        model = IntegracaoTaskStatus
        fields = '__all__'
        read_only_fields = ('task_id', 'user', 'status', 'created_at', 'updated_at', 'message', 'output_file', 'output_file_id', 'output_file_filename')


class KMeansTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    input_file_filename = serializers.CharField(source='input_file.filename', read_only=True) # Nome do arquivo de entrada
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True) # Nome do arquivo de saída

    class Meta:
        model = KMeansTaskStatus
        fields = '__all__'
        read_only_fields = ('task_id', 'user', 'status', 'created_at', 'updated_at', 'message', 'input_file', 'output_file', 'input_file_filename', 'output_file_id', 'output_file_filename')


class PredictionTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True) # Nome do arquivo de saída

    class Meta:
        model = PredictionTaskStatus
        fields = '__all__'
        read_only_fields = ('task_id', 'user', 'status', 'created_at', 'updated_at', 'message', 'output_file', 'output_file_id', 'output_file_filename')


class CustoInternacaoTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_image_url = serializers.SerializerMethodField()
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = CustoInternacaoTaskStatus
        fields = '__all__'

    def get_output_image_url(self, obj):
        if obj.output_image_file and obj.output_image_file.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.output_image_file.file.url)
            return obj.output_image_file.file.url
        return None


class DeteccaoSurtosTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)
    chart_data_file_id = serializers.PrimaryKeyRelatedField(source='chart_data_file', read_only=True)

    class Meta:
        model = DeteccaoSurtosTaskStatus
        fields = '__all__'


class LosHibridoTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)
    output_image_url = serializers.SerializerMethodField()

    class Meta:
        model = LosHibridoTaskStatus
        fields = '__all__'

    def get_output_image_url(self, obj):
        if obj.output_image_file and obj.output_image_file.file:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.output_image_file.file.url)
            return obj.output_image_file.file.url
        return None


class PerinatalTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)

    class Meta:
        model = PerinatalTaskStatus
        fields = '__all__'


class SobrevidaInfantilTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)

    class Meta:
        model = SobrevidaInfantilTaskStatus
        fields = '__all__'


class DoencasCronicasTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)

    class Meta:
        model = DoencasCronicasTaskStatus
        fields = '__all__'


class MoranMortalidadeTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = MoranMortalidadeTaskStatus
        fields = '__all__'


class LisaSinanTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = LisaSinanTaskStatus
        fields = '__all__'


class HotspotsInternacaoTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = HotspotsInternacaoTaskStatus
        fields = '__all__'


class MoranBivariadoTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = MoranBivariadoTaskStatus
        fields = '__all__'


class PainelGeograficoTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = PainelGeograficoTaskStatus
        fields = '__all__'


class BayesPequenasAreasTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = BayesPequenasAreasTaskStatus
        fields = '__all__'


class ChangepointBayesianoTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = ChangepointBayesianoTaskStatus
        fields = '__all__'


class BinomialNegativaTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = BinomialNegativaTaskStatus
        fields = '__all__'


class StlSarimaArbovirosesTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = StlSarimaArbovirosesTaskStatus
        fields = '__all__'


class QuebraEstruturalTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = QuebraEstruturalTaskStatus
        fields = '__all__'


class ExcessoMortalidadeTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = ExcessoMortalidadeTaskStatus
        fields = '__all__'


class SobrevidaTbTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = SobrevidaTbTaskStatus
        fields = '__all__'


class SobrevidaPermanenciaTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = SobrevidaPermanenciaTaskStatus
        fields = '__all__'


class SobrevidaReincidenciaTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = SobrevidaReincidenciaTaskStatus
        fields = '__all__'


class RedeComorbidadesTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = RedeComorbidadesTaskStatus
        fields = '__all__'


class RedeEspecializacaoTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = RedeEspecializacaoTaskStatus
        fields = '__all__'


class DiffInDiffTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = DiffInDiffTaskStatus
        fields = '__all__'


class RddPesoNascerTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = RddPesoNascerTaskStatus
        fields = '__all__'


class GravidadeTextoTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = GravidadeTextoTaskStatus
        fields = '__all__'


class SimilaridadeRelatosTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = SimilaridadeRelatosTaskStatus
        fields = '__all__'


class IsolationForestTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = IsolationForestTaskStatus
        fields = '__all__'


class HdbscanEstabelecimentosTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = HdbscanEstabelecimentosTaskStatus
        fields = '__all__'


class UmapPerfisTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = UmapPerfisTaskStatus
        fields = '__all__'


class AnaliseFatorialTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = AnaliseFatorialTaskStatus
        fields = '__all__'


class ObitoMaternoTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = ObitoMaternoTaskStatus
        fields = '__all__'


class SifilisCongenitaTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = SifilisCongenitaTaskStatus
        fields = '__all__'


class ObitoNeonatalTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = ObitoNeonatalTaskStatus
        fields = '__all__'


class UtiNeonatalTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = UtiNeonatalTaskStatus
        fields = '__all__'


class RobsonTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = RobsonTaskStatus
        fields = '__all__'


class KotelchuckTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = KotelchuckTaskStatus
        fields = '__all__'


class AbandonoHanseniaseTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = AbandonoHanseniaseTaskStatus
        fields = '__all__'


class FluxoPartosTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = FluxoPartosTaskStatus
        fields = '__all__'

class PrevisaoObitosTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = PrevisaoObitosTaskStatus
        fields = '__all__'

class PrevisaoNascimentosTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = PrevisaoNascimentosTaskStatus
        fields = '__all__'

class PrevisaoProducaoAmbulatorialTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = PrevisaoProducaoAmbulatorialTaskStatus
        fields = '__all__'


class IndiceCompostoTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = IndiceCompostoTaskStatus
        fields = '__all__'


class FluxoAltaComplexidadeTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = FluxoAltaComplexidadeTaskStatus
        fields = '__all__'


class DifusaoEspacialSurtoTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = DifusaoEspacialSurtoTaskStatus
        fields = '__all__'


class DesertosAssistenciaisTaskStatusSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source='user.username', read_only=True)
    output_file_id = serializers.PrimaryKeyRelatedField(source='output_file', read_only=True)
    output_file_filename = serializers.CharField(source='output_file.filename', read_only=True)

    class Meta:
        model = DesertosAssistenciaisTaskStatus
        fields = '__all__'


