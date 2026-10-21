"""Tests for the pure parts of audit.py."""

import importlib.util
import sys
import unittest
from datetime import UTC, datetime
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

NOW = datetime(2026, 10, 17, tzinfo=UTC)


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


class ReleaseTests(unittest.TestCase):
    def test_a_tag_with_a_changelog_section_and_matching_manifest_is_clean(
        self,
    ) -> None:
        self.assertEqual(
            audit.release_findings(
                "0.2.0",
                "## [Unreleased]\n\n## [0.2.0] - 2026-10-19\n",
                '.version = "0.2.0",',
            ),
            [],
        )

    def test_a_tag_without_its_changelog_section_is_an_error(self) -> None:
        errors = audit.release_findings(
            "0.2.0", "## [Unreleased]\n", '.version = "0.2.0",'
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("no `## [0.2.0]` section", errors[0])

    def test_a_manifest_that_disagrees_with_the_tag_is_an_error(self) -> None:
        errors = audit.release_findings("0.2.0", "## [0.2.0]\n", '.version = "0.1.0",')
        self.assertEqual(len(errors), 1)
        self.assertIn("says 0.1.0", errors[0])

    def test_a_manifest_without_a_version_is_an_error(self) -> None:
        errors = audit.release_findings("0.2.0", "## [0.2.0]\n", "")
        self.assertEqual(len(errors), 1)
        self.assertIn("no .version field", errors[0])


class ReadmeHeadingTests(unittest.TestCase):
    GOOD = "\n".join(f"## {h}\n" for h in audit.README_SECTIONS)

    def test_the_house_order_is_clean(self) -> None:
        self.assertEqual(audit.readme_heading_findings(self.GOOD), [])

    def test_an_extra_section_is_an_error(self) -> None:
        text = self.GOOD.replace("## Install", "## Design\n\n## Install")
        findings = audit.readme_heading_findings(text)
        self.assertEqual(len(findings), 1)
        self.assertIn("## Design", findings[0])

    def test_sections_out_of_order_are_an_error(self) -> None:
        text = self.GOOD.replace("Install", "TMP").replace("Documentation", "Install")
        text = text.replace("TMP", "Documentation")
        self.assertIn("out of order", " ".join(audit.readme_heading_findings(text)))

    def test_a_missing_section_is_an_error(self) -> None:
        text = self.GOOD.replace("## Work on it\n", "")
        self.assertEqual(
            audit.readme_heading_findings(text),
            ["README has no `## Work on it`"],
        )

    def test_a_heading_inside_a_code_fence_is_ignored(self) -> None:
        text = self.GOOD + "\n```sh\n## not a heading\n```\n"
        self.assertEqual(audit.readme_heading_findings(text), [])


class ChapterListTests(unittest.TestCase):
    GUIDE = (
        "Tagline.\n\n- [Parsing](#parsing): one.\n- [Limits](#limits): two.\n\n"
        "# Getting started\n\n## Install\n\n# Parsing\n\n# Limits\n"
    )
    README = (
        "## What is in it\n\n- [Parsing](https://baskingspot.dev/x/#parsing): one.\n\n"
        "## Install\n"
    )

    def findings(self, readme: str, guide: str) -> list[str]:
        return audit.chapter_list_findings("x", readme, guide)

    def test_matching_lists_are_clean(self) -> None:
        self.assertEqual(self.findings(self.README, self.GUIDE), [])

    def test_a_chapter_missing_from_the_guide_list_is_an_error(self) -> None:
        guide = self.GUIDE.replace("- [Parsing](#parsing): one.\n", "")
        self.assertIn("`#parsing`", " ".join(self.findings(self.README, guide)))

    def test_a_readme_link_to_nothing_is_an_error(self) -> None:
        readme = self.README.replace("#parsing", "#parsin")
        self.assertIn("`#parsin`", " ".join(self.findings(readme, self.GUIDE)))

    def test_a_readme_without_a_chapter_bullet_is_an_error(self) -> None:
        guide = self.GUIDE.replace("# Limits\n", "# Parsing again\n\n# Limits\n", 1)
        guide = guide.replace(
            "- [Limits](#limits)",
            "- [Parsing again](#parsing-again): x.\n- [Limits](#limits)",
        )
        self.assertIn("`#parsing-again`", " ".join(self.findings(self.README, guide)))

    def test_a_guide_without_getting_started_is_an_error(self) -> None:
        self.assertEqual(len(self.findings(self.README, "# Parsing\n")), 1)


class InstallCommandTests(unittest.TestCase):
    def test_a_released_library_installs_through_the_site(self) -> None:
        line = "zig fetch --save https://baskingspot.dev/cli/v0.1.0.tar.gz\n"
        self.assertEqual(
            audit.install_findings("cli", "0.1.0", line, line),
            [],
        )

    def test_the_old_git_form_is_an_error_once_released(self) -> None:
        line = "zig fetch --save git+https://github.com/baskingspot/cli\n"
        errors = audit.install_findings("cli", "0.1.0", line, line)
        self.assertEqual(len(errors), 2)
        self.assertIn("README.md", errors[0])
        self.assertIn("https://baskingspot.dev/cli/v0.1.0.tar.gz", errors[0])

    def test_a_repo_without_an_install_line_is_not_flagged(self) -> None:
        self.assertEqual(audit.install_findings("cli", "0.1.0", "# cli\n", ""), [])


class DependencyUrlTests(unittest.TestCase):
    def test_the_site_url_and_a_commit_pin_are_both_fine(self) -> None:
        text = """
            .url = "https://baskingspot.dev/testingx/v0.1.1.tar.gz",
            .url = "git+https://github.com/baskingspot/stdx#e8290a5c5eb5374066b4feb4946bf06aaba8e1f1",
        """
        self.assertEqual(audit.dependency_url_findings(text), [])

    def test_the_github_archive_url_is_an_error(self) -> None:
        text = "https://github.com/baskingspot/cli/archive/refs/tags/v0.1.0.tar.gz"
        errors = audit.dependency_url_findings(text)
        self.assertEqual(len(errors), 1)
        self.assertIn("git+...#<commit>", errors[0])

    def test_a_branch_pin_is_an_error(self) -> None:
        errors = audit.dependency_url_findings(
            "git+https://github.com/baskingspot/stdx#main"
        )
        self.assertEqual(len(errors), 1)

    def test_a_site_url_without_the_archive_extension_is_an_error(self) -> None:
        errors = audit.dependency_url_findings(
            "https://baskingspot.dev/testingx/v0.1.1"
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("/vX.Y.Z.tar.gz", errors[0])


class ReleaseCallerTests(unittest.TestCase):
    def test_a_source_only_repo_has_no_requirement(self) -> None:
        self.assertEqual(
            audit.release_caller_findings(False, "release-library.yml"), []
        )

    def test_a_program_caller_is_fine(self) -> None:
        caller = (
            "uses: baskingspot/gh-actions/.github/workflows/release.yml@abc # v1.0.0"
        )
        self.assertEqual(audit.release_caller_findings(True, caller), [])

    def test_the_library_caller_is_an_error_for_a_program(self) -> None:
        errors = audit.release_caller_findings(True, "release-library.yml")
        self.assertEqual(len(errors), 2)
        self.assertIn("uses the program workflow", errors[0])

    def test_a_missing_caller_is_an_error_for_a_program(self) -> None:
        errors = audit.release_caller_findings(True, "")
        self.assertEqual(len(errors), 1)
        self.assertIn("does not call the program workflow", errors[0])


class SlopLinkTests(unittest.TestCase):
    def test_a_human_doc_cannot_link_slop(self) -> None:
        findings = audit.slop_link_findings("README.md", "See docs/slop/notes.md.")
        self.assertEqual(len(findings), 1)
        self.assertIn("README.md line 1", findings[0])

    def test_plain_text_passes(self) -> None:
        self.assertEqual(audit.slop_link_findings("README.md", "See the guide."), [])
