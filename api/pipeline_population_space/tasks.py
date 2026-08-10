# api/pipeline_population_space/tasks.py
#
# Chama o PopulationSpace (biospace/plugins/population/) via subprocess --
# mesmo padrão da ponte já usada para owl/store.py (pipeline_hospitalizacao_rdf):
# venvs incompatíveis (biospace usa sklearn/networkx, não instalados no venv do
# LabSUS), então o processo do LabSUS nunca importa biospace diretamente.
#
# O subprocess (scripts/population_cli.py cluster) já faz tudo: consulta a BPHO
# via SPARQL (utilização hospitalar, força de trabalho), lê o parquet bruto do
# SIH via pandas (composição demográfica), monta o RepresentationSpace e roda
# KMeansPhenotyper -- devolve um JSON pronto, sem nenhuma lógica de domínio
# duplicada aqui.

import csv
import json
import logging
import os
import subprocess
from pathlib import Path

from celery import shared_task
from django.apps import apps
from django.conf import settings

from api.models import FileType

logger = logging.getLogger(__name__)


def _run_population_cli(command: str, payload: dict, timeout: int = 900) -> dict:
    # PYTHONPATH precisa incluir BIOSPACE_DIR -- rodar `python3 scripts/x.py` põe
    # scripts/ (não o cwd) em sys.path[0], então `import biospace` falharia sem isso
    # (mesmo problema encontrado manualmente ao testar population_cli.py). `env`
    # do subprocess SUBSTITUI o ambiente inteiro quando informado -- por isso
    # mesclamos com os.environ em vez de passar só a chave nova, senão PATH/HOME
    # desaparecem e o subprocess pode falhar de formas obscuras.
    env = {**os.environ, "PYTHONPATH": settings.BIOSPACE_DIR}
    result = subprocess.run(
        [settings.BIOSPACE_PYTHON, "scripts/population_cli.py", command],
        cwd=settings.BIOSPACE_DIR,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    if result.returncode != 0:
        try:
            error = json.loads(result.stderr.strip().splitlines()[-1])["error"]
        except (IndexError, ValueError, KeyError):
            error = result.stderr.strip() or "Falha desconhecida no population_cli.py."
        raise RuntimeError(error)
    return json.loads(result.stdout)


def _union_fieldnames(rows, base_fields, exclude=()):
    """Nomes de coluna para o CSV -- a UNIÃO das chaves de TODAS as linhas,
    não só da primeira. Achado real: quando um estabelecimento não tem
    vínculo profissional (n_affiliations=0), o dict de `values` nem inclui
    a chave `pct_affiliations_with_team` (ausência estrutural, nunca
    inventada, ver population_cli.py) -- csv.DictWriter levanta ValueError
    se uma linha mais adiante tiver uma chave que a primeira linha não
    tinha, então inferir fieldnames só de `rows[0]` quebra exatamente
    nesse caso real (confirmado testando risk com facility_0009717)."""
    extra = sorted({k for row in rows for k in row.keys() if k not in base_fields and k not in exclude})
    return list(base_fields) + extra


def _save_result_files(subdir, filename_stem, rows, fieldnames, result, user, description, file_type, task_id):
    """Salva o resultado de uma análise PopulationSpace em DOIS formatos --
    CSV (uma linha por estabelecimento/par/observação, pra abrir em
    planilha) e JSON (o `result` completo, incluindo estatísticas agregadas
    que não cabem numa linha de CSV, ex.: threshold, AUC, matched_pairs) --
    os dois registrados como ManagedFile, no mesmo padrão já usado por
    run_population_space_pipeline (Path(MEDIA_ROOT)/processed_data/<subdir>,
    file_type próprio, description legível). Retorna o ManagedFile do CSV
    (o "principal", referenciado por PopulationSpaceTaskStatus.output_file) --
    o JSON fica só registrado, descoberto via Banco de Dados/CsvManagerPage."""
    ManagedFile = apps.get_model('api', 'ManagedFile')

    output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / subdir
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_filename = f"{filename_stem}.csv"
    csv_path = output_dir / csv_filename
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
        writer.writeheader()
        writer.writerows(rows)
    csv_file = ManagedFile.objects.create(
        uploader=user,
        file=str(csv_path.relative_to(settings.MEDIA_ROOT)),
        filename=csv_filename,
        description=description,
        file_type=file_type,
        task_id=task_id,
    )

    json_filename = f"{filename_stem}.json"
    json_path = output_dir / json_filename
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    ManagedFile.objects.create(
        uploader=user,
        file=str(json_path.relative_to(settings.MEDIA_ROOT)),
        filename=json_filename,
        description=f"{description} (JSON completo, inclui estatísticas agregadas fora da tabela CSV).",
        file_type=file_type,
        task_id=task_id,
    )

    return csv_file


@shared_task(bind=True)
def run_population_space_pipeline(self, facility_specs, k, user_id, output_filename=None, representation="hospital"):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Pipeline PopulationSpace iniciada.',
                'facility_specs': facility_specs, 'k': k,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} estabelecimento(s) via BPHO/PySUS...',
        })

        result = _run_population_cli("cluster", {"facilities": facility_specs, "k": k, "representation": representation})

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        if output_filename and output_filename.strip():
            final_filename = output_filename.strip()
            if not final_filename.lower().endswith('.csv'):
                final_filename += '.csv'
        else:
            final_filename = f"population_space_{task_id[:8]}.csv"

        rows = []
        for f in result["facilities"]:
            row = {"facility_uri": f["facility_uri"], "cluster": f["cluster"]}
            row.update(f["values"])
            rows.append(row)

        fieldnames = _union_fieldnames(rows, ["facility_uri", "cluster"])

        output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / "population_space"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / final_filename
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)

        relative_path = str(output_path.relative_to(settings.MEDIA_ROOT))
        rep_label = "hospitais" if representation == "hospital" else "atenção primária (ESF/SIA)"
        output_file = ManagedFile.objects.create(
            uploader=user,
            file=relative_path,
            filename=final_filename,
            description=(
                f"PopulationSpace ({rep_label}): {len(rows)} estabelecimentos, K={k} (KMeans), "
                f"via BPHO (SPARQL)."
            ),
            file_type=FileType.POPULATION_SPACE,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {len(rows)} estabelecimentos carregados, K={k}."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'output_file_id': output_file.id, 'n_facilities': len(rows)}

    except Exception as e:
        logger.exception(f"Falha na pipeline PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_causal_pipeline(self, facility_specs, user_id, threshold=None):
    """Densidade de força de trabalho (vínculos/internação) vs. tempo de
    internação, entre hospitais reais -- ponte para population_cli.py causal."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Análise causal (densidade de força de trabalho x tempo de internação) iniciada.',
                'facility_specs': facility_specs,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} hospital(is) via BPHO...',
        })

        payload = {"facilities": facility_specs}
        if threshold is not None:
            payload["threshold"] = threshold
        result = _run_population_cli("causal", payload)

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        rows = [
            {"facility_uri": f["facility_uri"], "density": f["density"], "avg_length_of_stay_days": f.get("avg_length_of_stay_days")}
            for f in result["facilities"]
        ]
        output_file = _save_result_files(
            subdir="population_causal",
            filename_stem=f"population_causal_{task_id[:8]}",
            rows=rows,
            fieldnames=["facility_uri", "density", "avg_length_of_stay_days"],
            result=result,
            user=user,
            description=(
                f"PopulationSpace causal: {result['n_facilities']} hospitais, "
                f"{len(result['matched_pairs'])} par(es) pareado(s) por propensão, limiar de densidade={result['threshold']:.2f}."
            ),
            file_type=FileType.POP_CAUSAL,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = (
            f"Concluído. {result['n_facilities']} hospitais, "
            f"{len(result['matched_pairs'])} par(es) pareado(s) por propensão."
        )
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': result['n_facilities'], 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na análise causal PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_compare_pipeline(self, facility_specs, user_id, geometry='euclidean'):
    """Distâncias par a par entre estabelecimentos, sob a geometria escolhida
    -- ponte para population_cli.py compare (antes só acessível via CLI/chat
    da BPHO, agora também disparável como tela dedicada no LabSUS)."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': f'Comparação par a par ({geometry}) iniciada.',
                'facility_specs': facility_specs,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} estabelecimento(s) via BPHO...',
        })

        result = _run_population_cli("compare", {"facilities": facility_specs, "geometry": geometry})

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        output_file = _save_result_files(
            subdir="population_compare",
            filename_stem=f"population_compare_{task_id[:8]}",
            rows=result["distances"],
            fieldnames=["facility_a", "facility_b", "distance"],
            result=result,
            user=user,
            description=f"PopulationSpace comparação ({geometry}): {len(result['facilities'])} estabelecimentos, {len(result['distances'])} par(es) comparado(s).",
            file_type=FileType.POP_COMPARE,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {len(result['facilities'])} estabelecimentos, {len(result['distances'])} par(es) comparado(s)."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': len(result['facilities']), 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na comparação PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_anomaly_pipeline(self, facility_specs, user_id, contamination="auto"):
    """Detecção de anomalia (IsolationForest) entre hospitais reais -- ponte
    para population_cli.py anomaly."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Detecção de anomalias (IsolationForest) iniciada.',
                'facility_specs': facility_specs,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} hospital(is) via BPHO...',
        })

        result = _run_population_cli("anomaly", {"facilities": facility_specs, "contamination": contamination})

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        rows = []
        for f in result["facilities"]:
            row = {"facility_uri": f["facility_uri"], "anomaly_score": f["anomaly_score"], "is_outlier": f["is_outlier"]}
            row.update(f["values"])
            rows.append(row)
        fieldnames = _union_fieldnames(rows, ["facility_uri", "anomaly_score", "is_outlier"])
        output_file = _save_result_files(
            subdir="population_anomaly",
            filename_stem=f"population_anomaly_{task_id[:8]}",
            rows=rows,
            fieldnames=fieldnames,
            result=result,
            user=user,
            description=f"PopulationSpace anomalias: {result['n_outliers']} de {result['n_facilities']} hospitais sinalizados (IsolationForest, contaminação={contamination}).",
            file_type=FileType.POP_ANOMALY,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {result['n_outliers']} de {result['n_facilities']} hospitais sinalizados como anômalos."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': result['n_facilities'], 'n_outliers': result['n_outliers'], 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na detecção de anomalias PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_risk_pipeline(self, facility_specs, user_id, weights=None):
    """Score de risco transparente (soma ponderada de Features reais) --
    ponte para population_cli.py risk."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Score de risco iniciado.',
                'facility_specs': facility_specs,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} estabelecimento(s) via BPHO...',
        })

        payload = {"facilities": facility_specs}
        if weights:
            payload["weights"] = weights
        result = _run_population_cli("risk", payload)

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        rows = []
        for f in result["facilities"]:
            row = {"facility_uri": f["facility_uri"], "risk_score": f["risk_score"]}
            row.update(f["values"])
            rows.append(row)
        fieldnames = _union_fieldnames(rows, ["facility_uri", "risk_score"])
        output_file = _save_result_files(
            subdir="population_risk",
            filename_stem=f"population_risk_{task_id[:8]}",
            rows=rows,
            fieldnames=fieldnames,
            result=result,
            user=user,
            description=f"PopulationSpace score de risco: {result['n_facilities']} estabelecimentos rankeados, pesos={result['weights']}.",
            file_type=FileType.POP_RISK,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {result['n_facilities']} estabelecimentos rankeados."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': result['n_facilities'], 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha no score de risco PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_predict_uncertainty_pipeline(self, facility_specs, user_id, target_feature="avg_length_of_stay_days", kernel="rbf"):
    """Previsão com incerteza (Processo Gaussiano) de um indicador de
    utilização a partir de força de trabalho + demografia -- ponte para
    population_cli.py predict_uncertainty."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Previsão com incerteza (Processo Gaussiano) iniciada.',
                'facility_specs': facility_specs,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} hospital(is) via BPHO...',
        })

        result = _run_population_cli("predict_uncertainty", {
            "facilities": facility_specs, "target_feature": target_feature, "kernel": kernel,
        })

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        output_file = _save_result_files(
            subdir="population_uncertainty",
            filename_stem=f"population_uncertainty_{task_id[:8]}",
            rows=result["facilities"],
            fieldnames=["facility_uri", "actual", "predicted_mean", "predicted_std", "z_score"],
            result=result,
            user=user,
            description=f"PopulationSpace previsão com incerteza: {result['n_facilities']} hospitais, alvo={target_feature}, kernel={kernel}.",
            file_type=FileType.POP_UNCERTAINTY,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {result['n_facilities']} hospitais, alvo={target_feature}."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': result['n_facilities'], 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na previsão com incerteza PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_classify_pipeline(self, facility_specs, user_id, label_feature="avg_length_of_stay_days", threshold=None):
    """Classificador (RandomForest) + explicação SHAP -- ponte para
    population_cli.py classify."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Classificador + explicação SHAP iniciado.',
                'facility_specs': facility_specs,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} hospital(is) via BPHO...',
        })

        payload = {"facilities": facility_specs, "label_feature": label_feature}
        if threshold is not None:
            payload["threshold"] = threshold
        result = _run_population_cli("classify", payload)

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        output_file = _save_result_files(
            subdir="population_classify",
            filename_stem=f"population_classify_{task_id[:8]}",
            rows=result["facilities"],
            fieldnames=["facility_uri", "label_feature", "actual_value", "label_alto", "predicted_probability_alto"],
            result=result,
            user=user,
            description=(
                f"PopulationSpace classificador: {result['n_facilities']} hospitais, "
                f"{result['n_label_alto']} classificado(s) como '{label_feature} alto', limiar={result['threshold']:.2f}."
            ),
            file_type=FileType.POP_CLASSIFY,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = (
            f"Concluído. {result['n_facilities']} hospitais, "
            f"{result['n_label_alto']} classificado(s) como '{label_feature} alto'."
        )
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': result['n_facilities'], 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha no classificador PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_transitions_pipeline(self, facility_specs, user_id, k=3):
    """Fenotipagem + transições de fenótipo ao longo de várias competências --
    ponte para population_cli.py transitions. `facility_specs` aqui tem um
    formato DIFERENTE dos outros tasks: cada item é
    {facility_uri, uf, competencias: [{ano, mes}, ...]}, não um único
    {facility_uri, ano, mes, uf} -- é o único comando que carrega vários
    pontos no tempo por estabelecimento."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Transições de fenótipo iniciadas.',
                'facility_specs': facility_specs, 'k': k,
            }
        )
        n_competencias = sum(len(f.get('competencias', [])) for f in facility_specs)
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} estabelecimento(s), {n_competencias} competência(s) via BPHO...',
        })

        result = _run_population_cli("transitions", {"facilities": facility_specs, "k": k}, timeout=1800)

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        # Formato longo -- uma linha por (estabelecimento, competência), não uma
        # linha por estabelecimento -- é a forma tabular real do dado (cada
        # observação no tempo é sua própria linha, igual uma série temporal).
        rows = [
            {"facility_uri": f["facility_uri"], "competencia": s["competencia"], "phenotype": s["phenotype"]}
            for f in result["facilities"]
            for s in f["sequence"]
        ]
        output_file = _save_result_files(
            subdir="population_transitions",
            filename_stem=f"population_transitions_{task_id[:8]}",
            rows=rows,
            fieldnames=["facility_uri", "competencia", "phenotype"],
            result=result,
            user=user,
            description=(
                f"PopulationSpace transições: {len(facility_specs)} estabelecimentos, K={k} fenótipos, "
                f"{len(result['transition_summary'])} tipo(s) de transição observada(s)."
            ),
            file_type=FileType.POP_TRANSITIONS,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {len(facility_specs)} estabelecimentos, {len(result['transition_summary'])} tipo(s) de transição observada(s)."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': len(facility_specs), 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha nas transições de fenótipo PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_survival_pipeline(self, facility_specs, user_id, event_feature=None, event_threshold=None, k=3):
    """Sobrevida (Kaplan-Meier + Cox) sobre tempo até um evento demográfico --
    ponte para population_cli.py survival. Mesmo formato multi-competência de
    `run_population_transitions_pipeline` (único outro comando que carrega
    várias competências por estabelecimento): cada item de `facility_specs` é
    {facility_uri, uf, competencias: [{ano, mes}, ...]}."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Análise de sobrevida iniciada.',
                'facility_specs': facility_specs, 'k': k,
            }
        )
        n_competencias = sum(len(f.get('competencias', [])) for f in facility_specs)
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} estabelecimento(s), {n_competencias} competência(s) via BPHO...',
        })

        payload = {"facilities": facility_specs, "k": k}
        if event_feature:
            payload["event_feature"] = event_feature
        if event_threshold is not None:
            payload["event_threshold"] = event_threshold

        result = _run_population_cli("survival", payload, timeout=1800)

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        rows = result["facilities"]
        feat = result["event_feature"]
        output_file = _save_result_files(
            subdir="population_survival",
            filename_stem=f"population_survival_{task_id[:8]}",
            rows=rows,
            fieldnames=["facility_uri", "phenotype", "duration", "event", f"{feat}_baseline", f"{feat}_final"],
            result=result,
            user=user,
            description=(
                f"PopulationSpace sobrevida: {len(facility_specs)} estabelecimentos, K={k} fenótipos, "
                f"evento={feat} > {result['event_threshold']:.2f}"
                + (f", log-rank p={result['kaplan_meier']['logrank_p']:.3f}" if result.get('kaplan_meier') else "")
                + "."
            ),
            file_type=FileType.POP_SURVIVAL,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {len(facility_specs)} estabelecimentos analisados."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': len(facility_specs), 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na análise de sobrevida PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_intervene_pipeline(self, facility_specs, user_id, target_facility_uri, shifts, risk_weights=None, label_feature="avg_length_of_stay_days", threshold=None):
    """Simulador contrafactual -- ponte para population_cli.py intervene.
    Desloca Features (unidade bruta) de um estabelecimento-alvo e mede o
    efeito no Score de Risco e na probabilidade do Classificador, ambos já
    existentes (population_risk / population_classify)."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Simulação de intervenção iniciada.',
                'facility_specs': facility_specs,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} hospital(is) via BPHO...',
        })

        payload = {
            "facilities": facility_specs,
            "target_facility_uri": target_facility_uri,
            "shifts": shifts,
            "label_feature": label_feature,
        }
        if risk_weights:
            payload["risk_weights"] = risk_weights
        if threshold is not None:
            payload["threshold"] = threshold
        result = _run_population_cli("intervene", payload)

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        rows = [
            {
                "metric": "risk_score",
                "baseline": result["risk"]["baseline_score"],
                "counterfactual": result["risk"]["counterfactual_score"],
                "delta": result["risk"]["delta"],
            },
        ]
        if result.get("classify"):
            rows.append({
                "metric": "classify_probability_alto",
                "baseline": result["classify"]["baseline_probability_alto"],
                "counterfactual": result["classify"]["counterfactual_probability_alto"],
                "delta": result["classify"]["counterfactual_probability_alto"] - result["classify"]["baseline_probability_alto"],
            })

        output_file = _save_result_files(
            subdir="population_intervene",
            filename_stem=f"population_intervene_{task_id[:8]}",
            rows=rows,
            fieldnames=["metric", "baseline", "counterfactual", "delta"],
            result=result,
            user=user,
            description=(
                f"PopulationSpace intervenção: {target_facility_uri}, shifts em "
                f"{', '.join(shifts.keys())}, Δrisco={result['risk']['delta']:+.3f}."
            ),
            file_type=FileType.POP_INTERVENE,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. Δrisco={result['risk']['delta']:+.3f} para {target_facility_uri}."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': len(facility_specs), 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na simulação de intervenção PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_graph_pipeline(self, facility_specs, user_id, geometry='euclidean', k=5, phenotype_k=3):
    """Grafo de similaridade (k vizinhos mais próximos + comunidades Louvain)
    entre estabelecimentos -- ponte para population_cli.py graph."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': f'Grafo de similaridade ({geometry}) iniciado.',
                'facility_specs': facility_specs,
                'k': phenotype_k,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} estabelecimento(s) via BPHO...',
        })

        result = _run_population_cli("graph", {
            "facilities": facility_specs, "geometry": geometry, "k": k, "phenotype_k": phenotype_k,
        })

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        rows = []
        for n in result["nodes"]:
            row = {"facility_uri": n["facility_uri"], "community": n["community"], "phenotype": n["phenotype"], "degree": n["degree"]}
            row.update(n["values"])
            rows.append(row)
        fieldnames = _union_fieldnames(rows, ["facility_uri", "community", "phenotype", "degree"])

        output_file = _save_result_files(
            subdir="population_graph",
            filename_stem=f"population_graph_{task_id[:8]}",
            rows=rows,
            fieldnames=fieldnames,
            result=result,
            user=user,
            description=(
                f"PopulationSpace grafo ({geometry}, k={k}): {result['n_facilities']} estabelecimentos, "
                f"{result['n_communities']} comunidade(s), modularidade={result['modularity']:.3f}."
            ),
            file_type=FileType.POP_GRAPH,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {result['n_communities']} comunidade(s), modularidade={result['modularity']:.3f}."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': result['n_facilities'], 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha no grafo de similaridade PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_factor_pipeline(self, facility_specs, user_id, n_factors=2):
    """Análise Fatorial (eixos de variação compartilhada entre utilização/
    força de trabalho/demografia) -- ponte para population_cli.py factor."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Análise fatorial iniciada.',
                'facility_specs': facility_specs,
                'k': n_factors,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} estabelecimento(s) via BPHO...',
        })

        result = _run_population_cli("factor", {"facilities": facility_specs, "n_factors": n_factors})

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        rows = []
        for f in result["facilities"]:
            row = {"facility_uri": f["facility_uri"]}
            row.update(f["factor_scores"])
            row.update(f["values"])
            rows.append(row)
        factor_names = [f"factor_{i + 1}" for i in range(n_factors)]
        fieldnames = _union_fieldnames(rows, ["facility_uri"] + factor_names)

        output_file = _save_result_files(
            subdir="population_factor",
            filename_stem=f"population_factor_{task_id[:8]}",
            rows=rows,
            fieldnames=fieldnames,
            result=result,
            user=user,
            description=f"PopulationSpace fatores latentes: {result['n_facilities']} estabelecimentos, {n_factors} fator(es).",
            file_type=FileType.POP_FACTOR,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {result['n_facilities']} estabelecimentos, {n_factors} fator(es)."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': result['n_facilities'], 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na análise fatorial PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_topology_pipeline(self, facility_specs, user_id, min_persistence=0.5, max_dimension=1, n_cubes=5, perc_overlap=0.3):
    """Homologia persistente (Betti numbers) + grafo Mapper -- ponte para
    population_cli.py topology."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Análise topológica iniciada.',
                'facility_specs': facility_specs,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} estabelecimento(s) via BPHO...',
        })

        result = _run_population_cli("topology", {
            "facilities": facility_specs,
            "min_persistence": min_persistence,
            "max_dimension": max_dimension,
            "n_cubes": n_cubes,
            "perc_overlap": perc_overlap,
        })

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        rows = []
        for f in result["facilities"]:
            row = {"facility_uri": f["facility_uri"]}
            row.update(f["values"])
            rows.append(row)
        fieldnames = _union_fieldnames(rows, ["facility_uri"])

        output_file = _save_result_files(
            subdir="population_topology",
            filename_stem=f"population_topology_{task_id[:8]}",
            rows=rows,
            fieldnames=fieldnames,
            result=result,
            user=user,
            description=(
                f"PopulationSpace topologia: {result['n_facilities']} estabelecimentos, "
                f"Betti={result['betti_numbers']}, Mapper com {result['mapper']['n_nodes']} nó(s)."
            ),
            file_type=FileType.POP_TOPOLOGY,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. Betti={result['betti_numbers']}, Mapper com {result['mapper']['n_nodes']} nó(s)."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': result['n_facilities'], 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na análise topológica PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_early_warning_pipeline(self, facility_specs, user_id, min_points=8, window_size=4, n_surrogates=200, detrend_method='linear'):
    """Alerta precoce (critical slowing down) sobre a trajetória de cada
    estabelecimento -- ponte para population_cli.py early_warning. Mesmo
    formato multi-competência de `run_population_survival_pipeline`."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Análise de alerta precoce iniciada.',
                'facility_specs': facility_specs,
            }
        )
        n_competencias = sum(len(f.get('competencias', [])) for f in facility_specs)
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} estabelecimento(s), {n_competencias} competência(s) via BPHO...',
        })

        result = _run_population_cli("early_warning", {
            "facilities": facility_specs,
            "min_points": min_points,
            "window_size": window_size,
            "n_surrogates": n_surrogates,
            "detrend_method": detrend_method,
        }, timeout=1800)

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        rows = []
        for f in result["facilities"]:
            row = {
                "facility_uri": f["facility_uri"],
                "n_points": f["n_points"],
                "sufficient_data": f["sufficient_data"],
                "warning": f["warning"],
                "n_indicators_available": f["n_indicators_available"],
                "n_indicators_rising_significant": f["n_indicators_rising_significant"],
            }
            for name in ("variance", "autocorrelation", "skewness"):
                ind = f["indicators"].get(name, {})
                row[f"tau_{name}"] = ind.get("tau")
                row[f"p_{name}"] = ind.get("p_value")
            rows.append(row)

        output_file = _save_result_files(
            subdir="population_early_warning",
            filename_stem=f"population_early_warning_{task_id[:8]}",
            rows=rows,
            fieldnames=[
                "facility_uri", "n_points", "sufficient_data", "warning",
                "n_indicators_available", "n_indicators_rising_significant",
                "tau_variance", "p_variance", "tau_autocorrelation", "p_autocorrelation",
                "tau_skewness", "p_skewness",
            ],
            result=result,
            user=user,
            description=(
                f"PopulationSpace alerta precoce: {result['n_facilities']} estabelecimentos, "
                f"{result['n_warnings']} com alerta, {result['n_insufficient_data']} com dado insuficiente."
            ),
            file_type=FileType.POP_EARLY_WARNING,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {result['n_warnings']} de {result['n_facilities']} estabelecimento(s) com alerta."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': result['n_facilities'], 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na análise de alerta precoce PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_gnn_pipeline(self, facility_specs, user_id, geometry='euclidean', k=5, phenotype_k=3, label_fraction=0.5, hidden_dim=16, epochs=300, learning_rate=0.05):
    """GCN de 2 camadas (biospace.gnn.SimpleGCN) sobre o mesmo grafo k-NN
    de 'graph' -- ponte para population_cli.py gnn."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': f'GNN ({geometry}) iniciada.',
                'facility_specs': facility_specs,
                'k': phenotype_k,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} estabelecimento(s) via BPHO...',
        })

        result = _run_population_cli("gnn", {
            "facilities": facility_specs, "geometry": geometry, "k": k, "phenotype_k": phenotype_k,
            "label_fraction": label_fraction, "hidden_dim": hidden_dim, "epochs": epochs, "learning_rate": learning_rate,
        }, timeout=1800)

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        rows = [
            {
                "facility_uri": n["facility_uri"],
                "is_labeled": n["is_labeled"],
                "true_phenotype": n["true_phenotype"],
                "predicted_phenotype": n["predicted_phenotype"],
                "correct": n["correct"],
            }
            for n in result["nodes"]
        ]

        output_file = _save_result_files(
            subdir="population_gnn",
            filename_stem=f"population_gnn_{task_id[:8]}",
            rows=rows,
            fieldnames=["facility_uri", "is_labeled", "true_phenotype", "predicted_phenotype", "correct"],
            result=result,
            user=user,
            description=(
                f"PopulationSpace GNN ({geometry}, k={k}): {result['n_facilities']} estabelecimentos, "
                f"test_accuracy={result['test_accuracy']:.3f} (baseline={result['test_baseline_accuracy']:.3f})."
            ),
            file_type=FileType.POP_GNN,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. test_accuracy={result['test_accuracy']:.3f} (baseline={result['test_baseline_accuracy']:.3f})."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': result['n_facilities'], 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na GNN PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_dynamics_pipeline(self, facility_specs, user_id, n_worst=5):
    """Dinâmica populacional (biospace.dynamics.StabilityOperator) -- ponte
    para population_cli.py dynamics. Mesmo formato multi-competência de
    `run_population_survival_pipeline`, mas o resultado é POR FEATURE, não
    por estabelecimento (único caso assim nesta série)."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Análise de dinâmica iniciada.',
                'facility_specs': facility_specs,
            }
        )
        n_competencias = sum(len(f.get('competencias', [])) for f in facility_specs)
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} estabelecimento(s), {n_competencias} competência(s) via BPHO...',
        })

        result = _run_population_cli("dynamics", {
            "facilities": facility_specs, "n_worst": n_worst,
        }, timeout=1800)

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        rows = [
            {
                "name": f["name"], "mu": f["mu"], "phi_per_day": f["phi_per_day"],
                "is_stable": f["is_stable"], "n_pairs": f["n_pairs"],
                "half_life_days": f["half_life_days"], "resilience_score": f["resilience_score"],
            }
            for f in result["features"]
        ]

        output_file = _save_result_files(
            subdir="population_dynamics",
            filename_stem=f"population_dynamics_{task_id[:8]}",
            rows=rows,
            fieldnames=["name", "mu", "phi_per_day", "is_stable", "n_pairs", "half_life_days", "resilience_score"],
            result=result,
            user=user,
            description=(
                f"PopulationSpace dinâmica: {result['n_facilities']} estabelecimentos, "
                f"{result['n_stable']}/{result['n_features']} Features estáveis."
            ),
            file_type=FileType.POP_DYNAMICS,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {result['n_stable']}/{result['n_features']} Features estáveis."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': result['n_facilities'], 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na análise de dinâmica PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_per_capita_pipeline(self, facility_specs, user_id):
    """Taxa por mil habitantes usando a população do município como
    denominador -- ponte para population_cli.py per_capita."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Análise per capita iniciada.',
                'facility_specs': facility_specs,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(facility_specs)} estabelecimento(s) via BPHO...',
        })

        result = _run_population_cli("per_capita", {"facilities": facility_specs})

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        rows = [
            {
                "facility_uri": f["facility_uri"],
                "municipio_cod_ibge_6": f["municipio_cod_ibge_6"],
                "populacao": f["populacao"],
                "ano": f["ano"],
                "n_hospitalizations": f["n_hospitalizations"],
                "n_affiliations": f["n_affiliations"],
                "taxa_internacao_por_mil": f["taxa_internacao_por_mil"],
                "taxa_vinculos_por_mil": f["taxa_vinculos_por_mil"],
            }
            for f in result["facilities"]
        ]

        output_file = _save_result_files(
            subdir="population_per_capita",
            filename_stem=f"population_per_capita_{task_id[:8]}",
            rows=rows,
            fieldnames=[
                "facility_uri", "municipio_cod_ibge_6", "populacao", "ano",
                "n_hospitalizations", "n_affiliations",
                "taxa_internacao_por_mil", "taxa_vinculos_por_mil",
            ],
            result=result,
            user=user,
            description=(
                f"PopulationSpace per capita: {result['n_facilities']} estabelecimentos, "
                f"{result['n_municipio_resolved']} com município resolvido, "
                f"{result['n_populacao_resolved']} com população resolvida."
            ),
            file_type=FileType.POP_PER_CAPITA,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {result['n_populacao_resolved']}/{result['n_facilities']} com taxa calculada."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_facilities': result['n_facilities'], 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na análise per capita PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_municipio_pipeline(self, municipio_specs, diseases, user_id):
    """Ficha & comparação de MUNICÍPIO -- ponte para population_cli.py municipio.
    Único comando de PopulationSpace cujo B é uma cidade (MunicipioSystem),
    não um estabelecimento -- reaproveita PopulationSpaceTaskStatus/
    FileType porque a mecânica de task/arquivo é idêntica, só o objeto
    de análise muda."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Análise de município iniciada.',
                'facility_specs': municipio_specs,
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando {len(municipio_specs)} município(s) via SIH/SIM/SINASC/SINAN...',
        })

        result = _run_population_cli("municipio", {"municipios": municipio_specs, "diseases": diseases})

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        value_keys: list[str] = []
        for m in result["municipios"]:
            for k in m["values"]:
                if k not in value_keys:
                    value_keys.append(k)

        rows = [
            {"cod_ibge": m["cod_ibge"], **{k: m["values"].get(k) for k in value_keys}}
            for m in result["municipios"]
        ]

        output_file = _save_result_files(
            subdir="population_municipio",
            filename_stem=f"population_municipio_{task_id[:8]}",
            rows=rows,
            fieldnames=["cod_ibge"] + value_keys,
            result=result,
            user=user,
            description=f"PopulationSpace município: {result['loader_report']['n_municipios']} município(s).",
            file_type=FileType.POP_MUNICIPIO,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {result['loader_report']['n_municipios']} município(s) carregado(s)."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {'status': 'SUCCESS', 'n_municipios': result['loader_report']['n_municipios'], 'output_file_id': output_file.id}

    except Exception as e:
        logger.exception(f"Falha na análise de município PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_notificacao_pipeline(self, disease_code, year_suffixes, limit, user_id):
    """Ficha & desfecho de CASOS DE NOTIFICAÇÃO (agravo do SINAN) -- ponte para
    population_cli.py notificacao. Terceiro objeto de análise fora do
    estabelecimento/município: B aqui é UMA notificação (DiseaseCaseSystem)."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': f'Análise de notificação ({disease_code}) iniciada.',
                'facility_specs': {"disease_code": disease_code, "year_suffixes": year_suffixes},
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': f'Carregando notificações de {disease_code} ({", ".join(year_suffixes)}) via SINAN...',
        })

        result = _run_population_cli(
            "notificacao",
            {"disease_code": disease_code, "year_suffixes": year_suffixes, "limit": limit},
        )

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        value_keys: list[str] = []
        for c in result["sample_cases"]:
            for k in c["values"]:
                if k not in value_keys:
                    value_keys.append(k)

        rows = [
            {"case_id": c["case_id"], **{k: c["values"].get(k) for k in value_keys}}
            for c in result["sample_cases"]
        ]

        output_file = _save_result_files(
            subdir="population_notificacao",
            filename_stem=f"population_notificacao_{task_id[:8]}",
            rows=rows,
            fieldnames=["case_id"] + value_keys,
            result=result,
            user=user,
            description=(
                f"PopulationSpace notificação: {result['loader_report']['n_cases_loaded']} casos de "
                f"{disease_code}, {result['loader_report']['n_with_outcome']} com desfecho."
            ),
            file_type=FileType.POP_NOTIFICACAO,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = (
            f"Concluído. {result['loader_report']['n_cases_loaded']} casos carregados, "
            f"{result['loader_report']['n_with_outcome']} com desfecho."
        )
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {
            'status': 'SUCCESS',
            'n_cases_loaded': result['loader_report']['n_cases_loaded'],
            'output_file_id': output_file.id,
        }

    except Exception as e:
        logger.exception(f"Falha na análise de notificação PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise


@shared_task(bind=True)
def run_population_familia_pipeline(self, family_ids, sample_size, user_id):
    """Ficha & composição de FAMÍLIA (CadÚnico) -- ponte para
    population_cli.py familia. Quarto e último objeto de análise fora do
    estabelecimento: B aqui é UMA família (FamilySystem), consultada via
    SPARQL contra a BPHO."""
    User = apps.get_model(settings.AUTH_USER_MODEL)
    PopulationSpaceTaskStatus = apps.get_model('pipeline_population_space', 'PopulationSpaceTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None
    task_status_entry = None

    try:
        task_status_entry, _ = PopulationSpaceTaskStatus.objects.get_or_create(
            task_id=task_id,
            defaults={
                'user': user, 'status': 'STARTED',
                'message': 'Análise de família iniciada.',
                'facility_specs': {"family_ids": family_ids, "sample_size": sample_size},
            }
        )
        self.update_state(state='PROGRESS', meta={
            'progress': 10,
            'message': 'Consultando composição familiar via BPHO (SPARQL)...',
        })

        payload = {"family_ids": family_ids} if family_ids else {"sample_size": sample_size}
        result = _run_population_cli("familia", payload)

        self.update_state(state='PROGRESS', meta={'progress': 85, 'message': 'Salvando resultados...'})

        value_keys: list[str] = []
        for f in result["families"]:
            for k in f["values"]:
                if k not in value_keys:
                    value_keys.append(k)

        rows = [
            {"family_id": f["family_id"], **{k: f["values"].get(k) for k in value_keys}}
            for f in result["families"]
        ]

        output_file = _save_result_files(
            subdir="population_familia",
            filename_stem=f"population_familia_{task_id[:8]}",
            rows=rows,
            fieldnames=["family_id"] + value_keys,
            result=result,
            user=user,
            description=f"PopulationSpace família: {result['loader_report']['n_families_found']} família(s).",
            file_type=FileType.POP_FAMILIA,
            task_id=task_id,
        )

        task_status_entry.status = 'SUCCESS'
        task_status_entry.message = f"Concluído. {result['loader_report']['n_families_found']} família(s) encontrada(s)."
        task_status_entry.output_file = output_file
        task_status_entry.results_summary = result
        task_status_entry.save()

        return {
            'status': 'SUCCESS',
            'n_families_found': result['loader_report']['n_families_found'],
            'output_file_id': output_file.id,
        }

    except Exception as e:
        logger.exception(f"Falha na análise de família PopulationSpace {task_id}.")
        if task_status_entry:
            task_status_entry.status = 'FAILURE'
            task_status_entry.message = str(e)
            task_status_entry.save()
        raise
