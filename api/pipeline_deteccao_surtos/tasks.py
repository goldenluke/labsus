from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.apps import apps
import pandas as pd
import numpy as np
from pathlib import Path
import logging
import os
import re
import unicodedata
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from functools import lru_cache
from api.models import FileType

logger = logging.getLogger(__name__)

MAPA_UF = {
    'RO': '11', 'AC': '12', 'AM': '13', 'RR': '14', 'PA': '15',
    'AP': '16', 'TO': '17', 'MA': '21', 'PI': '22', 'CE': '23',
    'RN': '24', 'PB': '25', 'PE': '26', 'AL': '27', 'SE': '28',
    'BA': '29', 'MG': '31', 'ES': '32', 'RJ': '33', 'SP': '35',
    'PR': '41', 'SC': '42', 'RS': '43', 'MS': '50', 'MT': '51',
    'GO': '52', 'DF': '53',
}


def secure_filename(filename):
    filename = unicodedata.normalize('NFKD', filename).encode('ascii', 'ignore').decode('ascii')
    filename = re.sub(r'[\\/*?:"<>|]', '', filename)
    if filename.startswith('.'):
        filename = filename[1:]
    if not filename.strip():
        return "arquivo_sem_nome"
    return filename.strip()


def _get_sinan_diseases():
    from pysus.ftp.databases.sinan import SINAN
    return SINAN.diseases


@lru_cache(maxsize=1)
def _get_municipality_names():
    try:
        from api.utils.geo import get_municipality_mapping
        mapping = get_municipality_mapping()
        return {code: info['nome'] for code, info in mapping.items()}
    except Exception:
        return {}


def carregar_dados_sinan(ufs, anos, agravo, task_update_func=None):
    from pysus.ftp.databases.sinan import SINAN

    logger.info(f"Carregando dados SINAN-{agravo} para {ufs}/{anos}")

    valid_diseases = SINAN.diseases
    if agravo not in valid_diseases:
        raise ValueError(
            f"Código '{agravo}' não existe no SINAN. "
            f"Códigos válidos: {', '.join(sorted(valid_diseases.keys()))}"
        )

    if task_update_func:
        task_update_func(state='PROGRESS', meta={
            'progress': 5,
            'message': f'Conectando ao FTP do SINAN para {valid_diseases[agravo]}...'
        })

    sinan_db = SINAN()
    sinan_db.load()

    if task_update_func:
        task_update_func(state='PROGRESS', meta={
            'progress': 10,
            'message': 'Listando arquivos disponíveis...'
        })

    files = sinan_db.get_files(dis_code=agravo, year=anos)

    if not files:
        raise FileNotFoundError(
            f"Nenhum arquivo SINAN encontrado para {agravo} nos anos {anos}."
        )

    total_files = len(files)
    logger.info(f"Total de arquivos a baixar: {total_files}")

    dfs = []
    for i, file in enumerate(files):
        if task_update_func:
            progress = 10 + int(25 * (i + 1) / total_files)
            task_update_func(state='PROGRESS', meta={
                'progress': progress,
                'message': f'Baixando arquivo {i + 1}/{total_files} ({file.basename})...'
            })

        downloaded = sinan_db.download([file])
        if isinstance(downloaded, list):
            for p in downloaded:
                if hasattr(p, 'to_dataframe'):
                    dfs.append(p.to_dataframe())
        elif hasattr(downloaded, "to_dataframe"):
            dfs.append(downloaded.to_dataframe())

    if not dfs:
        raise ValueError("Falha ao converter os arquivos baixados em DataFrames.")

    df_brasil = pd.concat(dfs, ignore_index=True)

    cod_ufs = [MAPA_UF.get(u.upper(), u) for u in ufs]
    df_brasil['SG_UF_NOT'] = df_brasil['SG_UF_NOT'].astype(str)
    lista_filtros = list(set(cod_ufs + [u.upper() for u in ufs]))
    df_filtrado = df_brasil[df_brasil['SG_UF_NOT'].isin(lista_filtros)].copy()

    if df_filtrado.empty:
        raise ValueError(
            f"Nenhuma notificação encontrada para {agravo} em {ufs}/{anos}. "
            f"Verifique se há dados disponíveis para esses estados e anos."
        )

    logger.info(f"Dados carregados: {len(df_filtrado)} notificações.")
    return df_filtrado


def detectar_anomalias(df, dir_saida, task_update_func):
    from prophet import Prophet

    logger.info("Iniciando detecção de anomalias por município...")

    dt_col = None
    for col in ['DT_NOTIFIC', 'DT_SIN_PRI']:
        if col in df.columns:
            dt_col = col
            break

    if dt_col is None:
        raise ValueError("Coluna de data não encontrada nos dados SINAN.")

    df[dt_col] = pd.to_datetime(df[dt_col], errors='coerce')
    df.dropna(subset=[dt_col], inplace=True)

    contagem_mun = df['ID_MUNICIP'].value_counts()
    muns_relevantes = contagem_mun[contagem_mun > 50].index.tolist()
    total_muns = len(muns_relevantes)

    if total_muns == 0:
        logger.info("Nenhum município com volume suficiente para análise.")
        return pd.DataFrame(), []

    logger.info(f"Analisando {total_muns} municípios com histórico suficiente...")

    mun_names = _get_municipality_names()
    alertas_gerais = []
    charts_gerados = []
    series_completas = []

    for i, mun in enumerate(muns_relevantes):
        if i % 5 == 0:
            progress = 40 + int(50 * i / total_muns)
            task_update_func(state='PROGRESS', meta={
                'progress': min(progress, 90),
                'message': f'Analisando município {i + 1}/{total_muns}...'
            })

        df_mun = df[df['ID_MUNICIP'] == mun].copy()
        serie = df_mun.resample('W-SUN', on=dt_col).size().reset_index(name='y')
        serie.rename(columns={dt_col: 'ds'}, inplace=True)
        serie = serie.set_index('ds').asfreq('W-SUN').fillna(0).reset_index()

        if len(serie) < 20:
            continue

        try:
            m = Prophet(
                yearly_seasonality=True,
                weekly_seasonality=False,
                daily_seasonality=False,
                interval_width=0.95
            )
            m.fit(serie, algorithm='Newton')
            forecast = m.predict(serie)

            resultado = pd.concat([
                serie.set_index('ds'),
                forecast.set_index('ds')[['yhat', 'yhat_lower', 'yhat_upper', 'trend']]
            ], axis=1)

            resultado['SURTO'] = (resultado['y'] > resultado['yhat_upper']) & (resultado['y'] > 5)
            ultimas_semanas = resultado.iloc[-8:]
            surtos_recentes = ultimas_semanas[ultimas_semanas['SURTO']]

            serie_completa = resultado.reset_index().copy()
            serie_completa['MUNICIPIO_IBGE'] = mun
            serie_completa['MUNICIPIO_NOME'] = mun_names.get(str(mun), str(mun))
            series_completas.append(serie_completa)

            if not surtos_recentes.empty:
                fig = m.plot(forecast)
                plt.scatter(
                    surtos_recentes.index, surtos_recentes['y'],
                    color='red', label='Surto Detectado', zorder=10
                )
                plt.title(f"Detecção de Surto: Município {mun}")
                plt.xlabel("Data")
                plt.ylabel("Casos Notificados")
                plt.legend()
                chart_path = dir_saida / f"surto_{mun}.png"
                plt.savefig(chart_path, dpi=120, bbox_inches='tight')
                plt.close()
                charts_gerados.append(str(chart_path))

                for data, row in surtos_recentes.iterrows():
                    alertas_gerais.append({
                        'MUNICIPIO_IBGE': mun,
                        'MUNICIPIO_NOME': mun_names.get(str(mun), str(mun)),
                        'DATA_SEMANA': data.date(),
                        'CASOS_OBSERVADOS': int(row['y']),
                        'LIMITE_ESPERADO': int(row['yhat_upper']),
                        'EXCESSO_CASOS': int(row['y'] - row['yhat_upper'])
                    })
        except Exception as e:
            logger.warning(f"Erro ao processar município {mun}: {e}")
            continue

    df_chart = pd.concat(series_completas, ignore_index=True) if series_completas else pd.DataFrame()

    if alertas_gerais:
        return pd.DataFrame(alertas_gerais), charts_gerados, df_chart
    return pd.DataFrame(), charts_gerados, df_chart


@shared_task(bind=True, time_limit=1800, soft_time_limit=1500)
def run_outbreak_detection(self, user_id, ufs, anos, agravo, output_filename=None):
    ManagedFile = apps.get_model('api', 'ManagedFile')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    DeteccaoSurtosTaskStatus = apps.get_model('pipeline_deteccao_surtos', 'DeteccaoSurtosTaskStatus')

    task_id = self.request.id
    user = User.objects.get(id=user_id) if user_id else None

    task_status_entry, _ = DeteccaoSurtosTaskStatus.objects.get_or_create(
        task_id=task_id,
        defaults={
            'user': user,
            'status': 'STARTED',
            'ufs': ufs,
            'anos': anos,
            'agravo': agravo,
        }
    )

    try:
        disease_name = _get_sinan_diseases().get(agravo, agravo)

        self.update_state(state='PROGRESS', meta={
            'progress': 5, 'message': f'Validando parâmetros para {disease_name}...'
        })

        df_raw = carregar_dados_sinan(ufs, anos, agravo, task_update_func=self.update_state)

        output_dir = Path(settings.MEDIA_ROOT) / "processed_data" / "deteccao_surtos" / str(task_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.update_state(state='PROGRESS', meta={
            'progress': 40,
            'message': f'Detectando anomalias com Prophet em {disease_name}...'
        })
        df_alertas, charts, df_chart = detectar_anomalias(df_raw, output_dir, self.update_state)

        self.update_state(state='PROGRESS', meta={'progress': 92, 'message': 'Salvando relatório...'})

        csv_filename = secure_filename(output_filename or f"alertas_{agravo}_{task_id}")
        if not csv_filename.endswith('.csv'):
            csv_filename += '.csv'
        csv_path = output_dir / csv_filename
        output_csv_file = None
        chart_csv_file = None

        if not df_alertas.empty:
            df_alertas.to_csv(csv_path, sep=';', index=False, encoding='utf-8-sig')
            relative_csv_path = os.path.relpath(csv_path, settings.MEDIA_ROOT)
            output_csv_file = ManagedFile.objects.create(
                uploader=user,
                file=relative_csv_path,
                filename=csv_filename,
                description=f"Relatório de alertas de surto - {disease_name} ({len(df_alertas)} alertas)",
                file_type=FileType.DETECCAO_SURTOS,
                task_id=task_id
            )
            task_status_entry.output_file = output_csv_file

        if not df_chart.empty:
            chart_csv_name = secure_filename(f"chart_data_{agravo}_{task_id}.csv")
            chart_csv_path = output_dir / chart_csv_name
            df_chart.to_csv(chart_csv_path, sep=';', index=False, encoding='utf-8-sig')
            relative_chart_path = os.path.relpath(chart_csv_path, settings.MEDIA_ROOT)
            chart_csv_file = ManagedFile.objects.create(
                uploader=user,
                file=relative_chart_path,
                filename=chart_csv_name,
                description=f"Dados de série temporal para gráficos - {disease_name}",
                file_type=FileType.CHART_DATA,
                task_id=task_id
            )
            task_status_entry.chart_data_file = chart_csv_file

        total_alertas = len(df_alertas)
        task_status_entry.status = 'SUCCESS'
        task_status_entry.total_alertas = total_alertas
        task_status_entry.message = (
            f"Análise de {disease_name} concluída. "
            f"{total_alertas} alerta(s) detectado(s) em {len(charts)} município(s) "
            f"de {', '.join(ufs)} ({', '.join(str(a) for a in anos)})."
        )
        task_status_entry.save()

        return {
            'status': 'SUCCESS',
            'total_alertas': total_alertas,
            'output_csv_id': output_csv_file.id if output_csv_file else None,
            'chart_data_file_id': chart_csv_file.id if chart_csv_file else None,
            'charts_count': len(charts),
        }

    except SoftTimeLimitExceeded:
        logger.warning(f"Tempo limite excedido na pipeline {task_id}.")
        task_status_entry.status = 'FAILURE'
        task_status_entry.message = 'Tempo limite excedido. Tente com menos anos ou UFs.'
        task_status_entry.save()
        return {'status': 'FAILURE', 'message': task_status_entry.message}

    except Exception as e:
        logger.exception(f"Falha na pipeline de detecção de surtos {task_id}.")
        task_status_entry.status = 'FAILURE'
        task_status_entry.message = str(e)
        task_status_entry.save()
        raise
