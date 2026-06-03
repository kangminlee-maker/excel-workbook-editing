from __future__ import annotations

import sys
from pathlib import Path
import unittest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dwd import DwdError, build_dwd_context, select_subject


class DwdTests(unittest.TestCase):
    def test_select_subject_uses_verified_user_principal(self) -> None:
        self.assertEqual(
            select_subject({"principal": "Pilot.User@day1company.co.kr"}),
            "pilot.user@day1company.co.kr",
        )

    def test_select_subject_rejects_missing_email_principal(self) -> None:
        with self.assertRaisesRegex(DwdError, "principal"):
            select_subject({"principal": "google-subject-1"})

    def test_build_dwd_context_keeps_service_account_and_scopes(self) -> None:
        context = build_dwd_context(
            service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
            verified_identity={"principal": "pilot.user@day1company.co.kr"},
            scopes=("https://www.googleapis.com/auth/spreadsheets.readonly",),
        )

        self.assertEqual(context.subject, "pilot.user@day1company.co.kr")
        self.assertEqual(
            context.service_account_email,
            "day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
        )
        self.assertEqual(
            context.scopes,
            ("https://www.googleapis.com/auth/spreadsheets.readonly",),
        )

    def test_build_dwd_context_rejects_missing_scope(self) -> None:
        with self.assertRaisesRegex(DwdError, "scope"):
            build_dwd_context(
                service_account_email="day1-mcp-wrapper@day1-dev.iam.gserviceaccount.com",
                verified_identity={"principal": "pilot.user@day1company.co.kr"},
                scopes=(),
            )


if __name__ == "__main__":
    unittest.main()
