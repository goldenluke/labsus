# api/pipeline_ontologia/llm_chat.py
#
# Chat em linguagem natural sobre a BPHO, usando um modelo local (Ollama,
# llama3.1:8b) com tool-calling: o modelo decide quando gerar e executar uma
# consulta SPARQL contra o endpoint somente-leitura da BPHO (settings.BPHO_SPARQL_URL)
# e formula a resposta final em português a partir do resultado.
#
# Não usa nenhuma API externa (Anthropic/OpenAI) -- roda inteiramente local via Ollama.

import json
import logging
import re
import time

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def _population_space_cli(*args, **kwargs):
    # Import tardio: evita import circular entre pipeline_ontologia e
    # pipeline_population_space, e só paga o custo se a ferramenta for
    # realmente chamada (a maioria das perguntas nunca precisa dela).
    from api.pipeline_population_space.tasks import _run_population_cli
    return _run_population_cli(*args, **kwargs)

PREFIX = (
    "PREFIX : <http://datasus-ontology.local/onto#>\n"
    "PREFIX owl: <http://www.w3.org/2002/07/owl#>\n"
    "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\n"
    "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>\n"
)

MAX_TOOL_ROUNDS = 4
_SCHEMA_CACHE = {"text": None, "built_at": 0}
_SCHEMA_TTL_SECONDS = 600


def _query_bpho(query, accept="application/sparql-results+json"):
    # Consultas com propriedade em posição de objeto sobre classes com milhões de
    # instâncias (ex.: :facility em Affiliation, 6.16M triplas) podem passar de 30s
    # neste store -- medido ~31s para um único IRI. Um AVG de tempo de internação
    # sobre TODAS as ~1,16M Hospitalization (join com Admission+Discharge+TimePoint
    # x2) mediu ~99s. 150s dá margem sem deixar o chat pendurado indefinidamente.
    return requests.get(
        settings.BPHO_SPARQL_URL,
        params={"query": query},
        headers={"Accept": accept},
        timeout=150,
    )


def _fetch_classes():
    q = PREFIX + """
        SELECT ?class ?label ?comment WHERE {
            ?class a owl:Class .
            OPTIONAL { ?class rdfs:label ?label }
            OPTIONAL { ?class rdfs:comment ?comment }
            FILTER(STRSTARTS(STR(?class), STR(:)))
        } ORDER BY ?class
    """
    resp = _query_bpho(q)
    resp.raise_for_status()
    rows = resp.json()["results"]["bindings"]
    out = []
    for row in rows:
        name = row["class"]["value"].split("#")[-1]
        label = row.get("label", {}).get("value")
        comment = row.get("comment", {}).get("value")
        out.append((name, label, comment))
    return out


def _fetch_properties():
    q = PREFIX + """
        SELECT ?p ?dom ?rng WHERE {
            { ?p a owl:ObjectProperty } UNION { ?p a owl:DatatypeProperty }
            OPTIONAL { ?p rdfs:domain ?dom }
            OPTIONAL { ?p rdfs:range ?rng }
            FILTER(STRSTARTS(STR(?p), STR(:)))
        } ORDER BY ?p
    """
    resp = _query_bpho(q)
    resp.raise_for_status()
    rows = resp.json()["results"]["bindings"]
    out = []
    for row in rows:
        name = row["p"]["value"].split("#")[-1]
        dom = row.get("dom", {}).get("value", "").split("#")[-1] or None
        rng = row.get("rng", {}).get("value", "").split("#")[-1] or None
        out.append((name, dom, rng))
    return out


def build_schema_context(force=False):
    """Monta o bloco de contexto (classes + propriedades) usado no system prompt.
    Cacheado em processo por _SCHEMA_TTL_SECONDS -- a TBox muda raramente."""
    now = time.time()
    if not force and _SCHEMA_CACHE["text"] and (now - _SCHEMA_CACHE["built_at"] < _SCHEMA_TTL_SECONDS):
        return _SCHEMA_CACHE["text"]

    classes = _fetch_classes()
    properties = _fetch_properties()

    # Só classes com rótulo/comentário viram texto legível -- as demais (muitas
    # são vocabulário genérico BFO herdado, sem anotação própria) só poluiriam
    # o prompt de um modelo de 8B sem ajudar em nada.
    labeled = [(n, l, c) for n, l, c in classes if l or c]
    class_lines = "\n".join(
        f"- {n} ({l or n}): {c or 'sem descrição'}" for n, l, c in labeled
    )
    all_class_names = ", ".join(n for n, _, _ in classes)

    prop_lines = "\n".join(
        f"- {n}: domínio={dom or '?'}, alcance={rng or '?'}" for n, dom, rng in properties
    )

    text = f"""Classes da BPHO com descrição em português (as mais relevantes para perguntas sobre dados do SUS):
{class_lines}

Todas as classes existentes na ontologia (para referência, muitas sem descrição própria -- vocabulário genérico herdado do BFO):
{all_class_names}

Propriedades (predicados) disponíveis, com domínio (sujeito) e alcance (objeto):
{prop_lines}
"""
    _SCHEMA_CACHE["text"] = text
    _SCHEMA_CACHE["built_at"] = now
    return text


SYSTEM_PROMPT_TEMPLATE = """Você é um assistente que responde perguntas em português sobre a BPHO \
(Brazilian Public Health Ontology), uma ontologia formal (OWL 2 DL) que modela dados \
administrativos do SUS/DATASUS, com um armazenamento RDF real e persistente por trás.

Você tem uma ferramenta `query_sparql` que executa consultas SPARQL (SELECT/ASK) contra \
esse armazenamento e retorna o resultado em JSON. Use o prefixo `:` para \
<http://datasus-ontology.local/onto#> em toda consulta.

{schema}

Exemplos de perguntas e consultas corretas:
- "Quantas Hospitalization existem no total?" -> SELECT (COUNT(?h) AS ?n) WHERE {{ ?h a :Hospitalization }}
  (esse mesmo padrão funciona para qualquer classe: troque :Hospitalization por :Affiliation, :Person, \
  :NotifiableCaseInvestigation, :Team, :AIHRecord, etc.)
- "Quantas AIH foram rejeitadas?" -> SELECT (COUNT(?h) AS ?n) WHERE {{ ?h a :Hospitalization ; :hasProvenance ?aih . ?aih :hasStatus :Rejected }}
- "Hospitalizations por estabelecimento" -> SELECT ?facility (COUNT(?h) AS ?n) WHERE {{ ?h a :Hospitalization ; :atFacility ?facility }} GROUP BY ?facility ORDER BY DESC(?n) LIMIT 10
- "Quantos vínculos profissionais (Affiliation) têm equipe (Team) vinculada?" -> SELECT (COUNT(?a) AS ?n) WHERE {{ ?a a :Affiliation ; :team ?t }}
  (resultado real: 6.835 de ~6,16 milhões de Affiliation -- é o subconjunto ligado a equipes de saúde da \
  família (SIA/ESF), não todo profissional cadastrado tem equipe.)
- "Quantas Family/FamilyMembership existem?" -> mesmo padrão de contagem por classe (:Family = 5.000, :FamilyMembership = 13.556).
- "O que é uma Hospitalization?" -> não precisa de consulta SPARQL de instância; responda usando a descrição da classe já listada acima.

Padrão para perguntas com RECORTE DE TEMPO (ex.: "quantas admissões em dezembro de 2025?"): eventos \
(Admission, Discharge) se ligam a um TimePoint via a propriedade `:at`, e o TimePoint tem a data em \
`:dateTimeValue` (tipo xsd:dateTime). Use FILTER com comparação de data, não STRSTARTS:
SELECT (COUNT(?a) AS ?n) WHERE {{
  ?a a :Admission ; :at ?tp .
  ?tp :dateTimeValue ?dt .
  FILTER(?dt >= "2025-12-01T00:00:00"^^xsd:dateTime && ?dt < "2026-01-01T00:00:00"^^xsd:dateTime)
}}
(resultado real para dezembro/2025: 640.006 Admission. Não se preocupe em declarar PREFIX -- isso é \
adicionado automaticamente antes da execução, mesmo que você esqueça ou declare só parte deles.)

Padrão para TEMPO MÉDIO DE INTERNAÇÃO (duração entre Admission e Discharge da mesma Hospitalization, \
via `:hasPart`): SPARQL não tem uma função pronta para converter uma duração (resultado de subtrair \
dois xsd:dateTime) em número de dias -- extraia com REPLACE sobre a forma textual (ex.: "P5D" -> 5):
SELECT (AVG(?days) AS ?media) (COUNT(?h) AS ?n) WHERE {{
  ?h a :Hospitalization ; :atFacility :facility_XXXXXXX ; :hasPart ?adm ; :hasPart ?disc .
  ?adm a :Admission ; :at ?tp1 . ?tp1 :dateTimeValue ?d1 .
  ?disc a :Discharge ; :at ?tp2 . ?tp2 :dateTimeValue ?d2 .
  BIND((?d2 - ?d1) AS ?diff)
  BIND(xsd:integer(REPLACE(REPLACE(STR(?diff), "^PT0S$", "P0D"), "[PD]", "")) AS ?days)
}}
Prefira SEMPRE escopar por um :atFacility específico (rápido, ~8s) -- sem esse filtro, a consulta \
varre todas as ~1,16 milhão de Hospitalization e pode levar até ~100s (resultado real medido: 4.611 \
Hospitalization no facility_2077396, tempo médio 4.86 dias; todas as Hospitalization combinadas, \
tempo médio 13.72 dias). Se o usuário não especificar um estabelecimento, primeiro pergunte ou use o \
padrão de duas etapas abaixo para achar um IRI relevante, ou avise que a versão sem filtro pode demorar.

Padrão importante para perguntas que CRUZAM sistemas (ex.: "esse estabelecimento também tem vínculo \
profissional registrado?"): NUNCA faça um JOIN sem filtro entre duas classes grandes (ex.: juntar \
todo Affiliation com todo Hospitalization de uma vez) -- isso não retorna em tempo hábil neste \
armazenamento. Em vez disso, resolva em duas etapas, uma consulta por vez:
1. Primeiro descubra o IRI específico de interesse (ex.: o estabelecimento com mais Hospitalization):
   SELECT ?facility (COUNT(?h) AS ?n) WHERE {{ ?h a :Hospitalization ; :atFacility ?facility }} GROUP BY ?facility ORDER BY DESC(?n) LIMIT 1
2. Depois, com esse IRI já em mãos, consulte a outra classe filtrando por ele diretamente:
   SELECT (COUNT(?aff) AS ?n) WHERE {{ ?aff a :Affiliation ; :facility :facility_XXXXXXX }}
Esse padrão é o que prova que a mesma URI de HealthFacility é usada em Hospitalization (dado do SIH) \
e em Affiliation (vínculo profissional, dado do CNES/SIA) -- o ponto central da BPHO.

Ferramenta `compare_facilities`: use quando a pergunta for sobre SIMILARIDADE/diferença entre \
estabelecimentos específicos (ex.: "esses dois estabelecimentos são parecidos?", "compare o \
facility_2077396 com o facility_0000434"), não sobre um fato isolado de cada um. Ela chama o \
PopulationSpace (BioSpace) -- carrega utilização hospitalar, força de trabalho e composição \
demográfica de cada estabelecimento como um ponto num espaço de representação (12 dimensões) e \
devolve a distância euclidiana par a par. Interprete assim: distância PEQUENA (abaixo de ~1) = \
perfis muito parecidos; distância GRANDE (acima de ~3) = perfis bem diferentes, mesmo que o volume \
de internação seja parecido -- verifique nos `values` retornados QUAL indicador mais diverge (ex.: \
força de trabalho ou composição demográfica) antes de explicar a diferença. Essa ferramenta demora \
mais que `query_sparql` (pode levar alguns minutos para 2-3 estabelecimentos) -- isso é esperado.

Regras importantes:
1. Se a pergunta for sobre o SIGNIFICADO de um conceito (o que é X, defina Y), responda direto \
usando as descrições de classe acima -- não precisa executar SPARQL.
2. Se a pergunta pedir uma contagem, agregação ou lista de instâncias, gere e execute uma consulta SPARQL.
3. A ontologia NÃO modela atributos demográficos individuais (idade, sexo, raça/cor) como propriedades \
RDF -- esses campos vivem apenas nos CSVs brutos do DATASUS, fora do grafo (EXCETO via \
`compare_facilities`, que busca isso no parquet bruto do SIH, não na BPHO). Se perguntarem sobre \
demografia SEM ser uma comparação entre estabelecimentos, diga que a BPHO não tem esse dado \
modelado, em vez de inventar uma consulta SPARQL.
4. Nunca invente números. Se uma consulta falhar ou não retornar nada, diga isso.
5. Responda sempre em português, de forma direta e curta.
"""


def _ollama_chat(messages, tools=None):
    payload = {
        "model": getattr(settings, "OLLAMA_MODEL", "llama3.1:8b"),
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools
    resp = requests.post(
        f"{settings.OLLAMA_URL}/api/chat",
        json=payload,
        timeout=240,
    )
    resp.raise_for_status()
    return resp.json()["message"]


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_sparql",
            "description": "Executa uma consulta SPARQL (SELECT ou ASK) contra o armazenamento RDF da BPHO e retorna o resultado em JSON.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "A consulta SPARQL completa, usando o prefixo : para http://datasus-ontology.local/onto#",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_facilities",
            "description": (
                "Compara 2 ou mais estabelecimentos de saúde (HealthFacility) usando o PopulationSpace "
                "(BioSpace): carrega os indicadores de utilização hospitalar, força de trabalho e composição "
                "demográfica de cada um, e calcula a DISTÂNCIA GEOMÉTRICA (euclidiana) entre cada par -- "
                "quanto menor a distância, mais parecido o perfil dos estabelecimentos. Use isso quando a "
                "pergunta for sobre SIMILARIDADE/diferença entre estabelecimentos, não sobre um fato isolado."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "facility_cnes_list": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de códigos CNES (sem o prefixo 'facility_'), ex.: [\"2077396\", \"2082187\"].",
                    },
                },
                "required": ["facility_cnes_list"],
            },
        },
    },
]


def _execute_sparql_tool(query):
    # O modelo é inconsistente com PREFIX: às vezes omite todas as linhas, às vezes
    # declara só uma (ex.: xsd:) e ainda assim usa `:`/`owl:`/`rdfs:` sem declarar.
    # Checar só "PREFIX aparece em algum lugar" não é suficiente -- removemos toda
    # linha PREFIX que o modelo tenha escrito e prependemos nosso bloco canônico
    # completo, sempre, para nunca faltar (nem duplicar) uma declaração.
    query = re.sub(r"(?im)^\s*PREFIX\s+\S+:\s*<[^>]*>\s*$", "", query)
    query = PREFIX + query

    try:
        resp = _query_bpho(query)
    except requests.RequestException as e:
        return {"error": f"Endpoint SPARQL indisponível: {e}"}

    if resp.status_code != 200:
        return {"error": f"Consulta inválida: {resp.text[:500]}"}

    data = resp.json()
    bindings = data.get("results", {}).get("bindings") or data.get("boolean")
    if isinstance(bindings, bool):
        return {"result": bindings}

    rows = []
    for row in (bindings or [])[:25]:
        rows.append({k: v.get("value") for k, v in row.items()})
    truncated = len(bindings or []) > 25
    return {"rows": rows, "truncated": truncated, "row_count": len(bindings or [])}


# Competência já carregada no armazenamento durante esta sessão (ver owl/README.md) --
# hardcoded aqui de propósito: manter o schema da ferramenta simples (só a lista de
# CNES) é mais confiável para o modelo do que pedir ano/mês/uf por estabelecimento,
# risco de confusão já visto com ferramentas de esquema mais complexo.
_COMPARE_ANO = 2025
_COMPARE_MES = 12


def _execute_compare_tool(facility_cnes_list):
    facilities = [
        {"facility_uri": f"facility_{cnes}", "ano": _COMPARE_ANO, "mes": _COMPARE_MES}
        for cnes in facility_cnes_list
    ]
    try:
        return _population_space_cli("compare", {"facilities": facilities}, timeout=600)
    except Exception as e:  # noqa: BLE001 -- ponte de subprocess: qualquer erro vira resultado de ferramenta, não exceção
        return {"error": str(e)}


def chat(question, history=None):
    """Roda o loop de tool-calling. `history` é uma lista de {role, content}
    de turnos anteriores (sem o system prompt). Retorna (resposta, queries_usadas)."""
    schema = build_schema_context()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(schema=schema)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": question})

    queries_used = []

    for _ in range(MAX_TOOL_ROUNDS):
        message = _ollama_chat(messages, tools=TOOLS)
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            return message.get("content", "").strip(), queries_used

        messages.append(message)
        for call in tool_calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)

            if name == "compare_facilities":
                cnes_list = args.get("facility_cnes_list", [])
                queries_used.append(f"compare_facilities({', '.join(cnes_list)})")
                result = _execute_compare_tool(cnes_list)
            else:
                query = args.get("query", "")
                queries_used.append(query)
                result = _execute_sparql_tool(query)

            messages.append({
                "role": "tool",
                "content": json.dumps(result, ensure_ascii=False),
            })

    # Excedeu o limite de rodadas de ferramenta -- força uma resposta final sem tools.
    final = _ollama_chat(messages, tools=None)
    return final.get("content", "").strip() or "Não consegui formular uma resposta a tempo.", queries_used
