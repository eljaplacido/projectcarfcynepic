from typing import List, Dict, Optional
from pydantic import BaseModel

class Suggestion(BaseModel):
    id: str
    type: str # 'prompt_refinement', 'next_step', 'methodology'
    text: str
    action_payload: Optional[str] = None # e.g. the suggested query text

class ImprovementContext(BaseModel):
    current_query: str
    last_domain: Optional[str] = None
    last_confidence: Optional[float] = None
    available_columns: List[str] = []

class ImprovementSuggestionService:
    """
    Agentic service that analyzes user intent and context to suggest
    better prompts or next analytical steps.
    """
    
    def suggest(self, context: ImprovementContext) -> List[Suggestion]:
        suggestions = []
        
        # 1. Prompt Refinement Heuristics
        q = context.current_query.lower()
        if len(q) < 10 and len(q) > 0:
            suggestions.append(Suggestion(
                id='expand_query',
                type='prompt_refinement',
                text='Make your query more specific (mention treatment/outcome)',
                action_payload=f"What is the effect of [treatment] on [outcome] in {q}?"
            ))
            
        if 'cause' in q or 'effect' in q:
            if 'region' in context.available_columns and 'region' not in q:
                 suggestions.append(Suggestion(
                    id='subgroup_region',
                    type='prompt_refinement',
                    text='Drill down by Region',
                    action_payload=context.current_query + " grouping by region"
                ))

        # 2. Methodology Suggestions based on Domain
        if context.last_domain == 'complex' and context.last_confidence and context.last_confidence < 0.6:
             suggestions.append(Suggestion(
                id='switch_bayesian',
                type='methodology',
                text='Low confidence in Causal model. Try Bayesian inference?',
                action_payload="/mode bayesian"
            ))
            
        # 3. Generic Guidance
        if not q and not context.last_domain:
             suggestions.append(Suggestion(
                id='starter_causal',
                type='prompt_refinement',
                text='Analyze a causal effect',
                action_payload="Analyze the causal effect of [Treatment] on [Outcome]"
            ))
             suggestions.append(Suggestion(
                id='starter_trend',
                type='prompt_refinement',
                text='Analyze trends over time',
                action_payload="What is the trend of [Metric] over the last 12 months?"
            ))

        return suggestions

improvement_service = ImprovementSuggestionService()
