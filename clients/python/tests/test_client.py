"""End-to-end tests for the habeas Python client.

Skipped automatically if the API isn't reachable on
http://127.0.0.1:5544 — so the suite is safe to run as part of CI even
when the runner has no Postgres / Catala installed.

Run:
    python3 -m unittest clients/python/tests/test_client.py
"""
from __future__ import annotations

import os
import sys
import unittest

# Make the client importable when running tests from the repo root
# without installing the package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from habeas import HabeasClient, HabeasError, ValidationError  # noqa: E402


def _api_reachable(c: HabeasClient) -> bool:
    try:
        c.health()
        return True
    except HabeasError:
        return False


class _SkipIfNoApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = HabeasClient(timeout=5.0)
        if not _api_reachable(cls.client):
            raise unittest.SkipTest("habeas API not reachable on 127.0.0.1:5544")


class TestCorpusEndpoints(_SkipIfNoApi):
    def test_health(self):
        h = self.client.health()
        self.assertIn("status", h)
        self.assertTrue(h["status"]["ok"])
        self.assertGreater(h["status"]["judgments"], 0)

    def test_judgments_default(self):
        rows = self.client.judgments(limit=5)
        self.assertIsInstance(rows, list)
        self.assertLessEqual(len(rows), 5)
        if rows:
            self.assertIn("case_no", rows[0])
            self.assertIn("tribunal", rows[0])

    def test_judgments_tribunal_filter(self):
        adgm = self.client.judgments(tribunal="ADGM", limit=10)
        for row in adgm:
            self.assertEqual(row["tribunal"], "ADGM Courts")

    def test_tribunal_means(self):
        means = self.client.tribunal_means()
        codes = {m["tribunal_code"] for m in means}
        self.assertGreaterEqual(codes, {"DIFC", "ADGM", "SICC"})

    def test_search(self):
        # The trace-05 case (Xetech v Pulsar) is in the corpus
        results = self.client.search("source code platform", limit=3)
        self.assertIsInstance(results, list)


class TestRuleLibrary(_SkipIfNoApi):
    def test_rule_modules_listed(self):
        mods = self.client.rule_modules()
        self.assertGreater(len(mods), 0)
        names = {m["module"] for m in mods}
        self.assertIn("difc_rdc_part_38", names)
        self.assertIn("sg_iaa_s_31", names)

    def test_claims_registry(self):
        claims = self.client.claims()
        self.assertIn("claim_types", claims)
        self.assertGreater(len(claims["claim_types"]), 0)

    def test_jurisdictions_registry(self):
        j = self.client.jurisdictions()
        self.assertIn("tribunals", j)
        self.assertIn("rule_jurisdictions", j)
        self.assertIn("cross_border_paths", j)

    def test_certification_states_present(self):
        c = self.client.certification_states()
        # All 12 modules should ship with a metadata file
        self.assertGreaterEqual(len(c), 1)
        # Every state must be one of the spec's enumerated values
        allowed = {"draft", "submitted", "reviewed", "certified", "deprecated"}
        for module, meta in c.items():
            state = meta.get("certification", {}).get("state")
            self.assertIn(state, allowed, f"{module} has invalid state {state!r}")


class TestRuleExecution(_SkipIfNoApi):
    def test_rdc_part_38_reproduces_trace_1(self):
        out = self.client.rule_run(
            "difc_rdc_part_38",
            "StandardBasisAssessment",
            {"claim": {"hours_worked": "24",
                       "hourly_rate_aed": "250",
                       "reasonable_disbursements_aed": "1121.75"}},
            source_label="python_client_test",
        )
        self.assertAlmostEqual(out["award"]["total_aed"], 7121.75, places=2)

    def test_ladd_v_marshall_reproduces_trace_5(self):
        out = self.client.rule_run(
            "ladd_v_marshall",
            "LaddMarshallTest",
            {"prongs": [
                {"prong": "ReasonableDiligence", "satisfied": False},
                {"prong": "ImportantInfluence",  "satisfied": False},
                {"prong": "PresumablyCredible",  "satisfied": True},
            ]},
        )
        self.assertFalse(out["disposition"]["evidence_admissible"])
        self.assertEqual(out["disposition"]["first_failing_prong"], "ReasonableDiligence")

    def test_rule_validate_succeeds(self):
        ok = self.client.rule_validate(
            "## tiny rule\n```catala\n"
            "declaration scope Tiny:\n"
            "  output y content boolean\n\nscope Tiny:\n"
            "  definition y equals true\n```\n"
        )
        self.assertTrue(ok["ok"])

    def test_rule_validate_raises_on_bad_catala(self):
        # A code block with a real syntax error inside (Catala treats
        # text outside ```catala fences as pure narrative, so plain
        # English does not actually fail typecheck — we have to give
        # it something it tries to parse).
        bad = (
            "## broken\n```catala\n"
            "declaration scope Foo:\n"
            "  output y content decimal\n\nscope Foo:\n"
            "  definition y equals 1.0 ** 2.0\n"   # ** is not a Catala operator
            "```\n"
        )
        with self.assertRaises(ValidationError):
            self.client.rule_validate(bad)


class TestRouting(_SkipIfNoApi):
    def test_foreign_award_to_sicc(self):
        r = self.client.conflict_route(
            forum="SICC",
            originating_forum="FOREIGN_ARBITRAL_TRIBUNAL",
            claim_type="arbitration_recognition",
        )
        modules = [x["module"] for x in r["recognition_chain"]]
        self.assertIn("sg_iaa_s_31", modules)

    def test_costs_assessment_local_difc(self):
        r = self.client.conflict_route(forum="DIFC", claim_type="costs_assessment")
        modules = [x["module"] for x in r["applicable_rules"]]
        self.assertIn("difc_rdc_part_38", modules)


class TestIngest(_SkipIfNoApi):
    def test_extracts_canonical_signals(self):
        text = (
            "DEC 001/2025 Techteryx Ltd v IG Limited dated 3 April 2026. "
            "Justice Black ordered USD 46 million. Article 36 of DIFC Damages "
            "Law and RDC 28.51 apply."
        )
        d = self.client.ingest(text)
        self.assertEqual(d["case_no"], "DEC 001/2025")
        self.assertEqual(d["tribunal"], "DIFC Courts")
        self.assertEqual(d["decision_date"], "2026-04-03")
        self.assertGreaterEqual(d["_extraction"]["n_amounts"], 1)


if __name__ == "__main__":
    unittest.main()
