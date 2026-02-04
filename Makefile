# BIW Pokal - Makefile für einfache Commands

.PHONY: help dev prod build up down logs clean seed backup

help: ## Zeigt diese Hilfe
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# Development
dev: ## Startet Development-Server (SQLite)
	docker-compose -f docker-compose.dev.yml up -d
	@echo "✓ Development läuft:"
	@echo "  Frontend: http://localhost:5500"
	@echo "  Backend:  http://localhost:8000"
	@echo "  Logs:     make logs-dev"

dev-stop: ## Stoppt Development-Server
	docker-compose -f docker-compose.dev.yml down

logs-dev: ## Zeigt Development-Logs
	docker-compose -f docker-compose.dev.yml logs -f

# Production
prod: ## Startet Production-Server (Postgres)
	docker-compose up -d
	@echo "✓ Production läuft:"
	@echo "  Frontend: http://localhost"
	@echo "  Backend:  http://localhost:8000"
	@echo "  n8n:      http://localhost:5678"

prod-stop: ## Stoppt Production-Server
	docker-compose down

logs: ## Zeigt Production-Logs
	docker-compose logs -f

# Build
build: ## Baut alle Container neu
	docker-compose build --no-cache

# Container Management
up: ## Startet alle Container
	docker-compose up -d

down: ## Stoppt alle Container
	docker-compose down

restart: ## Startet alle Container neu
	docker-compose restart

ps: ## Zeigt Container-Status
	docker-compose ps

# Database
seed: ## Füllt Datenbank mit Testdaten
	docker-compose exec backend python seed.py

seed-clear: ## Löscht DB und füllt neu
	docker-compose exec backend python seed.py --clear
	@echo "⚠️  Backend neu starten: make restart"

backup: ## Erstellt Postgres-Backup
	@mkdir -p backups
	docker-compose exec -T postgres pg_dump -U biw_user biw_pokal > backups/backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✓ Backup erstellt in backups/"

restore: ## Stellt Backup wieder her (BACKUP=file.sql)
	@if [ -z "$(BACKUP)" ]; then echo "❌ Bitte BACKUP=file.sql angeben"; exit 1; fi
	docker-compose exec -T postgres psql -U biw_user biw_pokal < $(BACKUP)
	@echo "✓ Backup wiederhergestellt"

# Cleanup
clean: ## Stoppt Container und löscht Volumes
	docker-compose down -v
	@echo "⚠️  Alle Daten gelöscht!"

prune: ## Räumt ungenutzte Docker-Ressourcen auf
	docker system prune -f

# Testing
test-backend: ## Prüft Backend-Health
	@curl -f http://localhost:8000/health && echo "\n✓ Backend OK" || echo "\n❌ Backend nicht erreichbar"

test-frontend: ## Prüft Frontend
	@curl -f http://localhost/ && echo "\n✓ Frontend OK" || echo "\n❌ Frontend nicht erreichbar"

test: test-backend test-frontend ## Prüft alle Services

# SSL
ssl-certbot: ## Erstellt Let's Encrypt Zertifikat (DOMAIN=example.com)
	@if [ -z "$(DOMAIN)" ]; then echo "❌ Bitte DOMAIN=example.com angeben"; exit 1; fi
	certbot certonly --standalone -d $(DOMAIN)
	mkdir -p ssl
	cp /etc/letsencrypt/live/$(DOMAIN)/fullchain.pem ssl/cert.pem
	cp /etc/letsencrypt/live/$(DOMAIN)/privkey.pem ssl/key.pem
	@echo "✓ SSL-Zertifikat installiert"
	@echo "  nginx.conf anpassen und 'make restart' ausführen"
