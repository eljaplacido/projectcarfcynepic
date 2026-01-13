"""Train a DistilBERT router classifier for Cynefin domains."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from datasets import Dataset, DatasetDict
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

LABEL_TO_ID = {
    "Clear": 0,
    "Complicated": 1,
    "Complex": 2,
    "Chaotic": 3,
    "Disorder": 4,
}
ID_TO_LABEL = {value: key for key, value in LABEL_TO_ID.items()}


def _load_jsonl(path: Path) -> tuple[list[str], list[int]]:
    texts: list[str] = []
    labels: list[int] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            texts.append(str(item["text"]))
            labels.append(LABEL_TO_ID[item["label"]])
    return texts, labels


def _tokenize(batch: dict, tokenizer: AutoTokenizer, max_length: int) -> dict:
    return tokenizer(
        batch["text"],
        truncation=True,
        padding=True,
        max_length=max_length,
    )


def _compute_metrics(eval_pred):
    logits, labels = eval_pred
    preds = np.argmax(logits, axis=1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="weighted", zero_division=0
    )
    accuracy = accuracy_score(labels, preds)
    return {
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train the DistilBERT router model.")
    parser.add_argument(
        "--data-file",
        default="data/router_training/cynefin_router_training.jsonl",
    )
    parser.add_argument("--model-name", default="distilbert-base-uncased")
    parser.add_argument("--output-dir", default="models/router_distilbert")
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    data_path = Path(args.data_file)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    texts, labels = _load_jsonl(data_path)
    dataset = Dataset.from_dict({"text": texts, "label": labels})

    split = dataset.train_test_split(test_size=0.2, seed=args.seed)
    val_test = split["test"].train_test_split(test_size=0.5, seed=args.seed)
    dataset_dict = DatasetDict(
        train=split["train"],
        validation=val_test["train"],
        test=val_test["test"],
    )

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=len(LABEL_TO_ID),
    )

    tokenized = dataset_dict.map(
        lambda batch: _tokenize(batch, tokenizer, args.max_length),
        batched=True,
    )

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        logging_dir=str(output_dir / "logs"),
        logging_steps=50,
        seed=args.seed,
        save_total_limit=2,
        report_to=[],
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["validation"],
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=_compute_metrics,
    )

    trainer.train()

    test_metrics = trainer.evaluate(tokenized["test"])
    print("Test metrics:", test_metrics)

    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    mapping_path = output_dir / "label_mappings.json"
    mapping_path.write_text(
        json.dumps({"label_to_id": LABEL_TO_ID, "id_to_label": ID_TO_LABEL}, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
