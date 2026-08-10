# api/pipeline_ontologia/views.py
#
# Proxy para a BPHO (Brazilian Public Health Ontology) -- o endpoint SPARQL
# somente-leitura servido por owl/sparql_endpoint.py, rodando separadamente
# (venv/processo próprio da ontologia, fora do LabSUS). Este app não guarda
# nenhum estado próprio: cada view aqui é uma chamada HTTP para o endpoint
# SPARQL configurado em settings.BPHO_SPARQL_URL, com tratamento de erro para
# quando esse servidor não estiver de pé.
#
# Segurança: o proxy nunca precisa reimplementar a garantia de só-leitura --
# ela já vem de owl/sparql_endpoint.py, que só chama Store.query() (nunca
# Store.update()) contra um store aberto em modo read_only(). Este proxy só
# repassa a consulta e a resposta.

import logging

import requests
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes

from . import llm_chat
from api.permissions import HasBphoAccess
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

PREFIX = (
    "PREFIX : <http://datasus-ontology.local/onto#>\n"
    "PREFIX owl: <http://www.w3.org/2002/07/owl#>\n"
    "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
)


def _query_bpho(sparql_query: str, accept: str = "application/sparql-results+json"):
    """Envia uma consulta SPARQL ao endpoint da BPHO. Levanta requests.RequestException
    se o servidor não estiver acessível -- o chamador decide como responder."""
    return requests.get(
        settings.BPHO_SPARQL_URL,
        params={"query": sparql_query},
        headers={"Accept": accept},
        timeout=30,
    )


@api_view(["GET", "POST"])
@permission_classes([HasBphoAccess])
def sparql_proxy(request):
    """Repassa uma consulta SPARQL arbitrária (SELECT/ASK/CONSTRUCT/DESCRIBE)
    para o endpoint da BPHO e devolve a resposta tal como veio. A consulta
    vem em ?query= (GET) ou no corpo JSON {"query": "..."} (POST)."""
    query = request.query_params.get("query") if request.method == "GET" else request.data.get("query")
    if not query:
        return Response({"error": "parâmetro 'query' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)

    accept = request.headers.get("Accept", "application/sparql-results+json")
    try:
        upstream = _query_bpho(query, accept=accept)
    except requests.RequestException as e:
        logger.warning("BPHO SPARQL endpoint indisponível: %s", e)
        return Response(
            {"error": "Endpoint SPARQL da BPHO indisponível.", "detail": str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if upstream.status_code != 200:
        return Response(
            {"error": "Erro na consulta SPARQL.", "detail": upstream.text},
            status=status.HTTP_400_BAD_REQUEST,
        )

    content_type = upstream.headers.get("Content-Type", "application/json")
    if "json" in content_type:
        return Response(upstream.json())
    # Turtle/N-Triples/etc. (CONSTRUCT/DESCRIBE) -- devolve como texto bruto.
    return Response({"format": content_type, "data": upstream.text})


@api_view(["GET"])
@permission_classes([HasBphoAccess])
def classes_catalog(request):
    """Catálogo de classes da BPHO com rótulo/definição em português (rdfs:label/
    rdfs:comment), quando existirem. Usado para enriquecer páginas do LabSUS com
    o significado formal dos conceitos por trás dos dados (ex.: Hospitalization,
    HealthFacility, AIHRecordStatus) -- não substitui dicionários de código de
    campo do DATASUS (SEXO, RACA_COR, CID), que são um problema diferente."""
    query = PREFIX + """
        SELECT ?class ?label ?comment WHERE {
            ?class a owl:Class .
            OPTIONAL { ?class rdfs:label ?label }
            OPTIONAL { ?class rdfs:comment ?comment }
            FILTER(STRSTARTS(STR(?class), STR(:)))
        }
        ORDER BY ?class
    """

    try:
        upstream = _query_bpho(query)
    except requests.RequestException as e:
        logger.warning("BPHO SPARQL endpoint indisponível: %s", e)
        return Response(
            {"error": "Endpoint SPARQL da BPHO indisponível.", "detail": str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if upstream.status_code != 200:
        return Response({"error": upstream.text}, status=status.HTTP_400_BAD_REQUEST)

    bindings = upstream.json().get("results", {}).get("bindings", [])
    classes = []
    for row in bindings:
        uri = row["class"]["value"]
        classes.append({
            "uri": uri,
            "name": uri.split("#")[-1],
            "label": row.get("label", {}).get("value"),
            "comment": row.get("comment", {}).get("value"),
        })
    return Response({"count": len(classes), "classes": classes})


@api_view(["GET"])
@permission_classes([HasBphoAccess])
def store_stats(request):
    """Contagem total de triplas e instâncias por classe no armazenamento
    persistente da BPHO -- espelha owl/store.py stats()."""
    total_query = "SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }"
    per_class_query = PREFIX + """
        SELECT ?class (COUNT(?s) AS ?n) WHERE {
            ?s a ?class .
            FILTER(STRSTARTS(STR(?class), STR(:)))
        } GROUP BY ?class ORDER BY DESC(?n)
    """

    try:
        total_resp = _query_bpho(total_query)
        per_class_resp = _query_bpho(per_class_query)
    except requests.RequestException as e:
        logger.warning("BPHO SPARQL endpoint indisponível: %s", e)
        return Response(
            {"error": "Endpoint SPARQL da BPHO indisponível.", "detail": str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    if total_resp.status_code != 200 or per_class_resp.status_code != 200:
        return Response({"error": "Erro ao consultar estatísticas."}, status=status.HTTP_400_BAD_REQUEST)

    total = int(total_resp.json()["results"]["bindings"][0]["n"]["value"])
    per_class = {
        row["class"]["value"].split("#")[-1]: int(row["n"]["value"])
        for row in per_class_resp.json()["results"]["bindings"]
    }
    return Response({"total_triples": total, "instances_by_class": per_class})


@api_view(["POST"])
@permission_classes([HasBphoAccess])
def chat_bpho(request):
    """Chat em linguagem natural sobre a BPHO usando um LLM local (Ollama,
    ver settings.OLLAMA_URL/OLLAMA_MODEL) com tool-calling para SPARQL.
    Corpo: {"message": "...", "history": [{"role": "user"|"assistant", "content": "..."}]}."""
    message = request.data.get("message")
    if not message:
        return Response({"error": "campo 'message' é obrigatório."}, status=status.HTTP_400_BAD_REQUEST)
    history = request.data.get("history") or []

    try:
        answer, queries_used = llm_chat.chat(message, history=history)
    except requests.RequestException as e:
        logger.warning("Ollama indisponível: %s", e)
        return Response(
            {"error": "Modelo local (Ollama) indisponível.", "detail": str(e)},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({"answer": answer, "sparql_queries": queries_used})
