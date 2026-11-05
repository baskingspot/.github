"""Tests for incubate.py: the names it accepts and the text it writes."""

import hashlib
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


class UnchangedTest(unittest.TestCase):
    """Without `--zig-dual`, the rendered text is what it was before the flag.

    These are the bytes every single-version repo was created from. A
    deliberate change to the single-version template updates a hash here in
    the same commit, so the change is visible in the diff rather than assumed.
    """

    def test_the_single_version_justfile_is_byte_identical(self) -> None:
        text = inc.render_justfile("mylib", "Does a thing.")
        self.assertEqual(
            hashlib.sha256(text.encode()).hexdigest(),
            "b724a1dfb92744b8938600787f8464a64f4e2f7a9cb2c347633efcf973a25a84",
        )
        self.assertNotIn("check: test", text)
        self.assertIn("\n    ziglint\n", text)

    def test_the_single_version_agents_md_is_byte_identical(self) -> None:
        text = inc.render_agents("mylib", "Does a thing.")
        self.assertEqual(
            hashlib.sha256(text.encode()).hexdigest(),
            "0f408df244c46c11051fb61c613862292185a6fb6b57066c177cdc0b78802e1d",
        )


class DualTest(unittest.TestCase):
    """`--zig-dual`: the same repo with the previous Zig version wired in."""

    def test_the_dual_justfile_gates_on_check(self) -> None:
        text = inc.render_justfile("mylib", "Does a thing.", dual=True)
        self.assertIn("check: test", text)
        self.assertIn("ci: check lint", text)
        self.assertNotIn("ci: test lint", text)
        self.assertIn("\n    ziglint-0-16\n", text)
        self.assertNotIn("\n    ziglint\n", text)
        self.assertRegex(
            text,
            r'\[doc\("The per-version gate[^"]*"\)\]\n\[group\("ci"\)\]\ncheck: test',
        )

    def test_the_dual_ci_config_runs_check_in_the_old_shell(self) -> None:
        text = inc.render_ci_config()
        self.assertIn("jobs:\n", text)
        self.assertIn("- recipe: ci\n", text)
        self.assertIn("- recipe: check\n    shell: zig-old\n", text)

    def test_the_dual_agents_md_names_both_versions_and_the_old_shell(self) -> None:
        text = inc.render_agents("mylib", "Does a thing.", dual=True)
        self.assertIn("Zig 0.16 and 0.17", text)
        self.assertIn("nix develop .#zig-old", text)
        self.assertIn("just check", text)
        self.assertIn("ziglint-0-16", text)
        self.assertNotIn("follows the dual-version pattern", text)

    def test_the_flag_picks_the_dual_template(self) -> None:
        self.assertEqual(
            inc.template_ref(False, None), "github:baskingspot/nix#zig-library"
        )
        self.assertEqual(
            inc.template_ref(True, None),
            "github:baskingspot/nix#zig-library-dual",
        )
        self.assertEqual(
            inc.template_ref(True, "/tmp/nix#zig-library-dual"),
            "/tmp/nix#zig-library-dual",
        )


class ZigInitTest(unittest.TestCase):
    """The fix-ups for the tree `zig init` writes."""

    ROOT_ZIG = 'try writer.print("Run `zig build test` to run the tests.\\n", .{});\n'

    def make_tree(self, root: Path) -> None:
        (root / "src").mkdir(parents=True)
        (root / "src" / "root.zig").write_text(self.ROOT_ZIG)
        (root / "build.zig").write_text(
            "pub fn build(b: *std.Build) void {}\n\n" + inc.ARGS_BLOCK
        )

    def test_the_print_without_placeholders_becomes_a_write_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_tree(root)
            inc.patch_zig_init(root, dual=False)
            text = (root / "src" / "root.zig").read_text()
            self.assertIn("writer.writeAll(", text)
            self.assertNotIn("writer.print(", text)

    def test_the_dual_tree_gets_the_passthru_args_helper(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_tree(root)
            inc.patch_zig_init(root, dual=True)
            text = (root / "build.zig").read_text()
            self.assertIn("passthruArgs(b, run_cmd);", text)
            self.assertIn(
                "fn passthruArgs(b: *std.Build, run: *std.Build.Step.Run)", text
            )
            # The one reference left is inside the helper.
            self.assertEqual(text.count("b.args"), 1)

    def test_the_single_tree_keeps_zig_own_build_zig(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_tree(root)
            before = (root / "build.zig").read_text()
            inc.patch_zig_init(root, dual=False)
            self.assertEqual((root / "build.zig").read_text(), before)

    def test_a_tree_zig_did_not_write_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir()
            (root / "src" / "root.zig").write_text("// nothing to patch\n")
            (root / "build.zig").write_text("pub fn build() void {}\n")
            with self.assertRaises(SystemExit):
                inc.patch_zig_init(root, dual=True)


if __name__ == "__main__":
    unittest.main()
