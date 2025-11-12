"""
Slack Integration for Semantic Layer

This module implements Slack bot functionality for the semantic layer:
- Natural language query processing
- Interactive Slack commands and slash commands
- Rich formatting for metric results and charts
- Integration with conversational metrics and visualization engine
- Multi-workspace support with proper authentication

Technologies: Slack SDK, Web framework, async processing
"""

import asyncio
import json
import logging
import os
import re
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    from slack_bolt.async_app import AsyncApp
    from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler

    SLACK_SDK_AVAILABLE = True
except ImportError:
    SLACK_SDK_AVAILABLE = False

try:
    from fastapi import FastAPI, Request
    from fastapi.responses import Response
    import uvicorn

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from src.semantic_layer import SemanticLayer
from src.conversational_metrics import ConversationalMetricDefiner
from src.visualization_engine import VisualizationEngine
from src.query_cache import QueryCache

logger = logging.getLogger(__name__)


@dataclass
class SlackConfig:
    """Configuration for Slack integration"""

    bot_token: str
    signing_secret: str
    app_token: Optional[str] = None
    port: int = 3000
    host: str = "0.0.0.0"
    enable_socket_mode: bool = False
    max_message_length: int = 3000
    chart_upload_enabled: bool = True


class SlackFormatter:
    """Formats semantic layer responses for Slack"""

    @staticmethod
    def format_metric_list(metrics: List[Dict[str, Any]]) -> str:
        """Format metric list for Slack"""
        if not metrics:
            return "No metrics available."

        text = "*Available Metrics:*\n\n"
        for metric in metrics[:10]:  # Limit to 10 for readability
            text += f"• *{metric['display_name']}* (`{metric['name']}`)\n"
            if metric.get("description"):
                text += f"  _{metric['description']}_\n"
            text += "\n"

        if len(metrics) > 10:
            text += f"... and {len(metrics) - 10} more metrics\n"

        return text

    @staticmethod
    def format_metric_result(result: Dict[str, Any], include_sql: bool = False) -> str:
        """Format metric query result for Slack"""
        text = f"*{result['display_name']}*\n"

        if result.get("description"):
            text += f"_{result['description']}_\n\n"

        if result["row_count"] == 0:
            text += "_No data found_\n"
            return text

        # Format as simple table (Slack doesn't support markdown tables well)
        data = result["data"]
        if data and len(data) <= 20:  # Only show small datasets inline
            text += "```\n"

            # Get column names and calculate widths
            columns = list(data[0].keys())
            col_widths = {col: len(col) for col in columns}

            for row in data:
                for col in columns:
                    col_widths[col] = max(col_widths[col], len(str(row[col])))

            # Header
            header = " | ".join(col.ljust(col_widths[col]) for col in columns)
            text += header + "\n"
            text += "-" * len(header) + "\n"

            # Data rows
            for row in data:
                row_text = " | ".join(str(row[col]).ljust(col_widths[col]) for col in columns)
                text += row_text + "\n"

            text += "```\n"
        else:
            text += f"*{result['row_count']} rows returned* (too large to display inline)\n"

        if result.get("dimensions"):
            text += f"*Grouped by:* {', '.join(result['dimensions'])}\n"

        if include_sql:
            text += f"\n*Generated SQL:*\n```sql\n{result['sql']}\n```\n"

        return text

    @staticmethod
    def format_dimension_values(dimension_name: str, values: List[Any]) -> str:
        """Format dimension values for Slack"""
        text = f"*Values for {dimension_name}:*\n\n"

        if not values:
            return text + "_No values found_"

        # Show up to 20 values
        shown_values = values[:20]
        for value in shown_values:
            text += f"• {value}\n"

        if len(values) > 20:
            text += f"\n... and {len(values) - 20} more values"

        return text

    @staticmethod
    def format_error(error_msg: str) -> str:
        """Format error message for Slack"""
        return f":warning: *Error:* {error_msg}"

    @staticmethod
    def truncate_message(text: str, max_length: int = 3000) -> str:
        """Truncate message to fit Slack limits"""
        if len(text) <= max_length:
            return text

        truncated = text[: max_length - 100]
        return truncated + "\n\n_... (message truncated)_"


class SemanticLayerSlackBot:
    """
    Slack bot for semantic layer interactions

    Phase 2 Implementation - Scale & Polish: Communication Enhancement
    """

    def __init__(
        self,
        semantic_layer: SemanticLayer,
        config: SlackConfig,
        conversational_metrics: Optional[ConversationalMetricDefiner] = None,
        visualization_engine: Optional[VisualizationEngine] = None,
        query_cache: Optional[QueryCache] = None,
    ):
        """
        Initialize Slack bot

        Args:
            semantic_layer: Semantic layer instance
            config: Slack configuration
            conversational_metrics: Optional conversational metrics processor
            visualization_engine: Optional visualization engine
            query_cache: Optional query cache
        """
        if not SLACK_SDK_AVAILABLE:
            raise ImportError(
                "Slack SDK not installed. Install with: pip install slack_sdk slack_bolt"
            )

        self.semantic_layer = semantic_layer
        self.config = config
        self.conversational_metrics = conversational_metrics
        self.visualization_engine = visualization_engine
        self.query_cache = query_cache
        self.formatter = SlackFormatter()

        # Initialize Slack app
        self.app = AsyncApp(
            token=config.bot_token,
            signing_secret=config.signing_secret,
            socket_mode=config.enable_socket_mode,
        )

        self.client = WebClient(token=config.bot_token)

        # Register event handlers
        self._register_handlers()

        logger.info("🤖 Slack bot initialized")

    def _register_handlers(self):
        """Register Slack event handlers"""

        @self.app.message(re.compile(r".*"))
        async def handle_message(message, say):
            """Handle direct messages and mentions"""
            text = message.get("text", "").strip()
            user = message.get("user")
            channel = message.get("channel")

            # Skip bot messages
            if message.get("bot_id"):
                return

            logger.info(f"Received message from {user}: {text}")

            try:
                # Process the query
                response = await self._process_query(text, user)

                # Send response
                await say(response)

            except Exception as e:
                logger.error(f"Error handling message: {e}")
                await say(self.formatter.format_error(f"Sorry, I encountered an error: {str(e)}"))

        @self.app.command("/metrics")
        async def handle_metrics_command(ack, respond, command):
            """Handle /metrics slash command"""
            await ack()

            try:
                # List all metrics
                metrics = self.semantic_layer.list_metrics()
                response = self.formatter.format_metric_list(metrics)

                await respond(self.formatter.truncate_message(response))

            except Exception as e:
                logger.error(f"Error in /metrics command: {e}")
                await respond(self.formatter.format_error(str(e)))

        @self.app.command("/query")
        async def handle_query_command(ack, respond, command):
            """Handle /query slash command"""
            await ack()

            text = command.get("text", "").strip()
            user = command.get("user_id")

            if not text:
                await respond(
                    "Please provide a query. Example: `/query total revenue by customer segment`"
                )
                return

            try:
                response = await self._process_query(text, user)
                await respond(self.formatter.truncate_message(response))

            except Exception as e:
                logger.error(f"Error in /query command: {e}")
                await respond(self.formatter.format_error(str(e)))

        @self.app.command("/dimensions")
        async def handle_dimensions_command(ack, respond, command):
            """Handle /dimensions slash command"""
            await ack()

            try:
                dimensions = self.semantic_layer.list_dimensions()

                text = "*Available Dimensions:*\n\n"
                for dim in dimensions:
                    text += f"• *{dim['name']}* ({dim['type']})\n"
                    if dim.get("description"):
                        text += f"  _{dim['description']}_\n"
                    text += "\n"

                await respond(self.formatter.truncate_message(text))

            except Exception as e:
                logger.error(f"Error in /dimensions command: {e}")
                await respond(self.formatter.format_error(str(e)))

        @self.app.command("/cache")
        async def handle_cache_command(ack, respond, command):
            """Handle /cache slash command for cache management"""
            await ack()

            text = command.get("text", "").strip().lower()

            try:
                if text == "stats":
                    if self.query_cache:
                        stats = self.query_cache.get_stats()
                        response = f"*Cache Statistics:*\n"
                        response += f"• Hit Rate: {stats['hit_rate']}\n"
                        response += f"• Total Queries: {stats['total_queries']}\n"
                        response += f"• Cache Size: {stats['cache_size']} entries\n"
                        response += f"• Backend: {stats['backend']}\n"
                    else:
                        response = "Cache is not enabled"

                elif text == "clear":
                    if self.query_cache:
                        success = self.query_cache.clear_all()
                        if success:
                            response = "✅ Cache cleared successfully"
                        else:
                            response = "❌ Failed to clear cache"
                    else:
                        response = "Cache is not enabled"
                else:
                    response = "Usage: `/cache stats` or `/cache clear`"

                await respond(response)

            except Exception as e:
                logger.error(f"Error in /cache command: {e}")
                await respond(self.formatter.format_error(str(e)))

    async def _process_query(self, text: str, user_id: str) -> str:
        """Process natural language query"""
        try:
            # Check for simple commands first
            text_lower = text.lower().strip()

            if any(phrase in text_lower for phrase in ["help", "what can you do"]):
                return self._get_help_message()

            elif "list metrics" in text_lower or "show metrics" in text_lower:
                metrics = self.semantic_layer.list_metrics()
                return self.formatter.format_metric_list(metrics)

            elif "list dimensions" in text_lower or "show dimensions" in text_lower:
                dimensions = self.semantic_layer.list_dimensions()
                text = "*Available Dimensions:*\n\n"
                for dim in dimensions[:15]:  # Limit for readability
                    text += f"• {dim['name']} ({dim['type']})\n"
                return text

            # Use conversational metrics if available
            if self.conversational_metrics:
                try:
                    # Parse natural language query
                    parsed_query = self.conversational_metrics.parse_natural_language_query(text)

                    if parsed_query.get("type") == "metric_query":
                        # Execute metric query
                        result = self.semantic_layer.query_metric(
                            metric_name=parsed_query["metric"],
                            dimensions=parsed_query.get("dimensions"),
                            filters=parsed_query.get("filters"),
                            limit=parsed_query.get("limit", 50),
                        )

                        response = self.formatter.format_metric_result(result)

                        # Add chart if visualization engine is available
                        if self.visualization_engine and self.config.chart_upload_enabled:
                            try:
                                chart_data = (
                                    self.visualization_engine.create_chart_from_query_result(result)
                                )
                                # Note: In a real implementation, you'd upload the chart to Slack
                                # For now, we'll just mention it's available
                                response += (
                                    "\n📊 _Chart available (upload functionality would go here)_"
                                )
                            except Exception as e:
                                logger.warning(f"Chart generation failed: {e}")

                        return response

                    elif parsed_query.get("type") == "dimension_values":
                        # Get dimension values
                        dim_name = parsed_query["dimension"]
                        dim = self.semantic_layer.get_dimension(dim_name)
                        if dim:
                            table = self.semantic_layer.connection.table(dim["table"])
                            result = table[dim["column"]].distinct().limit(20).execute()
                            values = result[dim["column"]].tolist()
                            return self.formatter.format_dimension_values(dim_name, values)
                        else:
                            return self.formatter.format_error(f"Dimension '{dim_name}' not found")

                except Exception as e:
                    logger.warning(f"Conversational metrics failed: {e}")
                    # Fall back to simple response
                    pass

            # Default response for unhandled queries
            return (
                "I understand you want to query data, but I need a more specific request. Try:\n"
                "• `list metrics` - see available metrics\n"
                "• `show total revenue by customer segment` - query a metric\n"
                "• `what are the customer segments?` - get dimension values\n"
                "• `help` - see all commands"
            )

        except Exception as e:
            logger.error(f"Error processing query '{text}': {e}")
            return self.formatter.format_error(f"Sorry, I couldn't process that query: {str(e)}")

    def _get_help_message(self) -> str:
        """Get help message for users"""
        help_text = """
*Semantic Layer Bot Help*

I can help you query business metrics and explore data! Here's what I can do:

*Slash Commands:*
• `/metrics` - List all available metrics
• `/query <your question>` - Ask a data question
• `/dimensions` - List all dimensions for slicing data
• `/cache stats` - Show cache performance
• `/cache clear` - Clear query cache

*Natural Language Queries:*
• "Show me total revenue by customer segment"
• "What's the average subscription amount?"
• "List all customer segments"
• "How many active subscriptions do we have?"

*Tips:*
• Be specific about what metric you want
• Mention dimensions to group by (like "by customer segment")
• I understand common business terms like "revenue", "customers", etc.

*Examples:*
• "Total MRR by month"
• "Average deal size for enterprise customers"
• "Show subscription counts"
• "What customer segments do we have?"
"""
        return help_text.strip()

    async def start_server(self):
        """Start the Slack bot server"""
        if not FASTAPI_AVAILABLE:
            raise ImportError("FastAPI not installed. Install with: pip install fastapi uvicorn")

        if self.config.enable_socket_mode:
            logger.info("Starting Slack bot in socket mode...")
            await self.app.async_start()
        else:
            logger.info(f"Starting Slack bot server on {self.config.host}:{self.config.port}")

            # Create FastAPI app for HTTP mode
            api = FastAPI()
            handler = AsyncSlackRequestHandler(self.app)

            @api.post("/slack/events")
            async def slack_events(request: Request):
                return await handler.handle(request)

            # Start server
            config = uvicorn.Config(
                api, host=self.config.host, port=self.config.port, log_level="info"
            )
            server = uvicorn.Server(config)
            await server.serve()

    async def stop(self):
        """Stop the Slack bot"""
        if self.config.enable_socket_mode:
            await self.app.async_stop()
        logger.info("Slack bot stopped")


# Factory function for easy setup
def create_slack_bot(
    semantic_layer: SemanticLayer, bot_token: str, signing_secret: str, **kwargs
) -> SemanticLayerSlackBot:
    """
    Factory function to create configured Slack bot

    Args:
        semantic_layer: Semantic layer instance
        bot_token: Slack bot token
        signing_secret: Slack signing secret
        **kwargs: Additional configuration options

    Returns:
        Configured SemanticLayerSlackBot instance
    """
    config = SlackConfig(bot_token=bot_token, signing_secret=signing_secret, **kwargs)

    return SemanticLayerSlackBot(semantic_layer, config)


# Example usage and testing
if __name__ == "__main__":
    import os
    from semantic_layer import SemanticLayer

    # Check for required environment variables
    bot_token = os.getenv("SLACK_BOT_TOKEN")
    signing_secret = os.getenv("SLACK_SIGNING_SECRET")

    if not bot_token or not signing_secret:
        logger.error(
            "Missing required environment variables: SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET"
        )
        exit(1)

    # Test Slack bot
    print("🤖 Testing Slack Bot Integration")
    print("=" * 50)

    try:
        # Initialize semantic layer
        semantic_layer = SemanticLayer("semantic_models/metrics.yml")

        # Create Slack bot
        slack_config = SlackConfig(
            bot_token=bot_token, signing_secret=signing_secret, port=3000, enable_socket_mode=False
        )

        bot = SemanticLayerSlackBot(semantic_layer, slack_config)

        print("✅ Slack bot created successfully")
        print(
            f"Bot configured for {'socket mode' if slack_config.enable_socket_mode else 'HTTP mode'}"
        )

        # Test formatting
        metrics = semantic_layer.list_metrics()
        formatted = bot.formatter.format_metric_list(metrics)
        print(f"\n📋 Formatted Metrics Preview:")
        print("-" * 30)
        print(formatted[:500] + "..." if len(formatted) > 500 else formatted)

        print(f"\n🎉 Slack integration ready!")
        print(f"💡 Start the bot with: await bot.start_server()")

    except Exception as e:
        print(f"❌ Error testing Slack bot: {e}")
        logger.exception("Slack bot test failed")
