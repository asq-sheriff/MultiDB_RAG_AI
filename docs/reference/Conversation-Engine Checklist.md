# Conversation Engine Checklist — v2 (Ticket‑Ready)

> Copy → paste into Jira/Linear and fill blanks.

## 0) Ticket Header
**Story:** `[CE] <Feature / Flow Name>`  
**Goal:** <business impact / symptom reduced>  
**Owner:** <name> · **Due:** <date>  
**Dependencies:** NLU intents, Memory API, Safety service, TTS/ASR, Analytics

---

## 1) User & Context Contract
- [ ] Persona: `<Name, age, health constraints>`, timezone, cadence windows.
- [ ] Modalities: Voice, chat, push; fallbacks defined.
- [ ] Consent: Outreach, data sharing, escalation contacts verified.
- [ ] Familiarity anchors: greeting phrase, sonic cue, closing line.

**DoD:** Persona+consent load; deterministic greeting & closure within window.

---

## 2) Memory & Continuity
- [ ] Life Story Graph (people, places, events, artifacts) — CRUD via API.
- [ ] Preference Book (wake/check‑ins, rituals, favorites, dislikes, comms).
- [ ] Thread recall: last 3 sessions summarized + 1 surfaced callback.

**DoD:** Round‑trip CRUD; continuity snippet inserted in ≥1 reply/flow.

---

## 3) Intent & Affect Detection
- [ ] Intents: connect | reminisce | encourage_activity | soothe | plan_social | practical_info.
- [ ] Affect classifier → calm, low, anxious, sad, frustrated, warm, grief_adjustment with valence/arousal.
- [ ] Empathy gate: first 2 turns = reflect + normalize before problem-solving.

**DoD:** Tests cover ≥6 examples/intent; affect drives template selection.

---

## 4) Response Planning

### Policy Graph (planner)
Intent → Alliance Layer → Intervention → Continuity Renderer → Safety Check → Closure


- [ ] Two short options + “or something else?”
- [ ] Bounded optimism (no minimization).

**DoD:** Given same input & state, plan is deterministic (seeded) and explainable in logs.

---

## 5) Modules

### Intervention Modules
- **Reminiscence (10 min):** Safe, specific memory prompts; optional media cue (song/photo); avoid traumatic details unless user leads.
- **Behavioral Activation (BA):** One tiny action (≤5 min), afternoon follow-through, evening reward reflection.
- **Grounding:** 2-minute breath or 5-senses scan; voice pacing 140–160 wpm.
- **Social Bridge:** Compose/send 1‑tap message; schedule calls; respect Consent Profile.
- **Calm Info:** Plain-language explanations + next micro-step; never clinical diagnosis.


**DoD:** Each exposes `start()`, `nudge()`, `wrap()`, emits standardized events.

---

## 6) Safety & Escalation

### Safety & Escalation (non-clinical, clinically informed)
- **Yellow:** 2+ days of low mood/anxiety; sleep disruption → BA + offer human check-in.
- **Orange:** hopeless phrasing, marked agitation, repeated crisis keywords → initiate human outreach now; same-day check-in.
- **Red:** self-harm intent/plan, chest pain, acute confusion → contact emergency per consent; handoff SBAR; stay on line.

**SBAR (handoff payload example)**
```json
{
  "S": "Concern about escalating anxiety; user alone now",
  "B": "Recent bereavement; afternoon dip patterns; GAD-2 last week=3/6",
  "A": "Affect anxious (v=-0.5,a=0.7). No chest pain. No self-harm language.",
  "R": "Call daughter (consented) now; schedule nurse check-in within 24h"
}
```


**DoD:** Simulated Orange/Red utterances trigger correct branch & audit trail.

---

## 7) Copy & Prompts

### Prompt Style Guide (engine persona)
- Empathy-first: reflect → validate → normalize → two gentle choices → small next step.
- No problem-solving in the first two turns when distress is detected.
- Keep turns brief; avoid toxic positivity; close with availability line.


**DoD:** Prompt renders < 2,000 tokens with full context; hallucination guard tests pass.

---

## 8) Localization & Accessibility
- Large type; plain language grade ≤ 6.
- Voice pacing 140–160 wpm; longer pauses after questions.
- Hearing/vision toggles; captions ON; haptic cue optional.

**DoD:** Accessibility checklist passes; TTS/ASR configs stored per user.

---

## 9) Instrumentation

### Analytics & Events (v1.1)
Emit on every flow (as applicable):
- ce.intent_detected
- ce.affect_inferred
- ce.affect_hypothesis_updated  ← fire when affect label/strength changes intra-session
- ce.plan_selected
- ce.module_started / ce.module_completed
- ce.choice_made
- ce.nudge_delivered / ce.nudge_acknowledged
- ce.safety_flag
- ce.reflection_logged
- ce.metrics_snapshot

Event ordering must be deterministic for a fixed seed and state (validated in CI).


### Event Reference (when to emit / required fields)
| Event | When it fires | Required fields | Typical metadata |
|---|---|---|---|
| ce.intent_detected | After NLU parses a turn | intent, confidence | alternatives list |
| ce.affect_inferred | After affect classifier runs | affect.label, confidence, optional valence, arousal | model, rationales |
| ce.affect_hypothesis_updated | Affect updated due to new evidence | prior→posterior in metadata | delta_v, delta_a, triggers |
| ce.plan_selected | Planner chooses next module(s) | plan_id | reasons, guardrails |
| ce.module_started | A module begins | module | step, config |
| ce.choice_made | User selects an option | choice | menu id, dwell time |
| ce.module_completed | A module ends | module | outcome (mood shift, adherence) |
| ce.nudge_delivered | Scheduled nudge delivered | window id | channel |
| ce.nudge_acknowledged | User interacts with nudge | — | click type |
| ce.safety_flag | Safety rule matched | safety (yellow/orange/red) | rule id, excerpt (redacted) |
| ce.reflection_logged | Evening reflection saved | — | recap length |
| ce.metrics_snapshot | Daily/weekly roll-up | — | adherence, social touches |

ce.affect_hypothesis_updated example
```json
{
  "event_name": "ce.affect_hypothesis_updated",
  "user_id": "u_123",
  "session_id": "s_456",
  "trace_id": "t-8f2c",
  "ts": "2025-09-03T19:32:00Z",
  "affect": {"label":"grief_adjustment","confidence":0.86,"valence":-0.58,"arousal":0.48},
  "metadata": {"prior":{"label":"sad","valence":-0.6,"arousal":-0.3},"evidence":"prosody:sigh+wording:'waves'","delta_v":0.02,"delta_a":0.78}
}
```


**DoD:** Event ordering deterministic (CI-validated); sample trace per module attached to PR.

---

## 10) Success Metrics
- Weekly UCLA-3, GAD-2 trend targets.
- Ritual adherence ≥ 70%; BA completion ≥ 50%; social touches ≥ 1/wk.
- Post-empathy sentiment drop (turn+2) ≥ 0.2.

**DoD:** Dash tiles wired; events in warehouse; cohorts defined.
