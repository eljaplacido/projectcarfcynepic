import pytest
from src.services.schema_detector import schema_detector, SchemaDetectionResult
from src.services.improvement_suggestions import improvement_service, ImprovementContext, Suggestion
import pandas as pd
import io

def test_schema_detector_csv():
    csv_content = b"id,treatment,outcome,age\n1,DrugA,Recovered,25\n2,Placebo,NotRecovered,30"
    result = schema_detector.detect(csv_content, "test.csv")
    
    assert isinstance(result, SchemaDetectionResult)
    assert len(result.columns) == 4
    
    # Check inferred roles
    treatment_col = next(c for c in result.columns if c.name == 'treatment')
    assert treatment_col.suggested_role == 'treatment'
    
    outcome_col = next(c for c in result.columns if c.name == 'outcome')
    assert outcome_col.suggested_role == 'outcome'

def test_improvement_suggestions():
    # Context 1: Vague query
    ctx = ImprovementContext(current_query="effect")
    suggestions = improvement_service.suggest(ctx)
    assert len(suggestions) > 0
    assert any(s.type == 'prompt_refinement' for s in suggestions)
    
    # Context 2: Low confidence complex domain
    ctx_complex = ImprovementContext(
        current_query="why is this happening?",
        last_domain="complex",
        last_confidence=0.4
    )
    suggestions_complex = improvement_service.suggest(ctx_complex)
    assert any(s.id == 'switch_bayesian' for s in suggestions_complex)
    
class TestServices:
    pass
