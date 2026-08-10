# LabSUS — Laboratório de Inteligência em Saúde Pública

![Python](https://img.shields.io/badge/python-3.9%2B-blue.svg)
![Django](https://img.shields.io/badge/django-5.2-green.svg)
![React](https://img.shields.io/badge/react-18-blue.svg)

Plataforma de pesquisa e desenvolvimento (P&D) para transformar dados públicos de saúde brasileira (DATASUS, IBGE) em **inteligência acionável**: indicadores municipais, modelos preditivos, análise espacial, séries temporais e painéis geográficos.

O repositório é um **monorepo** com três frentes:

| Pasta | Papel |
| :--- | :--- |
| [`src/`](src/README.md) | **Ambiente de P&D** — prototipagem de indicadores, índices compostos e modelagem estatística/ML (notebooks/scripts independentes). |
| `api/` | Backend Django — apps `pipeline_*` que expõem cada linha de pesquisa como API + tarefas Celery. |
| `backend_project/` | Configuração do projeto Django (settings, urls, celery, wsgi/asgi). |
| `frontend/` | Interface React (Tailwind, Plotly) com dashboard, painéis geográficos e execução de pipelines. |
| `referencia/` | Dados de referência (população, malhas/espaciais, bases do IPEA). |

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────┐
│  frontend/  (React + Plotly + Tailwind)                 │
│  Dashboard · Mapas · Pipelines · Arquivos CSV           │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/JSON (DRF, Token Auth)
┌──────────────────────▼──────────────────────────────────┐
│  api/  (Django REST Framework)                          │
│  views/serializers · arquivos gerenciados (CSV/JSON)    │
│  api/pipeline_*  →  apps por linha de pesquisa          │
│  tasks.py (Celery) executa os módulos de features       │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│  src/ (P&D)  →  features · indices · modelagem · utils  │
│  referentes públicos: DATASUS (SIM, SINASC, SIH, CNES,  │
│  SIA, SINAN) e IBGE (Censo 2022)                        │
└─────────────────────────────────────────────────────────┘
```

### Backend (`api/`)

- **Apps de pipelines**: ~50 apps `api.pipeline_*` (indicadores, k-means, predição de internações, mortalidade, fluxo de pacientes, risco de readmissão, custo de internação, detecção de surtos, sobrevivência, doenças crônicas, ontologia BPHO, análise espacial, séries temporais, etc.), cada uma com `tasks.py` (Celery), `views.py`, `urls.py` e `models.py`.
- **Destaques temáticos**:
  - `pipeline_indicadores` — motor dinâmico que descobre e executa ~70 módulos de features (`modules/features/*.py`).
  - `pipeline_ontologia` / `pipeline_hospitalizacao_rdf` — integração com a ontologia BPHO (SPARQL local + chat em linguagem natural via Ollama).
  - `pipeline_population_space` — ponte para o plugin biospace.
- **Autenticação**: dj-rest-auth + allauth (login Google), TokenAuth do DRF.
- **Tarefas assíncronas**: Celery + Redis (`redis://localhost:6379/0`).

### Frontend (`frontend/`)

React 18 + Plotly + Tailwind. Páginas: Landing, Login (Google), Dashboard, Dashboards geográficos, Pipelines, Gerenciador de arquivos CSV, Histórico de tarefas.

---

## Como rodar

### 1. Backend (Django)

```bash
# em um venv com Python 3.9+
pip install django djangorestframework celery redis django-cors-headers \
            django-filter dj-rest-auth django-allauth pandas numpy

python manage.py migrate
python manage.py runserver  # http://127.0.0.1:8000
```

### 2. Celery (necessário para executar pipelines)

```bash
redis-server &
celery -A backend_project worker -B   # worker + beat
```

### 3. Frontend (React)

```bash
cd frontend
npm install
npm start   # http://127.0.0.1:3000
```

Configure a URL do backend em `frontend/.env.development` (`REACT_APP_BACKEND_URL`).

### 4. Integrações opcionais (ontologia BPHO)

Ver `backend_project/settings.py`:

- `BPHO_SPARQL_URL` — endpoint SPARQL local (`owl/sparql_endpoint.py`).
- `OLLAMA_URL` / `OLLAMA_MODEL` — LLM local (ex.: `qwen3-coder:30b`).
- `BIOSPACE_DIR` / `BIOSPACE_PYTHON` — venv próprio do biospace.

---

## Como nasce uma linha de pesquisa (fluxo P&D → produto)

1. **P&D** (`src/modelagem/`): analista valida hipóteses e métodos estatísticos/ML sobre os dados brutos.
2. **Feature**: indicador aprovado vira módulo reutilizável em `src/features/` e é replicado em `api/pipeline_indicadores/modules/features/`.
3. **Pipeline**: cria-se o app `api/pipeline_<tema>/` com task Celery + endpoints DRF.
4. **Visualização**: o frontend consome a API e renderiza mapas/gráficos no Dashboard.

---

## Fontes de dados

- SIM (mortalidade), SINASC (nascidos vivos), CNES (estabelecimentos), SIH (internações), SIA (ambulatorial), SINAN (agravos) — via FTP DATASUS.
- IBGE: Censo Demográfico 2022, estimativas populacionais (spline em `referencia/populacao/`), malhas municipais.
- Referências auxiliares: `referencia/ipea/`, `referencia/espaciais/`, `referencia/kmeans/`.

---

## Estrutura do repositório

```
labsus-github/
├── src/                # Ambiente de P&D (indicadores, índices, modelagem) → src/README.md
├── api/                # Apps Django (pipelines), models, serializers, views
├── backend_project/    # Settings/URLs/Celery do Django
├── frontend/           # React (dashboard, mapas, pipelines)
├── referencia/         # Dados de referência (população, espaciais, IPEA)
└── manage.py           # Entrypoint do Django
```

---

## Licença

Veja o arquivo `LICENSE` do projeto.