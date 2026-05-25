"""
Azure Function: KN Lane Risk Sentinel — backend tools
=====================================================

Four HTTP endpoints, all wired into the Foundry agent via OpenAPI:

  1. POST /api/calculate_reroute        — pure compute, no side-effects
  2. POST /api/send_approval_email      — Graph sendMail (visible action)
  3. POST /api/create_planner_task      — Graph Planner createTask (visible action)
  4. POST /api/log_decision_sharepoint  — Graph Lists API addItem (visible action)

Endpoints 2-4 authenticate to Microsoft Graph using the Function App's
System-Assigned Managed Identity. Required Graph application permissions
(admin consent required):
  - Mail.Send
  - Group.ReadWrite.All  (Planner sits under Groups)
  - Sites.ReadWrite.All

Demo IDs are read from App Settings:
  GRAPH_MAIL_FROM       UPN of mailbox that sends approval mails
  GRAPH_MAIL_TO         comma-separated recipient list
  GRAPH_PLANNER_PLAN    Planner plan ID for the demo
  GRAPH_PLANNER_BUCKET  Planner bucket ID for new tasks
  GRAPH_SP_SITE         SharePoint site ID (host,siteId,webId triple)
  GRAPH_SP_LIST         SharePoint list ID
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

import azure.functions as func
import httpx
from azure.identity import DefaultAzureCredential

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)
log = logging.getLogger("kn-sentinel")

GRAPH = "https://graph.microsoft.com/v1.0"
_credential = DefaultAzureCredential()


def _graph_token() -> str:
    return _credential.get_token("https://graph.microsoft.com/.default").token


def _graph_post(path: str, payload: dict[str, Any]) -> httpx.Response:
    token = _graph_token()
    url = f"{GRAPH}{path}"
    with httpx.Client(timeout=30.0) as client:
        return client.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
        )


def _json_response(body: dict[str, Any], status: int = 200) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps(body),
        mimetype="application/json",
        status_code=status,
    )


def _err(reason: str, detail: Any = None, status: int = 502) -> func.HttpResponse:
    return _json_response({"error": reason, "detail": detail}, status=status)


# ---------------------------------------------------------------------------
# 1. calculate_reroute — deterministic compute, no Graph
# ---------------------------------------------------------------------------

@app.function_name(name="calculate_reroute")
@app.route(route="calculate_reroute", methods=["POST"])
def calculate_reroute(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_json() if req.get_body() else {}
    origin = body.get("origin", "SHA")
    destination = body.get("destination", "HAM")
    current_carrier = body.get("current_carrier", "CMA")

    markdown = f"""**Reroute Recommendation: {origin} -> {destination}**

| | Current lane | Recommended reroute |
|---|---|---|
| Carrier | {current_carrier} (CMA CGM) | **HMM** |
| Transit time | 32 days (blocked) | 34.5 days |
| Cost per TEU | EUR 4,200 | EUR 4,350 (+3.6%) |
| Reliability | 78% (disrupted) | 84% |
| Risk score | 87/100 (HIGH) | 22/100 (LOW) |

**Recommendation:** Switch to **HMM** for the 18 TEU exposed to Typhoon Mawar.
Net impact: +2.5 days transit, +EUR 150/TEU, but avoids 8-12 day demurrage risk
at Shanghai. Estimated savings vs do-nothing: **EUR 47,000**.

_Source: KN TMS routing service (deterministic demo fixture)._
"""

    return _json_response({"markdown": markdown})


# ---------------------------------------------------------------------------
# 2. send_approval_email — Graph sendMail
# ---------------------------------------------------------------------------

@app.function_name(name="send_approval_email")
@app.route(route="send_approval_email", methods=["POST"])
def send_approval_email(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_json() if req.get_body() else {}
    shipment_id = body.get("shipment_id", "CMA-2847")
    new_carrier = body.get("new_carrier", "HMM")
    savings_eur = int(body.get("savings_eur", 47000))
    rationale = body.get("rationale", "Avoid Typhoon Mawar demurrage exposure.")

    mail_from = os.environ.get("GRAPH_MAIL_FROM")
    mail_to_raw = os.environ.get("GRAPH_MAIL_TO", mail_from or "")
    if not mail_from:
        return _err("missing_config", "GRAPH_MAIL_FROM not set", status=500)
    recipients = [
        {"emailAddress": {"address": a.strip()}}
        for a in mail_to_raw.split(",") if a.strip()
    ]

    subject = f"[Lane Risk Sentinel] Approval required: reroute {shipment_id} -> {new_carrier}"
    html_body = f"""
    <div style="font-family:Segoe UI,sans-serif;max-width:560px;">
      <h2 style="color:#005EB8;margin:0 0 12px;">Reroute approval requested</h2>
      <p>The Lane Risk Sentinel agent recommends rerouting
         <strong>{shipment_id}</strong> via <strong>{new_carrier}</strong>.</p>
      <table style="border-collapse:collapse;width:100%;font-size:14px;">
        <tr><td style="padding:6px 8px;background:#f3f6fb;"><strong>Shipment</strong></td>
            <td style="padding:6px 8px;">{shipment_id}</td></tr>
        <tr><td style="padding:6px 8px;background:#f3f6fb;"><strong>New carrier</strong></td>
            <td style="padding:6px 8px;">{new_carrier}</td></tr>
        <tr><td style="padding:6px 8px;background:#f3f6fb;"><strong>Estimated savings vs no-action</strong></td>
            <td style="padding:6px 8px;"><strong>EUR {savings_eur:,}</strong></td></tr>
        <tr><td style="padding:6px 8px;background:#f3f6fb;"><strong>Rationale</strong></td>
            <td style="padding:6px 8px;">{rationale}</td></tr>
      </table>
      <p style="margin-top:18px;">
        <a href="https://m365.cloud.microsoft/chat" style="background:#005EB8;color:#fff;padding:10px 18px;text-decoration:none;border-radius:4px;">Approve in Copilot</a>
        &nbsp;
        <a href="https://m365.cloud.microsoft/chat" style="background:#fff;color:#005EB8;border:1px solid #005EB8;padding:10px 18px;text-decoration:none;border-radius:4px;">Reject</a>
      </p>
      <p style="color:#666;font-size:12px;margin-top:24px;">
        Audit ID: {datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')} -
        sent by KN Lane Risk Sentinel (Foundry agent).
      </p>
    </div>
    """

    payload = {
        "message": {
            "subject": subject,
            "body": {"contentType": "HTML", "content": html_body},
            "toRecipients": recipients,
        },
        "saveToSentItems": True,
    }

    try:
        resp = _graph_post(f"/users/{mail_from}/sendMail", payload)
    except Exception as exc:  # noqa: BLE001
        log.exception("Graph sendMail failed")
        return _err("graph_error", str(exc))

    if resp.status_code >= 300:
        return _err("graph_status", {"status": resp.status_code, "body": resp.text})

    return _json_response({
        "markdown": (
            f"OK - approval e-mail dispatched for **{shipment_id}** "
            f"(new carrier **{new_carrier}**). Recipients: {len(recipients)}. "
            f"Receipt: Graph sendMail accepted at "
            f"{datetime.now(timezone.utc).isoformat()}."
        ),
        "shipment_id": shipment_id,
        "new_carrier": new_carrier,
        "recipients": [r["emailAddress"]["address"] for r in recipients],
        "graph_status": resp.status_code,
    })


# ---------------------------------------------------------------------------
# 3. create_planner_task — Graph Planner createTask
# ---------------------------------------------------------------------------

@app.function_name(name="create_planner_task")
@app.route(route="create_planner_task", methods=["POST"])
def create_planner_task(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_json() if req.get_body() else {}
    shipment_id = body.get("shipment_id", "CMA-2847")
    new_carrier = body.get("new_carrier", "HMM")
    savings_eur = int(body.get("savings_eur", 47000))
    notes = body.get("notes", "")

    plan_id = os.environ.get("GRAPH_PLANNER_PLAN")
    bucket_id = os.environ.get("GRAPH_PLANNER_BUCKET")
    if not plan_id or not bucket_id:
        return _err("missing_config", "GRAPH_PLANNER_PLAN / GRAPH_PLANNER_BUCKET not set", status=500)

    title = f"Reroute approval: {shipment_id} -> {new_carrier} (EUR {savings_eur:,})"
    payload = {
        "planId": plan_id,
        "bucketId": bucket_id,
        "title": title,
        "priority": 3,  # urgent
    }

    try:
        resp = _graph_post("/planner/tasks", payload)
    except Exception as exc:  # noqa: BLE001
        log.exception("Graph createTask failed")
        return _err("graph_error", str(exc))

    if resp.status_code >= 300:
        return _err("graph_status", {"status": resp.status_code, "body": resp.text})

    task = resp.json()
    task_id = task.get("id", "")

    # Attach a description as task details (best-effort, non-fatal).
    description = (
        f"Recommended by Lane Risk Sentinel.\n\n"
        f"Shipment: {shipment_id}\n"
        f"New carrier: {new_carrier}\n"
        f"Estimated savings vs no-action: EUR {savings_eur:,}\n\n"
        f"{notes}\n\n"
        f"Audit timestamp (UTC): {datetime.now(timezone.utc).isoformat()}"
    )
    try:
        token = _graph_token()
        with httpx.Client(timeout=15.0) as client:
            details_url = f"{GRAPH}/planner/tasks/{task_id}/details"
            g = client.get(details_url, headers={"Authorization": f"Bearer {token}"})
            etag = g.headers.get("ETag")
            if not etag and g.status_code < 300:
                etag = g.json().get("@odata.etag")
            if etag:
                client.patch(
                    details_url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "If-Match": etag,
                    },
                    json={"description": description},
                )
    except Exception:  # noqa: BLE001
        log.warning("Could not patch planner task details", exc_info=True)

    return _json_response({
        "markdown": (
            f"OK - Planner task created for **{shipment_id} -> {new_carrier}**. "
            f"Task ID `{task_id}`. Open it in Planner to approve / assign."
        ),
        "task_id": task_id,
        "title": title,
    })


# ---------------------------------------------------------------------------
# 4. log_decision_sharepoint — Graph Lists addItem
# ---------------------------------------------------------------------------

@app.function_name(name="log_decision_sharepoint")
@app.route(route="log_decision_sharepoint", methods=["POST"])
def log_decision_sharepoint(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_json() if req.get_body() else {}
    shipment_id = body.get("shipment_id", "CMA-2847")
    old_carrier = body.get("old_carrier", "CMA")
    new_carrier = body.get("new_carrier", "HMM")
    risk_before = int(body.get("risk_before", 87))
    risk_after = int(body.get("risk_after", 22))
    savings_eur = int(body.get("savings_eur", 47000))
    rationale = body.get("rationale", "Avoid Typhoon Mawar demurrage exposure.")

    site_id = os.environ.get("GRAPH_SP_SITE")
    list_id = os.environ.get("GRAPH_SP_LIST")
    if not site_id or not list_id:
        return _err("missing_config", "GRAPH_SP_SITE / GRAPH_SP_LIST not set", status=500)

    fields = {
        "Title": f"{shipment_id}: {old_carrier} -> {new_carrier}",
        "Shipment": shipment_id,
        "OldCarrier": old_carrier,
        "NewCarrier": new_carrier,
        "RiskBefore": risk_before,
        "RiskAfter": risk_after,
        "SavingsEUR": savings_eur,
        "Rationale": rationale,
        "DecidedAt": datetime.now(timezone.utc).isoformat(),
        "DecidedBy": "Lane Risk Sentinel (Foundry agent)",
    }
    payload = {"fields": fields}

    try:
        resp = _graph_post(f"/sites/{site_id}/lists/{list_id}/items", payload)
    except Exception as exc:  # noqa: BLE001
        log.exception("Graph addItem failed")
        return _err("graph_error", str(exc))

    if resp.status_code >= 300:
        return _err("graph_status", {"status": resp.status_code, "body": resp.text})

    item = resp.json()
    item_id = item.get("id", "")
    web_url = item.get("webUrl", "")
    return _json_response({
        "markdown": (
            f"OK - decision logged to SharePoint. "
            f"List item `{item_id}` for shipment **{shipment_id}** "
            f"(reroute **{old_carrier} -> {new_carrier}**, savings EUR {savings_eur:,})."
        ),
        "item_id": item_id,
        "web_url": web_url,
        "fields": fields,
    })


# ---------------------------------------------------------------------------
# 5. _bootstrap_sharepoint_list — one-shot, idempotent infra helper
#    Creates the RerouteDecisions list with all custom columns on the
#    supplied SharePoint site using the Function App's MI (which holds
#    Sites.ReadWrite.All). Returns the list ID for the App Settings.
# ---------------------------------------------------------------------------

@app.function_name(name="bootstrap_sharepoint_list")
@app.route(route="_bootstrap_sharepoint_list", methods=["POST"])
def bootstrap_sharepoint_list(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_json() if req.get_body() else {}
    site_id = body.get("site_id") or os.environ.get("GRAPH_SP_SITE")
    list_name = body.get("list_name", "RerouteDecisions")
    if not site_id:
        return _err("missing_param", "site_id required", status=400)

    token = _graph_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Idempotency: return existing list if present.
    with httpx.Client(timeout=30.0) as client:
        existing = client.get(
            f"{GRAPH}/sites/{site_id}/lists?$filter=displayName eq '{list_name}'",
            headers={"Authorization": f"Bearer {token}"},
        )
        if existing.status_code < 300 and existing.json().get("value"):
            lst = existing.json()["value"][0]
            return _json_response({
                "status": "already_exists",
                "list_id": lst["id"],
                "web_url": lst.get("webUrl"),
            })

        list_payload = {
            "displayName": list_name,
            "description": "KN Lane Risk Sentinel decision audit log",
            "list": {"template": "genericList"},
            "columns": [
                {"name": "Shipment",    "text": {}},
                {"name": "OldCarrier",  "text": {}},
                {"name": "NewCarrier",  "text": {}},
                {"name": "RiskBefore",  "number": {}},
                {"name": "RiskAfter",   "number": {}},
                {"name": "SavingsEUR",  "number": {}},
                {"name": "Rationale",   "text": {"allowMultipleLines": True}},
                {"name": "DecidedAt",   "dateTime": {}},
                {"name": "DecidedBy",   "text": {}},
            ],
        }
        created = client.post(
            f"{GRAPH}/sites/{site_id}/lists", headers=headers, json=list_payload
        )
        if created.status_code >= 300:
            return _err("graph_status", {"status": created.status_code, "body": created.text})
        lst = created.json()
        return _json_response({
            "status": "created",
            "list_id": lst["id"],
            "web_url": lst.get("webUrl"),
        })
