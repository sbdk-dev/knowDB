"""
Production Deployment Server

This module provides a comprehensive production-ready server that integrates:
- MCP Server for Claude Desktop integration
- Slack Bot for team communication
- Web API for external integrations
- Health checks and monitoring
- Configuration management
- Graceful shutdown handling

Technologies: FastAPI, asyncio, logging, configuration management
"""

import asyncio
import logging
import os
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import json

try:
    from fastapi import FastAPI, HTTPException, Request, Response, Depends
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import JSONResponse
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from src.semantic_layer import SemanticLayer
from src.conversational_metrics import ConversationalMetricDefiner
from src.visualization_engine import VisualizationEngine
from src.query_cache import QueryCache, CacheConfig, CacheBackend
from src.slack_integration import SemanticLayerSlackBot, SlackConfig
from src.security import SecurityMiddleware, Permission, User, add_security_headers, InputValidator

logger = logging.getLogger(__name__)


class DeploymentConfig:
    """Configuration management for production deployment"""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration from file or environment variables

        Args:
            config_path: Optional path to JSON configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or environment"""
        config = {}

        # Load from file if provided
        if self.config_path and Path(self.config_path).exists():
            try:
                with open(self.config_path) as f:
                    file_config = json.load(f)
                config.update(file_config)
                logger.info(f"📁 Loaded configuration from {self.config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config file {self.config_path}: {e}")

        # Override with environment variables
        env_config = {
            # Semantic Layer
            "semantic_models_path": os.getenv(
                "SEMANTIC_MODELS_PATH", "semantic_models/metrics.yml"
            ),
            # Server
            "server_host": os.getenv("SERVER_HOST", "0.0.0.0"),
            "server_port": int(os.getenv("SERVER_PORT", 8000)),
            "log_level": os.getenv("LOG_LEVEL", "INFO"),
            # Cache
            "cache_backend": os.getenv("CACHE_BACKEND", "memory"),
            "cache_ttl": int(os.getenv("CACHE_TTL", 1800)),
            "redis_url": os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            # Slack
            "slack_bot_token": os.getenv("SLACK_BOT_TOKEN"),
            "slack_signing_secret": os.getenv("SLACK_SIGNING_SECRET"),
            "slack_app_token": os.getenv("SLACK_APP_TOKEN"),
            "slack_enabled": os.getenv("SLACK_ENABLED", "false").lower() == "true",
            "slack_socket_mode": os.getenv("SLACK_SOCKET_MODE", "false").lower() == "true",
            # Features
            "enable_web_api": os.getenv("ENABLE_WEB_API", "true").lower() == "true",
            "enable_visualizations": os.getenv("ENABLE_VISUALIZATIONS", "true").lower() == "true",
            "enable_conversational": os.getenv("ENABLE_CONVERSATIONAL", "true").lower() == "true",
            # Security
            "cors_origins": os.getenv("CORS_ORIGINS", "*").split(","),
            "api_key": os.getenv("API_KEY"),  # Optional API key for web API
        }

        # Merge configurations (environment overrides file)
        config.update({k: v for k, v in env_config.items() if v is not None})

        return config

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set configuration value"""
        self.config[key] = value


class ProductionServer:
    """
    Production-ready server for semantic layer platform

    Phase A Implementation - Production Deployment
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize production server

        Args:
            config_path: Optional path to configuration file
        """
        self.config = DeploymentConfig(config_path)
        self.semantic_layer = None
        self.conversational_metrics = None
        self.visualization_engine = None
        self.query_cache = None
        self.slack_bot = None
        self.web_app = None
        self.server_task = None
        self.slack_task = None
        self.security_middleware = None

        # Setup logging
        self._setup_logging()

        # Initialize components
        self._initialize_components()

        logger.info("🚀 Production server initialized")

    def _setup_logging(self):
        """Setup production logging configuration"""
        log_level = getattr(logging, self.config.get("log_level", "INFO").upper())

        logging.basicConfig(
            level=log_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
                (
                    logging.FileHandler("semantic_layer.log")
                    if self.config.get("log_to_file")
                    else logging.NullHandler()
                ),
            ],
        )

        # Reduce noise from external libraries in production
        if log_level >= logging.INFO:
            logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    def _initialize_components(self):
        """Initialize all semantic layer components"""
        try:
            # 1. Initialize semantic layer
            semantic_models_path = self.config.get("semantic_models_path")
            self.semantic_layer = SemanticLayer(semantic_models_path)
            logger.info(f"✅ Semantic layer: {len(self.semantic_layer.list_metrics())} metrics")

            # 2. Initialize query cache
            self._initialize_cache()

            # 3. Initialize conversational metrics
            if self.config.get("enable_conversational", True):
                try:
                    self.conversational_metrics = ConversationalMetricDefiner(self.semantic_layer)
                    logger.info("✅ Conversational metrics enabled")
                except Exception as e:
                    logger.warning(f"Conversational metrics disabled: {e}")

            # 4. Initialize visualization engine
            if self.config.get("enable_visualizations", True):
                try:
                    self.visualization_engine = VisualizationEngine()
                    logger.info("✅ Visualization engine enabled")
                except Exception as e:
                    logger.warning(f"Visualization engine disabled: {e}")

            # 5. Initialize Slack bot
            if self.config.get("slack_enabled", False):
                self._initialize_slack_bot()

            # 6. Initialize web API
            if self.config.get("enable_web_api", True):
                self._initialize_web_api()

        except Exception as e:
            logger.error(f"Failed to initialize components: {e}")
            raise

    def _initialize_cache(self):
        """Initialize query cache with configured backend"""
        try:
            backend_name = self.config.get("cache_backend", "memory").lower()
            backend_map = {
                "memory": CacheBackend.MEMORY,
                "redis": CacheBackend.REDIS,
                "file": CacheBackend.FILE,
            }

            cache_config = CacheConfig(
                backend=backend_map.get(backend_name, CacheBackend.MEMORY),
                ttl_seconds=self.config.get("cache_ttl", 1800),
                redis_url=self.config.get("redis_url"),
                enable_metrics=True,
            )

            self.query_cache = QueryCache(cache_config)
            logger.info(f"✅ Query cache: {backend_name} backend")

        except Exception as e:
            logger.warning(f"Cache initialization failed: {e}")

    def _initialize_slack_bot(self):
        """Initialize Slack bot if configured"""
        try:
            bot_token = self.config.get("slack_bot_token")
            signing_secret = self.config.get("slack_signing_secret")

            if not bot_token or not signing_secret:
                logger.warning("Slack bot disabled: missing bot_token or signing_secret")
                return

            slack_config = SlackConfig(
                bot_token=bot_token,
                signing_secret=signing_secret,
                app_token=self.config.get("slack_app_token"),
                enable_socket_mode=self.config.get("slack_socket_mode", False),
                port=self.config.get("server_port", 8000) + 1,  # Use different port
            )

            self.slack_bot = SemanticLayerSlackBot(
                semantic_layer=self.semantic_layer,
                config=slack_config,
                conversational_metrics=self.conversational_metrics,
                visualization_engine=self.visualization_engine,
                query_cache=self.query_cache,
            )

            logger.info("✅ Slack bot configured")

        except Exception as e:
            logger.warning(f"Slack bot initialization failed: {e}")

    def _initialize_web_api(self):
        """Initialize FastAPI web application"""
        if not FASTAPI_AVAILABLE:
            logger.warning("Web API disabled: FastAPI not installed")
            return

        self.web_app = FastAPI(
            title="Semantic Layer API",
            description="Production API for semantic layer platform",
            version="1.0.0",
        )

        # Initialize security middleware
        self.security_middleware = SecurityMiddleware()

        # Add security middleware - order matters!
        @self.web_app.middleware("http")
        async def security_headers_middleware(request: Request, call_next):
            response = await call_next(request)
            return add_security_headers(response)

        # Add trusted host middleware
        allowed_hosts = ["*"]  # Configure based on environment
        if self.config.get("allowed_hosts"):
            allowed_hosts = self.config.get("allowed_hosts").split(",")

        self.web_app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

        # Fix CORS configuration to be more secure
        cors_origins = self.config.get("cors_origins", ["*"])
        if cors_origins == ["*"] and not self.config.get("debug", False):
            # In production, don't allow wildcard CORS
            cors_origins = [
                "http://localhost:3000",
                "https://your-domain.com",  # Configure for your domain
            ]
            logger.warning("Using restrictive CORS policy for production")

        self.web_app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "DELETE"],
            allow_headers=["Authorization", "Content-Type", "X-API-Key"],
        )

        # Add API routes
        self._setup_api_routes()

        logger.info("✅ Web API configured with security")

    def _setup_api_routes(self):
        """Setup FastAPI routes with authentication"""

        # Public health check endpoint
        @self.web_app.get("/health")
        async def health_check():
            """Health check endpoint - no auth required"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "1.0.0",
                "components": {
                    "semantic_layer": bool(self.semantic_layer),
                    "cache": bool(self.query_cache),
                    "conversational": bool(self.conversational_metrics),
                    "visualization": bool(self.visualization_engine),
                    "slack": bool(self.slack_bot),
                },
            }

        # Authentication helper
        async def get_current_user(request: Request) -> User:
            return await self.security_middleware.authenticate_request(request)

        # Authenticated endpoints
        @self.web_app.get("/metrics")
        async def list_metrics(request: Request, current_user: User = Depends(get_current_user)):
            """List all available metrics - requires READ_METRICS permission"""
            if not self.security_middleware.auth_manager.verify_permission(
                current_user, Permission.READ_METRICS
            ):
                raise HTTPException(status_code=403, detail="READ_METRICS permission required")

            if not self.semantic_layer:
                raise HTTPException(status_code=503, detail="Semantic layer not available")

            # Check rate limit
            if not self.security_middleware.auth_manager.check_rate_limit(current_user):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            return self.semantic_layer.list_metrics()

        @self.web_app.get("/dimensions")
        async def list_dimensions(request: Request, current_user: User = Depends(get_current_user)):
            """List all available dimensions - requires READ_METRICS permission"""
            if not self.security_middleware.auth_manager.verify_permission(
                current_user, Permission.READ_METRICS
            ):
                raise HTTPException(status_code=403, detail="READ_METRICS permission required")

            if not self.semantic_layer:
                raise HTTPException(status_code=503, detail="Semantic layer not available")

            # Check rate limit
            if not self.security_middleware.auth_manager.check_rate_limit(current_user):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            return self.semantic_layer.list_dimensions()

        @self.web_app.post("/query")
        async def query_metric(
            request: Request, query_request: dict, current_user: User = Depends(get_current_user)
        ):
            """Query a metric with filters and dimensions - requires QUERY_METRICS permission"""
            if not self.security_middleware.auth_manager.verify_permission(
                current_user, Permission.QUERY_METRICS
            ):
                raise HTTPException(status_code=403, detail="QUERY_METRICS permission required")

            if not self.semantic_layer:
                raise HTTPException(status_code=503, detail="Semantic layer not available")

            # Check rate limit
            if not self.security_middleware.auth_manager.check_rate_limit(current_user):
                raise HTTPException(status_code=429, detail="Rate limit exceeded")

            try:
                # Validate input
                validator = InputValidator()

                metric_name = query_request.get("metric_name")
                if not metric_name:
                    raise HTTPException(status_code=400, detail="metric_name is required")

                if not validator.validate_metric_name(metric_name):
                    raise HTTPException(status_code=400, detail="Invalid metric name format")

                # Validate dimensions
                dimensions = query_request.get("dimensions", [])
                if dimensions:
                    for dim in dimensions:
                        if not validator.validate_dimension_name(dim):
                            raise HTTPException(
                                status_code=400, detail=f"Invalid dimension name: {dim}"
                            )

                # Validate filters
                filters = query_request.get("filters", [])
                if filters:
                    for filter_expr in filters:
                        if not validator.validate_filter_expression(filter_expr):
                            raise HTTPException(
                                status_code=400, detail=f"Invalid filter expression: {filter_expr}"
                            )

                # Validate limit
                limit = query_request.get("limit", 100)
                if limit and (limit < 1 or limit > 10000):
                    raise HTTPException(status_code=400, detail="Limit must be between 1 and 10000")

                result = self.semantic_layer.query_metric(
                    metric_name=metric_name,
                    dimensions=dimensions,
                    filters=filters,
                    limit=limit,
                    order_by=query_request.get("order_by"),
                )

                # Log query for audit
                logger.info(f"Query executed by {current_user.username}: {metric_name}")

                return result

            except Exception as e:
                logger.error(f"Query error for user {current_user.username}: {e}")
                raise HTTPException(status_code=400, detail="Query execution failed")

        @self.web_app.get("/cache/stats")
        async def cache_stats(request: Request, current_user: User = Depends(get_current_user)):
            """Get cache statistics - requires READ_METRICS permission"""
            if not self.security_middleware.auth_manager.verify_permission(
                current_user, Permission.READ_METRICS
            ):
                raise HTTPException(status_code=403, detail="READ_METRICS permission required")

            if not self.query_cache:
                return {"status": "disabled"}

            return self.query_cache.get_stats()

        @self.web_app.post("/cache/clear")
        async def clear_cache(request: Request, current_user: User = Depends(get_current_user)):
            """Clear query cache - requires CACHE_MANAGE permission"""
            if not self.security_middleware.auth_manager.verify_permission(
                current_user, Permission.CACHE_MANAGE
            ):
                raise HTTPException(status_code=403, detail="CACHE_MANAGE permission required")

            if not self.query_cache:
                return {"status": "disabled"}

            success = self.query_cache.clear_all()
            logger.info(f"Cache cleared by {current_user.username}")
            return {"success": success}

        @self.web_app.get("/status")
        async def detailed_status():
            """Detailed system status"""
            status = {
                "timestamp": datetime.now().isoformat(),
                "uptime": "calculated_in_production",  # Would calculate actual uptime
                "semantic_layer": {
                    "status": "available" if self.semantic_layer else "unavailable",
                    "metrics_count": (
                        len(self.semantic_layer.list_metrics()) if self.semantic_layer else 0
                    ),
                    "dimensions_count": (
                        len(self.semantic_layer.list_dimensions()) if self.semantic_layer else 0
                    ),
                },
                "cache": (
                    self.query_cache.get_stats() if self.query_cache else {"status": "disabled"}
                ),
                "features": {
                    "conversational_metrics": bool(self.conversational_metrics),
                    "visualization_engine": bool(self.visualization_engine),
                    "slack_integration": bool(self.slack_bot),
                    "web_api": bool(self.web_app),
                },
                "configuration": {
                    "cache_backend": self.config.get("cache_backend"),
                    "slack_enabled": self.config.get("slack_enabled"),
                    "log_level": self.config.get("log_level"),
                },
            }

            return status

    async def start(self):
        """Start the production server"""
        logger.info("🚀 Starting semantic layer production server...")

        tasks = []

        # Start web API
        if self.web_app:
            server_config = uvicorn.Config(
                self.web_app,
                host=self.config.get("server_host", "0.0.0.0"),
                port=self.config.get("server_port", 8000),
                log_level=self.config.get("log_level", "info").lower(),
                access_log=False,  # Reduce noise in production
            )
            server = uvicorn.Server(server_config)
            self.server_task = asyncio.create_task(server.serve())
            tasks.append(self.server_task)
            logger.info(f"🌐 Web API started on http://{server_config.host}:{server_config.port}")

        # Start Slack bot
        if self.slack_bot:
            self.slack_task = asyncio.create_task(self.slack_bot.start_server())
            tasks.append(self.slack_task)
            logger.info("🤖 Slack bot started")

        if not tasks:
            logger.warning("No services to start - check configuration")
            return

        # Setup graceful shutdown
        self._setup_signal_handlers()

        # Wait for all services
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("Server shutdown requested")
        except Exception as e:
            logger.error(f"Server error: {e}")
            raise

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            asyncio.create_task(self.stop())

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def stop(self):
        """Stop the production server gracefully"""
        logger.info("🛑 Shutting down semantic layer server...")

        # Stop services
        if self.slack_task:
            self.slack_task.cancel()
            try:
                await self.slack_task
            except asyncio.CancelledError:
                pass

        if self.server_task:
            self.server_task.cancel()
            try:
                await self.server_task
            except asyncio.CancelledError:
                pass

        if self.slack_bot:
            await self.slack_bot.stop()

        logger.info("✅ Server shutdown complete")


# CLI interface for production deployment
async def main():
    """Main entry point for production server"""
    import argparse

    parser = argparse.ArgumentParser(description="Semantic Layer Production Server")
    parser.add_argument("--config", type=str, help="Path to configuration file")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Log level",
    )

    args = parser.parse_args()

    try:
        # Create and start server
        server = ProductionServer(config_path=args.config)

        # Override CLI arguments
        if args.host:
            server.config.set("server_host", args.host)
        if args.port:
            server.config.set("server_port", args.port)
        if args.log_level:
            server.config.set("log_level", args.log_level)

        await server.start()

    except KeyboardInterrupt:
        logger.info("Received interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
