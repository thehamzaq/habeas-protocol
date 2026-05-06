"""
Pure-Python reference evaluator for adgm_cpr_admissions.

Mirrors the Catala scope AdmissionsAndSetOff. ADGM Court Procedure
Rules 2016 Rule 42 (admissions and withdrawal) + Civil Evidence
Regulations §§ 181–182 (set-off):

    admissions_total = sum admitted items
    counterclaim_total = sum proven counterclaim items
    signed_net = admissions_total - counterclaim_total
    net_to_claimant = max(signed_net, 0)
    counterclaim_surplus = max(-signed_net, 0)

The clamp on net_to_claimant reflects the doctrinal point that the
admissions framework gives the *claimant* the right to judgment for
admitted sums net of any proven counterclaim set-off; if the
counterclaim exceeds the admissions, the surplus is the defendant's
counterclaim issue, a separate matter. The raw signed difference is
exposed in `signed_net_aed`.
"""

from decimal import Decimal


def _D(x) -> Decimal:
    return Decimal(str(x))


def admissions_and_set_off(admitted_items: list, counterclaim_items: list) -> dict:
    admitted_total = sum((_D(a["admitted_aed"]) for a in admitted_items), _D(0))
    counter_total = sum((_D(c["proven_aed"]) for c in counterclaim_items), _D(0))
    signed_net = admitted_total - counter_total
    net_to_claimant = signed_net if signed_net > _D(0) else _D("0.00")
    surplus = -signed_net if signed_net < _D(0) else _D("0.00")
    return {
        "admissions_total_aed": admitted_total,
        "counterclaim_total_aed": counter_total,
        "net_to_claimant_aed": net_to_claimant,
        "signed_net_aed": signed_net,
        "counterclaim_exceeds_admissions": signed_net < _D("0.00"),
        "counterclaim_surplus_aed": surplus,
    }


__all__ = ["admissions_and_set_off"]
