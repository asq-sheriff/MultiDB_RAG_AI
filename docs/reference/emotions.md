# Emotions & Empathic Engine — v2

## Purpose
Reduce loneliness/anxiety and provide safe, empathic companionship through evidence‑based micro‑interventions and consistent, familiar routines.


### Affect & Intent Ontology (valence–arousal)
| label | valence | arousal | default module(s) |
|---|---:|---:|---|
| calm | +0.3 | −0.3 | connect → practical_info |
| warm | +0.6 | +0.2 | connect → reminiscence |
| low | −0.3 | −0.4 | soothe → BA_micro |
| anxious | −0.5 | +0.7 | soothe → grounding → calm_info |
| sad | −0.6 | −0.3 | reminiscence_safe → BA_micro |
| frustrated | −0.4 | +0.5 | empathic_reflection → practical_info |
| **grief_adjustment** | **−0.6** | **+0.5** | soothe → reminiscence_safe → BA_micro → social_bridge |

Notes:
- Allow multiple labels with confidences (e.g., sad:0.62, grief_adjustment:0.58).
- Persist numeric valence/arousal alongside affect.label in analytics.
- Expose affect_hypothesis in traces; emit ce.affect_hypothesis_updated when it changes.


## Engine Inputs & Pipeline
- Inputs: persona, Life Story Graph, Preference Book, consent profile, context (time/location), signals (sleep/activity), recent sessions.
- Pipeline: intent+affect → Alliance layer (empathy, validation) → Intervention → Continuity renderer → Safety check → Closure.

### Policy Graph (planner)
Intent → Alliance Layer → Intervention → Continuity Renderer → Safety Check → Closure


### Intervention Modules
- **Reminiscence (10 min):** Safe, specific memory prompts; optional media cue (song/photo); avoid traumatic details unless user leads.
- **Behavioral Activation (BA):** One tiny action (≤5 min), afternoon follow-through, evening reward reflection.
- **Grounding:** 2-minute breath or 5-senses scan; voice pacing 140–160 wpm.
- **Social Bridge:** Compose/send 1‑tap message; schedule calls; respect Consent Profile.
- **Calm Info:** Plain-language explanations + next micro-step; never clinical diagnosis.


### Prompt Style Guide (engine persona)
- Empathy-first: reflect → validate → normalize → two gentle choices → small next step.
- No problem-solving in the first two turns when distress is detected.
- Keep turns brief; avoid toxic positivity; close with availability line.


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


### Measurement & HITL (caregiver portal)
- Weekly summary shows UCLA-3, GAD-2 trend, BA adherence, social touches.
- Emissions: ce.reflection_logged (after evening recap), ce.metrics_snapshot (daily/weekly roll-up).
- Portal actions: one-tap outreach templates; audit all hand-offs; SBAR preview on Orange/Red.

**Success targets**
- UCLA-3 / GAD-2 ∆ ≥ −1.0 by weeks 4–6; BA completion ≥ 50%; ritual adherence ≥ 70%; post-empathy sentiment drop (turn+2) ≥ 0.2.
(Updated 2025-09-03)


### Ready-to-use prompt block — Grief/Adjustment
> “I’m hearing **grief** and a bit of **restless energy**. That makes sense after what changed. **Two gentle options**: a **2‑minute breath** together or **remember one small comforting thing** about <name/place>. I’m with you.”

