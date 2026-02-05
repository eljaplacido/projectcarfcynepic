"""Unit tests for the schema detector service."""

import pytest
from src.services.schema_detector import schema_detector, SchemaDetector, SchemaDetectionResult, ColumnSchema


class TestSchemaDetector:
    """Tests for SchemaDetector class."""

    def test_detect_basic_csv(self):
        """Test detection of a basic CSV with treatment and outcome columns."""
        csv_content = b"""treatment,outcome,covariate1,user_id
1,100,50,A001
0,80,45,A002
1,120,55,A003
0,75,40,A004
"""
        result = schema_detector.detect(csv_content, "test.csv")

        assert isinstance(result, SchemaDetectionResult)
        assert result.row_count == 4
        assert result.has_header is True
        assert len(result.columns) == 4

    def test_detect_treatment_column(self):
        """Test that treatment columns are correctly identified."""
        csv_content = b"""treatment_group,sales,age
1,500,25
0,400,30
1,600,35
"""
        result = schema_detector.detect(csv_content, "test.csv")

        treatment_col = next(c for c in result.columns if c.name == "treatment_group")
        assert treatment_col.suggested_role == "treatment"

    def test_detect_outcome_column(self):
        """Test that outcome columns are correctly identified."""
        csv_content = b"""group,revenue,region
A,1000,US
B,800,EU
A,1200,APAC
"""
        result = schema_detector.detect(csv_content, "test.csv")

        outcome_col = next(c for c in result.columns if c.name == "revenue")
        assert outcome_col.suggested_role == "outcome"

    def test_detect_id_column(self):
        """Test that ID columns are correctly identified."""
        csv_content = b"""customer_id,purchase,category
C001,100,A
C002,200,B
C003,150,C
"""
        result = schema_detector.detect(csv_content, "test.csv")

        id_col = next(c for c in result.columns if c.name == "customer_id")
        assert id_col.suggested_role == "id"

    def test_detect_covariate_column(self):
        """Test that unmatched columns default to covariate."""
        csv_content = b"""treatment,outcome,age,gender
1,100,25,M
0,80,30,F
"""
        result = schema_detector.detect(csv_content, "test.csv")

        age_col = next(c for c in result.columns if c.name == "age")
        gender_col = next(c for c in result.columns if c.name == "gender")
        assert age_col.suggested_role == "covariate"
        assert gender_col.suggested_role == "covariate"

    def test_detect_program_as_treatment(self):
        """Test that 'program' keyword triggers treatment role."""
        csv_content = b"""supplier_program,scope3_emissions,region
1,-50,EU
0,10,US
"""
        result = schema_detector.detect(csv_content, "test.csv")

        program_col = next(c for c in result.columns if c.name == "supplier_program")
        assert program_col.suggested_role == "treatment"

    def test_detect_cost_as_outcome(self):
        """Test that 'cost' keyword triggers outcome role."""
        csv_content = b"""intervention,total_cost,department
1,5000,HR
0,8000,IT
"""
        result = schema_detector.detect(csv_content, "test.csv")

        cost_col = next(c for c in result.columns if c.name == "total_cost")
        assert cost_col.suggested_role == "outcome"

    def test_detect_churn_as_outcome(self):
        """Test that 'churn' keyword triggers outcome role."""
        csv_content = b"""treatment,churn_rate,segment
1,0.05,premium
0,0.15,basic
"""
        result = schema_detector.detect(csv_content, "test.csv")

        churn_col = next(c for c in result.columns if c.name == "churn_rate")
        assert churn_col.suggested_role == "outcome"

    def test_detect_handles_empty_csv(self):
        """Test that empty or malformed CSVs are handled gracefully."""
        csv_content = b""
        result = schema_detector.detect(csv_content, "empty.csv")

        assert result.columns == []
        assert result.row_count == 0

    def test_detect_sample_values(self):
        """Test that sample values are extracted correctly.

        SchemaDetector takes up to 5 non-null sample values per column.
        """
        csv_content = b"""treatment,outcome
1,100
0,80
1,120
0,75
1,110
"""
        result = schema_detector.detect(csv_content, "test.csv")

        treatment_col = next(c for c in result.columns if c.name == "treatment")
        # Schema detector takes head(5) samples
        assert len(treatment_col.sample_values) == 5
        assert "1" in treatment_col.sample_values
        assert "0" in treatment_col.sample_values

    def test_detect_dtype_inference(self):
        """Test that data types are correctly inferred."""
        csv_content = b"""int_col,float_col,str_col
1,1.5,hello
2,2.5,world
3,3.5,test
"""
        result = schema_detector.detect(csv_content, "test.csv")

        int_col = next(c for c in result.columns if c.name == "int_col")
        float_col = next(c for c in result.columns if c.name == "float_col")
        str_col = next(c for c in result.columns if c.name == "str_col")

        assert "int" in int_col.dtype
        assert "float" in float_col.dtype
        assert "object" in str_col.dtype


class TestColumnSchema:
    """Tests for ColumnSchema model."""

    def test_column_schema_creation(self):
        """Test basic ColumnSchema creation."""
        col = ColumnSchema(
            name="test_col",
            dtype="int64",
            sample_values=["1", "2", "3"],
            suggested_role="treatment"
        )

        assert col.name == "test_col"
        assert col.dtype == "int64"
        assert col.suggested_role == "treatment"

    def test_column_schema_optional_role(self):
        """Test that suggested_role is optional."""
        col = ColumnSchema(
            name="test_col",
            dtype="int64",
            sample_values=["1", "2", "3"]
        )

        assert col.suggested_role is None


class TestSchemaDetectionResult:
    """Tests for SchemaDetectionResult model."""

    def test_schema_detection_result_creation(self):
        """Test basic SchemaDetectionResult creation."""
        result = SchemaDetectionResult(
            columns=[
                ColumnSchema(name="col1", dtype="int64", sample_values=["1"])
            ],
            row_count=100,
            has_header=True
        )

        assert result.row_count == 100
        assert result.has_header is True
        assert len(result.columns) == 1
