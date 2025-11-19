"""
Intelligence Module for KnowDB

Provides natural language interpretation, statistical testing, and analysis suggestions
for query results. Implements execution-first pattern to prevent fabrication.
"""

from knowdb.intelligence.engine import IntelligenceEngine
from knowdb.intelligence.statistical import StatisticalTester

__all__ = [
    "IntelligenceEngine",
    "StatisticalTester",
]
