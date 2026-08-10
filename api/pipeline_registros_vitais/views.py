# api/pipeline_registros_vitais/views.py
#
# Proxy síncrono para a BPHO, mesma disciplina de api.pipeline_ontologia/
# api.pipeline_cnes_validity: sem models.py, sem Celery, cada view consulta o
# endpoint SPARQL somente-leitura da BPHO direto.
#
# Expõe Birth (SINASC, Fase 66) e Death/CauseOfDeath (SIM, Fase 68) --
# "registros vitais" é o nome usual, em demografia/vigilância em saúde, para
# nascimentos e óbitos tratados como um par temático -- os dois eventos que
# demarcam o início e o fim de uma vida, e os dois sistemas administrativos
# mais próximos disso no DATASUS (SINASC/SIM).

import logging

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from api.permissions import HasBphoAccess
from rest_framework.response import Response

logger = logging.getLogger(__name__)

PREFIX = "PREFIX : <http://datasus-ontology.local/onto#>\n"

Q_FACILITY_BIRTHS = PREFIX + "SELECT (COUNT(?b) AS ?n) WHERE { ?b a :Birth ; :atFacility :facility_%(cnes)s }"
Q_FACILITY_DEATHS = PREFIX + "SELECT (COUNT(?d) AS ?n) WHERE { ?d a :Death ; :atFacility :facility_%(cnes)s }"

Q_TOTAL_BIRTHS = PREFIX + "SELECT (COUNT(?b) AS ?n) WHERE { ?b a :Birth }"
Q_TOTAL_DEATHS = PREFIX + "SELECT (COUNT(?d) AS ?n) WHERE { ?d a :Death }"

# "Causa final" = CauseOfDeath que ninguém mais revisa (exclui a versão
# ORIGINAL de uma revisão, que é sempre o objeto de algum :revises).
Q_TOP_CAUSES = PREFIX + """
    SELECT ?code (COUNT(*) AS ?n) WHERE {
        ?c a :CauseOfDeath ; :icdCode ?code .
        FILTER NOT EXISTS { ?other :revises ?c }
    } GROUP BY ?code ORDER BY DESC(?n) LIMIT 15
"""

Q_REVISION_COUNT = PREFIX + "SELECT (COUNT(*) AS ?n) WHERE { ?x :revises ?y }"


def _query_bpho(sparql_query: str) -> dict:
    resp = requests.get(
        settings.BPHO_SPARQL_URL,
        params={"query": sparql_query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


def _n(data: dict) -> int:
    return int(data["results"]["bindings"][0]["n"]["value"])


@api_view(["GET"])
@permission_classes([HasBphoAccess])
def facility_vitals(request, cnes):
    """Contagem de Birth/Death num estabelecimento -- ambos podem ser zero
    (a maioria dos estabelecimentos não tem nascimento nem óbito real
    registrado; nem todo estabelecimento faz parto ou concentra óbitos)."""
    try:
        births = _query_bpho(Q_FACILITY_BIRTHS % {"cnes": cnes})
        deaths = _query_bpho(Q_FACILITY_DEATHS % {"cnes": cnes})
    except requests.RequestException as e:
        logger.warning("BPHO SPARQL endpoint indisponível: %s", e)
        return Response({"error": "Endpoint SPARQL da BPHO indisponível.", "detail": str(e)},
                         status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({"cnes": cnes, "births": _n(births), "deaths": _n(deaths)})


@api_view(["GET"])
@permission_classes([HasBphoAccess])
def summary(request):
    """Panorama nacional: total de nascimentos/óbitos reais, as 15 causas
    básicas de óbito mais frequentes (código CID, só a versão FINAL da causa
    quando houve revisão), e quantas revisões reais de causa básica existem
    no grafo (CAUSABAS_O != CAUSABAS, achado real da Fase 68)."""
    try:
        births = _query_bpho(Q_TOTAL_BIRTHS)
        deaths = _query_bpho(Q_TOTAL_DEATHS)
        causes = _query_bpho(Q_TOP_CAUSES)
        revisions = _query_bpho(Q_REVISION_COUNT)
    except requests.RequestException as e:
        logger.warning("BPHO SPARQL endpoint indisponível: %s", e)
        return Response({"error": "Endpoint SPARQL da BPHO indisponível.", "detail": str(e)},
                         status=status.HTTP_503_SERVICE_UNAVAILABLE)

    top_causes = [
        {"icd_code": b["code"]["value"], "count": int(b["n"]["value"])}
        for b in causes["results"]["bindings"]
    ]
    return Response({
        "total_births": _n(births),
        "total_deaths": _n(deaths),
        "top_causes_of_death": top_causes,
        "cause_of_death_revisions": _n(revisions),
    })
