"""Generate synthetic Cynefin router training data using DeepSeek.

This script batches prompts to reduce cost and writes JSONL + JSON output.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

DOMAINS = ["Clear", "Complicated", "Complex", "Chaotic", "Disorder"]

DOMAIN_PROMPTS: dict[str, str] = {
    "Clear": (
        "Generate 50 diverse examples of queries that belong to the \"Clear\" "
        "Cynefin domain.\n\n"
        "Clear domain characteristics:\n"
        "- The answer is obvious and requires no analysis\n"
        "- Direct lookup or standard procedure\n"
        "- Known answer, deterministic\n"
        "- Simple factual queries\n\n"
        "Examples:\n"
        "- \"What is 2+2?\"\n"
        "- \"Look up customer ID 12345\"\n"
        "- \"Get current stock price for AAPL\"\n"
        "- \"What is the current time?\"\n"
        "- \"Retrieve order status for order #789\"\n\n"
        "Generate 50 diverse examples across different contexts (business, tech, "
        "healthcare, finance, operations).\n"
        "Vary the phrasing and industry context while maintaining Clear domain traits.\n"
        "Return ONLY a JSON array of strings, no other text:\n"
        "[\"example1\", \"example2\", ...]"
    ),
    "Complicated": (
        "Generate 50 diverse examples of queries that belong to the \"Complicated\" "
        "Cynefin domain.\n\n"
        "Complicated domain characteristics:\n"
        "- Requires expert analysis but has a knowable answer\n"
        "- Root cause analysis needed\n"
        "- Multiple factors to consider\n"
        "- Optimization or diagnosis required\n\n"
        "Examples:\n"
        "- \"Why did our costs increase by 15%?\"\n"
        "- \"What caused the database query slowdown?\"\n"
        "- \"Analyze root cause of the production error\"\n"
        "- \"Optimize this machine learning model\"\n"
        "- \"Diagnose why customer churn increased\"\n\n"
        "Generate 50 diverse examples across different contexts.\n"
        "Return ONLY a JSON array of strings, no other text:\n"
        "[\"example1\", \"example2\", ...]"
    ),
    "Complex": (
        "Generate 50 diverse examples of queries that belong to the \"Complex\" "
        "Cynefin domain.\n\n"
        "Complex domain characteristics:\n"
        "- Novel situation where cause-effect is only clear in retrospect\n"
        "- Requires probing and exploration\n"
        "- High uncertainty, emergent behavior\n"
        "- Strategic or predictive questions\n\n"
        "Examples:\n"
        "- \"How will the market react to this new policy?\"\n"
        "- \"What's the best strategy for entering this market?\"\n"
        "- \"Predict user adoption of this new feature\"\n"
        "- \"How should we respond to this competitive threat?\"\n"
        "- \"What will customer behavior look like in 6 months?\"\n\n"
        "Generate 50 diverse examples across different contexts.\n"
        "Return ONLY a JSON array of strings, no other text:\n"
        "[\"example1\", \"example2\", ...]"
    ),
    "Chaotic": (
        "Generate 50 diverse examples of queries that belong to the \"Chaotic\" "
        "Cynefin domain.\n\n"
        "Chaotic domain characteristics:\n"
        "- Emergency requiring immediate stabilization\n"
        "- Crisis mode, critical failure\n"
        "- Immediate action needed\n"
        "- System instability\n\n"
        "Examples:\n"
        "- \"System is down! Critical failure!\"\n"
        "- \"Security breach detected! Immediate response needed!\"\n"
        "- \"Data corruption in progress! Stop it now!\"\n"
        "- \"Production server crashed! Emergency!\"\n"
        "- \"Critical bug in production! Fix immediately!\"\n\n"
        "Generate 50 diverse examples across different contexts.\n"
        "Return ONLY a JSON array of strings, no other text:\n"
        "[\"example1\", \"example2\", ...]"
    ),
    "Disorder": (
        "Generate 50 diverse examples of queries that belong to the \"Disorder\" "
        "Cynefin domain.\n\n"
        "Disorder domain characteristics:\n"
        "- Ambiguous or unclear request\n"
        "- Missing context or information\n"
        "- Contradictory requirements\n"
        "- Cannot confidently classify\n\n"
        "Examples:\n"
        "- \"What should I do?\"\n"
        "- \"Can you help me with something?\"\n"
        "- \"I need to figure out this problem\"\n"
        "- \"Something is wrong but I don't know what\"\n"
        "- \"Help me understand this situation\"\n\n"
        "Generate 50 diverse examples that are genuinely ambiguous or unclear.\n"
        "Return ONLY a JSON array of strings, no other text:\n"
        "[\"example1\", \"example2\", ...]"
    ),
}


def _clean_json_payload(content: str) -> str:
    """Strip markdown fences and return JSON payload string."""
    if "```json" in content:
        return content.split("```json")[1].split("```")[0].strip()
    if "```" in content:
        return content.split("```")[1].split("```")[0].strip()
    return content.strip()


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def _generate_batch(
    client: AsyncOpenAI,
    model: str,
    domain: str,
    temperature: float,
) -> list[str]:
    """Generate one batch of examples for a domain."""
    prompt = DOMAIN_PROMPTS[domain]
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Return only valid JSON arrays."},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
        max_tokens=2000,
    )
    content = response.choices[0].message.content or ""
    payload = _clean_json_payload(content)
    data = json.loads(payload)
    if not isinstance(data, list):
        raise ValueError("Expected a JSON array of strings.")
    return [str(item) for item in data]


async def _run(args: argparse.Namespace) -> None:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY is not set.")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    client = AsyncOpenAI(api_key=api_key, base_url=args.base_url)

    all_records: list[dict[str, Any]] = []

    for domain in DOMAINS:
        batches = args.examples_per_domain // args.batch_size
        if args.examples_per_domain % args.batch_size != 0:
            batches += 1
        print(f"Generating {args.examples_per_domain} {domain} examples ({batches} batches)...")

        total_for_domain = 0
        for batch_idx in range(batches):
            examples = await _generate_batch(
                client,
                args.model,
                domain,
                args.temperature,
            )
            trimmed = examples[: args.batch_size]
            total_for_domain += len(trimmed)
            for example in trimmed:
                all_records.append(
                    {"text": example, "label": domain, "source": "synthetic"}
                )
            print(f"  Batch {batch_idx + 1}/{batches}: {len(trimmed)} examples")
            await asyncio.sleep(args.delay_seconds)

        print(f"Completed {domain}: {total_for_domain} examples")

    jsonl_path = output_dir / "cynefin_router_training.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in all_records:
            handle.write(json.dumps(record, ensure_ascii=True) + "\n")

    json_path = output_dir / "cynefin_router_training.json"
    json_path.write_text(
        json.dumps(all_records, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )

    print(f"Wrote {len(all_records)} records to {jsonl_path}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate synthetic Cynefin router training data using DeepSeek."
    )
    parser.add_argument("--output-dir", default="data/router_training")
    parser.add_argument("--examples-per-domain", type=int, default=500)
    parser.add_argument("--batch-size", type=int, default=50)
    parser.add_argument("--delay-seconds", type=float, default=0.5)
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--temperature", type=float, default=0.9)
    parser.add_argument("--base-url", default="https://api.deepseek.com")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
