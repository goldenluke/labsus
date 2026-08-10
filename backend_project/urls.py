# backend_project/urls.py

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),

    # ⭐ ESTA LINHA INCLUI AS ROTAS GERAIS DA API (que usam api/views.py) ⭐
    path('api/', include('api.urls')),
    path('api/pipelines/regressao-obitos/', include('api.pipeline_regressao_obitos.urls')),
    # ⭐ ESTA LINHA INCLUI TODAS AS ROTAS DO SEU APP DE PIPELINES (INDICADORES E INTEGRAÇÃO) ⭐
    # O prefixo 'pipelines/indicadores/' aqui é crucial.
    path('api/pipelines/indicadores/', include('api.pipeline_indicadores.urls')),
    path('api/pipelines/kmeans/', include('api.pipeline_kmeans.urls')),
    path('api/pipelines/predicao/internacoes/', include('api.pipeline_predicao_internacoes.urls')), # CORRIGIDO: Adicionado a barra final aqui
    path('api/pipelines/fluxo-pacientes/', include('api.pipeline_fluxo_pacientes.urls')), # <-- ADICIONE ESTA LINHA
    path('api/pipelines/risco-readmissao/', include('api.pipeline_risco_readmissao.urls')),
    path('api/pipelines/custo-internacao/', include('api.pipeline_custo_internacao.urls')),
    path('api/pipelines/deteccao-surtos/', include('api.pipeline_deteccao_surtos.urls')),
    path('api/pipelines/los-hibrido/', include('api.pipeline_los_hibrido.urls')),
    path('api/pipelines/risco-perinatal/', include('api.pipeline_risco_perinatal.urls')),
    path('api/pipelines/sobrevida-infantil/', include('api.pipeline_sobrevida_infantil.urls')),
    path('api/pipelines/doencas-cronicas/', include('api.pipeline_doencas_cronicas.urls')),
    path('api/pipelines/ontologia/', include('api.pipeline_ontologia.urls')),
    path('api/pipelines/hospitalizacao-rdf/', include('api.pipeline_hospitalizacao_rdf.urls')),
    path('api/pipelines/population-space/', include('api.pipeline_population_space.urls')),
    path('api/pipelines/cnes-validity/', include('api.pipeline_cnes_validity.urls')),
    path('api/pipelines/registros-vitais/', include('api.pipeline_registros_vitais.urls')),
    path('api/pipelines/sinan-vigilancia/', include('api.pipeline_sinan_vigilancia.urls')),
    path('api/pipelines/fluxo-partos/', include('api.pipeline_fluxo_partos.urls')),
    path('api/pipelines/previsao-obitos/', include('api.pipeline_previsao_obitos.urls')),
    path('api/pipelines/previsao-nascimentos/', include('api.pipeline_previsao_nascimentos.urls')),
    path('api/pipelines/previsao-producao-ambulatorial/', include('api.pipeline_previsao_producao_ambulatorial.urls')),
    path('api/pipelines/indices-compostos/', include('api.pipeline_indices_compostos.urls')),
    path('api/pipelines/fluxo-alta-complexidade/', include('api.pipeline_fluxo_alta_complexidade.urls')),
    path('api/pipelines/difusao-espacial-surto/', include('api.pipeline_difusao_espacial_surto.urls')),
    path('api/pipelines/desertos-assistenciais/', include('api.pipeline_desertos_assistenciais.urls')),
    path('api/pipelines/moran-mortalidade/', include('api.pipeline_moran_mortalidade.urls')),
    path('api/pipelines/lisa-sinan/', include('api.pipeline_lisa_sinan.urls')),
    path('api/pipelines/hotspots-internacao/', include('api.pipeline_hotspots_internacao.urls')),
    path('api/pipelines/moran-bivariado/', include('api.pipeline_moran_bivariado.urls')),
    path('api/pipelines/gerar-painel-geografico/', include('api.pipeline_painel_geografico.urls')),
    path('api/pipelines/bayes-pequenas-areas/', include('api.pipeline_bayes_pequenas_areas.urls')),
    path('api/pipelines/changepoint-bayesiano/', include('api.pipeline_changepoint_bayesiano.urls')),
    path('api/pipelines/binomial-negativa/', include('api.pipeline_binomial_negativa.urls')),
    path('api/pipelines/stl-sarima-arboviroses/', include('api.pipeline_stl_sarima_arboviroses.urls')),
    path('api/pipelines/quebra-estrutural/', include('api.pipeline_quebra_estrutural.urls')),
    path('api/pipelines/excesso-mortalidade/', include('api.pipeline_excesso_mortalidade.urls')),
    path('api/pipelines/sobrevida-tb/', include('api.pipeline_sobrevida_tb.urls')),
    path('api/pipelines/sobrevida-permanencia/', include('api.pipeline_sobrevida_permanencia.urls')),
    path('api/pipelines/sobrevida-reincidencia/', include('api.pipeline_sobrevida_reincidencia.urls')),
    path('api/pipelines/rede-comorbidades/', include('api.pipeline_rede_comorbidades.urls')),
    path('api/pipelines/rede-especializacao/', include('api.pipeline_rede_especializacao.urls')),
    path('api/pipelines/diff-in-diff/', include('api.pipeline_diff_in_diff.urls')),
    path('api/pipelines/rdd-peso-nascer/', include('api.pipeline_rdd_peso_nascer.urls')),
    path('api/pipelines/gravidade-texto/', include('api.pipeline_gravidade_texto.urls')),
    path('api/pipelines/similaridade-relatos/', include('api.pipeline_similaridade_relatos.urls')),
    path('api/pipelines/isolation-forest/', include('api.pipeline_isolation_forest.urls')),
    path('api/pipelines/hdbscan-estabelecimentos/', include('api.pipeline_hdbscan_estabelecimentos.urls')),
    path('api/pipelines/umap-perfis/', include('api.pipeline_umap_perfis.urls')),
    path('api/pipelines/analise-fatorial/', include('api.pipeline_analise_fatorial.urls')),
    path('api/pipelines/obito-materno/', include('api.pipeline_obito_materno.urls')),
    path('api/pipelines/sifilis-congenita/', include('api.pipeline_sifilis_congenita.urls')),
    path('api/pipelines/obito-neonatal/', include('api.pipeline_obito_neonatal.urls')),
    path('api/pipelines/uti-neonatal/', include('api.pipeline_uti_neonatal.urls')),
    path('api/pipelines/robson/', include('api.pipeline_robson.urls')),
    path('api/pipelines/kotelchuck/', include('api.pipeline_kotelchuck.urls')),
    path('api/pipelines/abandono-hanseniase/', include('api.pipeline_abandono_hanseniase.urls')),

# ⭐ CORREÇÃO CRÍTICA AQUI: Adicionar URLs para servir MEDIA FILES em DEBUG mode ⭐

]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
