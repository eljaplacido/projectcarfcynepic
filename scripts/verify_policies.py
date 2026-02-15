#!/usr/bin/env python3
"""CSL Policy Verification Script.

Validates all .csl policy files in config/policies/.
Uses csl-core Z3 verification when available, falls back to syntax validation.

Usage:
    python scripts/verify_policies.py

Exit codes:
    0 - All policies valid
    1 - Validation errors found
"""

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
POLICY_DIR = PROJECT_ROOT / "config" / "policies"


def parse_csl_file(filepath: Path) -> dict:
    """Parse a .csl file and extract structure."""
    content = filepath.read_text(encoding="utf-8")

    result = {
        "file": filepath.name,
        "policies": [],
        "rules": [],
        "errors": [],
    }

    # Remove comments
    lines = []
    for line in content.splitlines():
        stripped = line.split("#")[0].rstrip()
        lines.append(stripped)
    clean = "\n".join(lines)

    # Find policy blocks
    policy_pattern = r'policy\s+(\w+)\s*\{'
    policy_matches = re.finditer(policy_pattern, clean)

    for match in policy_matches:
        policy_name = match.group(1)
        result["policies"].append(policy_name)

    if not result["policies"]:
        result["errors"].append(f"No policy blocks found in {filepath.name}")
        return result

    # Find rule blocks
    rule_pattern = r'rule\s+(\w+)\s*\{'
    rule_matches = re.finditer(rule_pattern, clean)

    for match in rule_matches:
        rule_name = match.group(1)
        result["rules"].append(rule_name)

    # Validate each rule has when/then/message
    rule_block_pattern = r'rule\s+(\w+)\s*\{([^}]*)\}'
    for match in re.finditer(rule_block_pattern, clean, re.DOTALL):
        rule_name = match.group(1)
        rule_body = match.group(2)

        if 'when ' not in rule_body and 'when\n' not in rule_body:
            result["errors"].append(f"Rule '{rule_name}' missing 'when' clause")
        if 'then ' not in rule_body and 'then\n' not in rule_body:
            result["errors"].append(f"Rule '{rule_name}' missing 'then' clause")
        if 'message' not in rule_body:
            result["errors"].append(f"Rule '{rule_name}' missing 'message' field")

    # Check balanced braces
    open_braces = clean.count('{')
    close_braces = clean.count('}')
    if open_braces != close_braces:
        result["errors"].append(
            f"Unbalanced braces: {open_braces} opening vs {close_braces} closing"
        )

    return result


def verify_with_csl_core(policy_dir: Path) -> tuple[bool, list[str]]:
    """Try to verify using csl-core Z3 verification."""
    try:
        import csl_core  # type: ignore[import-untyped]

        guard = csl_core.load_guard(str(policy_dir))
        verification = guard.verify()

        if verification.get("valid", False):
            return True, [f"Z3 verification passed: {verification.get('message', 'OK')}"]
        else:
            errors = verification.get("errors", [])
            return False, [f"Z3 verification failed: {e}" for e in errors]
    except ImportError:
        return True, []  # Not available, skip
    except Exception as e:
        return False, [f"Z3 verification error: {e}"]


def main() -> int:
    """Main verification entry point."""
    print("=" * 60)
    print("CSL Policy Verification")
    print("=" * 60)

    if not POLICY_DIR.exists():
        print(f"ERROR: Policy directory not found: {POLICY_DIR}")
        return 1

    csl_files = sorted(POLICY_DIR.glob("*.csl"))

    if not csl_files:
        print(f"WARNING: No .csl files found in {POLICY_DIR}")
        return 1

    print(f"\nFound {len(csl_files)} policy file(s) in {POLICY_DIR}\n")

    total_policies = 0
    total_rules = 0
    all_errors: list[str] = []

    for csl_file in csl_files:
        result = parse_csl_file(csl_file)
        n_policies = len(result["policies"])
        n_rules = len(result["rules"])
        total_policies += n_policies
        total_rules += n_rules

        status = "PASS" if not result["errors"] else "FAIL"
        icon = "+" if status == "PASS" else "!"
        print(f"  [{icon}] {result['file']}: {n_policies} policy(ies), {n_rules} rule(s) - {status}")

        for error in result["errors"]:
            print(f"      ERROR: {error}")
            all_errors.append(f"{result['file']}: {error}")

    # Try Z3 verification if available
    z3_ok, z3_messages = verify_with_csl_core(POLICY_DIR)
    for msg in z3_messages:
        print(f"\n  [Z3] {msg}")
    if not z3_ok:
        all_errors.extend(z3_messages)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Summary: {total_policies} policies, {total_rules} rules across {len(csl_files)} files")

    if all_errors:
        print(f"\nFAILED: {len(all_errors)} error(s) found")
        return 1
    else:
        print("\nPASSED: All policies valid")
        return 0


if __name__ == "__main__":
    sys.exit(main())
