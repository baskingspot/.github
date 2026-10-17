"""Tests for repo_settings.py. A fake API stands in for GitHub."""

import unittest
from typing import Any

import repo_settings as rs


class FakeApi:
    """Answers reads from a table and records every write."""

    def __init__(self, reads: dict[str, Any]) -> None:
        self.reads = reads
        self.writes: list[tuple[str, str, dict[str, Any] | None]] = []

    def get(self, path: str) -> Any:
        value = self.reads[path]
        if isinstance(value, rs.ApiError):
            raise value
        return value

    def send(self, method: str, path: str, body: dict[str, Any] | None = None) -> None:
        self.writes.append((method, path, body))


def matching_repo() -> dict[str, Any]:
    """A repo that already has every wanted value."""
    cfg = rs.CONFIG["repo"]
    meta = dict(cfg["fields"])
    meta["security_and_analysis"] = {
        k: {"status": v} for k, v in cfg["security_and_analysis"].items()
    }
    base = "repos/baskingspot/r"
    return {
        base: meta,
        f"{base}/vulnerability-alerts": {"_status": 204},
        f"{base}/automated-security-fixes": {
            "enabled": cfg["automated_security_fixes"]
        },
        f"{base}/private-vulnerability-reporting": {
            "enabled": cfg["private_vulnerability_reporting"]
        },
        f"{base}/code-scanning/default-setup": {
            "state": cfg["code_scanning_default_setup"]
        },
        f"{base}/actions/permissions": dict(cfg["actions"]),
        f"{base}/actions/permissions/workflow": dict(cfg["actions_workflow"]),
    }


class DiffTest(unittest.TestCase):
    def test_flatten_makes_dotted_keys(self) -> None:
        self.assertEqual(rs.flatten({"a": {"b": 1}, "c": 2}), {"a.b": 1, "c": 2})

    def test_a_repo_with_every_wanted_value_has_no_drift(self) -> None:
        have = rs.read_repo(FakeApi(matching_repo()), "r")
        self.assertEqual(rs.diff(rs.want_repo(), have), [])

    def test_a_changed_value_is_drift_with_both_sides(self) -> None:
        reads = matching_repo()
        reads["repos/baskingspot/r"]["has_wiki"] = True
        have = rs.read_repo(FakeApi(reads), "r")
        self.assertEqual(
            rs.diff(rs.want_repo(), have), [rs.Drift("fields.has_wiki", False, True)]
        )

    def test_an_unavailable_setting_is_not_drift(self) -> None:
        reads = matching_repo()
        base = "repos/baskingspot/r"
        reads[f"{base}/private-vulnerability-reporting"] = rs.ApiError("nope", 404)
        reads[f"{base}/code-scanning/default-setup"] = rs.ApiError("nope", 403)
        have = rs.read_repo(FakeApi(reads), "r")
        self.assertEqual(have["private_vulnerability_reporting"], rs.UNAVAILABLE)
        self.assertEqual(rs.diff(rs.want_repo(), have), [])

    def test_alerts_off_is_a_404_and_reads_as_false(self) -> None:
        reads = matching_repo()
        reads["repos/baskingspot/r/vulnerability-alerts"] = rs.ApiError("off", 404)
        have = rs.read_repo(FakeApi(reads), "r")
        self.assertIs(have["vulnerability_alerts"], False)
        self.assertEqual(
            rs.diff(rs.want_repo(), have),
            [rs.Drift("vulnerability_alerts", True, False)],
        )

    def test_a_server_error_is_not_swallowed(self) -> None:
        reads = matching_repo()
        reads["repos/baskingspot/r/automated-security-fixes"] = rs.ApiError("boom", 500)
        with self.assertRaises(rs.ApiError):
            rs.read_repo(FakeApi(reads), "r")


class ApplyTest(unittest.TestCase):
    def test_fields_and_analysis_go_in_one_patch_and_others_to_their_endpoints(
        self,
    ) -> None:
        api = FakeApi({})
        drifts = [
            rs.Drift("fields.has_wiki", False, True),
            rs.Drift("security_and_analysis.secret_scanning", "disabled", "enabled"),
            rs.Drift("private_vulnerability_reporting", True, False),
            rs.Drift("automated_security_fixes", False, True),
            rs.Drift("actions.sha_pinning_required", True, False),
        ]
        rs.apply_repo(api, "r", drifts)
        base = "repos/baskingspot/r"
        # One PATCH for the fields and the analysis, and one call per other
        # endpoint. The order between endpoints does not matter.
        self.assertEqual(
            api.writes[0],
            (
                "PATCH",
                base,
                {
                    "has_wiki": False,
                    "security_and_analysis": {
                        "secret_scanning": {"status": "disabled"}
                    },
                },
            ),
        )
        self.assertCountEqual(
            api.writes[1:],
            [
                ("PUT", f"{base}/private-vulnerability-reporting", None),
                ("DELETE", f"{base}/automated-security-fixes", None),
                ("PUT", f"{base}/actions/permissions", rs.CONFIG["repo"]["actions"]),
            ],
        )

    def test_pages_are_turned_off_by_deleting_the_site(self) -> None:
        api = FakeApi({})
        rs.apply_repo(api, "r", [rs.Drift("fields.has_pages", False, True)])
        self.assertEqual(api.writes, [("DELETE", "repos/baskingspot/r/pages", None)])

    def test_nothing_drifted_writes_nothing(self) -> None:
        api = FakeApi({})
        rs.apply_repo(api, "r", [])
        self.assertEqual(api.writes, [])

    def test_org_settings_patch_the_org_and_put_the_actions_policy(self) -> None:
        api = FakeApi({})
        rs.apply_org(
            api,
            [
                rs.Drift("fields.has_repository_projects", False, True),
                rs.Drift("actions.sha_pinning_required", True, False),
            ],
        )
        self.assertEqual(
            api.writes,
            [
                ("PATCH", "orgs/baskingspot", {"has_repository_projects": False}),
                (
                    "PUT",
                    "orgs/baskingspot/actions/permissions",
                    rs.CONFIG["org"]["actions"],
                ),
            ],
        )


class ConfigTest(unittest.TestCase):
    def test_every_security_setting_is_off_but_private_vulnerability_reporting(
        self,
    ) -> None:
        cfg = rs.CONFIG["repo"]
        self.assertEqual(set(cfg["security_and_analysis"].values()), {"disabled"})
        self.assertIs(cfg["automated_security_fixes"], False)
        self.assertIs(cfg["private_vulnerability_reporting"], True)
        self.assertEqual(cfg["code_scanning_default_setup"], "not-configured")

    def test_actions_must_be_pinned_at_both_levels(self) -> None:
        self.assertIs(rs.CONFIG["repo"]["actions"]["sha_pinning_required"], True)
        self.assertIs(rs.CONFIG["org"]["actions"]["sha_pinning_required"], True)

    def test_only_squash_merges_are_allowed(self) -> None:
        fields = rs.CONFIG["repo"]["fields"]
        self.assertIs(fields["allow_squash_merge"], True)
        self.assertIs(fields["allow_merge_commit"], False)
        self.assertIs(fields["allow_rebase_merge"], False)


if __name__ == "__main__":
    unittest.main()
