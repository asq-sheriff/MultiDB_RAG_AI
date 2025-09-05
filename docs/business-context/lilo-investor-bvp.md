# Lilo — Investor Memorandum (Confidential Draft)

*Date:* Aug 2025  
*Geography:* United States (initial focus)  
*Stage:* Pre‑seed / Seed  
*This document is confidential and intended solely for potential investors.*

---

## 1) Investment highlights
- **Massive, durable need:** Social isolation and anxiety among older adults are widespread, tied to poorer outcomes and rising costs. Demographics (65+ population growth through 2050) and staffing shortages make the problem acute and persistent.
- **Software‑first companion:** Lilo is an **emotion‑aware, safety‑governed** companion that turns short conversations into *actionable* micro‑interventions (breathing, journaling, call‑a‑friend, reminders) with auditable escalation to humans.
- **Enterprise‑grade posture:** HIPAA‑ready back end, consented “emotional memory,” right‑to‑erasure, and deterministic safety policies suitable for payers and senior‑living operators.
- **Proof path, not hype:** Pilot design emphasizes leading indicators (engagement minutes, emotion regulation deltas, loneliness scores) and **directional** utilization signals before scale.
- **Commercially pragmatic:** Device‑agnostic rollout; software subscriptions (PMPM/per‑resident) with optional voice minutes; integrations with care‑manager workflows.

---

## 2) Problem and why now
- **Aging in place meets staffing constraints:** Operators and payers must support calm, routine, and social connection without adding headcount. Traditional check‑ins don’t scale to demand.  
- **Cost & quality pressure:** Health plans compete on member experience (CAHPS/Stars), while seniors and families expect transparency and timely escalation.  
- **Technology adoption:** Seniors increasingly use mobile and voice; software‑first solutions can meet people where they are.

---

## 3) Solution overview (what Lilo is)
- **Emotion Engine**: continuous **valence × arousal** + discrete labels per turn; chooses tone and **regulation goal** (e.g., reduce arousal within 3 turns).  
- **Action Toolkit**: timers for breathing/mindfulness, journaling prompts, call‑a‑friend suggestions, resource lookups, reminders.  
- **Safety layer**: keyword heuristics + contextual risk scorer; scripted crisis playbooks; human handoffs; full audit trail.  
- **Privacy and control**: consented personal memory with TTL; PHI minimization; per‑user data erasure.  
- **Channels**: chat (web/mobile) at launch; optional voice (WebRTC).  
- **Integrations**: SSO, care‑manager inbox/CRM, optional EHR reads, SMS/voice gateways.

**What Lilo is not:** a clinician or diagnostic device. It augments staff and caregivers and escalates early when risk is detected.

---

## 4) Market opportunity (TAM/SAM/SOM)
**Top‑down**  
- **Senior living & home‑care**: ~1.7–1.9M units nationwide across IL/AL/MC; occupancy rising; operators under staffing pressure.  
- **Medicare Advantage**: 34M+ beneficiaries (2025), >50% of Medicare; plans invest heavily in experience and supplemental benefits.

**Bottom‑up (illustrative)**  
- **Senior living**: price point **$12–$25 per resident/month** (software), optional voice minutes; initial SAM: 500k residents across regional operators; **$72–$150M** ARR at 100% penetration of SAM.  
- **Health plans**: price point **$3–$8 PMPM** (software), voice optional; target cohorts (loneliness/SDoH, post‑discharge, BH waitlists) = 2–5% of MA lives per plan; **$72–$163M** ARR at 2–5% penetration of 30M+ MA lives.  
*Assumptions shown for sizing; final pricing/cohorts negotiated by channel and feature set.*

---

## 5) Competitive landscape
| Segment | Examples | Strengths | Gaps Lilo exploits |
|---|---|---|---|
| **Embodied robots** | ElliQ | High engagement, proactive routines | Hardware cost/ops; slower iteration; limited enterprise integrations |
| **Avatar + human back‑office** | CareCoach | High‑touch empathy; proven adherence | Services‑heavy; expensive to scale; integration depth |
| **Caregiving utilities** | Alexa Together | Alerts, activity feeds, partner networks | Utility‑first; not emotion‑aware; limited enterprise reporting |
| **Generic chat apps** | Replika, Character | Conversational stickiness | Not senior‑specific; no enterprise safety/compliance |

**Positioning:** Lilo is **software‑first, emotion‑to‑action**, with **policy transparency** and **HIPAA posture** for enterprise buyers.

---

## 6) Product & tech moat
- **Safety‑first policy graph** (deterministic nodes, schema‑validated tool use) + **checkpoints** for replay/HIL and auditability.  
- **Emotion → Action linkage** (regulation objectives with measurable deltas).  
- **Dual‑index RAG** (general psychoeducation + consented personal memory) with provenance.  
- **Vendor‑portable LLM routing** (frontier APIs + open‑weights via vLLM) to manage cost, latency, and privacy.  
- **Operational data network effects**: with partner consent, de‑identified patterns of “what helped” by persona feed policy improvements.

---

## 7) Traction & milestones
- **Design partners**: pipeline of senior‑living operators and MA plans for 90–120‑day pilots (letters of intent in progress).  
- **MVP**: text channel complete; voice in controlled beta; observability & safety dashboards online.  
- **Clinical & safety advisors**: external advisors engaged for red‑team and policy review.

---

## 8) Go‑to‑market (first 18 months)
**Channels**  
- **Senior living & home‑care**: direct enterprise sales (regional operators first), partnerships with staffing/training vendors.  
- **Health plans**: sell to innovation/quality leaders; start in specific cohorts (loneliness/SDoH, post‑discharge).  
- **Public sector**: state aging agencies via grants/cohorts (after enterprise proof).

**Pilot‑first motion**  
- 100–300 participants per pilot; success gates: engagement ≥25 min/week, emotion delta, UCLA‑3 improvement, zero unhandled crises, operator/plan CSAT.  
- Post‑pilot expansion to 1–5k lives with ROI scenarios.

---

## 9) Business model & unit economics (illustrative)
**Revenue**  
- **Senior living**: per‑resident/month tiers (Core, Plus with voice minutes).  
- **Health plans**: PMPM tiers; enterprise add‑ons (SSO, analytics export, caregiver portal).  
- **Services**: onboarding, staff training, outcomes reporting; optional integrations.

**COGS drivers**  
- Model inference (LLM tokens); voice minutes (ASR/TTS) for voice channel; vector DB & storage; observability; support.  
- **Gross margin targets:** 65–80% blended, depending on voice mix and model routing.  
- **Levers:** prompt distillation; caching; open‑weight routing for low‑risk subflows; summarization of long contexts.

---

## 10) Regulatory & compliance
- **HIPAA‑ready hosting** with BAAs; PHI minimization; consented emotional memory with TTL; DSAR/erasure workflows.  
- **Safety governance** aligned to reputable guidance; conservative defaults; incident & change‑control processes.  
- **Accessibility** and plain‑language UX for older adults; multilingual intents as roadmap.

---

## 11) Product roadmap
- **Now → 6 months:** voice GA; proactive check‑ins; caregiver portal; more safety red‑teaming; cohort‑specific playbooks (sleep, rumination, grief).  
- **6 → 12 months:** enterprise integrations (plan CRM/inbox); A/B testing framework for phrasing vs actions; additional languages/dialects.  
- **12 → 18 months:** expanded cohorts (post‑discharge, BH waitlists); open‑weight model fine‑tuning; outcomes publications with partners.

---

## 12) Financial projections (scenarios)
*(Illustrative, for planning only)*  
- **Year 1:** 6–10 pilots; convert 4–6; 10–20k paid lives exit‑year; ARR **$1.2–3.5M**.  
- **Year 2:** 60–100k paid lives; ARR **$8–18M**; gross margin 70%±5pp.  
- **Year 3:** 200–350k paid lives; ARR **$30–60M** with two channels performing; net retention >110%.

---

## 13) Team
- **Founders:** AI architecture, healthcare data, and enterprise GTM backgrounds.  
- **Advisors:** gerontology, behavioral health, and senior‑care operations.  
- **Hiring plan (next 12 months):** 2 applied ML, 2 full‑stack, 1 speech/real‑time, 1 security/infra, 2 enterprise AE, 1 CS lead.

---

## 14) Risks & mitigations
- **Attachment risk / over‑reliance** → frequent disclosures; encourage human contact; proactive limits; break reminders.  
- **Crisis detection miss** → dual detectors; human‑in‑loop for ambiguous cases; strict SLAs and audits.  
- **Privacy breach** → PHI minimization; DLP; vendor BAAs; DSAR automation; least‑privilege access & RLS.  
- **LLM cost/latency drift** → vendor‑portable routing; prompt distillation; open‑weight subflows.  
- **Procurement friction** → pilot‑first SOWs; quick wins; reference customers by segment.

---

## 15) Use of funds (18–24 month runway)
- **Product & ML (40%)**: emotion/policy improvements; voice GA; safety and eval tooling.  
- **Go‑to‑market (35%)**: enterprise AEs, marketing, customer success; pilots in 2–3 regions.  
- **Security & compliance (10%)**: audits, BAAs, privacy ops.  
- **G&A (15%)**: core ops and legal.

**Capital ask:** $X–Y million seed round; target runway 20–24 months.  
**Milestones to next round:** 100k+ paid lives across two channels; ≥70% blended gross margin; 3+ referenceable enterprise customers; one outcomes whitepaper.

---

## 16) Diligence packet (available upon request)
- Security & compliance summary; BAAs and vendor matrix.  
- Safety policies and escalation scripts; red‑team & eval suites.  
- Architecture & data‑flow diagrams; RLS and DSAR flows.  
- Pilot playbooks, reporting templates, and sample dashboards.  
- Customer discovery notes; letters of intent (as available).

---

## 17) Call to action
**Join us** in a pilot‑to‑scale trajectory that makes measurable improvements in calm, routine, and connection for older adults—while giving operators and payers auditable, privacy‑first engagement that supports their quality and cost goals.

