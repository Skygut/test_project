#!/bin/bash

# Скрипт для запуску GitLab CI pipeline
# Використання: ./scripts/trigger-pipeline.sh [OPTIONS]

set -e

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функція для виводу повідомлень
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

error() {
    echo -e "${RED}❌ $1${NC}"
}

# Параметри за замовчуванням
GITLAB_URL="https://gitlab.com"
PROJECT_ID=""
TRIGGER_TOKEN=""
BRANCH="main"
TRIGGER_RETRAIN="false"
DRIFT_DETECTED="false"
SLACK_WEBHOOK=""

# Функція для показу довідки
show_help() {
    cat << EOF
Скрипт для запуску GitLab CI pipeline

Використання:
    $0 [OPTIONS]

Опції:
    -u, --url URL              GitLab URL (за замовчуванням: https://gitlab.com)
    -p, --project-id ID        GitLab Project ID (обов'язково)
    -t, --token TOKEN          GitLab Trigger Token (обов'язково)
    -b, --branch BRANCH        Гілка для запуску (за замовчуванням: main)
    -r, --retrain              Запустити retrain моделі
    -d, --drift                Запустити при drift detection
    -s, --slack URL            Slack webhook URL для сповіщень
    -h, --help                 Показати цю довідку

Приклади:
    # Звичайний запуск
    $0 -p 123456 -t abc123

    # Запуск retrain
    $0 -p 123456 -t abc123 -r

    # Запуск при drift
    $0 -p 123456 -t abc123 -d

    # З Slack сповіщеннями
    $0 -p 123456 -t abc123 -s https://hooks.slack.com/...

EOF
}

# Парсинг аргументів командного рядка
while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            GITLAB_URL="$2"
            shift 2
            ;;
        -p|--project-id)
            PROJECT_ID="$2"
            shift 2
            ;;
        -t|--token)
            TRIGGER_TOKEN="$2"
            shift 2
            ;;
        -b|--branch)
            BRANCH="$2"
            shift 2
            ;;
        -r|--retrain)
            TRIGGER_RETRAIN="true"
            shift
            ;;
        -d|--drift)
            DRIFT_DETECTED="true"
            shift
            ;;
        -s|--slack)
            SLACK_WEBHOOK="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            error "Невідомий параметр: $1"
            show_help
            exit 1
            ;;
    esac
done

# Перевірка обов'язкових параметрів
if [[ -z "$PROJECT_ID" ]]; then
    error "Project ID обов'язковий. Використайте -p або --project-id"
    exit 1
fi

if [[ -z "$TRIGGER_TOKEN" ]]; then
    error "Trigger Token обов'язковий. Використайте -t або --token"
    exit 1
fi

# Підготовка даних для запиту
API_URL="$GITLAB_URL/api/v4/projects/$PROJECT_ID/trigger/pipeline"

# Побудова JSON payload
PAYLOAD="{\"token\":\"$TRIGGER_TOKEN\",\"ref\":\"$BRANCH\""

# Додавання змінних
VARIABLES=""
if [[ "$TRIGGER_RETRAIN" == "true" ]]; then
    VARIABLES="$VARIABLES,\"variables[TRIGGER_RETRAIN]\":\"true\""
fi

if [[ "$DRIFT_DETECTED" == "true" ]]; then
    VARIABLES="$VARIABLES,\"variables[DRIFT_DETECTED]\":\"true\""
fi

if [[ -n "$SLACK_WEBHOOK" ]]; then
    VARIABLES="$VARIABLES,\"variables[SLACK_WEBHOOK_URL]\":\"$SLACK_WEBHOOK\""
fi

if [[ -n "$VARIABLES" ]]; then
    PAYLOAD="$PAYLOAD$VARIABLES"
fi

PAYLOAD="$PAYLOAD}"

# Вивід інформації
log "Запуск GitLab CI pipeline..."
log "URL: $API_URL"
log "Гілка: $BRANCH"
log "Retrain: $TRIGGER_RETRAIN"
log "Drift: $DRIFT_DETECTED"

if [[ -n "$SLACK_WEBHOOK" ]]; then
    log "Slack webhook: $SLACK_WEBHOOK"
fi

# Відправка запиту
log "Відправка запиту до GitLab API..."

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$API_URL" \
    -H "Content-Type: application/json" \
    -d "$PAYLOAD")

# Розділення відповіді та HTTP коду
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
RESPONSE_BODY=$(echo "$RESPONSE" | head -n -1)

# Перевірка результату
if [[ "$HTTP_CODE" -eq 201 ]]; then
    success "Pipeline успішно запущено!"
    
    # Парсинг ID pipeline з відповіді
    PIPELINE_ID=$(echo "$RESPONSE_BODY" | grep -o '"id":[0-9]*' | cut -d':' -f2)
    
    if [[ -n "$PIPELINE_ID" ]]; then
        log "Pipeline ID: $PIPELINE_ID"
        log "Посилання: $GITLAB_URL/$PROJECT_ID/-/pipelines/$PIPELINE_ID"
    fi
    
    # Вивід JSON відповіді для деталей
    echo ""
    log "Деталі відповіді:"
    echo "$RESPONSE_BODY" | jq '.' 2>/dev/null || echo "$RESPONSE_BODY"
    
else
    error "Помилка запуску pipeline (HTTP $HTTP_CODE)"
    echo "Відповідь: $RESPONSE_BODY"
    exit 1
fi

log "Готово!"
