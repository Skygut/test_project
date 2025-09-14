# Скрипти для запуску MLOps Pipeline

Ця директорія містить скрипти для запуску та управління GitLab CI pipeline.

## 📁 Файли

- `trigger-pipeline.sh` - Bash скрипт для запуску pipeline
- `drift-webhook.py` - Python webhook сервер для drift detection
- `README.md` - Ця документація

## 🚀 trigger-pipeline.sh

Bash скрипт для запуску GitLab CI pipeline через API.

### Встановлення

```bash
chmod +x scripts/trigger-pipeline.sh
```

### Використання

```bash
# Базовий запуск
./scripts/trigger-pipeline.sh -p PROJECT_ID -t TRIGGER_TOKEN

# Запуск retrain
./scripts/trigger-pipeline.sh -p PROJECT_ID -t TRIGGER_TOKEN -r

# Запуск при drift detection
./scripts/trigger-pipeline.sh -p PROJECT_ID -t TRIGGER_TOKEN -d

# З Slack сповіщеннями
./scripts/trigger-pipeline.sh -p PROJECT_ID -t TRIGGER_TOKEN -s SLACK_WEBHOOK_URL
```

### Параметри

| Параметр | Опис | Обов'язковий |
|----------|------|--------------|
| `-p, --project-id` | GitLab Project ID | ✅ |
| `-t, --token` | GitLab Trigger Token | ✅ |
| `-u, --url` | GitLab URL (за замовчуванням: https://gitlab.com) | ❌ |
| `-b, --branch` | Гілка для запуску (за замовчуванням: main) | ❌ |
| `-r, --retrain` | Запустити retrain моделі | ❌ |
| `-d, --drift` | Запустити при drift detection | ❌ |
| `-s, --slack` | Slack webhook URL | ❌ |

### Приклади

```bash
# Звичайний запуск
./scripts/trigger-pipeline.sh -p 123456 -t abc123def456

# Запуск retrain з Slack сповіщеннями
./scripts/trigger-pipeline.sh \
  -p 123456 \
  -t abc123def456 \
  -r \
  -s https://hooks.slack.com/services/...

# Запуск при drift detection
./scripts/trigger-pipeline.sh \
  -p 123456 \
  -t abc123def456 \
  -d \
  -b main
```

## 🔗 drift-webhook.py

Python webhook сервер для обробки drift detection сповіщень.

### Встановлення

```bash
chmod +x scripts/drift-webhook.py
pip install requests  # якщо потрібно
```

### Використання

```bash
# Базовий запуск
GITLAB_PROJECT_ID=123456 \
GITLAB_TRIGGER_TOKEN=abc123def456 \
python scripts/drift-webhook.py

# З кастомними параметрами
python scripts/drift-webhook.py \
  --host 0.0.0.0 \
  --port 8080 \
  --project-id 123456 \
  --trigger-token abc123def456 \
  --branch main
```

### Environment змінні

| Змінна | Опис | За замовчуванням |
|--------|------|------------------|
| `GITLAB_URL` | GitLab URL | https://gitlab.com |
| `GITLAB_PROJECT_ID` | GitLab Project ID | - |
| `GITLAB_TRIGGER_TOKEN` | GitLab Trigger Token | - |
| `GITLAB_BRANCH` | GitLab branch | main |

### API Endpoint

```
POST /drift-webhook
Content-Type: application/json

{
  "event": "drift",
  "payload": {
    "p_val": 0.001,
    "is_drift": true,
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

## 🔧 Налаштування

### 1. Отримання GitLab Trigger Token

1. Перейти в GitLab проект
2. `Settings` → `CI/CD` → `Pipeline triggers`
3. Натиснути `Add trigger`
4. Скопіювати `Trigger token`

### 2. Отримання Project ID

1. Перейти в GitLab проект
2. `Settings` → `General` → `Project ID`
3. Скопіювати ID

### 3. Налаштування Slack Webhook (опціонально)

1. Перейти в Slack workspace
2. `Apps` → `Incoming Webhooks`
3. Створити новий webhook
4. Скопіювати URL

## 🐳 Docker

### Запуск webhook сервера в Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY scripts/drift-webhook.py .
RUN pip install requests

EXPOSE 8080
CMD ["python", "drift-webhook.py"]
```

```bash
docker build -t drift-webhook .
docker run -p 8080:8080 \
  -e GITLAB_PROJECT_ID=123456 \
  -e GITLAB_TRIGGER_TOKEN=abc123def456 \
  drift-webhook
```

## 🔄 Інтеграція з FastAPI

Додайте в `app/main.py`:

```python
# В функції _notify_webhook
def _notify_webhook(payload):
    import requests
    
    webhook_url = "http://drift-webhook:8080/drift-webhook"
    try:
        requests.post(webhook_url, json={
            "event": "drift",
            "payload": payload
        })
    except Exception as e:
        log.error(f"Webhook failed: {e}")
```

## 📊 Моніторинг

### Логи

```bash
# Логи trigger скрипта
./scripts/trigger-pipeline.sh -p 123456 -t abc123 2>&1 | tee pipeline.log

# Логи webhook сервера
python scripts/drift-webhook.py 2>&1 | tee webhook.log
```

### Перевірка статусу

```bash
# Перевірка GitLab pipeline
curl -H "PRIVATE-TOKEN: YOUR_TOKEN" \
  "https://gitlab.com/api/v4/projects/PROJECT_ID/pipelines"

# Перевірка webhook сервера
curl http://localhost:8080/health
```

## 🚨 Troubleshooting

### Помилки trigger скрипта

1. **"Project ID обов'язковий"**
   - Перевірте параметр `-p` або `--project-id`

2. **"Trigger Token обов'язковий"**
   - Перевірте параметр `-t` або `--token`

3. **"HTTP 401 Unauthorized"**
   - Перевірте правильність trigger token

4. **"HTTP 404 Not Found"**
   - Перевірте project ID та GitLab URL

### Помилки webhook сервера

1. **"Missing required environment variables"**
   - Встановіть `GITLAB_PROJECT_ID` та `GITLAB_TRIGGER_TOKEN`

2. **"Pipeline trigger failed"**
   - Перевірте GitLab API доступність
   - Перевірте правильність токенів

3. **"curl command failed"**
   - Встановіть curl: `apt-get install curl`

## 📞 Підтримка

Для питань та проблем:
1. Перевірте логи скриптів
2. Перевірте GitLab API доступність
3. Перевірте правильність токенів та ID
