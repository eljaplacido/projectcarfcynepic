# Router Training and DistilBERT Implementation Guide

This guide covers data generation, DistilBERT training, and domain adaptation for the Cynefin router. It is written for the Phase 4 research demo and keeps the current LLM router as a fallback.

## Goals

- Replace LLM-only routing with a fast, local DistilBERT classifier.
- Keep LLM routing as a fallback and for evaluation comparisons.
- Ship a domain-agnostic base model and document domain-specific adaptation.

## Dataset Strategy

### Domain-agnostic base (recommended default)
Cynefin classifies problem type, not industry. Start with a domain-agnostic base dataset that spans multiple contexts (business, tech, healthcare, finance, operations).

Recommended size:
- 300 to 500 examples per domain (1,500 to 2,500 total)

### Domain-specific adaptation (optional)
If router performance is weak for a specific domain, fine-tune the base model on domain-specific examples.

Recommended size:
- 100 to 300 examples per domain for that vertical

### Hybrid approach (best results)
Train a base model on domain-agnostic data, then fine-tune with a smaller domain-specific set. This preserves generality while boosting precision in a target domain.

## Training Data Generation (DeepSeek)

### Colab notebook
Use `modeltraining/router_training_colab.ipynb` for a hosted GPU run.
If the repo is private, set a GitHub token in the notebook and use it in the clone URL.

### Install router training dependencies
```bash
pip install -e ".[router]"
```

### JSONL schema
Use this structure for training items:
```json
{"text": "query text", "label": "Clear", "source": "synthetic"}
```

### DeepSeek generation notes
- Use `DEEPSEEK_API_KEY` in `.env`.
- Use the OpenAI-compatible API base URL `https://api.deepseek.com`.
- Batch generation (for example, 50 items per call) reduces cost and improves consistency.
- Wrap external API calls with tenacity retries.

### Script
Use `scripts/generate_router_training_data.py`:
- Domain prompts for Clear, Complicated, Complex, Chaotic, Disorder
- Tenacity retry wrapper for API calls
- JSONL output in `data/router_training/cynefin_router_training.jsonl`

Tenacity snippet:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def generate_batch(...):
    ...
```

## DistilBERT Training

### Recommended setup
- Model: `distilbert-base-uncased`
- Max length: 128
- Train/val/test split: 80/10/10
- Metrics: accuracy, weighted F1

### Training script outline
Use `scripts/train_router_model.py`:
- Load JSONL data
- Map labels to ids: Clear=0, Complicated=1, Complex=2, Chaotic=3, Disorder=4
- Use Hugging Face Trainer for fine-tuning
- Handle `TrainingArguments` compatibility across Transformers versions (for example, `evaluation_strategy` vs `eval_strategy`)
- Save model to `models/router_distilbert/`
- Save label mappings to `models/router_distilbert/label_mappings.json`

### Evaluation
Use `scripts/evaluate_router_model.py` to report accuracy and a confusion matrix.

## Router Integration Plan

Update `src/workflows/router.py` to support two modes:

1) LLM mode (current)
2) DistilBERT mode (new)

Suggested config:
- `ROUTER_MODE=distilbert|llm`
- `ROUTER_MODEL_PATH=models/router_distilbert`

Implementation notes:
- Keep existing entropy and confidence logic.
- Only replace the classification step.
- Do not touch `src/core/state.py`.
- Log all state transitions (use `state.add_reasoning_step`).

## Domain Adaptation

### When to adapt
- You see repeated misclassifications in a domain (for example, medical or legal).
- You need higher confidence thresholds for automated routing.

### Adaptation workflow
1. Collect domain-specific examples (labeled).
2. Fine-tune the base model on the domain set.
3. Save to a new model path (for example, `models/router_finance`).
4. Point `ROUTER_MODEL_PATH` to the domain model.

Optional: freeze the base layers and fine-tune only the classifier head to reduce overfitting.

## Evaluation and Validation

Recommended checks:
- Confusion matrix to spot boundary issues (Clear vs Complicated, Complex vs Complicated).
- Compare DistilBERT vs LLM on a shared test set.
- Track confidence distribution and entropy alignment.

Suggested script:
- `scripts/evaluate_router.py` that loads a test set and runs both modes.

## Repo Integration Checklist

- [ ] Add generation and training scripts under `scripts/`
- [ ] Add `docs/ROUTER_TRAINING.md`
- [ ] Add `models/` to `.gitignore` if not already
- [ ] Add unit tests for model-based router mode
- [ ] Update `CURRENT_STATUS.md` with progress

## Environment Variables

Required:
```
LLM_PROVIDER=deepseek
DEEPSEEK_API_KEY=sk-your-key
```

Optional:
```
ROUTER_MODE=distilbert
ROUTER_MODEL_PATH=models/router_distilbert
```

## Notes

- Keep API keys out of version control.
- If a training script uses external APIs, use tenacity retries.
- If you add new tools under `src/tools`, use Pydantic `BaseModel` schemas.
