"""Tests for CSL policy verification."""

import pytest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_DIR = PROJECT_ROOT / "config" / "policies"


class TestPolicyVerification:
    """Test suite for CSL policy file validation."""

    def test_policy_directory_exists(self):
        """Policy directory must exist."""
        assert POLICY_DIR.exists(), f"Policy directory not found: {POLICY_DIR}"

    def test_csl_files_exist(self):
        """At least one .csl file must exist."""
        csl_files = list(POLICY_DIR.glob("*.csl"))
        assert len(csl_files) > 0, "No .csl policy files found"

    def test_all_csl_files_parseable(self):
        """All .csl files must be parseable without errors."""
        # Import the verification module
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from verify_policies import parse_csl_file

        csl_files = list(POLICY_DIR.glob("*.csl"))
        for csl_file in csl_files:
            result = parse_csl_file(csl_file)
            assert not result["errors"], (
                f"Errors in {csl_file.name}: {result['errors']}"
            )

    def test_each_policy_has_rules(self):
        """Each .csl file must contain at least one rule."""
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from verify_policies import parse_csl_file

        csl_files = list(POLICY_DIR.glob("*.csl"))
        for csl_file in csl_files:
            result = parse_csl_file(csl_file)
            assert len(result["rules"]) > 0, (
                f"No rules found in {csl_file.name}"
            )

    def test_malformed_csl_caught(self, tmp_path):
        """Malformed CSL files should produce errors."""
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from verify_policies import parse_csl_file

        # Create a malformed .csl file
        bad_file = tmp_path / "bad_policy.csl"
        bad_file.write_text("this is not valid CSL content")

        result = parse_csl_file(bad_file)
        assert len(result["errors"]) > 0, "Malformed CSL should produce errors"

    def test_unbalanced_braces_caught(self, tmp_path):
        """Unbalanced braces should be caught."""
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from verify_policies import parse_csl_file

        bad_file = tmp_path / "unbalanced.csl"
        bad_file.write_text("""
policy test_policy {
    rule test_rule {
        when x == 1
        then y == 2
        message = "test"

""")
        result = parse_csl_file(bad_file)
        assert any("brace" in e.lower() for e in result["errors"]), \
            "Should catch unbalanced braces"

    def test_known_policies_present(self):
        """Known required policies must exist."""
        import sys
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from verify_policies import parse_csl_file

        required_policies = ["budget_limits", "action_gates", "chimera_guards", "data_access"]
        found_policies = set()

        for csl_file in POLICY_DIR.glob("*.csl"):
            result = parse_csl_file(csl_file)
            found_policies.update(result["policies"])

        for policy in required_policies:
            assert policy in found_policies, f"Required policy '{policy}' not found in any .csl file"

    def test_verification_script_exit_code(self):
        """verify_policies.py should return 0 for valid policies."""
        import subprocess
        result = subprocess.run(
            ["python", str(PROJECT_ROOT / "scripts" / "verify_policies.py")],
            capture_output=True,
            text=True,
            cwd=str(PROJECT_ROOT),
        )
        assert result.returncode == 0, (
            f"Verification failed with exit code {result.returncode}:\n{result.stdout}\n{result.stderr}"
        )
