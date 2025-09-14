#!/usr/bin/env python3
"""
Webhook сервер для обробки drift detection сповіщень
Запускає GitLab CI pipeline при виявленні дрейфу
"""

import os
import json
import logging
import subprocess
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import argparse

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
log = logging.getLogger(__name__)

class DriftWebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        """Обробка POST запитів від drift detector"""
        try:
            # Читання даних запиту
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            
            # Парсинг JSON
            try:
                data = json.loads(post_data.decode('utf-8'))
            except json.JSONDecodeError:
                log.error("Invalid JSON in request body")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Invalid JSON"}')
                return
            
            # Перевірка типу події
            event_type = data.get('event', '')
            if event_type != 'drift':
                log.warning(f"Unexpected event type: {event_type}")
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"error": "Expected drift event"}')
                return
            
            # Логування drift події
            payload = data.get('payload', {})
            log.info(f"Drift detected: {payload}")
            
            # Запуск GitLab CI pipeline
            success = self.trigger_retrain_pipeline(payload)
            
            if success:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "success", "message": "Pipeline triggered"}')
            else:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(b'{"status": "error", "message": "Failed to trigger pipeline"}')
                
        except Exception as e:
            log.error(f"Error processing webhook: {e}")
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"error": "Internal server error"}')
    
    def trigger_retrain_pipeline(self, drift_payload):
        """Запуск GitLab CI pipeline для retrain"""
        try:
            # Отримання конфігурації з environment
            gitlab_url = os.getenv('GITLAB_URL', 'https://gitlab.com')
            project_id = os.getenv('GITLAB_PROJECT_ID')
            trigger_token = os.getenv('GITLAB_TRIGGER_TOKEN')
            branch = os.getenv('GITLAB_BRANCH', 'main')
            
            if not all([project_id, trigger_token]):
                log.error("Missing GitLab configuration (GITLAB_PROJECT_ID, GITLAB_TRIGGER_TOKEN)")
                return False
            
            # Підготовка API запиту
            api_url = f"{gitlab_url}/api/v4/projects/{project_id}/trigger/pipeline"
            
            payload = {
                "token": trigger_token,
                "ref": branch,
                "variables[DRIFT_DETECTED]": "true",
                "variables[DRIFT_PAYLOAD]": json.dumps(drift_payload)
            }
            
            log.info(f"Triggering pipeline: {api_url}")
            
            # Використання curl для відправки запиту
            cmd = [
                'curl', '-s', '-w', '%{http_code}',
                '-X', 'POST', api_url,
                '-H', 'Content-Type: application/json',
                '-d', json.dumps(payload)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Розділення відповіді та HTTP коду
                response_lines = result.stdout.strip().split('\n')
                http_code = response_lines[-1]
                response_body = '\n'.join(response_lines[:-1])
                
                if http_code == '201':
                    log.info("Pipeline successfully triggered")
                    log.info(f"Response: {response_body}")
                    return True
                else:
                    log.error(f"Pipeline trigger failed with HTTP {http_code}")
                    log.error(f"Response: {response_body}")
                    return False
            else:
                log.error(f"curl command failed: {result.stderr}")
                return False
                
        except Exception as e:
            log.error(f"Error triggering pipeline: {e}")
            return False
    
    def log_message(self, format, *args):
        """Перевизначення для приховування стандартних логів HTTP сервера"""
        pass

def main():
    parser = argparse.ArgumentParser(description='Drift Detection Webhook Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind to (default: 8080)')
    parser.add_argument('--gitlab-url', help='GitLab URL (or set GITLAB_URL env var)')
    parser.add_argument('--project-id', help='GitLab Project ID (or set GITLAB_PROJECT_ID env var)')
    parser.add_argument('--trigger-token', help='GitLab Trigger Token (or set GITLAB_TRIGGER_TOKEN env var)')
    parser.add_argument('--branch', default='main', help='GitLab branch (or set GITLAB_BRANCH env var)')
    
    args = parser.parse_args()
    
    # Оновлення environment змінних з аргументів
    if args.gitlab_url:
        os.environ['GITLAB_URL'] = args.gitlab_url
    if args.project_id:
        os.environ['GITLAB_PROJECT_ID'] = args.project_id
    if args.trigger_token:
        os.environ['GITLAB_TRIGGER_TOKEN'] = args.trigger_token
    if args.branch:
        os.environ['GITLAB_BRANCH'] = args.branch
    
    # Перевірка конфігурації
    required_vars = ['GITLAB_PROJECT_ID', 'GITLAB_TRIGGER_TOKEN']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        log.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)
    
    # Запуск сервера
    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, DriftWebhookHandler)
    
    log.info(f"Starting drift webhook server on {args.host}:{args.port}")
    log.info(f"GitLab URL: {os.getenv('GITLAB_URL')}")
    log.info(f"Project ID: {os.getenv('GITLAB_PROJECT_ID')}")
    log.info(f"Branch: {os.getenv('GITLAB_BRANCH')}")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        log.info("Shutting down webhook server...")
        httpd.shutdown()

if __name__ == '__main__':
    main()
