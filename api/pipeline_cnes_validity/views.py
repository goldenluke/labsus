# api/pipeline_cnes_validity/views.py
#
# Proxy síncrono para a BPHO -- mesma disciplina de api.pipeline_ontologia:
# nenhum estado próprio (sem models.py, sem Celery), cada view consulta o
# endpoint SPARQL somente-leitura da BPHO (settings.BPHO_SPARQL_URL) direto.
#
# Expõe :Validity (Fase 65 da BPHO) -- qualificações regulatórias do CNES
# (habilitação de serviço, meta de gestão, incentivo financeiro, regra
# contratual, status de estabelecimento filantrópico/de ensino), com período
# de vigência (:validFrom/:validUntil).

import logging

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from api.permissions import HasBphoAccess
from rest_framework.response import Response

logger = logging.getLogger(__name__)

PREFIX = "PREFIX : <http://datasus-ontology.local/onto#>\n"

Q_FACILITY = PREFIX + """
    SELECT ?kind ?validFrom ?validUntil WHERE {
        ?v a :Validity ; :heldBy :facility_%(cnes)s ; :hasValidityKind ?kind ; :validFrom ?vf .
        ?vf :dateTimeValue ?validFrom .
        OPTIONAL { ?v :validUntil ?vu . ?vu :dateTimeValue ?validUntil }
    } ORDER BY ?kind ?validFrom
"""

Q_SUMMARY = PREFIX + """
    SELECT ?kind (COUNT(*) AS ?n) WHERE { ?v a :Validity ; :hasValidityKind ?kind }
    GROUP BY ?kind ORDER BY DESC(?n)
"""

Q_OPEN_ENDED = PREFIX + """
    SELECT ?kind (COUNT(*) AS ?n) WHERE {
        ?v a :Validity ; :hasValidityKind ?kind .
        FILTER NOT EXISTS { ?v :validUntil ?vu }
    } GROUP BY ?kind
"""


def _query_bpho(sparql_query: str) -> dict:
    resp = requests.get(
        settings.BPHO_SPARQL_URL,
        params={"query": sparql_query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()


@api_view(["GET"])
@permission_classes([HasBphoAccess])
def facility_validity(request, cnes):
    """Todas as qualificações reais (Validity) de UM estabelecimento, com
    período de vigência. Lista vazia é uma resposta válida -- nem todo
    estabelecimento tem qualificação registrada."""
    try:
        data = _query_bpho(Q_FACILITY % {"cnes": cnes})
    except requests.RequestException as e:
        logger.warning("BPHO SPARQL endpoint indisponível: %s", e)
        return Response({"error": "Endpoint SPARQL da BPHO indisponível.", "detail": str(e)},
                         status=status.HTTP_503_SERVICE_UNAVAILABLE)

    rows = []
    for b in data["results"]["bindings"]:
        rows.append({
            "kind": b["kind"]["value"].split("#")[-1],
            "valid_from": b["validFrom"]["value"],
            "valid_until": b.get("validUntil", {}).get("value"),
        })
    return Response({"cnes": cnes, "qualifications": rows, "count": len(rows)})


@api_view(["GET"])
@permission_classes([HasBphoAccess])
def summary(request):
    """Panorama nacional: contagem de Validity por tipo, e quantas ainda
    estão em vigor (sem validUntil) por tipo."""
    try:
        by_kind = _query_bpho(Q_SUMMARY)
        open_ended = _query_bpho(Q_OPEN_ENDED)
    except requests.RequestException as e:
        logger.warning("BPHO SPARQL endpoint indisponível: %s", e)
        return Response({"error": "Endpoint SPARQL da BPHO indisponível.", "detail": str(e)},
                         status=status.HTTP_503_SERVICE_UNAVAILABLE)

    counts = {b["kind"]["value"].split("#")[-1]: int(b["n"]["value"])
              for b in by_kind["results"]["bindings"]}
    open_counts = {b["kind"]["value"].split("#")[-1]: int(b["n"]["value"])
                   for b in open_ended["results"]["bindings"]}
    total = sum(counts.values())
    return Response({"total": total, "by_kind": counts, "still_open_by_kind": open_counts})
