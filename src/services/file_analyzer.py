"""File Analysis Service for CARF.

Supports parsing and analyzing various file types:
- CSV (pandas parsing)
- JSON (direct load)
- PDF (pypdf extraction)
- TXT/MD (raw text)
- Excel (openpyxl)
"""

import io
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger("carf.file_analyzer")


class FileAnalysisResult(BaseModel):
    """Result of file analysis."""

    file_type: str = Field(..., description="Detected file type")
    file_name: str = Field(..., description="Original file name")
    file_size: int = Field(..., description="File size in bytes")
    row_count: int | None = Field(None, description="Number of rows for tabular data")
    column_count: int | None = Field(None, description="Number of columns for tabular data")
    columns: list[str] | None = Field(None, description="Column names for tabular data")
    column_types: dict[str, str] | None = Field(None, description="Inferred column types")
    text_content: str | None = Field(None, description="Extracted text content")
    data_preview: list[dict[str, Any]] | None = Field(None, description="Preview rows for tabular data")
    suggested_treatment: str | None = Field(None, description="Suggested treatment variable")
    suggested_outcome: str | None = Field(None, description="Suggested outcome variable")
    suggested_covariates: list[str] | None = Field(None, description="Suggested covariate variables")
    analysis_ready: bool = Field(False, description="Whether data is ready for analysis")
    error: str | None = Field(None, description="Error message if parsing failed")


class FileAnalyzer:
    """Service for analyzing uploaded files."""

    SUPPORTED_TYPES = {
        ".csv": "text/csv",
        ".json": "application/json",
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".xls": "application/vnd.ms-excel",
    }

    # Common variable name patterns for auto-detection
    TREATMENT_PATTERNS = [
        "treatment", "intervention", "program", "policy", "discount",
        "campaign", "initiative", "action", "invest", "spend"
    ]
    OUTCOME_PATTERNS = [
        "outcome", "result", "target", "revenue", "churn", "conversion",
        "sales", "emission", "impact", "effect", "response"
    ]
    COVARIATE_PATTERNS = [
        "age", "gender", "region", "industry", "size", "segment",
        "category", "type", "group", "cohort", "control"
    ]

    def __init__(self):
        self._pdf_available = False
        self._excel_available = False
        self._check_optional_deps()

    def _check_optional_deps(self):
        """Check availability of optional dependencies."""
        try:
            import pypdf  # noqa: F401
            self._pdf_available = True
        except ImportError:
            logger.warning("pypdf not installed - PDF parsing disabled")

        try:
            import openpyxl  # noqa: F401
            self._excel_available = True
        except ImportError:
            logger.warning("openpyxl not installed - Excel parsing disabled")

    async def analyze_file(
        self,
        content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> FileAnalysisResult:
        """Analyze uploaded file content.

        Args:
            content: Raw file bytes
            filename: Original filename
            content_type: MIME type (optional, will be inferred)

        Returns:
            FileAnalysisResult with parsed data and suggestions
        """
        file_ext = Path(filename).suffix.lower()
        file_size = len(content)

        result = FileAnalysisResult(
            file_type=file_ext,
            file_name=filename,
            file_size=file_size,
        )

        try:
            if file_ext == ".csv":
                result = await self._parse_csv(content, result)
            elif file_ext == ".json":
                result = await self._parse_json(content, result)
            elif file_ext == ".pdf":
                result = await self._parse_pdf(content, result)
            elif file_ext in [".txt", ".md"]:
                result = await self._parse_text(content, result)
            elif file_ext in [".xlsx", ".xls"]:
                result = await self._parse_excel(content, result)
            else:
                result.error = f"Unsupported file type: {file_ext}"

        except Exception as e:
            logger.error(f"Error parsing file {filename}: {e}")
            result.error = str(e)

        return result

    async def _parse_csv(self, content: bytes, result: FileAnalysisResult) -> FileAnalysisResult:
        """Parse CSV file."""
        df = pd.read_csv(io.BytesIO(content))
        return self._process_dataframe(df, result)

    async def _parse_json(self, content: bytes, result: FileAnalysisResult) -> FileAnalysisResult:
        """Parse JSON file."""
        data = json.loads(content.decode("utf-8"))

        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # List of objects -> DataFrame
            df = pd.DataFrame(data)
            return self._process_dataframe(df, result)
        elif isinstance(data, dict):
            # Check if it's columnar format
            if all(isinstance(v, list) for v in data.values()):
                df = pd.DataFrame(data)
                return self._process_dataframe(df, result)
            else:
                # Nested JSON - extract as text
                result.text_content = json.dumps(data, indent=2)[:10000]
                result.analysis_ready = False
        else:
            result.text_content = str(data)[:10000]
            result.analysis_ready = False

        return result

    async def _parse_pdf(self, content: bytes, result: FileAnalysisResult) -> FileAnalysisResult:
        """Parse PDF file."""
        if not self._pdf_available:
            result.error = "PDF parsing requires pypdf. Install with: pip install pypdf"
            return result

        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(content))
        text_parts = []

        for page in reader.pages[:50]:  # Limit to first 50 pages
            text = page.extract_text()
            if text:
                text_parts.append(text)

        result.text_content = "\n\n".join(text_parts)[:50000]  # Limit text size
        result.analysis_ready = False  # PDF text needs further processing

        return result

    async def _parse_text(self, content: bytes, result: FileAnalysisResult) -> FileAnalysisResult:
        """Parse text/markdown file."""
        result.text_content = content.decode("utf-8", errors="replace")[:50000]
        result.analysis_ready = False
        return result

    async def _parse_excel(self, content: bytes, result: FileAnalysisResult) -> FileAnalysisResult:
        """Parse Excel file."""
        if not self._excel_available:
            result.error = "Excel parsing requires openpyxl. Install with: pip install openpyxl"
            return result

        df = pd.read_excel(io.BytesIO(content), engine="openpyxl")
        return self._process_dataframe(df, result)

    def _process_dataframe(self, df: pd.DataFrame, result: FileAnalysisResult) -> FileAnalysisResult:
        """Process a DataFrame and populate result."""
        result.row_count = len(df)
        result.column_count = len(df.columns)
        result.columns = list(df.columns)

        # Infer column types
        type_mapping = {
            "int64": "integer",
            "float64": "float",
            "object": "string",
            "bool": "boolean",
            "datetime64[ns]": "datetime",
            "category": "category",
        }
        result.column_types = {
            col: type_mapping.get(str(df[col].dtype), str(df[col].dtype))
            for col in df.columns
        }

        # Preview first 10 rows
        result.data_preview = df.head(10).to_dict(orient="records")

        # Suggest variables based on column names
        columns_lower = [col.lower() for col in df.columns]

        # Find treatment variable
        for pattern in self.TREATMENT_PATTERNS:
            for i, col in enumerate(columns_lower):
                if pattern in col:
                    result.suggested_treatment = df.columns[i]
                    break
            if result.suggested_treatment:
                break

        # Find outcome variable
        for pattern in self.OUTCOME_PATTERNS:
            for i, col in enumerate(columns_lower):
                if pattern in col and df.columns[i] != result.suggested_treatment:
                    result.suggested_outcome = df.columns[i]
                    break
            if result.suggested_outcome:
                break

        # Find covariates
        covariates = []
        for pattern in self.COVARIATE_PATTERNS:
            for i, col in enumerate(columns_lower):
                col_name = df.columns[i]
                if (pattern in col and
                    col_name != result.suggested_treatment and
                    col_name != result.suggested_outcome and
                    col_name not in covariates):
                    covariates.append(col_name)
        result.suggested_covariates = covariates[:5]  # Limit to 5 suggestions

        result.analysis_ready = (
            result.row_count is not None and
            result.row_count > 0 and
            result.column_count is not None and
            result.column_count > 1
        )

        return result

    async def analyze_text(
        self,
        text: str,
        query: str | None = None,
    ) -> dict[str, Any]:
        """Analyze raw text content.

        For text that's not tabular data, we extract insights
        that can be used to inform a causal query.

        Args:
            text: Raw text content
            query: Optional user query for context

        Returns:
            Dictionary with analysis results
        """
        # Basic text analysis
        word_count = len(text.split())
        char_count = len(text)
        line_count = len(text.split("\n"))

        return {
            "word_count": word_count,
            "char_count": char_count,
            "line_count": line_count,
            "preview": text[:1000] + ("..." if len(text) > 1000 else ""),
            "requires_llm_extraction": True,
            "message": "Text content detected. Use /chat to discuss the content or extract structured data.",
        }


# Singleton instance
_file_analyzer: FileAnalyzer | None = None


def get_file_analyzer() -> FileAnalyzer:
    """Get singleton FileAnalyzer instance."""
    global _file_analyzer
    if _file_analyzer is None:
        _file_analyzer = FileAnalyzer()
    return _file_analyzer
