"""Tests for the pure parts of audit.py."""

import importlib.util
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load() -> Any:
    """audit.py by path: `import audit` can mean the audit/ directory."""
    spec = importlib.util.spec_from_file_location(
        "audit_script", Path(__file__).with_name("audit.py")
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up here
    spec.loader.exec_module(module)
    return module


audit = _load()

NOW = datetime(2026, 10, 17, tzinfo=timezone.utc)


def repo(stage: str | None, created: str) -> dict[str, object]:
    return {
        "custom_properties": {"stage": stage} if stage else {},
        "created_at": created,
    }


class StageTest(unittest.TestCase):
    def test_a_stable_repo_is_audited(self) -> None:
        self.assertIsNone(
            audit.stage_finding("r", repo("stable", "2026-01-01T00:00:00Z"), NOW)
        )

    def test_a_repo_with_no_stage_counts_as_stable(self) -> None:
        self.assertIsNone(
            audit.stage_finding("r", repo(None, "2026-01-01T00:00:00Z"), NOW)
        )

    def test_a_new_incubating_repo_is_only_noted(self) -> None:
        finding = audit.stage_finding(
            "r", repo("incubating", "2026-10-01T00:00:00Z"), NOW
        )
        assert finding is not None
        self.assertEqual(finding.level, "info")
        self.assertIn("not audited", finding.message)

    def test_an_old_incubating_repo_is_a_warning(self) -> None:
        finding = audit.stage_finding(
            "r", repo("incubating", "2026-06-01T00:00:00Z"), NOW
        )
        assert finding is not None
        self.assertEqual(finding.level, "warn")
        self.assertIn("incubating for", finding.message)

    def test_a_mirror_is_never_a_warning_however_old(self) -> None:
        finding = audit.stage_finding("r", repo("mirror", "2025-01-01T00:00:00Z"), NOW)
        assert finding is not None
        self.assertEqual(finding.level, "info")


class PhraseTests(unittest.TestCase):
    def test_reserved_seats_are_found_singular_and_plural(self) -> None:
        self.assertEqual(
            audit.phrase_hits("Any other level is a Reserved Seat."), ["reserved seat"]
        )
        self.assertEqual(
            audit.phrase_hits("Three reserved seats, one empty seat."),
            ["reserved seat", "empty seat"],
        )

    def test_plain_text_and_lookalikes_are_clean(self) -> None:
        self.assertEqual(audit.phrase_hits("Take a seat. The seats are reserved."), [])
        self.assertEqual(audit.phrase_hits("unreserved seating"), [])


if __name__ == "__main__":
    unittest.main()


class TopicTests(unittest.TestCase):
    def test_a_zig_repo_carries_zig_and_zig_lang(self) -> None:
        self.assertEqual(
            audit.missing_topics(zig=True, package=False, topics=["zig"]), ["zig-lang"]
        )
        self.assertEqual(
            audit.missing_topics(zig=True, package=False, topics=["zig", "zig-lang"]),
            [],
        )

    def test_a_zig_package_also_carries_zig_package(self) -> None:
        self.assertEqual(
            audit.missing_topics(zig=True, package=True, topics=["zig", "zig-lang"]),
            ["zig-package"],
        )

    def test_specific_topics_are_allowed_on_top(self) -> None:
        self.assertEqual(
            audit.missing_topics(
                zig=True,
                package=True,
                topics=["zig", "zig-lang", "zig-package", "zstd"],
            ),
            [],
        )

    def test_a_repo_that_is_not_zig_needs_none_of_them(self) -> None:
        self.assertEqual(
            audit.missing_topics(zig=False, package=False, topics=["nix"]), []
        )


class LicenseTests(unittest.TestCase):
    def test_mit_and_apache_texts_match_their_spdx_id(self) -> None:
        self.assertTrue(
            audit.license_text_matches("MIT", "MIT License\n\nCopyright ...")
        )
        self.assertTrue(
            audit.license_text_matches("Apache-2.0", "Apache License\nVersion 2.0")
        )
        self.assertFalse(
            audit.license_text_matches("MIT", "Apache License\nVersion 2.0")
        )
        self.assertFalse(audit.license_text_matches("BSD-3-Clause", "anything"))
