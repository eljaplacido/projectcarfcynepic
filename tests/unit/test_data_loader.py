"""Tests for the DataLoaderService."""

import pytest
import pandas as pd
from src.services.data_loader import (
    DataLoaderService,
    DataSourceType,
    DataQuality,
    get_data_loader,
)


@pytest.fixture
def loader():
    """Create a fresh DataLoaderService for testing."""
    return DataLoaderService()


@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing."""
    return [
        {"treatment": 1, "outcome": 100, "age": 30, "region": "north"},
        {"treatment": 0, "outcome": 50, "age": 35, "region": "south"},
        {"treatment": 1, "outcome": 120, "age": 28, "region": "north"},
        {"treatment": 0, "outcome": 45, "age": 40, "region": "east"},
        {"treatment": 1, "outcome": 110, "age": 32, "region": "west"},
    ]


@pytest.fixture
def sample_csv_content():
    """Sample CSV content for testing."""
    return """treatment,outcome,age,region
1,100,30,north
0,50,35,south
1,120,28,north
0,45,40,east
1,110,32,west"""


class TestDataLoaderService:
    """Tests for DataLoaderService class."""

    def test_get_data_loader_singleton(self):
        """Test that get_data_loader returns same instance."""
        loader1 = get_data_loader()
        loader2 = get_data_loader()
        assert loader1 is loader2

    @pytest.mark.asyncio
    async def test_load_json_list(self, loader, sample_json_data):
        """Test loading JSON list data."""
        result = await loader.load_json(sample_json_data, "test_data")

        assert result.source_type == DataSourceType.JSON
        assert result.source_name == "test_data"
        assert result.row_count == 5
        assert result.column_count == 4

    @pytest.mark.asyncio
    async def test_load_json_dict_with_data_key(self, loader, sample_json_data):
        """Test loading JSON dict with 'data' key."""
        json_dict = {"data": sample_json_data}
        result = await loader.load_json(json_dict, "test_dict")

        assert result.row_count == 5

    @pytest.mark.asyncio
    async def test_load_json_string(self, loader):
        """Test loading JSON from string."""
        json_str = '[{"x": 1, "y": 2}, {"x": 3, "y": 4}]'
        result = await loader.load_json(json_str, "test_string")

        assert result.row_count == 2
        assert result.column_count == 2

    @pytest.mark.asyncio
    async def test_load_json_error_handling(self, loader):
        """Test error handling for invalid JSON."""
        result = await loader.load_json("invalid json {", "bad_data")

        assert result.quality == DataQuality.UNUSABLE
        assert result.quality_score == 0.0
        assert len(result.quality_issues) > 0

    @pytest.mark.asyncio
    async def test_load_csv(self, loader, sample_csv_content):
        """Test loading CSV content."""
        result = await loader.load_csv(sample_csv_content, "test.csv")

        assert result.source_type == DataSourceType.CSV
        assert result.source_name == "test.csv"
        assert result.row_count == 5
        assert result.column_count == 4

    @pytest.mark.asyncio
    async def test_load_csv_bytes(self, loader, sample_csv_content):
        """Test loading CSV from bytes."""
        csv_bytes = sample_csv_content.encode('utf-8')
        result = await loader.load_csv(csv_bytes, "test_bytes.csv")

        assert result.row_count == 5

    @pytest.mark.asyncio
    async def test_load_csv_error_handling(self, loader):
        """Test error handling for invalid CSV."""
        result = await loader.load_csv("not,valid\ncsv,with,extra,cols", "bad.csv")

        # Should still parse but might have quality issues
        assert result.source_type == DataSourceType.CSV

    @pytest.mark.asyncio
    async def test_load_dataframe(self, loader):
        """Test loading from pandas DataFrame."""
        df = pd.DataFrame({
            "treatment": [1, 0, 1],
            "outcome": [100, 50, 120],
        })
        result = await loader.load_dataframe(df, "test_df")

        assert result.source_type == DataSourceType.DATAFRAME
        assert result.row_count == 3
        assert result.column_count == 2

    @pytest.mark.asyncio
    async def test_load_api_response(self, loader, sample_json_data):
        """Test loading from API response."""
        result = await loader.load_api_response(sample_json_data, "api_data")

        assert result.source_name == "api_data"
        assert result.row_count == 5

    @pytest.mark.asyncio
    async def test_load_neo4j_query(self, loader):
        """Test loading from Neo4j query results."""
        query_result = [
            {"node_id": 1, "value": 100},
            {"node_id": 2, "value": 200},
        ]
        result = await loader.load_neo4j_query(query_result, "graph_query")

        assert result.source_type == DataSourceType.GRAPH
        assert result.row_count == 2

    @pytest.mark.asyncio
    async def test_column_metadata_extraction(self, loader, sample_json_data):
        """Test that column metadata is extracted correctly."""
        result = await loader.load_json(sample_json_data, "test")

        assert len(result.columns) == 4

        # Check treatment column
        treatment_col = next(c for c in result.columns if c.name == "treatment")
        assert treatment_col.dtype in ["int64", "float64", "object"]
        assert treatment_col.null_count == 0
        assert treatment_col.unique_count == 2

    @pytest.mark.asyncio
    async def test_column_role_detection_treatment(self, loader):
        """Test that treatment columns are detected."""
        data = [{"intervention_group": 1, "result": 100}]
        result = await loader.load_json(data, "test")

        treatment_col = next(c for c in result.columns if c.name == "intervention_group")
        assert treatment_col.suggested_role == "treatment"

    @pytest.mark.asyncio
    async def test_column_role_detection_outcome(self, loader):
        """Test that outcome columns are detected."""
        data = [{"group": 1, "emissions_reduction": 50}]
        result = await loader.load_json(data, "test")

        outcome_col = next(c for c in result.columns if c.name == "emissions_reduction")
        assert outcome_col.suggested_role == "outcome"

    @pytest.mark.asyncio
    async def test_column_role_detection_covariate(self, loader):
        """Test that covariate columns are detected."""
        data = [{"x": 1, "age": 30, "gender": "M", "region": "EU"}]
        result = await loader.load_json(data, "test")

        age_col = next(c for c in result.columns if c.name == "age")
        assert age_col.suggested_role == "covariate"

        region_col = next(c for c in result.columns if c.name == "region")
        assert region_col.suggested_role == "covariate"

    @pytest.mark.asyncio
    async def test_quality_assessment_excellent(self, loader):
        """Test quality assessment for excellent data."""
        # Large, complete dataset with treatment and outcome
        data = [
            {"treatment": i % 2, "outcome": 100 + i * 10, "age": 25 + i, "region": "EU"}
            for i in range(1000)
        ]
        result = await loader.load_json(data, "excellent_data")

        assert result.quality in [DataQuality.EXCELLENT, DataQuality.GOOD]
        assert result.quality_score >= 0.75

    @pytest.mark.asyncio
    async def test_quality_assessment_poor_missing_data(self, loader):
        """Test quality assessment for data with missing values."""
        data = [
            {"treatment": 1, "outcome": 100, "age": None},
            {"treatment": 0, "outcome": None, "age": 30},
            {"treatment": None, "outcome": 50, "age": 35},
            {"treatment": 1, "outcome": None, "age": None},
        ]
        result = await loader.load_json(data, "poor_data")

        # Should have quality issues
        assert len(result.quality_issues) > 0
        assert result.quality_score < 0.8

    @pytest.mark.asyncio
    async def test_quality_assessment_small_sample(self, loader):
        """Test quality assessment for small samples."""
        data = [
            {"x": 1, "y": 2},
            {"x": 3, "y": 4},
        ]
        result = await loader.load_json(data, "small_data")

        # Small sample should lower quality score
        assert result.quality_score < 0.9

    @pytest.mark.asyncio
    async def test_suggested_analysis_config(self, loader):
        """Test that analysis configuration is suggested."""
        data = [
            {"program_enrolled": 1, "revenue_impact": 100, "age": 30, "industry": "tech"},
            {"program_enrolled": 0, "revenue_impact": 50, "age": 35, "industry": "finance"},
        ]
        result = await loader.load_json(data, "test")

        assert result.suggested_treatment == "program_enrolled"
        assert result.suggested_outcome == "revenue_impact"
        assert "age" in result.suggested_covariates or "industry" in result.suggested_covariates

    @pytest.mark.asyncio
    async def test_data_caching(self, loader, sample_json_data):
        """Test that loaded data is cached."""
        result = await loader.load_json(sample_json_data, "cached_test")

        cached = loader.get_cached_data(result.data_id)
        assert cached is not None
        assert cached.data_id == result.data_id
        assert cached.row_count == result.row_count

    def test_cache_retrieval_not_found(self, loader):
        """Test cache retrieval for non-existent data."""
        result = loader.get_cached_data("nonexistent_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_clear_cache(self, loader, sample_json_data):
        """Test clearing the cache."""
        result = await loader.load_json(sample_json_data, "to_clear")
        data_id = result.data_id

        loader.clear_cache()

        assert loader.get_cached_data(data_id) is None

    @pytest.mark.asyncio
    async def test_data_records_limited(self, loader):
        """Test that data records are limited to 10000 rows."""
        large_data = [{"x": i} for i in range(15000)]
        result = await loader.load_json(large_data, "large_test")

        assert len(result.data_records) == 10000
        assert result.row_count == 15000

    @pytest.mark.asyncio
    async def test_sample_values_extracted(self, loader, sample_json_data):
        """Test that sample values are extracted for columns."""
        result = await loader.load_json(sample_json_data, "test")

        for col in result.columns:
            assert len(col.sample_values) <= 5
