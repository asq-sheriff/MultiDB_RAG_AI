# Emotional Health Metrics — Implementation Guide for Lilo (US · Japan · Europe)
*Prepared: 2025-09-04*


This guide shows **what to measure**, **how to score**, and **how to wire events** so your AI companion can track *emotional health* responsibly across the US, Japan, and Europe. It includes official links, licensing notes, UX copy, and JSON schemas you can paste into your codebase.

---

## TL;DR — Pilot battery (pragmatic)
- **Baseline + 90 days:** PHQ-8 (or PHQ-9), GAD-7, **WHO-5** (well‑being), **LSNS‑6** (social connectedness), **EQ‑5D‑5L** *(optional QoL utility)*.
- **Weekly:** WHO-5 (5 items, ~1 min) + micro check-in in‑conversation (2–3 items).
- **Biweekly:** PHQ‑8/9 + GAD‑7 (alternating weeks for seniors if burden is a concern).
- **Monthly:** WEMWBS (or **MHC‑SF**), plus **LSNS‑6** (if social support is a focus).
- **Contextual/adhoc:** PANAS (affect snapshot), PSS (stress), GDS‑15 (for 65+).

> Localizations exist for **Japanese** and multiple **European** languages for most instruments listed. See each tool’s link for licensing and translations.

---

## At‑a‑glance: instruments, purpose, time, links
| Instrument | Domain | Items / Time | Licensing & Notes | Official / Primary Links |
|---|---|---:|---|---|
| **PHQ‑9 / PHQ‑8** | Depressive symptoms | 9 (or 8) / 2–3 min | Free to use; see scoring/cutoffs; PHQ‑8 omits suicidality item for some settings | [PHQ Screeners](https://www.phqscreeners.com/); [APA PHQ‑9 PDF](https://www.apa.org/depression-guideline/patient-health-questionnaire.pdf) |
| **GAD‑7** | Anxiety | 7 / ~2 min | Free; standard cutoffs | [GAD‑7 PDF (ADAA)](https://adaa.org/sites/default/files/GAD-7_Anxiety-updated_0.pdf) |
| **PROMIS Anxiety/Depression** | Emotional distress (CAT/short forms) | 4–8 / 1–3 min | HealthMeasures; T‑scores; CAT available | [PROMIS overview](https://www.healthmeasures.net/explore-measurement-systems/promis); [Adult measures](https://www.healthmeasures.net/explore-measurement-systems/promis/intro-to-promis/list-of-adult-measures) |
| **WHO‑5** | Well‑being (positive) | 5 / ~1 min | Free; 0–100 transform; many translations | [WHO overview](https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01) |
| **WEMWBS / SWEMWBS** | Mental well‑being | 14 / 7 / 2–4 min | **License required** for commercial use | [Warwick WEMWBS](https://warwick.ac.uk/services/innovations/wemwbs/); [How it works](https://warwick.ac.uk/services/innovations/wemwbs/how/) |
| **MHC‑SF** | Flourishing (emotional/psych/social) | 14 / 3–4 min | Research‑friendly; cite Keyes | [MHC‑SF overview (UNC)](https://peplab.web.unc.edu/wp-content/uploads/sites/18901/2018/11/MHC-SFoverview.pdf) |
| **SWLS** | Life satisfaction | 5 / ~1 min | Research‑friendly; widely used | [SWLS (Diener)](https://labs.psychology.illinois.edu/~ediener/SWLS.html) |
| **SF‑36 / RAND‑36 (MHI‑5 subscale)** | HRQoL (+ mental health) | 36 / 7–10 min | Free via **RAND** (not Optum SF‑36); scoring guide | [RAND SF‑36 scoring](https://www.rand.org/health-care/surveys_tools/mos/36-item-short-form/scoring.html) |
| **WHOQOL‑BREF** | QoL (psych domain included) | 26 / 5–8 min | WHO; cross‑cultural; scoring guide | [WHOQOL‑BREF](https://www.who.int/tools/whoqol/whoqol-bref) |
| **EQ‑5D‑5L (+ VAS)** | Health utility (+ anxiety/depression dimension) | 5+VAS / 2–3 min | **EuroQol registration**; country value sets | [EuroQol EQ‑5D‑5L](https://euroqol.org/information-and-support/euroqol-instruments/eq-5d-5l/) |
| **PANAS** | Positive/negative affect | 20 / 2–3 min | Free for research; short forms exist | [PANAS PDF](https://ogg.osu.edu/media/documents/MB%20Stream/PANAS.pdf) |
| **PSS‑10** | Perceived stress | 10 / ~2 min | Copyright © Cohen; use per terms | [PSS PDF](https://www.slu.edu/medicine/family-medicine/-pdf/perceived-stress-scale.pdf) |
| **LSNS‑6** | Social network size/isoln | 6 / ~2 min | Older adults focus; family & friends subscores | [LSNS‑6 (Boston College)](https://www.bc.edu/bc-web/schools/ssw/sites/lubben/description/versions-of-the-lsns.html) |
| **De Jong Gierveld (6‑item)** | Social & emotional loneliness | 6 / ~2 min | Cross‑national; scoring nuances | [Manual / 6‑item PDF](https://research.vu.nl/files/887976/2006%20RoA%20deJongGierveld%20vTilburg%206-item%20scale%20loneliness.pdf) |
| **GDS‑15** | Geriatric depression | 15 / 3–5 min | Senior‑friendly yes/no items | [Stanford GDS](https://web.stanford.edu/~yesavage/GDS.html) |
| **K6/K10** | Psychological distress | 6/10 / 1–3 min | Population surveillance; cutoffs vary | [K6 (Harvard/NCS)](https://www.hcp.med.harvard.edu/ncs/ftpdir/k6/Self%20admin_K6.pdf); [Scoring FAQ](https://www.hcp.med.harvard.edu/ncs//ftpdir/k6/Scoring_K6_K10.pdf) |
| **CES‑D / CESD‑R** | Depressive symptoms (epidemiologic) | 20 / 4–6 min | Research; cutoffs around 16+ commonly used | [APA CES‑D](https://www.apa.org/depression-guideline/epidemiologic-studies-scale.pdf) |

> **Localization:** WHO‑5, PHQ‑9/8, GAD‑7, LSNS‑6, WHOQOL‑BREF and EQ‑5D‑5L have **Japanese** and **EU language** versions. WEMWBS requires licensing for translations.

---

## Scoring & app logic (copy‑paste ready)

### PHQ‑9 / PHQ‑8
- **Score:** Sum item scores (0–3 each). PHQ‑9 total 0–27; PHQ‑8 total 0–24. Cutoffs 5/10/15/20 for PHQ‑9 severity.  
- **Suicidality:** PHQ‑9 item 9 is *risk‑relevant* → always run safety policy if score ≥ 1.  
- **Emit events:** `ce.metrics_snapshot` (score), `ce.safety_flag` (if thresholds), `survey.response.saved`.  
Links: [PHQ site](https://www.phqscreeners.com/), [APA PHQ‑9 PDF](https://www.apa.org/depression-guideline/patient-health-questionnaire.pdf).

**Pseudocode**
```python
phq_total = sum(items)  # 0..27 (PHQ-9); 0..24 (PHQ-8)
severity = bucket(phq_total, [0,5,10,15,20,27])
if item9 >= 1: emit("ce.safety_flag", {"safety":"orange"})
emit("survey.response.saved", {"instrument":"phq9","score":phq_total,"severity":severity})
```

### GAD‑7
- **Score:** Sum (0–21). 5/10/15 = mild/moderate/severe.  
- **Use:** Anxiety monitoring in weekly/biweekly cadence.  
Link: [ADAA GAD‑7 PDF](https://adaa.org/sites/default/files/GAD-7_Anxiety-updated_0.pdf).

### WHO‑5
- **Score:** Sum raw (0–25), multiply by 4 → **0–100** (higher = better). ≤ 50 often used as low well‑being trigger.  
- **Use:** Weekly well‑being pulse; culturally robust (incl. Japan/EU).  
Link: [WHO-5 overview](https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01).

### WEMWBS / SWEMWBS
- **Score:** Sum items → 14–70 (WEMWBS). Meaningful change ≈ **3+ points** (program-level).  
- **Licensing:** Required for commercial deployments.  
Links: [WEMWBS site](https://warwick.ac.uk/services/innovations/wemwbs/), [How it works](https://warwick.ac.uk/services/innovations/wemwbs/how/).

### PROMIS Anxiety/Depression
- **Score:** T‑scores (mean 50, SD 10). Use **HealthMeasures** scoring (short forms or CAT).  
Links: [PROMIS overview](https://www.healthmeasures.net/explore-measurement-systems/promis), [Adult measures](https://www.healthmeasures.net/explore-measurement-systems/promis/intro-to-promis/list-of-adult-measures).

### LSNS‑6
- **Score:** Sum across 6 items (0–30). Common **risk flag ≤ 12** (check program policy).  
Link: [BC LSNS versions](https://www.bc.edu/bc-web/schools/ssw/sites/lubben/description/versions-of-the-lsns.html).

### De Jong Gierveld (6‑item)
- **Score:** 2 sub‑scores (emotional/social) + total; uses agree/neutral/disagree mapping; see manual PDF for exact rules.  
Link: [6‑item scoring PDF](https://research.vu.nl/files/887976/2006%20RoA%20deJongGierveld%20vTilburg%206-item%20scale%20loneliness.pdf).

### GDS‑15 (65+)
- **Score:** 1 point per depressive answer; 0–4 normal; 5–8 mild; 9–11 moderate; 12–15 severe (program‑specific thresholds).  
Links: [Stanford GDS](https://web.stanford.edu/~yesavage/GDS.html).

### K6/K10
- **Score:** K6 sum 0–24 (reverse code per rules). **≥13** indicates probable serious mental illness in many studies.  
Links: [K6 questionnaire](https://www.hcp.med.harvard.edu/ncs/ftpdir/k6/Self%20admin_K6.pdf), [Scoring FAQ](https://www.hcp.med.harvard.edu/ncs//ftpdir/k6/Scoring_K6_K10.pdf).

### CES‑D / CESD‑R
- **Score:** Sum 0–60; **≥16** commonly used as depressive symptoms threshold in population studies.  
Links: [APA CES‑D](https://www.apa.org/depression-guideline/epidemiologic-studies-scale.pdf).

### SF‑36 / RAND‑36 (MHI‑5)
- **Score:** Per RAND manual; mental health subscale (MHI‑5) often used as a light proxy.  
Links: [RAND scoring](https://www.rand.org/health-care/surveys_tools/mos/36-item-short-form/scoring.html).

### WHOQOL‑BREF
- **Score:** 4 domains (incl. Psychological). Items 1–5 scale, transformed to 0–100 per domain; use WHO/US center guides.  
Links: [WHOQOL‑BREF](https://www.who.int/tools/whoqol/whoqol-bref).

### EQ‑5D‑5L (optional)
- **Score:** Profile (5 dimensions) + VAS. To compute **utility** you must apply a **country‑specific value set** (via EuroQol).  
Links: [EuroQol EQ‑5D‑5L](https://euroqol.org/information-and-support/euroqol-instruments/eq-5d-5l/).

### PANAS / PSS (contextual)
- **PANAS:** Positive & Negative affect (two sums).  
- **PSS‑10:** Reverse items 4, 5, 7, 8; sum to 0–40 (higher = more stress).  
Links: [PANAS PDF](https://ogg.osu.edu/media/documents/MB%20Stream/PANAS.pdf), [PSS PDF](https://www.slu.edu/medicine/family-medicine/-pdf/perceived-stress-scale.pdf).

---

## Where these fit in the app (cadence & triggers)
- **Onboarding (Day 0):** PHQ‑8/9, GAD‑7, WHO‑5, LSNS‑6, optional EQ‑5D‑5L.  
- **Weekly pulse:** WHO‑5 (5 items) during evening reflection flow.  
- **Biweekly:** Alternate **PHQ** and **GAD** to reduce burden (e.g., PHQ week A, GAD week B).  
- **Monthly:** WEMWBS or MHC‑SF for positive mental health; LSNS‑6 for social connectedness.  
- **Context triggers:** If affect high‑arousal (e.g., anxious), offer **GAD‑2** micro; if low well‑being, prompt WEMWBS next window.  
- **Seniors (65+):** Consider **GDS‑15** instead of PHQ‑9 if clinical team prefers a geriatric screener.

---

## Events & storage (aligns with analytics v1.1)
Use a dedicated event for any instrument submission and one for derived metrics snapshots.

```json
{
  "event_name": "survey.response.saved",
  "user_id": "u_123",
  "trace_id": "t-789",
  "ts": "2025-09-04T17:20:00Z",
  "instrument": "phq9",
  "version": "en-US:v1",
  "items": [0,1,1,2,1,2,0,1,0],
  "score": 8,
  "severity": "mild",
  "metadata": {"mode":"chat","locale":"en-US","window":"evening"}
}
```

Create/update a **metrics snapshot** after scoring:
```json
{
  "event_name": "ce.metrics_snapshot",
  "user_id": "u_123",
  "trace_id": "t-789",
  "ts": "2025-09-04T17:20:02Z",
  "metrics": {
    "phq9": 8,
    "gad7": null,
    "who5": 64,
    "wemwbs": null,
    "lsns6": 14
  }
}
```

**Recommended store (table/collection `survey_responses`)**
```json
{
  "user_id":"u_123",
  "instrument":"phq9",
  "lang":"ja-JP",
  "version":"v1",
  "administered_at":"2025-09-04T17:20:00Z",
  "channel":"chat",
  "responses":[0,1,2,1,0,1,1,0,0],
  "score":8,
  "subscores":null,
  "severity":"mild",
  "value_set":"",  // for EQ-5D only
  "consent_id":"c_456",
  "trace_id":"t-789"
}
```

---

## UX copy (friendly, senior‑aware)
- **Intro (baseline):** “To support you better, I have a **few short check‑ins** people often find helpful. It takes about **2–3 minutes**, and you can skip anything.”  
- **During survey:** “Thanks — short answers are perfect. If anything feels uncomfortable, say ‘skip’.”  
- **Close (normal):** “Saved. I’ll use this to tailor your check‑ins, and I’ll **never share** without your permission.”  
- **Close (flagged):** “Thanks for sharing that. I’m going to **slow down and check on you** a little more closely now. If you’d like, I can bring in a **human check‑in**.”

**Micro prompt (WHO‑5 weekly):**  
“Over the **last two weeks**, how often did you feel **cheerful/in good spirits**? (All the time → At no time)”

---

## Localization & licensing
- **Translations:** WHO‑5, PHQ‑9/8, GAD‑7, WHOQOL‑BREF, EQ‑5D‑5L, LSNS‑6 have validated translations (Japanese & EU languages).  
- **Commercial licensing:** **WEMWBS** requires a license for commercial use; **EQ‑5D** requires registration and a country **value set** for utility.  
- **Attribution:** Follow each instrument’s attribution guidance (owner, year, copyright).
- **Data minimization:** Store raw item arrays and total/subscores; avoid storing free‑text unless necessary.

---

## Dashboards & interpretation
- **Trend tiles:** PHQ‑9/GAD‑7 lines, WHO‑5 weekly bars, WEMWBS monthly points.  
- **Flags:** `phq9_item9>=1` (safety review), **K6≥13**, **LSNS‑6≤12**, **WHO‑5≤50** (program-specific thresholds).  
- **Program outcomes:** pre/post change on **WHO‑5**, proportion with **PHQ/GAD** category improvement, and change in **LSNS‑6**.

---

## Implementation notes per instrument (details)
- **PHQ‑8 vs PHQ‑9:** Prefer **PHQ‑8** for remote pilots if your clinical governance wants to avoid automated handling of suicidality in‑app; otherwise use PHQ‑9 with explicit **safety branch** when item 9 ≥ 1.  
- **EQ‑5D utility:** Don’t compute utility without the correct **country value set**; store profile + VAS and compute utility server‑side after configuration.  
- **SF‑36/RAND‑36:** Use **RAND** scoring resources (public) and include the **MHI‑5** mental health subscale for a light mental health snapshot.  
- **PROMIS CAT:** If you enable CAT, host the **HealthMeasures** scoring service or use their recommended providers; store the **T‑scores**.

---

## References & official resources
- PROMIS / HealthMeasures: https://www.healthmeasures.net/  
- PHQ‑9/PHQ‑8: https://www.phqscreeners.com/ · [APA PHQ‑9 PDF](https://www.apa.org/depression-guideline/patient-health-questionnaire.pdf)  
- GAD‑7: [ADAA PDF](https://adaa.org/sites/default/files/GAD-7_Anxiety-updated_0.pdf)  
- WHO‑5: [WHO overview](https://www.who.int/publications/m/item/WHO-UCN-MSD-MHE-2024.01)  
- WEMWBS: https://warwick.ac.uk/services/innovations/wemwbs/  
- MHC‑SF: [Overview PDF](https://peplab.web.unc.edu/wp-content/uploads/sites/18901/2018/11/MHC-SFoverview.pdf)  
- SWLS: https://labs.psychology.illinois.edu/~ediener/SWLS.html  
- SF‑36/RAND‑36: https://www.rand.org/health-care/surveys_tools/mos/36-item-short-form/scoring.html  
- WHOQOL‑BREF: https://www.who.int/tools/whoqol/whoqol-bref  
- EQ‑5D‑5L: https://euroqol.org/information-and-support/euroqol-instruments/eq-5d-5l/  
- PANAS: [Scale PDF](https://ogg.osu.edu/media/documents/MB%20Stream/PANAS.pdf) · PSS: [PSS‑10 PDF](https://www.slu.edu/medicine/family-medicine/-pdf/perceived-stress-scale.pdf)  
- LSNS‑6: https://www.bc.edu/bc-web/schools/ssw/sites/lubben/description/versions-of-the-lsns.html  
- De Jong Gierveld: [6‑item PDF](https://research.vu.nl/files/887976/2006%20RoA%20deJongGierveld%20vTilburg%206-item%20scale%20loneliness.pdf)  
- GDS‑15: https://web.stanford.edu/~yesavage/GDS.html  
- K6/K10: [K6 questionnaire](https://www.hcp.med.harvard.edu/ncs/ftpdir/k6/Self%20admin_K6.pdf) · [Scoring FAQ](https://www.hcp.med.harvard.edu/ncs//ftpdir/k6/Scoring_K6_K10.pdf)  
- CES‑D: [APA CES‑D PDF](https://www.apa.org/depression-guideline/epidemiologic-studies-scale.pdf)

---

### Appendix: Minimal JSON Schema (survey response)
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "survey.response.saved",
  "type": "object",
  "properties": {
    "event_name": {"const":"survey.response.saved"},
    "user_id": {"type":"string"},
    "trace_id": {"type":"string"},
    "ts": {"type":"string","format":"date-time"},
    "instrument": {"type":"string","enum":[
      "phq9","phq8","gad7","who5","wemwbs","mhc_sf","swls","sf36","whoqol_bref",
      "eq5d_5l","panas","pss10","lsns6","dejong6","gds15","k6","k10","cesd"
    ]},
    "version": {"type":"string"},
    "lang": {"type":"string"},
    "items": {"type":"array","items":{"type":["integer","number","string"]}},
    "score": {"type":["number","integer","null"]},
    "subscores": {"type":["object","null"]},
    "severity": {"type":["string","null"]},
    "metadata": {"type":"object","additionalProperties":true}
  },
  "required": ["event_name","user_id","trace_id","ts","instrument","items"]
}
```

---

**Implementation checklist**
- [ ] Choose battery & cadence by cohort (US / EU / Japan).  
- [ ] Confirm **licensing** (WEMWBS, EQ‑5D) and **translations**.  
- [ ] Implement scoring helpers + **unit tests** per instrument.  
- [ ] Emit `survey.response.saved` and `ce.metrics_snapshot` with deterministic ordering.  
- [ ] Add flags/alerts (PHQ item 9, K6≥13, LSNS‑6≤12, WHO‑5≤50).  
- [ ] Render compassionate UX copy; allow **skip** at any point.  
- [ ] Store **consent** and honor **erasure** requests.

---

*This guide complements your Conversation Engine and Analytics v1.1. It keeps the stack boring (audit, consent, encryption) and the experience kind (short, localized, senior‑friendly).* 
