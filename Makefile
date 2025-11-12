# knowDB Semantic Layer Platform Makefile
# Provides common development and deployment tasks

.PHONY: help setup demo validate test format lint clean install deploy docs security check
.DEFAULT_GOAL := help

# Colors for output
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
BLUE := \033[34m
RESET := \033[0m

##@ Help
help: ## Display this help message
	@echo "$(BLUE)knowDB Semantic Layer Platform$(RESET)"
	@echo "================================"
	@echo ""
	@echo "$(GREEN)Available commands:$(RESET)"
	@awk 'BEGIN {FS = ":.*##"; printf ""} /^[a-zA-Z_-]+:.*?##/ { printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(RESET)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup
setup: ## Create executable setup script
	@echo "$(YELLOW)Creating setup executable...$(RESET)"
	@cat setup.sh > setup
	@chmod a+x setup
	@echo "$(GREEN)✅ Setup script ready. Run './setup' to install.$(RESET)"

install: ## Install all dependencies and set up environment
	@echo "$(YELLOW)Installing knowDB platform...$(RESET)"
	@./setup.sh
	@echo "$(GREEN)✅ Installation complete!$(RESET)"

##@ Development
demo: ## Run interactive demo with sample data
	@echo "$(YELLOW)Starting knowDB demo...$(RESET)"
	@echo "$(BLUE)Ensuring sample data exists...$(RESET)"
	@if [ ! -f "data/sample.duckdb" ]; then \
		echo "$(YELLOW)Generating sample data...$(RESET)"; \
		uv run python create_sample_data.py; \
	fi
	@echo "$(GREEN)✅ Demo data ready$(RESET)"
	@echo ""
	@echo "$(BLUE)Demo Instructions:$(RESET)"
	@echo "1. Start the MCP server: uv run python src/mcp_server.py"
	@echo "2. Configure Claude Desktop with the paths shown in setup"
	@echo "3. Ask Claude: 'What metrics are available?'"
	@echo "4. Try: 'Show me MRR by customer segment'"
	@echo ""
	@echo "$(YELLOW)Available sample metrics:$(RESET)"
	@uv run python -c "import yaml; config = yaml.safe_load(open('semantic_models/metrics.yml')); [print(f'  • {m[\"name\"]}: {m[\"display_name\"]}') for m in config['semantic_model']['metrics'][:5]]"

validate: ## Run all validation checks
	@echo "$(YELLOW)Running platform validation...$(RESET)"
	@echo "$(BLUE)1. Testing core functionality...$(RESET)"
	@uv run pytest tests/test_semantic_layer.py -v --tb=short
	@echo ""
	@echo "$(BLUE)2. Security validation...$(RESET)"
	@uv run pytest tests/test_security.py -v --tb=short
	@echo ""
	@echo "$(BLUE)3. Basic imports check...$(RESET)"
	@uv run python -c "import ibis, pandas, yaml; print('✅ Core dependencies working')"
	@echo "$(GREEN)✅ All validation checks passed!$(RESET)"

##@ Testing
test: ## Run all tests
	@echo "$(YELLOW)Running test suite...$(RESET)"
	@uv run pytest tests/ -v

test-security: ## Run security tests only
	@echo "$(YELLOW)Running security tests...$(RESET)"
	@uv run pytest tests/test_security.py -v

test-core: ## Run core platform tests only
	@echo "$(YELLOW)Running core platform tests...$(RESET)"
	@uv run pytest tests/test_semantic_layer.py -v

test-watch: ## Run tests in watch mode
	@echo "$(YELLOW)Running tests in watch mode... (Ctrl+C to stop)$(RESET)"
	@uv run pytest-watch tests/

##@ Code Quality
format: ## Format code with black and fix imports
	@echo "$(YELLOW)Formatting code...$(RESET)"
	@uv run black src/ tests/ --quiet
	@echo "$(GREEN)✅ Code formatted$(RESET)"

lint: ## Run linting checks
	@echo "$(YELLOW)Running linting checks...$(RESET)"
	@echo "$(BLUE)Black formatting check...$(RESET)"
	@uv run black --check src/ tests/ || (echo "$(RED)❌ Code needs formatting. Run 'make format'$(RESET)" && exit 1)
	@echo "$(BLUE)Python syntax check...$(RESET)"
	@uv run python -m py_compile src/*.py
	@echo "$(GREEN)✅ All linting checks passed$(RESET)"

security: ## Run comprehensive security check
	@echo "$(YELLOW)Running security audit...$(RESET)"
	@uv run pytest tests/test_security.py::test_security_suite_comprehensive -v
	@echo "$(GREEN)✅ Security audit completed$(RESET)"

check: ## Run all quality checks (format, lint, security, test)
	@echo "$(YELLOW)Running comprehensive quality checks...$(RESET)"
	@$(MAKE) lint
	@$(MAKE) security
	@$(MAKE) test
	@echo "$(GREEN)✅ All quality checks passed!$(RESET)"

##@ Deployment
deploy-dev: ## Deploy development server
	@echo "$(YELLOW)Starting development server...$(RESET)"
	@uv run python src/mcp_server.py

deploy-prod: ## Deploy production server
	@echo "$(YELLOW)Deploying to production...$(RESET)"
	@./deploy.sh start

deploy-docker: ## Build and run with Docker
	@echo "$(YELLOW)Building Docker container...$(RESET)"
	@docker build -t knowdb:latest .
	@echo "$(YELLOW)Starting Docker container...$(RESET)"
	@docker-compose up -d
	@echo "$(GREEN)✅ Docker deployment ready$(RESET)"

##@ Documentation
docs: ## Generate and serve documentation
	@echo "$(YELLOW)Documentation available:$(RESET)"
	@echo "  📖 README.md - Main documentation"
	@echo "  🚀 QUICKSTART.md - Quick setup guide"
	@echo "  💡 EXAMPLES.md - Usage examples"
	@echo "  🔧 TROUBLESHOOTING.md - Common issues"
	@echo "  🛡️ SECURITY_AUDIT_RESOLUTION.md - Security details"
	@echo "  🚀 PRODUCTION_DEPLOYMENT.md - Production setup"

docs-serve: ## Serve documentation locally (if mkdocs available)
	@if command -v mkdocs >/dev/null 2>&1; then \
		echo "$(YELLOW)Serving documentation at http://localhost:8000$(RESET)"; \
		mkdocs serve; \
	else \
		echo "$(BLUE)MkDocs not installed. Documentation available as markdown files.$(RESET)"; \
		$(MAKE) docs; \
	fi

##@ Utilities
clean: ## Clean up temporary files and cache
	@echo "$(YELLOW)Cleaning up...$(RESET)"
	@rm -rf .pytest_cache/
	@rm -rf src/__pycache__/
	@rm -rf tests/__pycache__/
	@rm -rf .mypy_cache/
	@rm -rf .coverage
	@rm -rf htmlcov/
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -name "*.pyc" -delete
	@echo "$(GREEN)✅ Cleanup complete$(RESET)"

reset: clean ## Reset environment (clean + remove .venv)
	@echo "$(YELLOW)Resetting environment...$(RESET)"
	@rm -rf .venv/
	@rm -f setup
	@echo "$(GREEN)✅ Environment reset. Run 'make install' to reinstall.$(RESET)"

status: ## Show project status and health check
	@echo "$(BLUE)knowDB Platform Status$(RESET)"
	@echo "======================"
	@echo ""
	@echo "$(YELLOW)Environment:$(RESET)"
	@echo "  Python: $$(python3 --version 2>/dev/null || echo 'Not found')"
	@echo "  uv: $$(uv --version 2>/dev/null || echo 'Not found')"
	@echo "  Virtual env: $$([ -d .venv ] && echo '✅ Ready' || echo '❌ Missing')"
	@echo ""
	@echo "$(YELLOW)Data:$(RESET)"
	@echo "  Sample database: $$([ -f data/sample.duckdb ] && echo '✅ Ready' || echo '❌ Missing')"
	@echo "  Test database: $$([ -f data/test.duckdb ] && echo '✅ Ready' || echo '❌ Missing')"
	@echo ""
	@echo "$(YELLOW)Configuration:$(RESET)"
	@echo "  Metrics config: $$([ -f semantic_models/metrics.yml ] && echo '✅ Ready' || echo '❌ Missing')"
	@echo "  MCP server: $$([ -f src/mcp_server.py ] && echo '✅ Ready' || echo '❌ Missing')"
	@echo ""
	@if [ -d .venv ] && [ -f data/sample.duckdb ] && [ -f semantic_models/metrics.yml ]; then \
		echo "$(GREEN)✅ Platform ready for use!$(RESET)"; \
	else \
		echo "$(RED)⚠️  Run 'make install' to complete setup$(RESET)"; \
	fi

##@ Quick Start
quick-start: ## Complete setup and demo in one command
	@echo "$(BLUE)🚀 knowDB Quick Start$(RESET)"
	@echo "===================="
	@$(MAKE) install
	@echo ""
	@$(MAKE) validate
	@echo ""
	@$(MAKE) demo
	@echo ""
	@echo "$(GREEN)🎉 Quick start complete!$(RESET)"
	@echo "$(BLUE)Next: Configure Claude Desktop and start asking questions!$(RESET)"