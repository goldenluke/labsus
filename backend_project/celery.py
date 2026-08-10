
from celery import Celery
import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend_project.settings')

app = Celery('backend_project')
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

# Definindo uma tarefa periódica para agendar a integração
@app.task
def integrate_lab_sus_data_periodically():
    # Lógica para integrar com o LexLab
    response = requests.get('URL_DO_LABSUS_API')
    data = response.json()
    # Aqui, você pode fazer a integração com LexLab
    requests.post('URL_DO_LABLEX_API', json=data)


