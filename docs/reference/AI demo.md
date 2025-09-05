# Demo Script — Reminiscence → BA Nudge → Evening Reflection (+metrics)

**Persona:** *Mrs. Lewis (78)* — mornings at 08:30, loves Motown, friend **Anita**, afternoon porch sits, light knee pain.  
**Assumptions:** consented SMS to Anita; check-in windows 08:30 / 14:00 / 19:30; captions ON; voice pacing 150 wpm.

---

## Scene 1 — Morning Check‑in & Reminiscence (08:30)
**State in:** `affect=calm/low`, slept early; yesterday she missed her sister.

**A1 (Assistant):**  
“Good morning, Mrs. Lewis. I’m glad to be with you. Yesterday you mentioned thinking about your sister. **Would it feel nice to revisit a favorite memory**, or shall we **just ease in with a gentle hello**?”

**U1 (User):**  
“Let’s talk about my sister. We used to dance to Motown.”

**Engine (internal):**  
- intent: `reminisce`   
- affect: `warm/low`  
- plan: `Alliance → Reminiscence(10) → Continuity cue (Motown)`

**A2:**  
“It sounds **fond and a little tender**. **What song** brings you both back the most? I can **play a short clip** while we talk, or **we can just picture it together**.”

**U2:**  
“‘My Girl.’ We danced in the kitchen.”

**A3:**  
“I can picture it—sunlight on the floor. **Would you like a 20‑second clip**, or shall I **ask a question to paint the scene**?”

**U3:**  
“Play a clip.”

*(Plays 20 s clip; captions ON. Events: `module_started: reminiscence`, `media_played`.)*

**A4:**  
“Beautiful. **What made those kitchen dances special**—the music, the company, or the feeling of being silly together?”

**U4:**  
“The company.”

**A5 (wrap):**  
“Thank you for sharing that. I’ll note **‘My Girl’** as a **mood‑lift** for you. I’m here all day—**tap the green dot** if you want me.”

**Events emitted:**  
`ce.intent_detected(reminisce)`, `ce.affect_inferred(low)`, `ce.plan_selected(rem-10)`, `ce.module_completed(reminiscence)`

---

## Scene 2 — BA Nudge (14:00)
**Trigger:** scheduled afternoon energy dip; BA plan = “2‑minute porch sit + text Anita photo.”

**A6 (push/voice):**  
“Hi Mrs. Lewis. **A tiny lift** might feel good. **Would you like 2 minutes on the porch** or **send Anita a quick hello**? Either works.”

**U5:**  
“Porch, then I’ll text her.”

**A7:**  
“Lovely. I’ll stay with you. **Name three things you see** out there, and I’ll save the note for Anita after.”

*(Timer runs, gentle pacing. Events: `ce.nudge_delivered`, `ce.choice_made: porch`.)*

**U6:**  
“I see the maple tree, the blue sky, and a bird feeder.”

**A8 (reinforce & bridge):**  
“Nicely noticed. **Want me to send Anita**: *‘Thinking of you—blue sky, bird feeder, made me smile’*?”

**U7:**  
“Yes, send it.”

*(Sends SMS via consented channel. Events: `social_bridge_sent`, `ce.module_completed(ba)`.)*

---

## Scene 3 — Evening Reflection & Metrics (19:30)
**A9:**  
“Good evening, Mrs. Lewis. **A small recap, if you’re up for it.** You took a porch moment and messaged Anita. **What felt nicest today**—the breeze, the memory, or the message?”

**U8:**  
“The memory…and Anita replied with a heart.”

**A10 (affect label + closure):**  
“That sounds **warming and connected**. I’ll mark today as a **good‑mood day**, and keep *‘My Girl’* handy. **Would you like a similar nudge tomorrow**, or prefer just a hello?”

**U9:**  
“Similar nudge.”

**A11:**  
“Got it. **I’ll check in with a tiny lift tomorrow afternoon.** I’m here if you need me.”

**Events emitted:**  
`ce.reflection_logged`, `ce.metrics_snapshot`, `ce.plan_selected(eve_reflection)`

---

## Run of Show (for live demo)
1. **Prep**: load persona, enable captions, verify SMS sandbox.  
2. **Start**: show policy graph & memory snippets on a side console (for transparency).  
3. **Scene 1**: play 20 s music clip; show `intent/affect/plan` debug tiles.  
4. **Scene 2**: trigger scheduled nudge; accept user choice; fire SMS; display event stream.  
5. **Scene 3**: show metrics card (“Today’s touches”) and adherence.  
6. **Close**: highlight continuity (“My Girl saved as quick‑lift”), schedule tomorrow’s BA.  

---

## “Today’s Summary” (example payload)
```json
{
  "event_name": "ce.metrics_snapshot",
  "user_id": "u_123",
  "trace_id": "t-8f2c",
  "session_id": "s_456",
  "ts": "2025-09-02T23:30:00Z",
  "metadata": {
    "touches": {"reminiscence": true, "ba": true, "social_bridge": true},
    "mood_shift": 1,
    "affect_after_empathy_drop": -0.22,
    "adherence": {"scheduled": 2, "completed": 2},
    "notes_saved": ["song: My Girl"]
  }
}
```
