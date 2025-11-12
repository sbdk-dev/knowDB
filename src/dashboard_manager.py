"""
Dashboard Manager - Auto-Save and Management for Evidence.dev

Implements WrenAI-style chart generation with automatic Evidence.dev dashboard creation.
Every AI analyst query automatically saves to a dashboard with smart naming and cleanup.
"""

import re
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import pandas as pd

logger = logging.getLogger(__name__)


class DashboardManager:
    """
    Manages Evidence.dev dashboards with auto-save functionality
    
    Features:
    - Auto-save every query to timestamped dashboard
    - Combine multiple queries into named dashboards
    - Auto-cleanup old dashboards
    - List and manage existing dashboards
    """
    
    def __init__(self, dashboards_path: str = "dashboards/pages"):
        self.dashboards_path = Path(dashboards_path)
        self.dashboards_path.mkdir(parents=True, exist_ok=True)
        self.last_saved_dashboard = None
        
    def auto_save_query(self, 
                       query_text: str,
                       understanding: Dict[str, Any],
                       result: pd.DataFrame,
                       sql: str,
                       chart_recommendation: Dict[str, Any]) -> Dict[str, str]:
        """
        Automatically save query results to Evidence.dev dashboard
        
        Returns dict with dashboard_name, path, and url
        """
        
        # Generate smart dashboard name
        dashboard_name = self._generate_dashboard_name(understanding, query_text)
        
        # Create dashboard markdown
        markdown = self._create_dashboard_markdown(
            title=dashboard_name,
            query_text=query_text,
            understanding=understanding,
            result=result,
            sql=sql,
            chart_recommendation=chart_recommendation
        )
        
        # Save to file
        safe_name = self._sanitize_name(dashboard_name)
        dashboard_path = self.dashboards_path / f"{safe_name}.md"
        
        with open(dashboard_path, 'w') as f:
            f.write(markdown)
        
        self.last_saved_dashboard = safe_name
        
        logger.info(f"Auto-saved dashboard: {safe_name}")
        
        return {
            "dashboard_name": safe_name,
            "path": str(dashboard_path),
            "url": f"http://localhost:3000/{safe_name}"
        }
    
    def save_as(self, new_name: str) -> Dict[str, str]:
        """Rename the last saved dashboard"""
        
        if not self.last_saved_dashboard:
            raise ValueError("No dashboard to rename. Run a query first.")
        
        old_path = self.dashboards_path / f"{self.last_saved_dashboard}.md"
        if not old_path.exists():
            raise FileNotFoundError(f"Dashboard {self.last_saved_dashboard} not found")
        
        safe_new_name = self._sanitize_name(new_name)
        new_path = self.dashboards_path / f"{safe_new_name}.md"
        
        # Read and update content
        content = old_path.read_text()
        content = content.replace(
            f"title: {self.last_saved_dashboard}",
            f"title: {safe_new_name}"
        )
        
        # Write to new location
        new_path.write_text(content)
        old_path.unlink()  # Delete old file
        
        self.last_saved_dashboard = safe_new_name
        
        return {
            "dashboard_name": safe_new_name,
            "path": str(new_path),
            "url": f"http://localhost:3000/{safe_new_name}"
        }
    
    def add_to_dashboard(self, 
                        dashboard_name: str,
                        query_text: str,
                        understanding: Dict[str, Any],
                        result: pd.DataFrame,
                        sql: str,
                        chart_recommendation: Dict[str, Any]) -> Dict[str, str]:
        """Add current query to an existing dashboard"""
        
        safe_name = self._sanitize_name(dashboard_name)
        dashboard_path = self.dashboards_path / f"{safe_name}.md"
        
        if not dashboard_path.exists():
            raise FileNotFoundError(f"Dashboard {safe_name} not found")
        
        # Read existing content
        existing_content = dashboard_path.read_text()
        
        # Generate new section
        new_section = self._create_chart_section(
            query_text=query_text,
            understanding=understanding,
            result=result,
            sql=sql,
            chart_recommendation=chart_recommendation,
            section_number=self._count_sections(existing_content) + 1
        )
        
        # Append new section
        updated_content = existing_content + "\n\n" + new_section
        
        # Save
        dashboard_path.write_text(updated_content)
        
        return {
            "dashboard_name": safe_name,
            "path": str(dashboard_path),
            "url": f"http://localhost:3000/{safe_name}"
        }
    
    def list_dashboards(self) -> List[Dict[str, Any]]:
        """List all Evidence.dev dashboards"""
        
        dashboards = []
        
        for dashboard_file in sorted(self.dashboards_path.glob("*.md")):
            # Parse dashboard info
            content = dashboard_file.read_text()
            
            # Extract title
            title_match = re.search(r'title:\s*(.+)', content)
            title = title_match.group(1) if title_match else dashboard_file.stem
            
            # Count sections (charts)
            num_charts = content.count('```sql')
            
            # Get modified time
            mod_time = datetime.fromtimestamp(dashboard_file.stat().st_mtime)
            
            # Check if auto-generated (has timestamp in name)
            is_auto = bool(re.match(r'.*-\d{8}-\d{6}', dashboard_file.stem))
            
            dashboards.append({
                "name": dashboard_file.stem,
                "title": title,
                "num_charts": num_charts,
                "modified": mod_time.strftime("%Y-%m-%d %H:%M"),
                "is_auto_generated": is_auto,
                "url": f"http://localhost:3000/{dashboard_file.stem}"
            })
        
        return dashboards
    
    def cleanup_old_dashboards(self, days_old: int = 7) -> List[str]:
        """Remove auto-generated dashboards older than N days"""
        
        cleaned = []
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        for dashboard_file in self.dashboards_path.glob("*.md"):
            # Only cleanup auto-generated (timestamp in name)
            if re.match(r'.*-\d{8}-\d{6}', dashboard_file.stem):
                mod_time = datetime.fromtimestamp(dashboard_file.stat().st_mtime)
                
                if mod_time < cutoff_date:
                    dashboard_file.unlink()
                    cleaned.append(dashboard_file.stem)
                    logger.info(f"Cleaned up old dashboard: {dashboard_file.stem}")
        
        return cleaned
    
    # Helper methods
    
    def _generate_dashboard_name(self, understanding: Dict[str, Any], query_text: str) -> str:
        """Generate smart dashboard name from query"""
        
        intent = understanding.get("intent", "analysis")
        metrics = understanding.get("entities", {}).get("metrics", [])
        dimensions = understanding.get("entities", {}).get("dimensions", [])
        
        # Build name parts
        parts = []
        
        # Add primary metric
        if metrics:
            parts.append(metrics[0].replace("_", "-"))
        
        # Add intent hint
        if intent == "trend_analysis":
            parts.append("trend")
        elif intent == "comparison":
            parts.append("comparison")
        elif intent == "cohort_analysis":
            parts.append("cohort")
        
        # Add timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        parts.append(timestamp)
        
        return "-".join(parts) if parts else f"analysis-{timestamp}"
    
    def _sanitize_name(self, name: str) -> str:
        """Sanitize dashboard name for filesystem"""
        # Remove special characters, replace spaces with hyphens
        safe = re.sub(r'[^\w\s-]', '', name.lower())
        safe = re.sub(r'[\s_]+', '-', safe)
        return safe.strip('-')
    
    def _create_dashboard_markdown(self,
                                   title: str,
                                   query_text: str,
                                   understanding: Dict[str, Any],
                                   result: pd.DataFrame,
                                   sql: str,
                                   chart_recommendation: Dict[str, Any]) -> str:
        """Create Evidence.dev markdown for a dashboard"""
        
        safe_title = title.replace("-", " ").title()
        
        markdown = f"""---
title: {safe_title}
---

# {safe_title}

*Auto-generated by knowDB AI Analyst on {datetime.now().strftime("%Y-%m-%d %H:%M")}*

**Original Question**: "{query_text}"

---

"""
        
        # Add chart section
        markdown += self._create_chart_section(
            query_text=query_text,
            understanding=understanding,
            result=result,
            sql=sql,
            chart_recommendation=chart_recommendation,
            section_number=1
        )
        
        return markdown
    
    def _create_chart_section(self,
                             query_text: str,
                             understanding: Dict[str, Any],
                             result: pd.DataFrame,
                             sql: str,
                             chart_recommendation: Dict[str, Any],
                             section_number: int) -> str:
        """Create a chart section for Evidence.dev"""
        
        intent = understanding.get("intent", "analysis")
        chart_type = chart_recommendation.get("chart_type", "bar")
        
        # Determine columns
        columns = list(result.columns)
        x_col = columns[0] if columns else "x"
        y_cols = columns[1:] if len(columns) > 1 else columns
        
        section = f"""
## Chart {section_number}: {intent.replace('_', ' ').title()}

### Query

```sql data_{section_number}
{sql}
```

### Visualization

"""
        
        # Add appropriate Evidence.dev chart component
        if chart_type == "line" or intent == "trend_analysis":
            y_list = "\n".join([f"  - {col}" for col in y_cols])
            section += f"""
<LineChart
    data={{{{data_{section_number}}}}}
    x={x_col}
    y={{{{[
{y_list}
    ]}}}}
/>
"""
        elif chart_type == "bar" or intent == "comparison":
            y_col = y_cols[0] if y_cols else x_col
            section += f"""
<BarChart
    data={{{{data_{section_number}}}}}
    x={x_col}
    y={y_col}
/>
"""
        else:
            # Default to table
            section += f"""
<DataTable
    data={{{{data_{section_number}}}}}
    search=true
    rows=20
/>
"""
        
        section += """

### Data Details

<DataTable
    data={data_""" + str(section_number) + """}
    rows=10
/>

---

"""
        
        return section
    
    def _count_sections(self, content: str) -> int:
        """Count number of chart sections in markdown"""
        return content.count('```sql data_')


def format_auto_save_message(dashboard_info: Dict[str, str],
                            is_first_save: bool = True) -> str:
    """Format the auto-save message for Claude Desktop"""
    
    if is_first_save:
        return f"""

---

## 💾 Auto-Saved to Dashboard

📊 **Dashboard**: {dashboard_info['dashboard_name']}
🌐 **View**: {dashboard_info['url']}
📂 **Path**: `{dashboard_info['path']}`

**Your Options**:
- Click the URL above to view in Evidence.dev
- `save_as("custom-name")` - Rename this dashboard
- `add_to_dashboard("existing-name")` - Add to another dashboard
- Continue asking questions - each saves automatically!

💡 **Tip**: Auto-generated dashboards are cleaned up after 7 days. Rename to keep forever!
"""
    else:
        return f"""

---

## 💾 Added to Dashboard

📊 **Dashboard**: {dashboard_info['dashboard_name']}
🌐 **View**: {dashboard_info['url']}
🎯 **Charts**: Now contains multiple visualizations

**Keep Building**:
- Keep asking questions to add more charts
- `save_as("final-name")` when you're happy with it
- `list_dashboards()` to see all your dashboards
"""


# Example usage and testing
if __name__ == "__main__":
    # Test dashboard manager
    manager = DashboardManager()
    
    # Sample data
    sample_df = pd.DataFrame({
        'snapshot_month': ['2024-01', '2024-02', '2024-03'],
        'total_mrr': [28000, 29500, 31000]
    })
    
    sample_understanding = {
        'intent': 'trend_analysis',
        'entities': {
            'metrics': ['total_mrr'],
            'dimensions': ['snapshot_month']
        }
    }
    
    sample_sql = "SELECT snapshot_month, total_mrr FROM monthly_mrr_snapshots"
    
    sample_chart = {
        'chart_type': 'line',
        'title': 'MRR Trend'
    }
    
    # Auto-save
    result = manager.auto_save_query(
        query_text="Show me MRR trend",
        understanding=sample_understanding,
        result=sample_df,
        sql=sample_sql,
        chart_recommendation=sample_chart
    )
    
    print("Dashboard saved!")
    print(f"Name: {result['dashboard_name']}")
    print(f"URL: {result['url']}")
    
    # List dashboards
    dashboards = manager.list_dashboards()
    print(f"\nTotal dashboards: {len(dashboards)}")
