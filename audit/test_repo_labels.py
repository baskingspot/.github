"""Tests for repo_labels.py. The plan is pure, so these need no network."""

import unittest
from typing import Any

import repo_labels as rl


def have(*labels: tuple[str, str, str]) -> dict[str, dict[str, str]]:
    return {
        name: {"color": color, "description": description}
        for name, color, description in labels
    }


class PlanTest(unittest.TestCase):
    def test_a_repo_with_the_canonical_set_has_no_changes(self) -> None:
        canonical = [
            (label["name"], label["color"], label["description"])
            for label in rl.LABELS["canonical"]
        ]
        changes, leftovers = rl.plan(have(*canonical))

        self.assertEqual([], changes)
        self.assertEqual([], leftovers)

    def test_a_missing_label_is_created_with_its_body(self) -> None:
        changes, _ = rl.plan({})

        created = {
            change.name: change for change in changes if change.action == "create"
        }
        self.assertIn("priority:10-now", created)
        body = created["priority:10-now"].body or {}
        self.assertEqual("d93f0b", body["color"])

    def test_a_wrong_color_is_an_update_not_a_second_copy(self) -> None:
        changes, _ = rl.plan(
            have(
                (
                    "priority:10-now",
                    "000000",
                    "Do this before anything else in the org.",
                )
            )
        )

        actions = [(change.action, change.name) for change in changes]
        self.assertIn(("update", "priority:10-now"), actions)
        self.assertNotIn(("create", "priority:10-now"), actions)

    def test_a_superseded_label_is_deleted(self) -> None:
        changes, _ = rl.plan(have(("bug", "d73a4a", "Something is not working")))

        self.assertIn("delete bug", [str(change) for change in changes])

    def test_a_repo_label_outside_the_scheme_is_reported_and_kept(self) -> None:
        changes, leftovers = rl.plan(have(("aead", "ffffff", "tls topic")))

        self.assertEqual(["aead"], leftovers)
        self.assertEqual([], [change for change in changes if change.name == "aead"])

    def test_an_empty_description_on_github_matches_a_written_one_only_when_equal(
        self,
    ) -> None:
        changes, _ = rl.plan(have(("blocked", "b4a7d6", "")))

        self.assertIn("update blocked", [str(change) for change in changes])


class ApplyTest(unittest.TestCase):
    def test_each_change_becomes_one_write(self) -> None:
        sent: list[tuple[str, str, dict[str, Any] | None]] = []

        class Api:
            def get(self, path: str) -> Any:
                raise AssertionError("apply must not read")

            def send(
                self, method: str, path: str, body: dict[str, Any] | None = None
            ) -> None:
                sent.append((method, path, body))

        changes = [
            rl.Change("create", "blocked", {"color": "b4a7d6", "description": "x"}),
            rl.Change(
                "update", "priority:10-now", {"color": "d93f0b", "description": "y"}
            ),
            rl.Change("delete", "bug"),
        ]
        refused = rl.apply_changes(Api(), "stdx", changes)

        self.assertEqual([], refused)
        self.assertEqual(
            [
                ("POST", "repos/baskingspot/stdx/labels"),
                ("PATCH", "repos/baskingspot/stdx/labels/priority:10-now"),
                ("DELETE", "repos/baskingspot/stdx/labels/bug"),
            ],
            [(method, path) for method, path, _ in sent],
        )
        # GitHub refuses a create with no name, which is how this shipped broken once.
        self.assertEqual("blocked", (sent[0][2] or {})["name"])
        self.assertEqual("b4a7d6", (sent[0][2] or {})["color"])
        self.assertNotIn("name", sent[1][2] or {})

    def test_a_refusal_does_not_stop_the_rest(self) -> None:
        from repo_settings import ApiError

        class Api:
            def get(self, path: str) -> Any:
                raise AssertionError("apply must not read")

            def send(
                self, method: str, path: str, body: dict[str, Any] | None = None
            ) -> None:
                if path.endswith("bug"):
                    raise ApiError("DELETE failed: 422", 422)

        changes = [rl.Change("delete", "bug"), rl.Change("delete", "invalid")]
        refused = rl.apply_changes(Api(), "stdx", changes)

        self.assertEqual(1, len(refused))
        self.assertIn("delete bug", refused[0])


if __name__ == "__main__":
    unittest.main()
