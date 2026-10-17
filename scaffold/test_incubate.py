"""Tests for incubate.py: the names it accepts and the text it writes."""

import tempfile
import unittest
from pathlib import Path

import incubate as inc

SHA = "a" * 40


class NameTest(unittest.TestCase):
    def test_a_good_name_and_matching_directory_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inc.check_name("my-lib", Path(tmp) / "my-lib")

    def test_a_bad_name_is_refused(self) -> None:
        for bad in ("My-Lib", "1lib", "my lib", "-lib", ""):
            with self.assertRaises(SystemExit, msg=bad):
                inc.check_name(bad, Path("/tmp") / (bad or "x"))

    def test_the_directory_must_be_named_for_the_project(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            inc.check_name("mylib", Path("/tmp/other"))
        self.assertIn("zig init", str(caught.exception))

    def test_a_directory_with_files_is_refused_and_an_empty_one_is_not(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "mylib"
            target.mkdir()
            inc.check_name("mylib", target)
            (target / "x").write_text("x")
            with self.assertRaises(SystemExit):
                inc.check_name("mylib", target)


class TextTest(unittest.TestCase):
    def test_the_license_names_the_contributors_not_a_person(self) -> None:
        text = inc.render_license(2026)
        self.assertIn("Copyright (c) 2026 baskingspot contributors", text)
        self.assertTrue(text.startswith("MIT License"))
        self.assertNotIn("Robenolt", text)

    def test_the_readme_says_it_is_unstable(self) -> None:
        text = inc.render_readme("mylib", "Does a thing.")
        self.assertTrue(text.startswith("# mylib\n\nDoes a thing."))
        self.assertIn("incubating", text)

    def test_the_justfile_follows_the_house_style(self) -> None:
        text = inc.render_justfile("mylib", "Does a thing.")
        self.assertIn("[private]\ndefault:", text)
        self.assertIn("ci: test lint", text)
        for recipe in ("test", "lint", "fmt", "ci"):
            self.assertRegex(
                text, rf'\[doc\("[^"]+"\)\]\n\[group\("[a-z]+"\)\]\n{recipe}'
            )

    def test_the_workflows_pin_the_gh_actions_release_by_sha_with_its_tag(self) -> None:
        for text in (inc.render_ci(SHA, "v1.2.3"), inc.render_zizmor(SHA, "v1.2.3")):
            self.assertIn(f"@{SHA} # v1.2.3", text)
            self.assertIn("permissions: {}", text)
        self.assertIn("secrets.CACHIX_AUTH_TOKEN", inc.render_ci(SHA, "v1.2.3"))
        self.assertNotIn("ubuntu-latest", inc.render_ci(SHA, "v1.2.3"))

    def test_agents_md_names_the_repo_and_the_settings_rule(self) -> None:
        text = inc.render_agents("mylib", "Does a thing.")
        self.assertIn("baskingspot/mylib", text)
        self.assertIn("just settings", text)


if __name__ == "__main__":
    unittest.main()
