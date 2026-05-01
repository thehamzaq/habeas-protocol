"""Habeas Protocol — Python client.

Thin wrapper around the local API at http://127.0.0.1:5544. Stdlib-only
by default (urllib.request); optionally uses `requests` if installed.

Quick start:

    from habeas import HabeasClient
    c = HabeasClient()
    print(c.health())
    print(c.tribunal_means())
    out = c.rule_run("difc_rdc_part_38", "StandardBasisAssessment", {
        "claim": {
            "hours_worked": "24",
            "hourly_rate_aed": "250",
            "reasonable_disbursements_aed": "1121.75",
        },
    })
    print(out["award"]["total_aed"])  # → 7121.75

The full endpoint list is documented at api/openapi.yaml.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

__all__ = ["HabeasClient", "HabeasError", "ValidationError", "AdminModeRequired"]
__version__ = "0.1.0"


class HabeasError(Exception):
    """Base for all client-side errors raised by HabeasClient."""

    def __init__(self, message: str, *, status: int | None = None, payload: Any = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


class ValidationError(HabeasError):
    """Raised when /api/rule_validate returns ok=False or a 4xx."""


class AdminModeRequired(HabeasError):
    """Raised when /api/rule_save is called against a non-admin server."""


class HabeasClient:
    """Client for the Habeas Protocol API.

    Parameters
    ----------
    base_url:
        Root URL of the API. Defaults to ``http://127.0.0.1:5544``.
    timeout:
        Per-request timeout in seconds.
    user_agent:
        Sent as the ``User-Agent`` header.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:5544",
        *,
        timeout: float = 30.0,
        user_agent: str = f"habeas-python/{__version__}",
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.user_agent = user_agent

    # ----- internal HTTP helpers -----

    def _request(self, method: str, path: str, *,
                 params: dict[str, Any] | None = None,
                 body: Any = None) -> Any:
        url = self.base_url + path
        if params:
            qs = urllib.parse.urlencode(
                {k: v for k, v in params.items() if v is not None},
                doseq=True,
            )
            if qs:
                url = url + ("&" if "?" in url else "?") + qs
        data: bytes | None = None
        headers = {"User-Agent": self.user_agent, "Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                raw = r.read()
        except urllib.error.HTTPError as e:
            raw = e.read()
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"error": raw.decode("utf-8", errors="replace")}
            err_msg = payload.get("error") if isinstance(payload, dict) else str(payload)
            if e.code == 500 and isinstance(err_msg, str) and "save-back is disabled" in err_msg:
                raise AdminModeRequired(err_msg, status=e.code, payload=payload) from e
            raise HabeasError(f"HTTP {e.code}: {err_msg}", status=e.code, payload=payload) from e
        except urllib.error.URLError as e:
            raise HabeasError(f"could not reach {url}: {e.reason}") from e
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            raise HabeasError(f"non-JSON response from {url}: {e}") from e

    def _get(self, path: str, **params: Any) -> Any:
        return self._request("GET", path, params=params)

    def _post(self, path: str, body: Any) -> Any:
        return self._request("POST", path, body=body)

    # ----- corpus -----

    def health(self) -> dict[str, Any]:
        """GET /api/health — Postgres reachability + judgment count."""
        return self._get("/api/health")

    def judgments(self, *, tribunal: str | None = None, limit: int = 500) -> list[dict]:
        """GET /api/judgments — list coded judgments (mirrors data/judgments.json)."""
        return self._get("/api/judgments", tribunal=tribunal, limit=limit)

    def rules(self, *, limit: int = 20) -> list[dict]:
        """GET /api/rules — top-cited instruments across the corpus."""
        return self._get("/api/rules", limit=limit)

    def tribunal_means(self) -> list[dict]:
        """GET /api/tribunal_means — paper-headline means."""
        return self._get("/api/tribunal_means")

    def search(self, q: str, *, limit: int = 10) -> list[dict]:
        """GET /api/search — full-text search over extracted document text."""
        return self._get("/api/search", q=q, limit=limit)

    # ----- rule library + routing metadata -----

    def rule_modules(self) -> list[dict]:
        """GET /api/rule_modules — every rule module + scope + schema pointer."""
        return self._get("/api/rule_modules")

    def claims(self) -> dict:
        """GET /api/claims — claim-type → applicable rules registry."""
        return self._get("/api/claims")

    def jurisdictions(self) -> dict:
        """GET /api/jurisdictions — multi-jurisdiction routing data."""
        return self._get("/api/jurisdictions")

    def certification_states(self) -> dict[str, dict]:
        """GET /api/certification_states — per-module certification state."""
        return self._get("/api/certification_states")

    def certification_spec(self) -> dict:
        """GET /api/certification_spec — the certification YAML."""
        return self._get("/api/certification_spec")

    # ----- audit log -----

    def runs_recent(self, *, limit: int = 50) -> list[dict]:
        """GET /api/runs/recent — recent rule_run rows (slim)."""
        return self._get("/api/runs/recent", limit=limit)

    def runs_stats(self) -> list[dict]:
        """GET /api/runs/stats — per-(module, scope) audit-log aggregates."""
        return self._get("/api/runs/stats")

    # ----- rule execution -----

    def rule_run(
        self,
        module: str,
        scope: str,
        inputs: dict,
        *,
        source_label: str | None = None,
    ) -> dict:
        """POST /api/rule_run — run a rule module's scope over inputs.

        Writes an audit-log row regardless of success/failure. Module
        and scope names are alphabet-restricted server-side.
        """
        body: dict[str, Any] = {"module": module, "scope": scope, "inputs": inputs}
        if source_label is not None:
            body["source_label"] = source_label
        return self._post("/api/rule_run", body)

    def rule_validate(self, source: str) -> dict:
        """POST /api/rule_validate — typecheck + interpret arbitrary Catala source.

        Raises ``ValidationError`` if the response is not {ok: True}.
        Use ``rule_validate_raw`` to inspect the failure reason directly.
        """
        res = self.rule_validate_raw(source)
        if not res.get("ok"):
            stage = res.get("stage", "unknown")
            errors = res.get("errors", "")
            raise ValidationError(f"validation failed (stage={stage}): {errors}", payload=res)
        return res

    def rule_validate_raw(self, source: str) -> dict:
        """POST /api/rule_validate — raw response (no exception on ok=False)."""
        return self._post("/api/rule_validate", {"source": source})

    def rule_save(self, filename: str, source: str) -> dict:
        """POST /api/rule_save — admin-mode-only save-back to rules/<filename>.

        Server must be started with ``HABEAS_ADMIN_MODE=1``. Raises
        ``AdminModeRequired`` otherwise.
        """
        return self._post("/api/rule_save", {"filename": filename, "source": source})

    # ----- ingestion + conflict-of-laws -----

    def ingest(self, text: str) -> dict:
        """POST /api/ingest — heuristic regex sweep over pasted text/HTML."""
        return self._post("/api/ingest", {"text": text})

    def conflict_route(
        self,
        *,
        forum: str,
        claim_type: str | None = None,
        originating_forum: str | None = None,
        governing_law: str | None = None,
    ) -> dict:
        """POST /api/conflict_route — multi-jurisdiction routing resolver."""
        body: dict[str, Any] = {"forum": forum}
        if claim_type is not None:
            body["claim_type"] = claim_type
        if originating_forum is not None:
            body["originating_forum"] = originating_forum
        if governing_law is not None:
            body["governing_law"] = governing_law
        return self._post("/api/conflict_route", body)
