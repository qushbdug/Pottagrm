# Yemen Net Bot Makefile
.PHONY: help install run test clean deploy

# Default target
help:
	@echo "🤖 Yemen Net Bot - Available Commands:"
	@echo ""
	@echo "📦 Installation:"
	@echo "  install     - Install dependencies"
	@echo "  install-dev - Install development dependencies"
	@echo ""
	@echo "🚀 Running:"
	@echo "  run         - Run bot locally"
	@echo "  run-prod    - Run bot in production mode"
	@echo ""
	@echo "🧪 Testing:"
	@echo "  test        - Run tests"
	@echo "  lint        - Run linting"
	@echo "  format      - Format code"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  clean       - Clean temporary files"
	@echo "  clean-db    - Clean database files"
	@echo ""
	@echo "🚀 Deployment:"
	@echo "  deploy      - Deploy to production"
	@echo "  backup      - Backup database"

# Installation
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt

install-dev:
	@echo "📦 Installing development dependencies..."
	pip install -r requirements-dev.txt

# Running
run:
	@echo "🚀 Starting bot in development mode..."
	python run_bot.py

run-prod:
	@echo "🚀 Starting bot in production mode..."
	python main.py

# Testing
test:
	@echo "🧪 Running tests..."
	python -m pytest tests/ -v

lint:
	@echo "🔍 Running linting..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

format:
	@echo "✨ Formatting code..."
	black .

# Cleaning
clean:
	@echo "🧹 Cleaning temporary files..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type f -name "*.log" -delete
	find . -type f -name "bot_data" -delete

clean-db:
	@echo "🗄️ Cleaning database files..."
	rm -f *.db
	rm -f *_backup_*.db

# Deployment
deploy:
	@echo "🚀 Deploying to production..."
	git add .
	git commit -m "Deploy: $(shell date)"
	git push origin main

deploy-render:
	@echo "🚀 Preparing for Render deployment..."
	chmod +x deploy_render.sh
	./deploy_render.sh

deploy-github:
	@echo "🚀 Deploying to GitHub..."
	git add .
	git commit -m "Deploy to GitHub: $(shell date)"
	git push origin main

backup:
	@echo "💾 Creating database backup..."
	cp yemen_net.db "yemen_net_backup_$(shell date +%Y%m%d_%H%M%S).db"

# Database operations
migrate:
	@echo "🔄 Running database migrations..."
	python -c "from bot.database.migrations import run_migrations; run_migrations()"

# Development
dev-setup: install-dev
	@echo "🔧 Development environment setup complete!"
	@echo "Run 'make run' to start the bot"

# Production setup
prod-setup: install
	@echo "🚀 Production environment setup complete!"
	@echo "Run 'make run-prod' to start the bot"