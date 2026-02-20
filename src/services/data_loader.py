"""Data Loader Service for CARF.

Provides unified data loading from multiple sources:
- JSON payloads
- CSV files
- API responses
- Time-series data
- Graph data (Neo4j queries)

This service abstracts data ingestion and provides consistent
data structures for the analysis pipeline.
"""

import io
import json
import logging
from collections import OrderedDict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger("carf.data_loader")


class DataSourceType(str, Enum):
    """Types of data sources supported."""
    JSON = "json"
    CSV = "csv"
    API = "api"
    TIME_SERIES = "time_series"
    GRAPH = "graph"
    DATAFRAME = "dataframe"
    DICT = "dict"


class DataQuality(str, Enum):
    """Data quality assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNUSABLE = "unusable"


class DataColumn(BaseModel):
    """Metadata for a data column."""
    name: str
    dtype: str
    null_count: int = 0
    null_percentage: float = 0.0
    unique_count: int = 0
    sample_values: list[Any] = Field(default_factory=list)
    suggested_role: str | None = None  # treatment, outcome, covariate, etc.


class LoadedData(BaseModel):
    """Result of data loading operation."""
    data_id: str = Field(default_factory=lambda: str(uuid4())[:8])
    source_type: DataSourceType
    source_name: str
    loaded_at: datetime = Field(default_factory=datetime.utcnow)

    # Data shape
    row_count: int = 0
    column_count: int = 0

    # Column metadata
    columns: list[DataColumn] = Field(default_factory=list)

    # Quality assessment
    quality: DataQuality = DataQuality.FAIR
    quality_score: float = 0.5
    quality_issues: list[str] = Field(default_factory=list)

    # The actual data (stored as records)
    data_records: list[dict[str, Any]] = Field(default_factory=list)

    # Suggested analysis config
    suggested_treatment: str | None = None
    suggested_outcome: str | None = None
    suggested_covariates: list[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


class DataLoaderService:
    """Service for loading data from multiple sources."""

    # Patterns for detecting column roles
    TREATMENT_PATTERNS = [
        "treatment", "intervention", "program", "policy", "action",
        "exposed", "group", "treated", "control"
    ]
    OUTCOME_PATTERNS = [
        "outcome", "result", "effect", "impact", "response",
        "target", "dependent", "y_", "emissions", "revenue", "cost"
    ]
    COVARIATE_PATTERNS = [
        "age", "gender", "region", "industry", "size", "type",
        "category", "segment", "year", "month", "date"
    ]

    _max_cache_size = 20

    def __init__(self):
        self._cache: OrderedDict[str, LoadedData] = OrderedDict()

    async def load_json(
        self,
        json_data: dict | list | str,
        source_name: str = "json_payload"
    ) -> LoadedData:
        """Load data from JSON payload."""
        try:
            if isinstance(json_data, str):
                data = json.loads(json_data)
            else:
                data = json_data

            # Convert to DataFrame
            if isinstance(data, list):
                df = pd.DataFrame(data)
            elif isinstance(data, dict):
                if "data" in data:
                    df = pd.DataFrame(data["data"])
                else:
                    df = pd.DataFrame([data])
            else:
                raise ValueError(f"Unsupported JSON structure: {type(data)}")

            return self._process_dataframe(df, DataSourceType.JSON, source_name)

        except Exception as e:
            logger.error(f"Failed to load JSON: {e}")
            return LoadedData(
                source_type=DataSourceType.JSON,
                source_name=source_name,
                quality=DataQuality.UNUSABLE,
                quality_score=0.0,
                quality_issues=[str(e)]
            )

    async def load_csv(
        self,
        csv_content: str | bytes | io.BytesIO,
        source_name: str = "csv_file"
    ) -> LoadedData:
        """Load data from CSV content."""
        try:
            if isinstance(csv_content, bytes):
                csv_content = io.BytesIO(csv_content)
            elif isinstance(csv_content, str):
                csv_content = io.StringIO(csv_content)

            df = pd.read_csv(csv_content)
            return self._process_dataframe(df, DataSourceType.CSV, source_name)

        except Exception as e:
            logger.error(f"Failed to load CSV: {e}")
            return LoadedData(
                source_type=DataSourceType.CSV,
                source_name=source_name,
                quality=DataQuality.UNUSABLE,
                quality_score=0.0,
                quality_issues=[str(e)]
            )

    async def load_dataframe(
        self,
        df: pd.DataFrame,
        source_name: str = "dataframe"
    ) -> LoadedData:
        """Load data from an existing DataFrame."""
        return self._process_dataframe(df, DataSourceType.DATAFRAME, source_name)

    async def load_api_response(
        self,
        response_data: dict | list,
        source_name: str = "api_response"
    ) -> LoadedData:
        """Load data from an API response."""
        return await self.load_json(response_data, source_name)

    async def load_neo4j_query(
        self,
        query_result: list[dict],
        source_name: str = "neo4j_query"
    ) -> LoadedData:
        """Load data from Neo4j query results."""
        try:
            df = pd.DataFrame(query_result)
            return self._process_dataframe(df, DataSourceType.GRAPH, source_name)
        except Exception as e:
            logger.error(f"Failed to load Neo4j data: {e}")
            return LoadedData(
                source_type=DataSourceType.GRAPH,
                source_name=source_name,
                quality=DataQuality.UNUSABLE,
                quality_score=0.0,
                quality_issues=[str(e)]
            )

    def _process_dataframe(
        self,
        df: pd.DataFrame,
        source_type: DataSourceType,
        source_name: str
    ) -> LoadedData:
        """Process a DataFrame and extract metadata."""
        columns = []
        quality_issues = []

        for col in df.columns:
            null_count = df[col].isna().sum()
            null_pct = null_count / len(df) if len(df) > 0 else 0

            if null_pct > 0.3:
                quality_issues.append(f"High null rate in {col}: {null_pct:.0%}")

            # Get sample values
            non_null = df[col].dropna()
            samples = non_null.head(5).tolist() if len(non_null) > 0 else []

            # Detect role
            role = self._detect_column_role(col)

            columns.append(DataColumn(
                name=col,
                dtype=str(df[col].dtype),
                null_count=int(null_count),
                null_percentage=null_pct,
                unique_count=int(df[col].nunique()),
                sample_values=samples,
                suggested_role=role
            ))

        # Assess quality
        quality_score = self._calculate_quality_score(df, columns)
        quality = self._score_to_quality(quality_score)

        # Suggest analysis configuration
        treatment = next(
            (c.name for c in columns if c.suggested_role == "treatment"),
            None
        )
        outcome = next(
            (c.name for c in columns if c.suggested_role == "outcome"),
            None
        )
        covariates = [
            c.name for c in columns
            if c.suggested_role == "covariate"
        ]

        # Convert to records
        records = df.head(10000).to_dict(orient="records")

        loaded = LoadedData(
            source_type=source_type,
            source_name=source_name,
            row_count=len(df),
            column_count=len(df.columns),
            columns=columns,
            quality=quality,
            quality_score=quality_score,
            quality_issues=quality_issues,
            data_records=records,
            suggested_treatment=treatment,
            suggested_outcome=outcome,
            suggested_covariates=covariates
        )

        # Cache the result with LRU eviction
        self._cache[loaded.data_id] = loaded
        while len(self._cache) > self._max_cache_size:
            self._cache.popitem(last=False)

        return loaded

    def _detect_column_role(self, column_name: str) -> str | None:
        """Detect the likely role of a column based on its name."""
        name_lower = column_name.lower()

        for pattern in self.TREATMENT_PATTERNS:
            if pattern in name_lower:
                return "treatment"

        for pattern in self.OUTCOME_PATTERNS:
            if pattern in name_lower:
                return "outcome"

        for pattern in self.COVARIATE_PATTERNS:
            if pattern in name_lower:
                return "covariate"

        return None

    def _calculate_quality_score(
        self,
        df: pd.DataFrame,
        columns: list[DataColumn]
    ) -> float:
        """Calculate overall data quality score (0-1)."""
        scores = []

        # Completeness score
        avg_null_rate = sum(c.null_percentage for c in columns) / len(columns) if columns else 0
        completeness_score = 1 - avg_null_rate
        scores.append(completeness_score)

        # Sample size score
        n_rows = len(df)
        if n_rows >= 1000:
            size_score = 1.0
        elif n_rows >= 500:
            size_score = 0.9
        elif n_rows >= 100:
            size_score = 0.7
        elif n_rows >= 50:
            size_score = 0.5
        else:
            size_score = 0.3
        scores.append(size_score)

        # Uniqueness score (check for duplicates)
        duplicate_rate = df.duplicated().sum() / len(df) if len(df) > 0 else 0
        uniqueness_score = 1 - duplicate_rate
        scores.append(uniqueness_score)

        # Role detection score
        has_treatment = any(c.suggested_role == "treatment" for c in columns)
        has_outcome = any(c.suggested_role == "outcome" for c in columns)
        role_score = 1.0 if has_treatment and has_outcome else 0.5 if has_treatment or has_outcome else 0.3
        scores.append(role_score)

        return sum(scores) / len(scores)

    def _score_to_quality(self, score: float) -> DataQuality:
        """Convert numeric score to quality level."""
        if score >= 0.9:
            return DataQuality.EXCELLENT
        elif score >= 0.75:
            return DataQuality.GOOD
        elif score >= 0.5:
            return DataQuality.FAIR
        elif score >= 0.25:
            return DataQuality.POOR
        else:
            return DataQuality.UNUSABLE

    def get_cached_data(self, data_id: str) -> LoadedData | None:
        """Retrieve cached data by ID."""
        if data_id in self._cache:
            self._cache.move_to_end(data_id)
            return self._cache[data_id]
        return None

    def clear_cache(self) -> None:
        """Clear the data cache."""
        self._cache.clear()


# Singleton instance
_data_loader: DataLoaderService | None = None


def get_data_loader() -> DataLoaderService:
    """Get singleton DataLoaderService instance."""
    global _data_loader
    if _data_loader is None:
        _data_loader = DataLoaderService()
    return _data_loader
