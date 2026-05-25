# KN AI Context Snapshot — internal grounding document

> **Purpose:** Internal context snapshot for grounding the Researcher Agent. Upload this file to Researcher together with the regulatory-impact prompt so the agent grounds its analysis in *both* (a) public EU/Swiss/global regulation and (b) KN's actual AI footprint, vertical exposure and operational reality. Treat as confidential, KN-internal.
>
> **Owner:** Group AI & Innovation Office (Sgi GI-I) · **Last refresh:** 2026-05 · **Classification:** Internal — KN + Microsoft account team

---

## 1. KN AI footprint (May 2026)

### K.AI platform
- **K.AI** is KN's group-wide GenAI platform built on top of Azure OpenAI, internal MCP-based service bus, and a Kuehne-hosted RAG layer.
- In production for: AI coding assistance (developer + non-developer), business-partner master-data cleansing, sea-freight document classification, customer-service draft-reply assistance.
- Awarded **CDQ Good Practice Award 2025** for GenAI in business-partner master data and Responsible AI recognition.
- **Strategic target:** become the most digitally advanced logistics company by **2030**.

### Microsoft footprint (in scope for this assessment)
- M365 Copilot — large pilot population, evaluating broad rollout.
- Copilot Studio — early agent prototypes (Sea Logistics ops, Contract Logistics customer-onboarding).
- GitHub Copilot — in production for engineering teams.
- Dynamics 365 — D365 Customer Service in selected business units; AI Agents pilots planned.
- Azure OpenAI Service + Azure AI Foundry — production workloads under K.AI.

### Data & governance baseline
- Primary data residency: **EU (Frankfurt, Amsterdam) + Switzerland (Zurich North)**.
- Identity: single Entra ID tenant across the group; SCIM-provisioned from SAP SuccessFactors.
- Compliance baselines already in place: ISO 27001, ISO 14001, GDPR controller posture, TAPA FSR/TSR for cargo security.
- Responsible AI: internal AI policy aligned to **OECD AI Principles** and the **NIST AI RMF**; internal AI ethics board (~12 members) chaired by the Chief AI & Innovation Officer.

---

## 2. Vertical exposure that drives regulatory risk

KN moves cargo for industries that sit in the **highest-impact** AI-regulation buckets:

| Vertical | Share of group revenue (approx) | Why it matters for AI regulation |
|---|---|---|
| Pharma & Healthcare | ~14% | Cold-chain integrity, MDR / IVDR audit trails, FDA + EMA serialisation. AI-driven exception handling = high-risk territory under the EU AI Act. |
| Aerospace & Defence | ~8% | ITAR / EAR / EU Dual-Use Reg 2021/821 exposure. AI-assisted screening of consignees = sanctions-screening, restricted under EU AI Act and US export law. |
| High-Tech & Semicon | ~11% | Export controls (US, NL, JP), counterfeit prevention, tamper detection. Sensitive to AI-driven anomaly detection mis-classifications. |
| Chemicals & Hazmat | ~6% | ADR / IMDG / IATA-DGR. Document-classification AI errors are safety incidents, not service issues. |
| Perishables | ~4% | Cold chain, regulator-mandated audit trails. AI tied directly to consumer safety. |
| Automotive / Industrial / FMCG | ~57% | Generally lower regulatory criticality, but customer-imposed AI-clauses (especially OEM-driven) are spreading. |

> **Implication:** roughly **~43% of KN revenue** touches verticals where *any* AI-driven decision in the supply chain falls into the EU AI Act's "high-risk" classification — directly or via customer-imposed contractual flow-down.

---

## 3. Live AI use cases that touch regulation

| # | Use case | Owner | Stack | Regulatory lens |
|---|---|---|---|---|
| U1 | Customer-service draft replies (multilingual) | Customer Service Excellence | K.AI + Azure OpenAI | EU AI Act limited-risk (transparency); GDPR Art 22 if used unsupervised |
| U2 | Sea-freight document classification (BoL, packing list) | Sea Logistics Ops | K.AI + Azure OpenAI vision | EU AI Act high-risk *if* used for customs declarations; GDPR processor flows |
| U3 | Master-data deduplication & enrichment (business partners) | Master Data Office | K.AI RAG + Dataverse | GDPR + Swiss revFADP; **CDQ Good Practice 2025** |
| U4 | Sanctions / restricted-party screening assistance | Compliance | K.AI + external lists | **Explicit EU AI Act high-risk** (Annex III); EU Dual-Use; OFAC |
| U5 | AI coding assistance | Engineering | GitHub Copilot + K.AI internal | IP / open-source license hygiene; EU AI Act limited-risk |
| U6 | Lane-risk + reroute reasoning (planned, pilot) | Sea Logistics | Copilot Studio + Dataverse | EU AI Act limited-risk (operational); customer-contract AI-clauses |
| U7 | Customer-churn / commercial-risk scoring (planned, pilot) | Commercial Excellence | K.AI + internal analytics | **EU AI Act limited-risk → high-risk if used for tier-down or contract termination decisions** |
| U8 | Cold-chain anomaly detection (pharma reefer) | Pharma Vertical | K.AI + IoT signals | **EU AI Act high-risk** (linked to safety of medicinal products) |

---

## 4. Geographic footprint relevant for regulation

- **EU member-state operations:** all 27, with heaviest workforce concentration in DE, NL, BE, FR, ES, IT, PL.
- **Switzerland HQ:** subject to **Swiss revFADP** + emerging Swiss Federal Council position on AI (Jan 2026 dispatch — Switzerland will *not* copy the EU AI Act 1:1, but will adopt sector-specific rules + adhere to the **Council of Europe Framework Convention on AI** signed Sep 2024).
- **UK operations:** subject to pro-innovation, sector-led approach (DSIT 2024–2026 framework). No horizontal AI Act equivalent — yet.
- **US operations:** federal — Executive Order on AI status uncertain post 2025 transition; state-level (CA SB 1047 dead, but Colorado AI Act enters force Feb 2026, NY AI bias audit law active). FAR/DFARS for federal contracts.
- **APAC operations:** China — Interim Measures for GenAI (active since Aug 2023) + 2025 algorithmic registry expansion. Singapore — Model AI Governance Framework (voluntary). Japan — soft-law approach. South Korea — AI Basic Act passed Dec 2024, effective Jan 2026.
- **Middle East:** UAE — National AI Strategy 2031, light-touch. KSA — SDAIA AI Ethics Principles, contract-driven.

---

## 5. What KN already does (so the agent doesn't re-tell us things we have)

- ISO 27001 + ISO 14001 certified at group level.
- GDPR + Swiss revFADP compliance programme since 2018 (revFADP since 2023).
- Internal AI policy v2.1 (Mar 2026): mandatory human-in-the-loop for any AI decision affecting a customer commercial outcome.
- Responsible AI training: ~60% of in-scope employees completed Level 1; Level 2 ("AI builders") rolling out Q2 2026.
- Internal AI inventory: ~140 use cases logged, ~40 in production, ~12 classified internally as high-risk.
- Active dialogue with **DigitalEurope, FIATA, CLECAT** on logistics-sector AI Act guidance.

---

## 6. What we do NOT yet have (the gaps we want the Researcher to surface)

- **ISO/IEC 42001** (AI Management System) — assessing certification need; nothing in place yet.
- **EU AI Act Annex III article-by-article mapping** against our 12 internally-classified high-risk use cases — partial only.
- **Cyber Resilience Act (CRA)** impact on K.AI's internal tooling and any customer-facing digital products — not yet mapped.
- **EU Data Act** (effective Sep 2025) — exposure assessment on customer-data-portability obligations not finished.
- **Customer AI-clause register** — we see customer contracts increasingly carry AI-clauses (especially from pharma + aerospace customers); no central register yet.
- **Swiss sector-specific AI rules pipeline** — no formal tracking process.
- **NIS2 + DORA** intersection with AI workloads — DORA only applies to us indirectly (as a service provider to financial-services customers), but exposure is not quantified.

---

## 7. Questions the AI & Innovation Office is being asked by the Board

1. "When does the EU AI Act actually bite for us, and on which use cases?"
2. "Are we ISO/IEC 42001 certifiable today, and is it worth the effort?"
3. "What does the new Swiss federal AI position mean for our HQ obligations?"
4. "Where is our regulatory blind spot — what are we doing today that will become illegal or contractually unacceptable in 12–24 months?"
5. "How do we benchmark against Maersk, DHL, DSV, Geodis on AI-regulatory readiness — are they ahead, behind, or the same?"
6. "What is the cheapest credible governance posture that satisfies customers, regulators, and the board, without slowing K.AI down?"

---

*This snapshot is the grounding context. The Researcher Agent should treat this as the* **internal-state baseline** *and combine it with current public regulatory sources to produce the impact brief.*
