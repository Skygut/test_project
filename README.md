# AIOps Quality Project

Повноцінний MLOps проект для продакшн‑інференсу з FastAPI, Helm, ArgoCD, Prometheus/Grafana, Loki/Promtail, Great Expectations та CI/CD для retrain.

## 🏗️ Архітектура проекту

```
aiops-quality-project/
├── app/                    # FastAPI inference сервіс
│   └── main.py            # Основний API з drift detection
├── model/                 # Модель та тренування
│   ├── train.py           # Скрипт тренування з data quality checks
│   └── data_quality.py    # Great Expectations для перевірки якості
├── tests/                 # Unit тести
│   ├── test_app.py        # Тести FastAPI
│   └── test_data_quality.py # Тести data quality
├── helm/                  # Helm чарти для Kubernetes
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
├── argocd/                # GitOps конфігурація
│   └── application.yaml
├── grafana/               # Дашборди моніторингу
│   └── dashboards.json
├── prometheus/            # Конфігурація метрик
│   └── additionalScrapeConfigs.yaml
├── loki/                  # Конфігурація логування
│   ├── loki-config.yaml
│   └── promtail-config.yaml
├── .gitlab-ci.yml         # CI/CD пайплайн
├── Dockerfile             # Контейнер для локальної розробки
├── requirements.txt       # Python залежності
└── README.md
```

## 🚀 Швидкий старт

### 1. Локальна розробка

```bash
# Створення віртуального середовища
python -m venv .venv && source .venv/bin/activate

# Встановлення залежностей
pip install -r requirements.txt

# Тренування моделі
python model/train.py

# Запуск API сервісу
uvicorn app.main:app --reload --port 8000
```

### 2. Тестування API

```bash
# Health check
curl http://localhost:8000/health

# Метрики Prometheus
curl http://localhost:8000/metrics

# Прогнозування
curl -X POST "http://localhost:8000/predict" \
     -H "Content-Type: application/json" \
     -d '{"data": [[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]]}'
```

### 3. Docker

```bash
# Збірка образу
docker build -t aiops-quality-project .

# Запуск контейнера
docker run -p 8000:8000 aiops-quality-project
```

## 🏗️ Розгортання в Kubernetes

### 1. Helm

```bash
# Встановлення чарту
helm upgrade --install aiops ./helm -n aiops --create-namespace

# Перевірка статусу
kubectl get pods -n aiops
```

### 2. ArgoCD

```bash
# Додавання додатку в ArgoCD
kubectl apply -f argocd/application.yaml

# Перевірка синхронізації
kubectl get applications -n argocd
```

### 3. Моніторинг

```bash
# Port-forward для доступу до сервісів
kubectl port-forward -n aiops svc/aiops-quality-project 8000:80
kubectl port-forward -n monitoring svc/prometheus-server 9090:80
kubectl port-forward -n monitoring svc/grafana 3000:80
```

## 📊 Моніторинг та логування

### Prometheus метрики

- `requests_total` - загальна кількість запитів
- `request_latency_seconds` - латентність запитів
- `drift_events_total` - кількість виявлених дрейфів

### Grafana дашборд

Імпортуйте `grafana/dashboards.json` для отримання:
- Графіки запитів за секунду
- Розподіл латентності (p50, p95, p99)
- Статистика дрейфів та помилок
- Використання пам'яті

### Loki + Promtail

Логи збираються автоматично з подів у namespace `aiops`:
- Структуровані логи з рівнями (INFO, WARNING, ERROR)
- Централізований збір через Promtail
- Пошук та аналіз через Grafana

## 🔄 CI/CD пайплайн

### Етапи пайплайну

1. **test** - перевірка якості коду та unit тести
2. **train** - тренування моделі з data quality checks
3. **build** - збірка Docker образу
4. **deploy** - оновлення Helm values та деплой

### Запуск retrain

```bash
# Вручну через GitLab UI
# Або через webhook
curl -X POST "https://gitlab.com/api/v4/projects/PROJECT_ID/trigger/pipeline" \
     -H "Content-Type: application/json" \
     -d '{"token": "YOUR_TOKEN", "ref": "main", "variables[TRIGGER_RETRAIN]": "true"}'
```

## 🔍 Data Quality та Drift Detection

### Great Expectations

- Перевірка якості вхідних даних
- Валідація структури та типів даних
- Статистичні перевірки розподілів

### Drift Detection

- **Alibi Detect** - MMD тест для виявлення дрейфу
- **Статистичні тести** - KS та Anderson-Darling тести
- **Автоматичні сповіщення** - webhook при виявленні дрейфу

### Налаштування

```yaml
# helm/values.yaml
env:
  - name: DRIFT_ENABLED
    value: "true"
  - name: DRIFT_WEBHOOK
    value: "https://your-webhook-url.com/drift"
```

## 🧪 Тестування

```bash
# Запуск всіх тестів
pytest tests/ -v

# З покриттям коду
pytest tests/ --cov=app --cov=model --cov-report=html

# Перевірка якості коду
flake8 app/ model/ --max-line-length=100
```

## 📈 Моніторинг продуктивності

### Ключові метрики

- **Throughput**: запити за секунду
- **Latency**: p50, p95, p99 латентність
- **Error Rate**: відсоток помилкових запитів
- **Drift Events**: кількість виявлених дрейфів
- **Resource Usage**: CPU та пам'ять

### Алерти

Налаштуйте алерти в Prometheus для:
- Високої латентності (>1s p95)
- Високого error rate (>5%)
- Виявлення дрейфу
- Високого використання ресурсів

## 🔧 Налаштування

### Змінні середовища

| Змінна | Опис | За замовчуванням |
|--------|------|------------------|
| `MODEL_PATH` | Шлях до файлу моделі | `./model/model.pkl` |
| `MODEL_VERSION_PATH` | Шлях до версії моделі | `./model/model_version.txt` |
| `DRIFT_ENABLED` | Увімкнути drift detection | `false` |
| `DRIFT_WEBHOOK` | URL для сповіщень про дрейф | - |

### Helm values

```yaml
# Ресурси
resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi

# Репліки
replicaCount: 1

# Моніторинг
serviceMonitor:
  enabled: true
  interval: 15s
```

## 🛠️ Розробка

### Структура коду

- `app/main.py` - FastAPI додаток з API endpoints
- `model/train.py` - скрипт тренування моделі
- `model/data_quality.py` - Great Expectations перевірки
- `tests/` - unit тести

### Додавання нових перевірок

1. Розширте `DataQualityChecker` в `model/data_quality.py`
2. Додайте нові expectations для Great Expectations
3. Оновіть тести в `tests/test_data_quality.py`

### Додавання нових метрик

1. Додайте метрики в `app/main.py`
2. Оновіть Grafana дашборд
3. Додайте алерти в Prometheus

## 🚀 Roadmap

### ✅ Реалізовано

- [x] FastAPI inference сервіс
- [x] Helm чарти для Kubernetes
- [x] ArgoCD GitOps деплой
- [x] Prometheus метрики
- [x] Grafana дашборди
- [x] Loki + Promtail логування
- [x] Great Expectations data quality
- [x] Drift detection (Alibi Detect + статистичні тести)
- [x] CI/CD пайплайн з тестами
- [x] Unit тести та code coverage

### 🔄 В планах

- [ ] S3/MinIO сховище артефактів моделі
- [ ] Canary/Blue-Green деплой через Argo Rollouts
- [ ] MLflow для експериментів
- [ ] Автоматичне масштабування (HPA)
- [ ] Безпека (RBAC, Network Policies)
- [ ] Backup та відновлення моделей

## 📞 Підтримка

Для питань та проблем:
1. Перевірте логи: `kubectl logs -n aiops -l app=aiops-quality-project`
2. Перевірте метрики: `kubectl port-forward -n monitoring svc/prometheus-server 9090:80`
3. Перевірте статус ArgoCD: `kubectl get applications -n argocd`

## 📄 Ліцензія

MIT License