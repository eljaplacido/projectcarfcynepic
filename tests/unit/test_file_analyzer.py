"""
Tests for the file analyzer service.
"""

import pytest
import json
from src.services.file_analyzer import (
    FileAnalyzer,
    FileAnalysisResult,
)


class TestFileAnalyzer:
    """Tests for the FileAnalyzer class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = FileAnalyzer()

    @pytest.mark.asyncio
    async def test_analyze_csv_file(self):
        """Test CSV file analysis."""
        csv_content = b"""name,age,score
Alice,25,85
Bob,30,92
Charlie,22,78"""

        result = await self.analyzer.analyze_file(
            content=csv_content,
            filename="data.csv",
            content_type="text/csv",
        )

        assert result.file_type == ".csv"
        assert result.file_name == "data.csv"
        assert result.row_count == 3
        assert result.column_count == 3
        assert "name" in result.columns
        assert "age" in result.columns
        assert "score" in result.columns
        assert result.analysis_ready is True

    @pytest.mark.asyncio
    async def test_analyze_json_file(self):
        """Test JSON file analysis."""
        json_content = json.dumps({
            "data": [
                {"name": "Alice", "value": 100},
                {"name": "Bob", "value": 200}
            ],
            "meta": {"source": "test"}
        }).encode()

        result = await self.analyzer.analyze_file(
            content=json_content,
            filename="data.json",
            content_type="application/json",
        )

        assert result.file_type == ".json"
        assert result.file_name == "data.json"
        # JSON files may not have analysis_ready=True unless they contain tabular data

    @pytest.mark.asyncio
    async def test_analyze_text_file(self):
        """Test text file analysis."""
        text_content = b"""This is a test document.
It contains multiple lines.
And some sample text for analysis."""

        result = await self.analyzer.analyze_file(
            content=text_content,
            filename="notes.txt",
            content_type="text/plain",
        )

        assert result.file_type == ".txt"
        assert result.file_name == "notes.txt"

    @pytest.mark.asyncio
    async def test_analyze_csv_with_treatment_outcome(self):
        """Test CSV variable suggestion for causal analysis."""
        csv_content = b"""treatment_group,outcome_measure,age,gender,region
1,85.2,25,M,North
0,72.1,30,F,South
1,88.5,22,M,East"""

        result = await self.analyzer.analyze_file(
            content=csv_content,
            filename="causal_data.csv",
            content_type="text/csv",
        )

        assert result.row_count == 3
        assert result.column_count == 5
        assert result.analysis_ready is True
        
        # Should have variable suggestions
        assert result.suggested_treatment is not None or result.suggested_outcome is not None

    @pytest.mark.asyncio
    async def test_analyze_csv_type_inference(self):
        """Test that file type is inferred from filename."""
        csv_content = b"""id,value
1,100
2,200"""

        result = await self.analyzer.analyze_file(
            content=csv_content,
            filename="data.csv",
            content_type=None,  # No content type provided
        )

        assert result.file_type == ".csv"
        assert result.analysis_ready is True

    @pytest.mark.asyncio
    async def test_analyze_text_content(self):
        """Test text content analysis (not file upload)."""
        text = """
        Analyzing the impact of training programs on employee performance.
        Treatment: intensive_training (0/1)
        Outcome: productivity_score
        Controls: experience_years, education_level
        """

        result = await self.analyzer.analyze_text(text)

        assert result is not None
        assert "preview" in result or "word_count" in result

    @pytest.mark.asyncio
    async def test_empty_csv(self):
        """Test handling of empty CSV files."""
        csv_content = b""

        result = await self.analyzer.analyze_file(
            content=csv_content,
            filename="empty.csv",
            content_type="text/csv",
        )

        # Should handle gracefully
        assert result.row_count == 0 or result.error is not None

    @pytest.mark.asyncio
    async def test_csv_with_numeric_columns(self):
        """Test CSV with numeric data detection."""
        csv_content = b"""customer_id,discount_received,churned,months_active,support_tickets
1,1,0,24,2
2,0,1,6,8
3,1,0,36,1
4,0,1,3,12
5,1,0,18,3"""

        result = await self.analyzer.analyze_file(
            content=csv_content,
            filename="customer_data.csv",
            content_type="text/csv",
        )

        assert result.row_count == 5
        assert result.column_count == 5
        assert result.analysis_ready is True

    @pytest.mark.asyncio
    async def test_file_size_recorded(self):
        """Test that file size is recorded."""
        csv_content = b"""a,b,c
1,2,3"""

        result = await self.analyzer.analyze_file(
            content=csv_content,
            filename="small.csv",
            content_type="text/csv",
        )

        assert result.file_size == len(csv_content)


class TestFileAnalyzerErrorHandling:
    """Error handling tests for FileAnalyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = FileAnalyzer()

    @pytest.mark.asyncio
    async def test_malformed_csv(self):
        """Test handling of malformed CSV."""
        # Inconsistent column counts
        csv_content = b"""a,b,c
1,2
3,4,5,6"""

        result = await self.analyzer.analyze_file(
            content=csv_content,
            filename="bad.csv",
            content_type="text/csv",
        )

        # Should not crash, might have error or partial result
        assert result is not None

    @pytest.mark.asyncio
    async def test_invalid_json(self):
        """Test handling of invalid JSON."""
        json_content = b"{ invalid json }"

        result = await self.analyzer.analyze_file(
            content=json_content,
            filename="bad.json",
            content_type="application/json",
        )

        # Should not crash, should have error
        assert result is not None
        assert result.error is not None or result.analysis_ready is False

    @pytest.mark.asyncio
    async def test_binary_content(self):
        """Test handling of binary content."""
        binary_content = bytes([0x00, 0x01, 0x02, 0xFF, 0xFE, 0xFD])

        result = await self.analyzer.analyze_file(
            content=binary_content,
            filename="binary.dat",
            content_type="application/octet-stream",
        )

        # Should handle gracefully
        assert result is not None

    @pytest.mark.asyncio
    async def test_unsupported_extension(self):
        """Test handling of unsupported file extensions."""
        content = b"some content"

        result = await self.analyzer.analyze_file(
            content=content,
            filename="file.xyz",
            content_type="application/x-unknown",
        )

        # Should handle gracefully
        assert result is not None


class TestFileAnalyzerTextAnalysis:
    """Tests for text analysis functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = FileAnalyzer()

    @pytest.mark.asyncio
    async def test_analyze_text_with_query(self):
        """Test text analysis with user query."""
        text = "Sales data from Q1 2024 showing product performance."
        query = "What factors affect sales?"

        result = await self.analyzer.analyze_text(text, query=query)

        assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_empty_text(self):
        """Test analysis of empty text."""
        result = await self.analyzer.analyze_text("")

        assert result is not None

    @pytest.mark.asyncio
    async def test_analyze_long_text(self):
        """Test analysis of longer text content."""
        long_text = " ".join(["word"] * 1000)

        result = await self.analyzer.analyze_text(long_text)

        assert result is not None
