# api/pipeline_hospitalizacao_rdf/tasks.py
#
# Pipeline de prova de conceito: em vez de baixar o SIH com PySUS e agregar
# com pandas (como pipeline_predicao_internacoes/pipeline_regressao_obitos
# fazem), esta pipeline:
#   1. Pede à BIBLIOTECA DA ONTOLOGIA (owl/pysus_to_rdf.py + owl/store.py,
#      rodando no venv/processo PRÓPRIO da ontologia -- não no venv do
#      LabSUS, que tem uma versão antiga e incompatível do PySUS) para
#      carregar a competência solicitada no armazenamento RDF persistente
#      da BPHO, via subprocess (`store.py load sih_hospitalization ...`).
#      Isto é idempotente -- carregar a mesma competência duas vezes não
#      duplica nada (URIs determinísticas, manifest da Fase 54).
#   2. Consulta esse armazenamento por SPARQL (endpoint HTTP somente-leitura
#      da BPHO, settings.BPHO_SPARQL_URL) para obter agregados -- Hospitalization
#      por HealthFacility e por AIHRecordStatus -- em vez de um groupby de
#      DataFrame.
#   3. Grava o resultado como CSV, registrado como ManagedFile, do mesmo
#      jeito que qualquer outra pipeline do LabSUS.
#
# Por que isto prova algo: os identificadores de HealthFacility usados aqui
# são os MESMOS que o cadastro de vínculo profissional (CNES) e o vínculo de
# equipe (SIA) já usam na BPHO (Fases 62/63) -- então o resultado desta
# pipeline já nasce cruzável com dado de outros sistemas administrativos,
# sem nenhum trabalho de correspondência de chave adicional.

import csv
import logging
import subprocess
from pathlib import Path

import requests
from celery import shared_task
from django.apps import apps
from django.conf import settings

from api.models import FileType

logger = logging.getLogger(__name__)

PREFIX = "PREFIX : <http://datasus-ontology.local/onto#>\n"

Q_FACILITY_AGG = PREFIX + """
    SELECT ?facility (COUNT(DISTINCT ?h) AS ?n) WHERE {
        ?h a :Hospitalization ; :atFacility ?facility .
    } GROUP BY ?facility ORDER BY DESC(?n) LIMIT 20
"""

Q_STATUS_AGG = PREFIX + """
    SELECT ?status (COUNT(DISTINCT ?h) AS ?n) WHERE {
        ?h a :Hospitalization ; :hasProvenance ?aih .
        ?aih :hasStatus ?status .
    } GROUP BY ?status
"""

Q_TOTAL = "SELECT (COUNT(?h) AS ?n) WHERE { ?h a <http://datasus-ontology.local/onto#Hospitalization> }"


def _load_competencia(uf: str, ano: int, mes: int, grupo: str, task_instance=None) -> None:
    cmd = [
        settings.BPHO_ONTO_PYTHON, "store.py", "load", "sih_hospitalization",
        "--state", uf, "--year", str(ano), "--month", str(mes), "--group", grupo,
    ]
    if task_instance:
        task_instance.update_state(state='PROGRESS', meta={
            'progress': 20, 'message': f'Carregando SIH/{grupo} {uf} {mes:02d}/{ano} no armazenamento da BPHO...'
        })
    result = subprocess.run(cmd, cwd=settings.BPHO_ONTO_DIR, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        raise RuntimeError(f"Falha ao carregar competência na BPHO: {result.stderr.strip()}")
    logger.info("store.py load: %s", result.stderr.strip())


def _sparql(query: str) -> dict:
    resp = requests.get(settings.BPHO_SPARQL_URL, params={"query": query},
                         headers={"Accept": "application/sparql-results+json"}, timeout=60)
    resp.raise_for_status()
    return resp.json()


@shared_task(bind=True)
def run_hospitalizacao_rdf_pipeline(self, uf, ano, mes, grupo, user_id, output_filename=None):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    HospitalizacaoRDFTaskStatus = apps.get_model('pipeline_hospitalizacao_rdf', 'HospitalizacaoRDFTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = HospitalizacaoRDFTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Pipeline de Hospitalização (RDF/BPHO) iniciada.',
                'uf': uf, 'ano': ano, 'mes': mes, 'grupo': grupo,
            }
        )
        self.update_state(state='PROGRESS', meta={'progress': 5, 'message': 'Iniciando...'})

        _load_competencia(uf, ano, mes, grupo, self)

        self.update_state(state='PROGRESS', meta={'progress': 70, 'message': 'Consultando agregados via SPARQL...'})
        facility_agg = _sparql(Q_FACILITY_AGG)["results"]["bindings"]
        status_agg = _sparql(Q_STATUS_AGG)["results"]["bindings"]
        total = int(_sparql(Q_TOTAL)["results"]["bindings"][0]["n"]["value"])

        if not facility_agg:
            raise Exception("Nenhum HealthFacility com Hospitalization encontrado no armazenamento da BPHO.")

        self.update_state(state='PROGRESS', meta={'progress': 90, 'message': 'Salvando resultados...'})

        rows = []
        for row in facility_agg:
            facility_uri = row["facility"]["value"]
            rows.append({
                "cnes": facility_uri.rsplit("_", 1)[-1],
                "facility_uri": facility_uri,
                "hospitalizations": int(row["n"]["value"]),
            })

        if output_filename and output_filename.strip():
            final_filename = output_filename.strip()
            if not final_filename.lower().endswith('.csv'):
                final_filename += '.csv'
        else:
            final_filename = f"hospitalizacao_rdf_{uf.lower()}_{ano}{mes:02d}_{task_id[:8]}.csv"

        output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / "hospitalizacao_rdf"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / final_filename
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["cnes", "facility_uri", "hospitalizations"], delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

        status_summary = {
            row["status"]["value"].split("#")[-1]: int(row["n"]["value"]) for row in status_agg
        }
        results_summary = {
            "total_hospitalizations_no_store": total,
            "by_status": status_summary,
            "top_facilities": rows,
            "note": (
                "total_hospitalizations_no_store reflete o armazenamento BPHO inteiro "
                "(acumulado de todas as competências já carregadas), não só esta requisição."
            ),
        }

        relative_path = str(output_path.relative_to(settings.MEDIA_ROOT))
        output_file = ManagedFile.objects.create(
            uploader=user,
            file=relative_path,
            filename=final_filename,
            description=(
                f"Hospitalizações reais (SIH/{grupo}, {uf} {mes:02d}/{ano}) agregadas por estabelecimento "
                f"via consulta SPARQL contra a BPHO. {total} Hospitalization no armazenamento no total."
            ),
            file_type=FileType.HOSPITALIZACAO_RDF,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {len(rows)} estabelecimentos no top-20, {total} Hospitalization no total."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = results_summary
        task_status_entry.save()

        return {'status': 'SUCCESS', 'output_file_id': output_file.id, 'total': total}

    except Exception as e:
        logger.exception(f"Falha na pipeline de hospitalização RDF {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise
