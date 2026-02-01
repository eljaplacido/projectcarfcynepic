import pandas as pd
import io
from typing import List, Dict, Optional
from pydantic import BaseModel

class ColumnSchema(BaseModel):
    name: str
    dtype: str
    sample_values: List[str]
    suggested_role: Optional[str] = None  # 'treatment', 'outcome', 'covariate', 'id'
    
class SchemaDetectionResult(BaseModel):
    columns: List[ColumnSchema]
    row_count: int
    has_header: bool

class SchemaDetector:
    """
    Intelligent CSV schema detector that infers causal roles for columns.
    """
    
    def detect(self, file_content: bytes, filename: str) -> SchemaDetectionResult:
        try:
            # Try sniffing first
            content_str = file_content.decode('utf-8')
            sniffer = pd.read_csv(io.StringIO(content_str), nrows=5)
            has_header = True # Simplified assumption for now
            
            df = pd.read_csv(io.StringIO(content_str), nrows=100) # Sample 100 rows
            
            columns = []
            for col in df.columns:
                dtype = str(df[col].dtype)
                sample = df[col].dropna().head(3).astype(str).tolist()
                
                role = self._suggest_role(col, dtype)
                
                columns.append(ColumnSchema(
                    name=col,
                    dtype=dtype,
                    sample_values=sample,
                    suggested_role=role
                ))
                
            return SchemaDetectionResult(
                columns=columns,
                row_count=len(df), # Estimate or use sample size
                has_header=has_header
            )
            
        except Exception as e:
            print(f"Schema detection failed: {e}")
            return SchemaDetectionResult(columns=[], row_count=0, has_header=False)

    def _suggest_role(self, col_name: str, dtype: str) -> str:
        name = col_name.lower()
        
        # Treatment heuristics
        if any(x in name for x in ['treatment', 'intervention', 'program', 'campaign', 'variant', 'group']):
            return 'treatment'
            
        # Outcome heuristics
        if any(x in name for x in ['outcome', 'result', 'revenue', 'sales', 'conversion', 'score', 'churn', 'cost']):
            return 'outcome'
            
        # ID heuristics
        if any(x in name for x in ['id', 'user', 'customer', 'sku', 'uuid']) and ('int' in dtype or 'object' in dtype):
            if 'valid' in name: return 'covariate' # avoid validation_id false positives if needed
            return 'id'
            
        # Covariates (everything else that is valid)
        return 'covariate'

schema_detector = SchemaDetector()
