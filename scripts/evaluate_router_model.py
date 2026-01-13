"""Evaluate a trained DistilBERT router model on a JSONL dataset."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

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


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the router model.")
    parser.add_argument(
        "--data-file",
        default="data/router_training/cynefin_router_training.jsonl",
    )
    parser.add_argument("--model-path", default="models/router_distilbert")
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--max-examples", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    data_path = Path(args.data_file)
    texts, labels = _load_jsonl(data_path)

    if args.max_examples and args.max_examples > 0:
        texts = texts[: args.max_examples]
        labels = labels[: args.max_examples]

    tokenizer = AutoTokenizer.from_pretrained(args.model_path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = AutoModelForSequenceClassification.from_pretrained(args.model_path)
    model.to(device)
    model.eval()

    preds: list[int] = []
    for text in texts:
        inputs = tokenizer(
            text,
            truncation=True,
            padding=True,
            max_length=args.max_length,
            return_tensors="pt",
        )
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.no_grad():
            outputs = model(**inputs)
        logits = outputs.logits.detach().cpu().numpy()[0]
        preds.append(int(np.argmax(logits)))

    accuracy = accuracy_score(labels, preds)
    print(f"Accuracy: {accuracy:.4f}")
    print("Confusion matrix:")
    print(confusion_matrix(labels, preds))
    target_names = [ID_TO_LABEL[i] for i in range(len(ID_TO_LABEL))]
    print("Classification report:")
    print(classification_report(labels, preds, target_names=target_names))


if __name__ == "__main__":
    main()
