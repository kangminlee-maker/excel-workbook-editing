from __future__ import annotations

import json
import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from auth import AuthConfig
from workload_identity import build_readiness_summary


class WorkloadIdentityReadinessTests(unittest.TestCase):
    def test_readiness_summary_contains_no_sensitive_identity_value(self) -> None:
        summary = build_readiness_summary(
            {
                "auth_config": AuthConfig(
                    accepted_issuers=("https://accounts.google.com",),
                    audience="broker-client-id",
                    accepted_audiences=("broker-client-id", "mcp-client-id"),
                    hosted_domain="day1company.co.kr",
                ),
                "policy": {"version": "test", "principals": {}},
                "service_account_email": "runtime-delegated@example.iam.gserviceaccount.com",
            }
        )

        serialized = json.dumps(summary, sort_keys=True)
        self.assertTrue(summary["ready"])
        self.assertEqual(summary["authority_mode"], "workload_identity")
        self.assertEqual(summary["delegation_mode"], "domain_wide_delegation")
        self.assertEqual(summary["accepted_audience_count"], 2)
        self.assertTrue(summary["hosted_domain_required"])
        self.assertNotIn("runtime-delegated", serialized)

    def test_readiness_summary_marks_missing_policy_as_not_ready(self) -> None:
        summary = build_readiness_summary(
            {
                "auth_config": AuthConfig(
                    accepted_issuers=("https://accounts.google.com",),
                    audience="broker-client-id",
                    accepted_audiences=("broker-client-id",),
                ),
                "policy": None,
                "service_account_email": "runtime-delegated@example.iam.gserviceaccount.com",
            }
        )

        self.assertFalse(summary["ready"])
        self.assertFalse(summary["configured"]["broker_policy"])

    def test_readiness_summary_uses_primary_audience_when_no_extra_audiences(self) -> None:
        summary = build_readiness_summary(
            {
                "auth_config": AuthConfig(
                    accepted_issuers=("https://accounts.google.com",),
                    audience="broker-client-id",
                ),
                "policy": {"version": "test", "principals": {}},
                "service_account_email": "runtime-delegated@example.iam.gserviceaccount.com",
            }
        )

        self.assertTrue(summary["configured"]["accepted_audiences"])
        self.assertEqual(summary["accepted_audience_count"], 1)


if __name__ == "__main__":
    unittest.main()
