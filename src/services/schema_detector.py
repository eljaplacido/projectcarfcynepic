"""Schema Detection and Data Quality Validation Service.

Provides intelligent CSV/data schema detection with:
- Column role inference (treatment, outcome, covariate, id)
- Data quality validation (completeness, consistency, outliers)
- Recommendations for data improvement
- Causal analysis readiness assessment
"""

import io
import logging
from enum import Enum
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger("carf.schema_detector")


class DataQualityLevel(str, Enum):
    """Data quality assessment levels."""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    UNUSABLE = "unusable"


class ColumnSchema(BaseModel):
    """Schema information for a single column."""
    name: str
    dtype: str
    sample_values: list[str]
    suggested_role: str | None = None  # 'treatment', 'outcome', 'covariate', 'id'
    confidence: float = Field(0.5, ge=0.0, le=1.0, description="Role suggestion confidence")
    # Quality metrics
    null_count: int = 0
    null_percentage: float = 0.0
    unique_count: int = 0
    unique_percentage: float = 0.0
    min_value: Any | None = None
    max_value: Any | None = None
    mean_value: float | None = None
    std_value: float | None = None
    outlier_count: int = 0
    quality_issues: list[str] = Field(default_factory=list)


class DataQualityReport(BaseModel):
    """Comprehensive data quality report."""
    overall_score: float = Field(..., ge=0.0, le=1.0)
    overall_level: DataQualityLevel
    completeness_score: float = Field(0.0, ge=0.0, le=1.0)
    consistency_score: float = Field(0.0, ge=0.0, le=1.0)
    uniqueness_score: float = Field(0.0, ge=0.0, le=1.0)
    validity_score: float = Field(0.0, ge=0.0, le=1.0)
    sample_size_adequate: bool = True
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    causal_analysis_ready: bool = False
    causal_readiness_issues: list[str] = Field(default_factory=list)


class SchemaDetectionResult(BaseModel):
    """Complete schema detection result with quality assessment."""
    columns: list[ColumnSchema]
    row_count: int
    has_header: bool
    # Quality assessment
    quality_report: DataQualityReport | None = None
    # Role detection summary
    detected_treatment: str | None = None
    detected_outcome: str | None = None
    detected_covariates: list[str] = Field(default_factory=list)
    detected_ids: list[str] = Field(default_factory=list)
    # Recommendations
    analysis_recommendations: list[str] = Field(default_factory=list)


class SchemaDetector:
    """Intelligent CSV schema detector with data quality validation.

    Features:
    - Column role inference for causal analysis
    - Comprehensive data quality metrics
    - Causal analysis readiness assessment
    - Actionable recommendations
    """

    # Role detection patterns with confidence weights
    ROLE_PATTERNS = {
        "treatment": {
            "exact": ["treatment", "intervention", "exposure", "treated"],
            "partial": ["program", "campaign", "variant", "group", "condition", "arm"],
            "confidence_exact": 0.95,
            "confidence_partial": 0.75,
        },
        "outcome": {
            "exact": ["outcome", "target", "response", "result"],
            "partial": ["revenue", "sales", "conversion", "churn", "score", "cost",
                       "profit", "retention", "engagement", "satisfaction", "ltv",
                       "emissions", "impact", "effect"],
            "confidence_exact": 0.95,
            "confidence_partial": 0.80,
        },
        "id": {
            "exact": ["id", "user_id", "customer_id", "session_id", "record_id"],
            "partial": ["user", "customer", "sku", "uuid", "key", "identifier"],
            "confidence_exact": 0.95,
            "confidence_partial": 0.70,
        },
        "time": {
            "exact": ["date", "timestamp", "datetime", "time"],
            "partial": ["created", "updated", "period", "month", "year", "day"],
            "confidence_exact": 0.90,
            "confidence_partial": 0.70,
        },
    }

    # Minimum sample sizes for different analysis types
    MIN_SAMPLE_SIZES = {
        "causal": 100,
        "recommended_causal": 500,
        "bayesian": 30,
        "recommended_bayesian": 200,
    }

    def detect(self, file_content: bytes, filename: str) -> SchemaDetectionResult:
        """Detect schema and assess data quality.

        Args:
            file_content: Raw file bytes
            filename: Original filename

        Returns:
            SchemaDetectionResult with columns, quality report, and recommendations
        """
        try:
            content_str = file_content.decode('utf-8')
            df = pd.read_csv(io.StringIO(content_str))
            has_header = True
            row_count = len(df)

            columns = []
            roles = {"treatment": [], "outcome": [], "covariate": [], "id": [], "time": []}

            for col in df.columns:
                col_schema = self._analyze_column(df, col)
                columns.append(col_schema)

                # Track role assignments
                if col_schema.suggested_role:
                    roles.get(col_schema.suggested_role, roles["covariate"]).append(col)

            # Assess overall data quality
            quality_report = self._assess_data_quality(df, columns)

            # Build recommendations
            recommendations = self._generate_recommendations(df, columns, roles, quality_report)

            return SchemaDetectionResult(
                columns=columns,
                row_count=row_count,
                has_header=has_header,
                quality_report=quality_report,
                detected_treatment=roles["treatment"][0] if roles["treatment"] else None,
                detected_outcome=roles["outcome"][0] if roles["outcome"] else None,
                detected_covariates=[c for c in roles["covariate"]],
                detected_ids=roles["id"],
                analysis_recommendations=recommendations,
            )

        except Exception as e:
            logger.error(f"Schema detection failed: {e}")
            return SchemaDetectionResult(
                columns=[],
                row_count=0,
                has_header=False,
                quality_report=DataQualityReport(
                    overall_score=0.0,
                    overall_level=DataQualityLevel.UNUSABLE,
                    issues=[f"Failed to parse file: {e}"],
                    recommendations=["Ensure file is valid CSV format"],
                ),
            )

    def _analyze_column(self, df: pd.DataFrame, col: str) -> ColumnSchema:
        """Analyze a single column for schema and quality."""
        series = df[col]
        dtype = str(series.dtype)
        sample = series.dropna().head(5).astype(str).tolist()

        # Basic stats
        null_count = int(series.isnull().sum())
        null_pct = null_count / len(series) if len(series) > 0 else 0
        unique_count = int(series.nunique())
        unique_pct = unique_count / len(series) if len(series) > 0 else 0

        # Numeric stats
        min_val = max_val = mean_val = std_val = None
        outlier_count = 0

        if pd.api.types.is_numeric_dtype(series):
            min_val = float(series.min()) if not series.isnull().all() else None
            max_val = float(series.max()) if not series.isnull().all() else None
            mean_val = float(series.mean()) if not series.isnull().all() else None
            std_val = float(series.std()) if not series.isnull().all() else None

            # Detect outliers using IQR
            if std_val and std_val > 0:
                q1 = series.quantile(0.25)
                q3 = series.quantile(0.75)
                iqr = q3 - q1
                outlier_mask = (series < q1 - 1.5 * iqr) | (series > q3 + 1.5 * iqr)
                outlier_count = int(outlier_mask.sum())

        # Quality issues
        quality_issues = []
        if null_pct > 0.3:
            quality_issues.append(f"High missing values: {null_pct:.1%}")
        if unique_pct == 1.0 and len(series) > 10:
            quality_issues.append("All unique values - may be ID column")
        if unique_pct < 0.01 and len(series) > 100:
            quality_issues.append("Very low cardinality - consider as categorical")
        if outlier_count > len(series) * 0.05:
            quality_issues.append(f"High outlier count: {outlier_count}")

        # Role detection
        role, confidence = self._suggest_role(col, dtype, unique_pct, len(series))

        return ColumnSchema(
            name=col,
            dtype=dtype,
            sample_values=sample,
            suggested_role=role,
            confidence=confidence,
            null_count=null_count,
            null_percentage=null_pct,
            unique_count=unique_count,
            unique_percentage=unique_pct,
            min_value=min_val,
            max_value=max_val,
            mean_value=mean_val,
            std_value=std_val,
            outlier_count=outlier_count,
            quality_issues=quality_issues,
        )

    def _suggest_role(
        self,
        col_name: str,
        dtype: str,
        unique_pct: float,
        row_count: int,
    ) -> tuple[str, float]:
        """Suggest column role with confidence score."""
        name_lower = col_name.lower().replace("_", " ").replace("-", " ")

        # Check each role pattern
        for role, patterns in self.ROLE_PATTERNS.items():
            # Exact matches
            for pattern in patterns["exact"]:
                if pattern in name_lower.split() or name_lower == pattern:
                    return role, patterns["confidence_exact"]

            # Partial matches
            for pattern in patterns["partial"]:
                if pattern in name_lower:
                    return role, patterns["confidence_partial"]

        # Heuristic-based detection
        # High cardinality numeric -> likely covariate or outcome
        if pd.api.types.is_numeric_dtype(dtype) and unique_pct > 0.1:
            return "covariate", 0.5

        # Binary or low cardinality -> possibly treatment
        if unique_pct < 0.05 and row_count > 50:
            # Could be treatment if binary
            return "covariate", 0.4

        return "covariate", 0.3

    def _assess_data_quality(
        self,
        df: pd.DataFrame,
        columns: list[ColumnSchema],
    ) -> DataQualityReport:
        """Assess overall data quality."""
        issues = []
        recommendations = []

        # Completeness (non-null ratio)
        total_cells = df.shape[0] * df.shape[1]
        null_cells = df.isnull().sum().sum()
        completeness = 1 - (null_cells / total_cells) if total_cells > 0 else 0

        if completeness < 0.95:
            issues.append(f"Missing values: {(1-completeness):.1%} of data")
            recommendations.append("Handle missing values through imputation or removal")

        # Consistency (data types and patterns)
        consistency = 1.0
        mixed_type_cols = []
        for col in columns:
            if col.dtype == "object" and col.unique_percentage > 0.5:
                # Possible mixed types
                mixed_type_cols.append(col.name)
                consistency -= 0.1

        if mixed_type_cols:
            issues.append(f"Possible mixed types in: {mixed_type_cols[:3]}")

        consistency = max(0, consistency)

        # Uniqueness (duplicate rows)
        duplicate_ratio = df.duplicated().sum() / len(df) if len(df) > 0 else 0
        uniqueness = 1 - duplicate_ratio

        if duplicate_ratio > 0.05:
            issues.append(f"Duplicate rows: {duplicate_ratio:.1%}")
            recommendations.append("Review and remove duplicate records")

        # Validity (outliers and range checks)
        total_outliers = sum(c.outlier_count for c in columns)
        total_numeric_rows = sum(
            len(df) for c in columns if c.dtype in ['int64', 'float64']
        )
        outlier_ratio = total_outliers / total_numeric_rows if total_numeric_rows > 0 else 0
        validity = 1 - min(outlier_ratio, 0.5)  # Cap impact

        if outlier_ratio > 0.05:
            issues.append(f"High outlier ratio: {outlier_ratio:.1%}")
            recommendations.append("Investigate outliers - may be data errors or valid extremes")

        # Sample size adequacy
        sample_size_adequate = len(df) >= self.MIN_SAMPLE_SIZES["causal"]
        if not sample_size_adequate:
            issues.append(f"Sample size ({len(df)}) below minimum ({self.MIN_SAMPLE_SIZES['causal']})")
            recommendations.append(f"Collect at least {self.MIN_SAMPLE_SIZES['recommended_causal']} samples for robust causal analysis")

        # Causal analysis readiness
        causal_ready = True
        causal_issues = []

        has_treatment = any(c.suggested_role == "treatment" for c in columns)
        has_outcome = any(c.suggested_role == "outcome" for c in columns)

        if not has_treatment:
            causal_ready = False
            causal_issues.append("No treatment column detected")
        if not has_outcome:
            causal_ready = False
            causal_issues.append("No outcome column detected")
        if len(df) < self.MIN_SAMPLE_SIZES["causal"]:
            causal_ready = False
            causal_issues.append(f"Insufficient sample size for causal analysis")
        if completeness < 0.80:
            causal_ready = False
            causal_issues.append("Too many missing values for reliable analysis")

        # Overall score
        overall_score = (
            completeness * 0.30 +
            consistency * 0.20 +
            uniqueness * 0.25 +
            validity * 0.25
        )

        overall_level = (
            DataQualityLevel.EXCELLENT if overall_score > 0.95
            else DataQualityLevel.GOOD if overall_score > 0.85
            else DataQualityLevel.FAIR if overall_score > 0.70
            else DataQualityLevel.POOR if overall_score > 0.50
            else DataQualityLevel.UNUSABLE
        )

        return DataQualityReport(
            overall_score=overall_score,
            overall_level=overall_level,
            completeness_score=completeness,
            consistency_score=consistency,
            uniqueness_score=uniqueness,
            validity_score=validity,
            sample_size_adequate=sample_size_adequate,
            issues=issues,
            recommendations=recommendations,
            causal_analysis_ready=causal_ready,
            causal_readiness_issues=causal_issues,
        )

    def _generate_recommendations(
        self,
        df: pd.DataFrame,
        columns: list[ColumnSchema],
        roles: dict[str, list[str]],
        quality_report: DataQualityReport,
    ) -> list[str]:
        """Generate analysis recommendations."""
        recommendations = []

        # Role-based recommendations
        if not roles["treatment"]:
            recommendations.append(
                "Specify treatment column: Look for binary/categorical column representing intervention"
            )
        if not roles["outcome"]:
            recommendations.append(
                "Specify outcome column: Identify the metric you want to measure effect on"
            )
        if len(roles["covariate"]) < 2 and len(df.columns) > 3:
            recommendations.append(
                "Include covariates: Add confounding variables to control for selection bias"
            )

        # Quality-based recommendations
        if quality_report.completeness_score < 0.95:
            recommendations.append(
                "Handle missing data: Consider multiple imputation for robust analysis"
            )

        # Sample size recommendations
        if len(df) < self.MIN_SAMPLE_SIZES["recommended_causal"]:
            recommendations.append(
                f"Consider collecting more data: Current {len(df)} samples, recommend {self.MIN_SAMPLE_SIZES['recommended_causal']}+"
            )

        # Analysis type recommendation
        if quality_report.causal_analysis_ready:
            recommendations.append(
                "Data appears ready for causal analysis: Use Complicated domain with DoWhy"
            )
        else:
            recommendations.append(
                "Data not ready for causal analysis: Consider Bayesian exploration first"
            )

        return recommendations


# Singleton instance
schema_detector = SchemaDetector()
