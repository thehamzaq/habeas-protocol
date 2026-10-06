"""
Pure-Python reference evaluator for difc_third_party_disclosure.

Mirrors the Catala scope ThirdPartyDisclosureGates exactly: same input
field names (`element`, `made_out`, `rdc_condition`), same output field
names (`order_grantable`, `nph_made_out`, etc.), same gate semantics
(every required enum value must appear with `made_out=true`; duplicates
and over-pleading are tolerated; empty inputs reject).

This file ALSO provides the legacy `third_party_disclosure` function used
by trace-07's evaluator (that function takes a different shape — `label`
and `satisfied` plus respondents/windows — and is retained for the
trace's narrative-friendly inputs). The two functions are separate
APIs; the rule-library conformance test exercises the Catala-mirroring
function (`third_party_disclosure_gates`).
"""

from typing import List


# ---------------------------------------------------------------------
# Catala-mirroring evaluator (the rule-library API).
# ---------------------------------------------------------------------

NPH_REQUIRED_ELEMENTS = (
    "NPE_WrongEstablished",
    "NPE_RespondentMixedUp",
    "NPE_PossessesInformation",
    "NPE_DisclosureNecessaryInInterestsOfJustice",
)
BT_REQUIRED_ELEMENTS = (
    "BTE_TracingClaimAsserted",
    "BTE_HoldsTraceableProceeds",
    "BTE_DisclosureNecessaryForTracing",
)
RDC_REQUIRED_CONDITIONS = (
    "RDC_LikelyToSupportOrAffect",
    "RDC_NecessaryToDisposeOrSaveCosts",
)


def _all_required_made_out(findings, key, required):
    """True iff every value in `required` appears with field
    `made_out=True` somewhere in `findings` (where each finding has
    the discriminant under `key`). Empty inputs reject. A finding
    recorded twice with opposite values is an error, not a pass."""
    seen = {}
    for f in findings:
        made_out = f.get("made_out")
        if not isinstance(made_out, bool):
            raise ValueError(
                f"made_out must be true or false for {f.get(key)!r}, got {made_out!r}")
        if seen.setdefault(f.get(key), made_out) != made_out:
            raise ValueError(f"contradictory findings for {f.get(key)!r}")
    return all(seen.get(r) is True for r in required)


def third_party_disclosure_gates(
    nph_findings: List[dict],
    bt_findings: List[dict],
    rdc_findings: List[dict],
) -> dict:
    """Mirrors Catala scope ThirdPartyDisclosureGates.

    Inputs:
      nph_findings: list of {element: NorwichPharmacalElement, made_out: bool}
      bt_findings:  list of {element: BankersTrustElement,     made_out: bool}
      rdc_findings: list of {rdc_condition: RDC2852Condition,  made_out: bool}

    Output mirrors the Catala DisclosureGates struct.
    """
    nph = _all_required_made_out(nph_findings, "element", NPH_REQUIRED_ELEMENTS)
    bt = _all_required_made_out(bt_findings, "element", BT_REQUIRED_ELEMENTS)
    rdc = _all_required_made_out(rdc_findings, "rdc_condition", RDC_REQUIRED_CONDITIONS)
    all_gates = nph and bt and rdc
    return {
        "nph_made_out": nph,
        "bankers_trust_made_out": bt,
        "rdc_2852_made_out": rdc,
        "all_gates_satisfied": all_gates,
        # The three routes are independent: any one made out is a basis
        # for the order (a threshold; the relief stays discretionary).
        "order_grantable": nph or bt or rdc,
    }


# ---------------------------------------------------------------------
# Legacy trace-07 evaluator (NOT a Catala mirror — narrative inputs
# with respondents and compliance windows). Retained for trace-07's
# evaluate.py.
# ---------------------------------------------------------------------

def third_party_disclosure(
    norwich_pharmacal_elements: List[dict],
    bankers_trust_elements: List[dict],
    rdc_2852_conditions: List[dict],
    respondents: List[dict],
    compliance_windows: dict,
) -> dict:
    """Trace-07 narrative evaluator. Accepts {label, satisfied} list
    items and emits trace-friendly output including respondents and
    compliance windows. NOT a Catala mirror — see
    third_party_disclosure_gates above for that.
    """
    def _gate(items):
        for x in items:
            if not isinstance(x["satisfied"], bool):
                raise ValueError(
                    f"satisfied must be true or false, got {x['satisfied']!r}")
        return len(items) > 0 and all(x["satisfied"] for x in items)

    nph = _gate(norwich_pharmacal_elements)
    bt = _gate(bankers_trust_elements)
    rdc = _gate(rdc_2852_conditions)
    all_gates = nph and bt and rdc

    n_resp = len(respondents)
    n_opposing = sum(1 for r in respondents
                     if r.get("opposes_substance", False))

    return {
        "nph_made_out": nph,
        "bankers_trust_made_out": bt,
        "rdc_2852_made_out": rdc,
        "all_gates_satisfied": all_gates,
        "order_granted": all_gates,
        "n_respondents": n_resp,
        "n_respondents_opposing_substance": n_opposing,
        "information_window_days":
            compliance_windows.get("information_confirmation_days"),
        "documents_window_days":
            compliance_windows.get("documents_production_days"),
    }


__all__ = ["third_party_disclosure_gates", "third_party_disclosure"]
