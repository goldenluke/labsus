# api/pipeline_sinan_vigilancia/views.py
#
# Proxy síncrono para a BPHO, mesma disciplina de api.pipeline_ontologia/
# api.pipeline_cnes_validity/api.pipeline_registros_vitais: sem models.py,
# sem Celery, cada view consulta o endpoint SPARQL somente-leitura da BPHO
# direto.
#
# Expõe NotifiableCaseInvestigation/CaseOutcome (SINAN, Fase 67/70) -- 48 das
# 49 bases (agravos) reais do SINAN, carregadas na mesma rodada. A BPHO não
# tem uma propriedade própria ligando cada investigação ao código do agravo
# (achado real: o agravo fica só no identificador do indivíduo, derivado do
# arquivo de origem -- ver Fase 70) -- a busca por agravo aqui usa esse
# mesmo prefixo determinístico via STRSTARTS, não uma propriedade RDF
# dedicada.

import logging

import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from api.permissions import HasBphoAccess
from rest_framework.response import Response

logger = logging.getLogger(__name__)

PREFIX = "PREFIX : <http://datasus-ontology.local/onto#>\n"

# As 48 bases reais carregadas nesta rodada (Fase 70) -- NTRA/TRAC à parte,
# são AggregateActivity, não NotifiableCaseInvestigation (ver aggregate_bases
# abaixo). INFL confirmado ausente do catálogo, em qualquer época testada.
CASE_BASES = sorted([
    "ACBI", "ACGR", "ANIM", "ANTR", "BOTU", "CANC", "CHAG", "CHIK", "COQU",
    "DENG", "DERM", "DIFT", "ESQU", "EXAN", "FMAC", "FTIF", "HANS", "HANT",
    "HEPA", "IEXO", "LEIV", "LEPT", "LERD", "LTAN", "MALA", "MENI", "MENT",
    "PAIR", "PFAN", "PNEU", "RAIV", "SDTA", "SIFA", "SIFC", "SIFG", "SRC",
    "TETA", "TETN", "TOXC", "TOXG", "TUBE", "VARC", "VIOL", "ZIKA",
])
AGGREGATE_BASES = ["NTRA", "TRAC"]

# Consulta direta sobre :CaseOutcome (sem OPTIONAL a partir de
# NotifiableCaseInvestigation) -- medido contra dado real: ~31s contra 4,65M
# CaseOutcome, muito mais rápido que o join com OPTIONAL sobre os 7,3M
# NotifiableCaseInvestigation (>115s, expirou o timeout de teste).
Q_NATIONAL_OUTCOME = PREFIX + """
    SELECT ?outcome (COUNT(*) AS ?n) WHERE {
        ?o a :CaseOutcome ; a ?outcome . FILTER(?outcome != :CaseOutcome)
    } GROUP BY ?outcome
"""

Q_TOTAL_CASES = PREFIX + "SELECT (COUNT(?n) AS ?total) WHERE { ?n a :NotifiableCaseInvestigation }"
Q_TOTAL_AGGREGATE = PREFIX + "SELECT (COUNT(?a) AS ?total) WHERE { ?a a :AggregateActivity }"


def _q_agravo_outcome(code: str) -> str:
    return PREFIX + """
        SELECT ?outcome (COUNT(*) AS ?n) WHERE {
            ?nci a :NotifiableCaseInvestigation .
            FILTER(STRSTARTS(STR(?nci), CONCAT(STR(:), "nci_%s")))
            OPTIONAL { ?nci :resultsIn ?out . ?out a ?outcome . FILTER(?outcome != :CaseOutcome) }
        } GROUP BY ?outcome
    """ % code


def _q_agravo_total_aggregate(code: str) -> str:
    return PREFIX + """
        SELECT (COUNT(?a) AS ?n) WHERE {
            ?a a :AggregateActivity .
            FILTER(STRSTARTS(STR(?a), CONCAT(STR(:), "aggact_%s")))
        }
    """ % code


def _query_bpho(sparql_query: str, timeout: int = 90) -> dict:
    resp = requests.get(
        settings.BPHO_SPARQL_URL,
        params={"query": sparql_query},
        headers={"Accept": "application/sparql-results+json"},
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def _outcome_breakdown(bindings) -> dict:
    result = {}
    total = 0
    for b in bindings:
        n = int(b["n"]["value"])
        total += n
        if "outcome" in b:
            result[b["outcome"]["value"].split("#")[-1]] = n
        else:
            result.setdefault("_sem_desfecho", 0)
            result["_sem_desfecho"] += n
    result["_total"] = total
    return result


@api_view(["GET"])
@permission_classes([HasBphoAccess])
def bases_disponiveis(request):
    """As 48 bases reais carregadas -- 46 de caso individual, 2 agregadas
    (surto/tracoma) -- para popular um seletor no frontend."""
    return Response({"case_bases": CASE_BASES, "aggregate_bases": AGGREGATE_BASES})


@api_view(["GET"])
@permission_classes([HasBphoAccess])
def summary(request):
    """Panorama nacional: total de investigações de caso, total de
    atividades agregadas, e a distribuição de desfecho (CaseOutcome) através
    de TODOS os 46 agravos individuais carregados juntos. A consulta de
    desfecho é direta sobre CaseOutcome (sem OPTIONAL a partir de
    NotifiableCaseInvestigation) -- medido contra dado real: ~31s, contra
    >115s (expirou) da versão com OPTIONAL sobre os 7,3M casos."""
    try:
        total_cases_resp = _query_bpho(Q_TOTAL_CASES)
        total_aggregate = _query_bpho(Q_TOTAL_AGGREGATE)
        outcome = _query_bpho(Q_NATIONAL_OUTCOME, timeout=60)
    except requests.RequestException as e:
        logger.warning("BPHO SPARQL endpoint indisponível: %s", e)
        return Response({"error": "Endpoint SPARQL da BPHO indisponível.", "detail": str(e)},
                         status=status.HTTP_503_SERVICE_UNAVAILABLE)

    total_cases = int(total_cases_resp["results"]["bindings"][0]["total"]["value"])
    breakdown = {b["outcome"]["value"].split("#")[-1]: int(b["n"]["value"])
                 for b in outcome["results"]["bindings"]}
    breakdown["_sem_desfecho"] = total_cases - sum(breakdown.values())
    breakdown["_total"] = total_cases

    return Response({
        "total_notifiable_case_investigations": total_cases,
        "total_aggregate_activities": int(total_aggregate["results"]["bindings"][0]["total"]["value"]),
        "outcome_breakdown": breakdown,
    })


@api_view(["GET"])
@permission_classes([HasBphoAccess])
def agravo_lookup(request, code):
    """Busca por um agravo específico (código real do SINAN, ex.: TUBE,
    DENG, CHIK). NTRA/TRAC são agregados -- devolvem só uma contagem, sem
    desfecho (não são casos individuais)."""
    code = code.upper().strip()
    if code in AGGREGATE_BASES:
        try:
            data = _query_bpho(_q_agravo_total_aggregate(code))
        except requests.RequestException as e:
            logger.warning("BPHO SPARQL endpoint indisponível: %s", e)
            return Response({"error": "Endpoint SPARQL da BPHO indisponível.", "detail": str(e)},
                             status=status.HTTP_503_SERVICE_UNAVAILABLE)
        n = int(data["results"]["bindings"][0]["n"]["value"])
        return Response({"code": code, "is_aggregate": True, "total_aggregate_activities": n})

    if code not in CASE_BASES:
        return Response(
            {"error": f"Agravo {code!r} não está entre as 48 bases carregadas nesta rodada."},
            status=status.HTTP_404_NOT_FOUND,
        )

    try:
        data = _query_bpho(_q_agravo_outcome(code), timeout=120)
    except requests.RequestException as e:
        logger.warning("BPHO SPARQL endpoint indisponível: %s", e)
        return Response({"error": "Endpoint SPARQL da BPHO indisponível.", "detail": str(e)},
                         status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({
        "code": code,
        "is_aggregate": False,
        "outcome_breakdown": _outcome_breakdown(data["results"]["bindings"]),
    })
