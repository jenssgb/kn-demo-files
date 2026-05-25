# Power Automate Flow: LRS-OnApprove
**Purpose:** Handle the human response to the Lane Risk Sentinel approval Adaptive Card. Called by the agent after `send_approval_card`. Runs the on-approve / on-reject / on-timeout branches per Lane Risk Playbook Section 2.

**Connectors used:** Microsoft Teams, Outlook 365, Dataverse, Microsoft 365 Approvals, Power BI (optional dashboard refresh).

---

## Trigger

**When a HTTP request is received** (called from the agent via the *HTTP Request* action) OR **When an Adaptive Card response is received** (Teams trigger).

**Body schema:**
```json
{
  "action": "approve | reject | modify",
  "shipmentId": "CMA-2847",
  "proposalId": "ALT-010",
  "decisionRef": "LRS-2026-2847",
  "respondedBy": "leila.gharani@kn.com",
  "respondedAtUtc": "2026-02-13T15:08:42Z",
  "modifyAction": null,
  "reason": null
}
```

---

## Branches

### Switch on `action`

#### Branch: APPROVE
1. **Get proposal details** - Dataverse `Get a row` on `LRS_RoutingProposals` filtered by `proposalId`.
2. **Update D365 shipment record** - Dynamics 365 Customer Service `Update a record` on the Case entity:
   - `kn_routing` = proposal newRouting
   - `kn_eta` = proposal newEtaUtc
   - `kn_carrier` = proposal selectedCarrier
   - `kn_decisionRef` = decisionRef
3. **Send customer email** - Outlook 365 `Send an email (V2)`:
   - To: `anna.berg@contoso.com`
   - Cc: `respondedBy` (the K+N account owner)
   - Subject + body from template `Customer-Notification-Email.md` with token substitution (shipmentId, original ETA, new ETA, cost delta, decisionRef, approvalTimestamp).
4. **Post confirmation back to Teams** - Microsoft Teams `Post message in chat or channel` to `#contoso-account`:
   > "✅ Reroute approved by {respondedBy} at {respondedAtUtc}. Customer notification sent. Ref: {decisionRef}."
5. **Log to incident ledger** - Dataverse `Add a new row` to `LRS_Incidents`:
   - status = `APPROVED`, full reasoning chain, all timestamps, approver identity.
6. **Refresh Power BI semantic model** (optional) - so the K+N Lane Risk dashboard reflects the new incident within minutes.

#### Branch: REJECT
1. **Log to incident ledger** with status `REJECTED` and `reason` (if provided).
2. **Escalate to global cold-chain duty officer** - Microsoft 365 Approvals `Start an approval` to duty officer with full context.
3. **Post notice to Teams** `#contoso-account`:
   > "⚠️ Reroute rejected by {respondedBy}. Escalated to global cold-chain duty officer. Shipment remains on original lane. Customer not yet notified."

#### Branch: MODIFY
1. **Re-call the Lane Risk Sentinel agent** via HTTP, passing `modifyAction` and `reason` in the body. The parent agent will re-plan based on the constraint (e.g. "switch-lane", "hold", "escalate") and either send a new Adaptive Card or close the case.

#### Branch: TIMEOUT (default, after 60 min)
**Source:** parallel branch `Delay until` + `Get response details` (Approvals connector handles timeout natively).
1. **Auto-escalate to duty officer** via Approvals.
2. **SMS fallback** to account owner via Twilio connector (if configured) - else Teams chat message.
3. **Log to incident ledger** with status `TIMEOUT_ESCALATED`.

---

## Error handling

- Each connector action has `Configure run after` set to also run on **failure**, routing to a "**Log + alert**" scope:
  - Log the failure to Dataverse `LRS_Incidents` with status `flow_failure`.
  - Post to `#kn-ops-monitoring` Teams channel for K+N IT.
- The flow as a whole has a top-level **Try / Catch / Finally** pattern using parallel branches + run-after conditions.

---

## Returns to the agent

```json
{
  "decisionRef": "LRS-2026-2847",
  "outcome": "APPROVED",
  "downstreamActions": ["d365-updated", "customer-emailed", "teams-confirmed", "ledger-logged"],
  "respondedBy": "leila.gharani@kn.com",
  "respondedAtUtc": "2026-02-13T15:08:42Z",
  "elapsedSeconds": 187
}
```

The agent stores this in the `LRS_Incidents` row for full traceability and so the real-time evaluation feature can score whether the agent's proposal was approved as-is, modified, or rejected (precision of the recommender).
