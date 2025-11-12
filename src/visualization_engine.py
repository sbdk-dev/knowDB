"""
Visualization Engine

This module implements visualization capabilities for the semantic layer:
- Auto-generate charts based on metric queries
- Support for multiple chart types (bar, line, pie, table)
- Smart chart recommendations based on data types
- Export capabilities (JSON, HTML, PNG)
- Integration with semantic layer queries

Phase C Implementation: Enhanced User Experience
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import base64
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class ChartConfig:
    """Configuration for chart generation"""

    chart_type: str  # 'bar', 'line', 'pie', 'table', 'scatter', 'histogram'
    title: str
    x_axis_label: Optional[str] = None
    y_axis_label: Optional[str] = None
    color_scheme: str = "default"
    width: int = 800
    height: int = 600
    show_values: bool = True
    interactive: bool = True


@dataclass
class ChartData:
    """Chart data and metadata"""

    config: ChartConfig
    data: pd.DataFrame
    chart_json: Dict[str, Any]
    html_output: Optional[str] = None
    svg_output: Optional[str] = None


class VisualizationEngine:
    """
    Creates charts and visualizations from semantic layer query results

    Automatically selects appropriate chart types based on data characteristics
    and provides multiple output formats for different use cases.
    """

    def __init__(self, theme: str = "default"):
        """
        Initialize visualization engine

        Args:
            theme: Color theme ('default', 'dark', 'light', 'business')
        """
        self.theme = theme
        self.color_schemes = self._load_color_schemes()
        self.chart_templates = self._load_chart_templates()

    def create_chart_from_query_result(
        self,
        query_result: Dict[str, Any],
        chart_type: Optional[str] = None,
        title: Optional[str] = None,
    ) -> ChartData:
        """
        Create chart from semantic layer query result

        Args:
            query_result: Result from semantic_layer.query_metric()
            chart_type: Specific chart type or None for auto-detection
            title: Chart title or None to generate automatically

        Returns:
            ChartData with chart configuration and outputs
        """
        # Convert query result to DataFrame
        df = pd.DataFrame(query_result["data"])

        if df.empty:
            return self._create_empty_chart(query_result)

        # Auto-detect chart type if not specified
        if not chart_type:
            chart_type = self._recommend_chart_type(df, query_result)

        # Generate title if not provided
        if not title:
            title = self._generate_chart_title(query_result, chart_type)

        # Create chart configuration
        config = self._create_chart_config(
            chart_type=chart_type, title=title, data=df, query_result=query_result
        )

        # Generate chart data
        chart_json = self._generate_chart_json(df, config, query_result)

        # Generate HTML output for embedding
        html_output = self._generate_html_output(chart_json, config)

        return ChartData(config=config, data=df, chart_json=chart_json, html_output=html_output)

    def create_dashboard(self, query_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create multi-chart dashboard from multiple query results

        Args:
            query_results: List of semantic layer query results

        Returns:
            Dashboard configuration with multiple charts
        """
        charts = []

        for i, result in enumerate(query_results):
            chart = self.create_chart_from_query_result(result)
            charts.append(
                {
                    "id": f"chart_{i}",
                    "chart_data": chart,
                    "position": {"row": i // 2, "col": i % 2},  # 2-column layout
                }
            )

        dashboard = {
            "title": "Metrics Dashboard",
            "created_at": datetime.now().isoformat(),
            "charts": charts,
            "layout": "grid",
            "theme": self.theme,
        }

        return dashboard

    def _recommend_chart_type(self, df: pd.DataFrame, query_result: Dict[str, Any]) -> str:
        """Recommend chart type based on data characteristics"""
        dimensions = query_result.get("dimensions", [])
        metric_name = query_result.get("metric", "")

        # No dimensions = single value = big number display
        if not dimensions:
            return "big_number"

        # One dimension
        elif len(dimensions) == 1:
            dim_col = dimensions[0]
            if dim_col in df.columns:
                unique_values = df[dim_col].nunique()

                # Time-based dimension
                if any(
                    word in dim_col.lower() for word in ["date", "time", "month", "day", "year"]
                ):
                    return "line"

                # Categorical with few values = pie chart
                elif unique_values <= 6:
                    return "pie"

                # Categorical with many values = bar chart
                else:
                    return "bar"

        # Two dimensions = grouped bar or scatter
        elif len(dimensions) == 2:
            return "grouped_bar"

        # Multiple dimensions = table
        else:
            return "table"

    def _generate_chart_title(self, query_result: Dict[str, Any], chart_type: str) -> str:
        """Generate descriptive chart title"""
        metric_display = query_result.get("display_name", query_result.get("metric", "Metric"))
        dimensions = query_result.get("dimensions", [])

        if not dimensions:
            return metric_display
        elif len(dimensions) == 1:
            return f"{metric_display} by {dimensions[0].replace('_', ' ').title()}"
        else:
            return f"{metric_display} Analysis"

    def _create_chart_config(
        self, chart_type: str, title: str, data: pd.DataFrame, query_result: Dict[str, Any]
    ) -> ChartConfig:
        """Create chart configuration based on data and type"""

        # Determine axis labels
        dimensions = query_result.get("dimensions", [])
        metric_name = query_result.get("metric", "Value")

        x_axis_label = None
        y_axis_label = query_result.get("display_name", metric_name)

        if dimensions:
            x_axis_label = dimensions[0].replace("_", " ").title()

        return ChartConfig(
            chart_type=chart_type,
            title=title,
            x_axis_label=x_axis_label,
            y_axis_label=y_axis_label,
            color_scheme=self.color_schemes[self.theme],
            width=800,
            height=600,
            show_values=True,
            interactive=True,
        )

    def _generate_chart_json(
        self, df: pd.DataFrame, config: ChartConfig, query_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate chart JSON configuration (Plotly format)"""

        chart_type = config.chart_type
        dimensions = query_result.get("dimensions", [])
        metric_name = query_result.get("metric", "value")

        if chart_type == "big_number":
            return self._create_big_number_chart(df, config, metric_name)
        elif chart_type == "bar":
            return self._create_bar_chart(df, config, dimensions, metric_name)
        elif chart_type == "line":
            return self._create_line_chart(df, config, dimensions, metric_name)
        elif chart_type == "pie":
            return self._create_pie_chart(df, config, dimensions, metric_name)
        elif chart_type == "table":
            return self._create_table_chart(df, config)
        else:
            # Default to bar chart
            return self._create_bar_chart(df, config, dimensions, metric_name)

    def _create_big_number_chart(
        self, df: pd.DataFrame, config: ChartConfig, metric_name: str
    ) -> Dict[str, Any]:
        """Create big number display for single values"""
        if not df.empty and metric_name in df.columns:
            value = df[metric_name].iloc[0]

            # Format value appropriately
            if isinstance(value, (int, float)):
                if value >= 1000000:
                    formatted_value = (
                        f"${value/1000000:.1f}M"
                        if "revenue" in metric_name.lower() or "amount" in metric_name.lower()
                        else f"{value/1000000:.1f}M"
                    )
                elif value >= 1000:
                    formatted_value = (
                        f"${value/1000:.1f}K"
                        if "revenue" in metric_name.lower() or "amount" in metric_name.lower()
                        else f"{value/1000:.1f}K"
                    )
                else:
                    formatted_value = (
                        f"${value:,.2f}"
                        if "revenue" in metric_name.lower() or "amount" in metric_name.lower()
                        else f"{value:,.0f}"
                    )
            else:
                formatted_value = str(value)
        else:
            formatted_value = "N/A"

        return {
            "type": "big_number",
            "value": formatted_value,
            "title": config.title,
            "subtitle": f"Current {metric_name.replace('_', ' ').title()}",
            "color": config.color_scheme["primary"],
        }

    def _create_bar_chart(
        self, df: pd.DataFrame, config: ChartConfig, dimensions: List[str], metric_name: str
    ) -> Dict[str, Any]:
        """Create bar chart configuration"""
        if not dimensions or dimensions[0] not in df.columns:
            return {"error": "Invalid dimensions for bar chart"}

        x_col = dimensions[0]
        y_col = metric_name

        return {
            "data": [
                {
                    "x": df[x_col].tolist(),
                    "y": df[y_col].tolist(),
                    "type": "bar",
                    "marker": {"color": config.color_scheme["primary"]},
                    "text": df[y_col].tolist() if config.show_values else None,
                    "textposition": "auto",
                }
            ],
            "layout": {
                "title": config.title,
                "xaxis": {"title": config.x_axis_label},
                "yaxis": {"title": config.y_axis_label},
                "width": config.width,
                "height": config.height,
                "template": "plotly_white",
            },
        }

    def _create_line_chart(
        self, df: pd.DataFrame, config: ChartConfig, dimensions: List[str], metric_name: str
    ) -> Dict[str, Any]:
        """Create line chart configuration"""
        if not dimensions or dimensions[0] not in df.columns:
            return {"error": "Invalid dimensions for line chart"}

        x_col = dimensions[0]
        y_col = metric_name

        return {
            "data": [
                {
                    "x": df[x_col].tolist(),
                    "y": df[y_col].tolist(),
                    "type": "scatter",
                    "mode": "lines+markers",
                    "line": {"color": config.color_scheme["primary"], "width": 3},
                    "marker": {"size": 8},
                }
            ],
            "layout": {
                "title": config.title,
                "xaxis": {"title": config.x_axis_label},
                "yaxis": {"title": config.y_axis_label},
                "width": config.width,
                "height": config.height,
                "template": "plotly_white",
            },
        }

    def _create_pie_chart(
        self, df: pd.DataFrame, config: ChartConfig, dimensions: List[str], metric_name: str
    ) -> Dict[str, Any]:
        """Create pie chart configuration"""
        if not dimensions or dimensions[0] not in df.columns:
            return {"error": "Invalid dimensions for pie chart"}

        labels_col = dimensions[0]
        values_col = metric_name

        return {
            "data": [
                {
                    "labels": df[labels_col].tolist(),
                    "values": df[values_col].tolist(),
                    "type": "pie",
                    "marker": {"colors": config.color_scheme["palette"]},
                    "textinfo": "label+percent",
                    "textposition": "auto",
                }
            ],
            "layout": {
                "title": config.title,
                "width": config.width,
                "height": config.height,
                "template": "plotly_white",
            },
        }

    def _create_table_chart(self, df: pd.DataFrame, config: ChartConfig) -> Dict[str, Any]:
        """Create table configuration"""
        return {
            "data": [
                {
                    "type": "table",
                    "header": {
                        "values": list(df.columns),
                        "fill": {"color": config.color_scheme["secondary"]},
                        "font": {"color": "white", "size": 14},
                    },
                    "cells": {
                        "values": [df[col].tolist() for col in df.columns],
                        "fill": {"color": "white"},
                        "font": {"size": 12},
                    },
                }
            ],
            "layout": {
                "title": config.title,
                "width": config.width,
                "height": config.height,
                "template": "plotly_white",
            },
        }

    def _generate_html_output(self, chart_json: Dict[str, Any], config: ChartConfig) -> str:
        """Generate HTML output for chart embedding"""

        # Handle big number display differently
        if chart_json.get("type") == "big_number":
            return f"""
            <div style="text-align: center; padding: 40px; background: white; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                <div style="font-size: 48px; font-weight: bold; color: {chart_json['color']}; margin-bottom: 10px;">
                    {chart_json['value']}
                </div>
                <div style="font-size: 18px; color: #666; margin-bottom: 5px;">
                    {chart_json['title']}
                </div>
                <div style="font-size: 14px; color: #999;">
                    {chart_json['subtitle']}
                </div>
            </div>
            """

        # Generate Plotly HTML for other chart types
        plotly_json = json.dumps(chart_json, indent=2)

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <title>{config.title}</title>
        </head>
        <body>
            <div id="chart" style="width:100%;height:100%;"></div>
            <script>
                var config = {plotly_json};
                Plotly.newPlot('chart', config.data, config.layout);
            </script>
        </body>
        </html>
        """

        return html

    def _create_empty_chart(self, query_result: Dict[str, Any]) -> ChartData:
        """Create empty chart when no data is available"""
        config = ChartConfig(
            chart_type="empty",
            title=f"No data available for {query_result.get('display_name', 'metric')}",
        )

        chart_json = {"type": "empty", "message": "No data to display", "title": config.title}

        html_output = f"""
        <div style="text-align: center; padding: 60px; color: #666;">
            <div style="font-size: 24px; margin-bottom: 10px;">📊</div>
            <div style="font-size: 18px; margin-bottom: 5px;">{config.title}</div>
            <div style="font-size: 14px;">Try adjusting your filters or date range</div>
        </div>
        """

        return ChartData(
            config=config, data=pd.DataFrame(), chart_json=chart_json, html_output=html_output
        )

    def _load_color_schemes(self) -> Dict[str, Dict[str, Any]]:
        """Load color schemes for different themes"""
        return {
            "default": {
                "primary": "#3498db",
                "secondary": "#2c3e50",
                "accent": "#e74c3c",
                "palette": [
                    "#3498db",
                    "#2ecc71",
                    "#e74c3c",
                    "#f39c12",
                    "#9b59b6",
                    "#1abc9c",
                    "#34495e",
                    "#e67e22",
                ],
            },
            "dark": {
                "primary": "#61dafb",
                "secondary": "#20232a",
                "accent": "#ff6b6b",
                "palette": [
                    "#61dafb",
                    "#4ecdc4",
                    "#ff6b6b",
                    "#feca57",
                    "#ff9ff3",
                    "#54a0ff",
                    "#5f27cd",
                    "#00d2d3",
                ],
            },
            "business": {
                "primary": "#2c5aa0",
                "secondary": "#1e3d59",
                "accent": "#ff6b35",
                "palette": [
                    "#2c5aa0",
                    "#1e3d59",
                    "#ff6b35",
                    "#f5d76e",
                    "#52d3aa",
                    "#41ead4",
                    "#c44569",
                    "#f8b500",
                ],
            },
        }

    def _load_chart_templates(self) -> Dict[str, Dict[str, Any]]:
        """Load chart templates for common patterns"""
        return {
            "revenue_trends": {
                "chart_type": "line",
                "title": "Revenue Trends",
                "color_scheme": "business",
            },
            "segment_breakdown": {
                "chart_type": "pie",
                "title": "Breakdown by Segment",
                "color_scheme": "default",
            },
            "metric_comparison": {
                "chart_type": "bar",
                "title": "Metric Comparison",
                "color_scheme": "default",
            },
        }

    def export_chart(
        self, chart_data: ChartData, format: str = "html", output_path: Optional[str] = None
    ) -> str:
        """
        Export chart to various formats

        Args:
            chart_data: Chart data to export
            format: Export format ('html', 'json', 'svg')
            output_path: Output file path (optional)

        Returns:
            Path to exported file or content string
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == "html":
            content = chart_data.html_output or ""
            if output_path:
                with open(output_path, "w") as f:
                    f.write(content)
                return output_path
            else:
                filename = f"chart_{timestamp}.html"
                with open(filename, "w") as f:
                    f.write(content)
                return filename

        elif format == "json":
            content = json.dumps(chart_data.chart_json, indent=2)
            if output_path:
                with open(output_path, "w") as f:
                    f.write(content)
                return output_path
            else:
                filename = f"chart_{timestamp}.json"
                with open(filename, "w") as f:
                    f.write(content)
                return filename

        else:
            raise ValueError(f"Unsupported export format: {format}")


# Example usage and testing
if __name__ == "__main__":
    # Test visualization engine with sample data

    # Create sample query result
    sample_query_result = {
        "metric": "total_mrr",
        "display_name": "Monthly Recurring Revenue",
        "description": "Total monthly recurring revenue",
        "dimensions": ["customer_segment"],
        "data": [
            {"customer_segment": "Enterprise", "total_mrr": 25000},
            {"customer_segment": "Mid-Market", "total_mrr": 15000},
            {"customer_segment": "SMB", "total_mrr": 8000},
        ],
        "row_count": 3,
        "sql": "SELECT customer_segment, SUM(subscription_amount) as total_mrr FROM ...",
    }

    print("📊 Testing Visualization Engine")
    print("=" * 50)

    # Initialize visualization engine
    viz_engine = VisualizationEngine(theme="business")

    # Create chart from query result
    chart = viz_engine.create_chart_from_query_result(sample_query_result)

    print(f"Chart Type: {chart.config.chart_type}")
    print(f"Title: {chart.config.title}")
    print(f"Data Shape: {chart.data.shape}")

    # Export chart
    html_file = viz_engine.export_chart(chart, format="html")
    json_file = viz_engine.export_chart(chart, format="json")

    print(f"\n📁 Exported Files:")
    print(f"  HTML: {html_file}")
    print(f"  JSON: {json_file}")

    # Test big number chart
    single_value_result = {
        "metric": "total_mrr",
        "display_name": "Total MRR",
        "dimensions": [],
        "data": [{"total_mrr": 48000}],
        "row_count": 1,
    }

    big_number_chart = viz_engine.create_chart_from_query_result(single_value_result)
    print(f"\n📈 Big Number Chart:")
    print(f"  Type: {big_number_chart.config.chart_type}")
    print(f"  Title: {big_number_chart.config.title}")

    # Test dashboard creation
    dashboard = viz_engine.create_dashboard([sample_query_result, single_value_result])
    print(f"\n📊 Dashboard:")
    print(f"  Charts: {len(dashboard['charts'])}")
    print(f"  Theme: {dashboard['theme']}")

    print("\n✅ Visualization engine test complete!")
