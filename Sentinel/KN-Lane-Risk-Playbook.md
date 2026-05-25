# K+N Lane Risk Playbook
**Version 4.2 | Effective Q1 2026 | Owner: K+N Global Sea Logistics, Cold-Chain Center of Excellence**

This playbook defines how K+N classifies shipment risk on customer lanes and the required mitigation response per risk level. Used as the **grounded knowledge source** for the Lane Risk Sentinel autonomous agent in Microsoft Copilot Studio.

---

## 1. Risk scoring matrix

A shipment is scored **LOW**, **MED**, or **HIGH** based on the worst of three input dimensions: **Cargo Integrity**, **Schedule Integrity**, and **External Disruption**.

### 1.1 Cargo Integrity (reefer / dangerous goods only)
| Condition | Score |
|---|---|
| Reefer actual temp within ±0.5°C of setpoint AND no carrier alarm in last 24h | LOW |
| Reefer actual temp deviation 0.5°C to 2.5°C OR single alarm within 24h | MED |
| Reefer actual temp deviation > 2.5°C OR multiple alarms OR DG containment breach reported | HIGH |
| Non-reefer / non-DG containers default to LOW on this dimension. | - |

### 1.2 Schedule Integrity
| Condition | Score |
|---|---|
| Current ETA within ±12h of original ETA | LOW |
| Current ETA delayed 12h to 36h vs original | MED |
| Current ETA delayed > 36h vs original OR customer SLA breach forecast | HIGH |

### 1.3 External Disruption
| Condition | Score |
|---|---|
| No active weather alerts, no port congestion > 24h, no sanctions hit | LOW |
| Active weather alert on route OR port congestion 24-48h forecast | MED |
| Typhoon / hurricane / port closure on route OR sanctions hit on consignee, carrier or vessel | HIGH |

**Final shipment risk score = MAX(Cargo, Schedule, External).**

---

## 2. Response per risk level

### LOW
- **Action:** log to internal watch list. No customer contact required.
- **Cadence:** revisit at next daily sweep (06:00 CET).
- **Owner:** automated. No human required.

### MED
- **Action:** post informational adaptive card to the K+N account team's Teams channel within 30 minutes of detection.
- **Customer contact:** none unless a second MED signal lands within 12h on the same shipment (then escalate to account owner judgement).
- **Owner:** account team (informed, not action-required). Create Planner task for visibility.

### HIGH
- **Action:** immediate mitigation. Within 60 minutes from detection:
  1. Pull alternate routing options from K+N TMS (free capacity in next 72h on equivalent lane).
  2. Draft routing proposal including ETA delta, cost delta, environmental impact delta.
  3. Validate proposal against customer Master Service Agreement (cost ceiling, mode constraints, carrier whitelist).
  4. Send approval request to designated K+N account owner via Microsoft Teams (Adaptive Card with Approve / Reject / Modify actions).
- **On approval:** trigger downstream Power Automate flow to update shipment record, notify customer in writing, log decision to incident ledger.
- **On rejection:** escalate to global cold-chain duty officer; capture reason for model improvement loop.
- **On timeout (no response in 60 min):** auto-escalate to duty officer + page account owner via SMS fallback.

---

## 3. Customer-specific overrides

### Contoso Industries (MSA-CONTOSO-2024)
- **SLA window:** mitigation plan must reach customer within **4 hours** of any reefer excursion above 2.0°C.
- **Cost ceiling for autonomous reroute:** €3,500 per shipment without further approval.
- **Carrier whitelist for reroute:** CMA CGM, Maersk, Hapag-Lloyd, Hamburg Süd, HMM.
- **Mode constraint:** reefer cargo must stay sea-only unless customer explicitly approves air uplift.
- **Designated account owner:** see `ContosoShipments.accountOwner` field on the relevant record.
- **Notification template:** use *Customer-Notification-Email.md* with auto-generated ref `LRS-{year}-{shipmentId-suffix}`.

---

## 4. Reroute eligibility checklist

Before sending an alternate routing proposal for HIGH-risk shipments, the agent must verify all of the following:

- [ ] Origin port has confirmed cargo handover capability for the alternate carrier
- [ ] Alternate vessel/flight has confirmed free capacity for the next 72h window
- [ ] Alternate routing keeps the cargo within the customer's contracted carrier whitelist
- [ ] Sanctions screen returns CLEAR for the alternate carrier, vessel and consignee
- [ ] Total cost delta is within the customer's MSA ceiling
- [ ] ETA delta improves vs the no-action ETA by at least 12h (otherwise propose hold-and-monitor instead)

If any check fails, the agent must **not** send an autonomous reroute proposal. Instead, escalate with the failed check noted.

---

## 5. Audit & evaluation

Every agent decision (LOW/MED/HIGH classification, reroute proposal, approval, rejection) is logged to the `LRS_Incidents` Dataverse table with:
- timestamp, shipmentId, inputs (snapshot), reasoning summary, decision, approver, outcome
- Used by the Copilot Studio **real-time evaluation** feature to track precision/recall of the risk classifier vs human override decisions.

---

*This document is the authoritative source for Lane Risk Sentinel. Any change in business rule must be reflected here first; the agent will pick it up at the next 06:00 CET sweep without redeployment.*
