## 🎯 Purpose & Vision

* A **therapeutic emotional AI assistant for seniors**, designed to:

  * Reduce loneliness and anxiety
  * Support medication/treatment adherence
  * Lighten caregiver and family burden
  * Provide **safe, empathic companionship** at scale

---

## 🛠️ Core Capabilities

* **Voice + Chat interface** (multi-modal interaction: natural conversation, reminders, and nudges)
* **Empathetic conversation engine** → keeps tone calm, caring, and human-centered
* **Routine nudges & engagement** → reminders for meds, appointments, daily habits
* **Cognitive stimulation** → light memory games, discussions, personalized prompts
* **Safety checks** → daily check-ins, escalation when signs of distress are detected
* **Explanations w/ citations** → Retrieval-Augmented Generation (RAG) ensures accuracy and explainability

---

## 🔐 Compliance & Architecture

* **HIPAA-by-design**

  * Deployable into customer’s **own VPC**
  * Supports **SSO/SAML** for enterprise access
  * **Immutable audit logs**
  * **Customer-managed data retention**

---

## 📊 Pilot-Modeled Outcomes

* **Loneliness** ↓ \~2 points
* **Anxiety incidents** ↓ \~35%
* **ED (Emergency Dept) visits** ↓ \~8%
* **Readmissions** ↓ \~12%
* **Family/staff satisfaction** ↑ +18%

---

## 🧩 Target Users

* **Seniors** (especially isolated or with chronic conditions)
* **Caregivers & family** (receive peace of mind and escalation alerts)
* **Healthcare orgs** under pressure from staff shortages & value-based care models

---

## ✨ Positioning

* Distinct from general-purpose chatbots: designed for **healthcare safety, trust, and empathy**
* Aimed at **value-based care, senior living, and chronic condition management**

# Stateful Agentic RAG — v2

## Overview
Agentic Router orchestrates sub‑agents (conversation, safety, search/RAG, scheduling) with stateful memory and deterministic rituals.


### Ritual Scheduler (deterministic windows)
- Windows: morning 07:30–09:30, afternoon 13:30–15:30, evening 19:00–20:30 with jitter ±5 min.
- Deterministic seed per user for reproducible timing in tests.
- Offline: queue missed nudges; coalesce into a single polite message on reconnection.


### Router — Debug & Observability
- Debug panel surfaces: intent, affect_hypothesis (valence/arousal), plan_id, top 3 memory snippets.
- Log prior→posterior diffs when emitting ce.affect_hypothesis_updated.
- Failure modes:
  - Missing media rights → degrade to text-only reminiscence; set metadata.media_rights_missing=true.
  - Network loss during module → persist state and resume idempotently.
- HITL: Webhook posts SBAR JSON to caregiver portal on Orange/Red.


---
