# Persona Schema — Postgres + pgvector (Lilo Senior Empathic Companion)

*Goal:* A production‑ready relational + vector schema that **encodes the chatbot’s persona** (senior‑specialist mental‑health companion), including tone, boundaries, prompts, knowledge cards, safety playbooks, and phrase banks — all versioned, auditable, and retrievable at runtime.

*Stack assumptions:* Postgres 15/16, `pgvector` 0.6+, Python services (FastAPI/LangGraph), BGE‑large‑en‑v1.5 (1024‑D) for embeddings.

---

## 0) Bootstrap (one‑time)

```sql
CREATE EXTENSION IF NOT EXISTS vector; -- pgvector
CREATE SCHEMA IF NOT EXISTS persona;
CREATE SCHEMA IF NOT EXISTS kb;       -- knowledge cards (psychoeducation/copings)
CREATE SCHEMA IF NOT EXISTS policy;   -- SAFE-T, tools, allow/deny
CREATE SCHEMA IF NOT EXISTS phrasing; -- empathy lexicon
CREATE SCHEMA IF NOT EXISTS eval;     -- OSCEs, gold responses (optional)
```

---

## 1) Core persona & versioning

> One persona can have multiple versions; the app selects the **active** version per tenant/experiment. Prompts, styles, phrase banks, and policies hang off `persona_version`.

```sql
-- Primary identity
CREATE TABLE persona.persona (
  persona_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key                 TEXT UNIQUE NOT NULL,                    -- e.g., 'lilo_senior_empathic'
  display_name        TEXT NOT NULL,                           -- e.g., 'Lilo — Senior Empathic Companion'
  description         TEXT,
  default_locale      TEXT NOT NULL DEFAULT 'en-US',
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
  active_version_id   UUID                                      -- FK below
);

-- Versioning for prompts/policies/phrases
CREATE TABLE persona.persona_version (
  persona_version_id  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  persona_id          UUID NOT NULL REFERENCES persona.persona(persona_id) ON DELETE CASCADE,
  version             TEXT NOT NULL,                            -- semver like '1.0.0'
  status              TEXT NOT NULL DEFAULT 'active',           -- active|draft|archived
  notes               TEXT,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Bind active version
ALTER TABLE persona.persona
  ADD CONSTRAINT persona_active_version_fk
  FOREIGN KEY (active_version_id) REFERENCES persona.persona_version(persona_version_id);
```

---

## 2) System prompts & style parameters

> Prompts are structured fragments (blocks) used by orchestration (e.g., ingress disclosure, default system prompt, crisis prompt). Style parameters keep **NURSE/OARS** weights and brevity targets.

```sql
CREATE TABLE persona.prompt_block (
  prompt_block_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  persona_version_id  UUID NOT NULL REFERENCES persona.persona_version(persona_version_id) ON DELETE CASCADE,
  name                TEXT NOT NULL,      -- e.g., 'system_default', 'ingress_disclosure', 'refusal_medical'
  locale              TEXT NOT NULL DEFAULT 'en-US',
  content_md          TEXT NOT NULL,      -- markdown/plaintext with placeholders: {{policy}}, {{tone}}, etc.
  weight              INT  NOT NULL DEFAULT 100,  -- for retrieval or stitching priority
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ON persona.prompt_block (persona_version_id, name, locale);

CREATE TABLE persona.style_params (
  persona_version_id  UUID PRIMARY KEY REFERENCES persona.persona_version(persona_version_id) ON DELETE CASCADE,
  reading_grade_target SMALLINT NOT NULL DEFAULT 7,
  max_sentences        SMALLINT NOT NULL DEFAULT 3,
  prefer_reflection_ratio NUMERIC(3,2) NOT NULL DEFAULT 0.60,  -- share of reflective turns before advice
  nurse_weights        JSONB NOT NULL DEFAULT '{"Name":1,"Understand":1,"Respect":1,"Support":1,"Explore":1}',
  mi_oars_weights      JSONB NOT NULL DEFAULT '{"Open":1,"Affirm":1,"Reflect":1,"Summarize":1}',
  tone_tags            TEXT[] NOT NULL DEFAULT ARRAY['warm','calm','plain-language']
);
```

---

## 3) Phrase bank (empathy lexicon) with vectors

> Persona‑specific phrasing blocks: empathy, actions, and phrases‑to‑avoid. We store embeddings to fetch **on‑tone** lines by query/context.

```sql
CREATE TABLE phrasing.phrase_bank (
  phrase_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  persona_version_id  UUID NOT NULL REFERENCES persona.persona_version(persona_version_id) ON DELETE CASCADE,
  locale              TEXT NOT NULL DEFAULT 'en-US',
  kind                TEXT NOT NULL CHECK (kind IN ('empathy','action_copy','avoid','disclosure','escalation')),
  tags                TEXT[] NOT NULL DEFAULT '{}',            -- e.g., {'NURSE:Name','grief','late-night'}
  text                TEXT NOT NULL,
  embedder_id         TEXT NOT NULL DEFAULT 'bge-large-en-v1.5',
  dim                 INT  NOT NULL DEFAULT 1024 CHECK (dim = 1024),
  embedding           VECTOR(1024),                            -- L2-normalized cosine vectors
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ANN index for fast nearest-neighbor by cosine
CREATE INDEX phrase_bank_ivf_cos ON phrasing.phrase_bank USING ivfflat (embedding vector_cosine_ops) WITH (lists=100);
CREATE INDEX phrase_bank_tags_idx ON phrasing.phrase_bank USING GIN (tags);
```

---

## 4) Knowledge cards (psychoeducation + actions) with vectors

> Cards mirror your Canon Pack. They’re retrieval units with Do/Don’t, empathy samples, micro‑actions, escalation rules, and provenance.

```sql
CREATE TABLE kb.knowledge_card (
  kc_id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  persona_version_id  UUID NOT NULL REFERENCES persona.persona_version(persona_version_id) ON DELETE CASCADE,
  locale              TEXT NOT NULL DEFAULT 'en-US',
  topic               TEXT NOT NULL,                             -- e.g., 'Grief at night'
  do_list             TEXT[] NOT NULL,
  dont_list           TEXT[] NOT NULL,
  empathy_examples    TEXT[] NOT NULL,
  action_examples     TEXT[] NOT NULL,
  escalation_rules    JSONB NOT NULL,                            -- {triggers:[], playbook:'safe-t.v1'}
  sources             JSONB NOT NULL,                            -- [{name,url,as_of}]
  body_md             TEXT,                                      -- optional longer copy
  embedder_id         TEXT NOT NULL DEFAULT 'bge-large-en-v1.5',
  dim                 INT  NOT NULL DEFAULT 1024 CHECK (dim = 1024),
  embedding           VECTOR(1024),
  created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX kc_ivf_cos ON kb.knowledge_card USING ivfflat (embedding vector_cosine_ops) WITH (lists=200);
CREATE INDEX kc_topic_idx ON kb.knowledge_card (topic);
```

---

## 5) Safety policy: SAFE‑T playbooks, triggers, and tools

> Hard limits live in tables. The orchestrator composes responses only if allowed by policy. SAFE‑T scripts are **fixed text** by locale.

```sql
-- Tool catalog (what actions the agent can call)
CREATE TABLE policy.tool_catalog (
  tool_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  key                 TEXT UNIQUE NOT NULL,             -- 'breathing_timer', 'journaling', 'call_prompt', ...
  description         TEXT NOT NULL,
  params_schema_json  JSONB NOT NULL                    -- JSON Schema for tool params
);

-- Persona-specific allow/deny & limits per tool
CREATE TABLE policy.tool_policy (
  persona_version_id  UUID NOT NULL REFERENCES persona.persona_version(persona_version_id) ON DELETE CASCADE,
  tool_id             UUID NOT NULL REFERENCES policy.tool_catalog(tool_id) ON DELETE CASCADE,
  allowed             BOOLEAN NOT NULL DEFAULT TRUE,
  max_per_turn        SMALLINT NOT NULL DEFAULT 1,
  contexts            TEXT[] NOT NULL DEFAULT ARRAY['default'], -- e.g., {'default','late-night'}
  PRIMARY KEY (persona_version_id, tool_id)
);

-- Risk triggers (regex and lexical cues)
CREATE TABLE policy.risk_trigger (
  trigger_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  persona_version_id  UUID NOT NULL REFERENCES persona.persona_version(persona_version_id) ON DELETE CASCADE,
  locale              TEXT NOT NULL DEFAULT 'en-US',
  pattern_regex       TEXT NOT NULL,                  -- server compiles to RE2/PCRE
  severity            TEXT NOT NULL CHECK (severity IN ('low','med','high')),
  notes               TEXT
);

-- SAFE-T scripts (fixed language; no free-form generation)
CREATE TABLE policy.safet_script (
  script_id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  persona_version_id  UUID NOT NULL REFERENCES persona.persona_version(persona_version_id) ON DELETE CASCADE,
  locale              TEXT NOT NULL DEFAULT 'en-US',
  name                TEXT NOT NULL,                  -- 'opening', 'resource_offer', 'handoff', 'end_session'
  copy_md             TEXT NOT NULL
);

-- Crisis resources per region (988, local aging services)
CREATE TABLE policy.resource_directory (
  resource_id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  locale              TEXT NOT NULL DEFAULT 'en-US',
  region_code         TEXT NOT NULL,                  -- e.g., 'US', 'US-CA'
  kind                TEXT NOT NULL,                  -- 'crisis_hotline','eldercare_locator','aps'
  label               TEXT NOT NULL,
  url                 TEXT,
  phone               TEXT,
  active              BOOLEAN NOT NULL DEFAULT TRUE
);
```

---

## 6) Golden responses & few‑shot seeds (optional but useful)

> Store persona‑vetted exemplar turns, retrievable by topic/intent.

```sql
CREATE TABLE eval.gold_response (
  gold_id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  persona_version_id  UUID NOT NULL REFERENCES persona.persona_version(persona_version_id) ON DELETE CASCADE,
  locale              TEXT NOT NULL DEFAULT 'en-US',
  intent              TEXT NOT NULL,                 -- 'validate_then_nudge', 'refusal_medical', ...
  user_utterance      TEXT NOT NULL,
  assistant_reply     TEXT NOT NULL,
  tags                TEXT[] NOT NULL DEFAULT '{}',
  embedder_id         TEXT NOT NULL DEFAULT 'bge-large-en-v1.5',
  dim                 INT  NOT NULL DEFAULT 1024 CHECK (dim = 1024),
  embedding           VECTOR(1024)
);

CREATE INDEX gold_ivf_cos ON eval.gold_response USING ivfflat (embedding vector_cosine_ops) WITH (lists=100);
```

---

## 7) Embedding refresh workflow

> Content changes should trigger re‑embedding; avoid big triggers that call models. Use a queue table and a worker.

```sql
CREATE TABLE kb.embedding_queue (
  queue_id            BIGSERIAL PRIMARY KEY,
  target_table        TEXT NOT NULL,    -- 'kb.knowledge_card' | 'phrasing.phrase_bank' | 'eval.gold_response'
  target_pk           UUID NOT NULL,
  requested_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  processed_at        TIMESTAMPTZ
);

-- Example trigger to enqueue when KC body changes
CREATE OR REPLACE FUNCTION kb.enqueue_kc_embedding() RETURNS trigger AS $$
BEGIN
  INSERT INTO kb.embedding_queue (target_table, target_pk) VALUES ('kb.knowledge_card', NEW.kc_id);
  RETURN NEW;
END; $$ LANGUAGE plpgsql;

CREATE TRIGGER trg_kc_embed_enqueue
AFTER INSERT OR UPDATE OF topic, body_md, empathy_examples, action_examples
ON kb.knowledge_card
FOR EACH ROW EXECUTE FUNCTION kb.enqueue_kc_embedding();
```

A worker (Python) reads from `embedding_queue`, computes BGE embeddings with **query‑prefix** for search (e.g., `"Represent this sentence for searching relevant passages: " + text`), **L2‑normalizes**, and writes back to the `embedding` column.

---

## 8) Runtime: fetching the persona and composing a reply

**Step A — Load persona config**

```sql
-- Get active version and style
SELECT p.persona_id, pv.persona_version_id, sp.*
FROM persona.persona p
JOIN persona.persona_version pv ON pv.persona_version_id = p.active_version_id
LEFT JOIN persona.style_params sp ON sp.persona_version_id = pv.persona_version_id
WHERE p.key = 'lilo_senior_empathic';
```

**Step B — Retrieve prompt blocks**

```sql
SELECT name, content_md
FROM persona.prompt_block
WHERE persona_version_id = $1 AND locale = 'en-US'
ORDER BY weight DESC;
```

**Step C — Semantic retrieval for knowledge + phrasing**

```sql
-- Assume :qvec is a 1024-D L2-normalized vector for the user turn
-- 1) Top K knowledge cards
SELECT kc_id, topic, 1 - (embedding <#> :qvec) AS sim, empathy_examples, action_examples, escalation_rules
FROM kb.knowledge_card
WHERE persona_version_id = $1 AND locale = 'en-US'
ORDER BY embedding <#> :qvec
LIMIT 4;

-- 2) Top empathy lines (matching tags from KC or inferred emotion)
SELECT text, tags, 1 - (embedding <#> :qvec) AS sim
FROM phrasing.phrase_bank
WHERE persona_version_id = $1 AND kind = 'empathy'
ORDER BY embedding <#> :qvec
LIMIT 8;
```

**Step D — Check allowed tools**

```sql
SELECT tc.key, tp.allowed, tp.max_per_turn
FROM policy.tool_catalog tc
JOIN policy.tool_policy tp ON tp.tool_id = tc.tool_id
WHERE tp.persona_version_id = $1 AND tp.allowed = TRUE;
```

**Step E — Crisis check (regex prefilter)**

```sql
SELECT severity, pattern_regex
FROM policy.risk_trigger
WHERE persona_version_id = $1 AND locale = 'en-US';
-- App applies these patterns; if match → switch to SAFE-T scripts below.
```

**Step F — SAFE‑T scripted copy**

```sql
SELECT name, copy_md
FROM policy.safet_script
WHERE persona_version_id = $1 AND locale = 'en-US'
ORDER BY name;
```

---

## 9) Example inserts (seed the persona)

```sql
-- Persona + version
INSERT INTO persona.persona (key, display_name, description)
VALUES ('lilo_senior_empathic','Lilo — Senior Empathic Companion','Emotion-aware, non-clinical senior support with safety-first policies')
RETURNING persona_id;

INSERT INTO persona.persona_version (persona_id, version, notes)
VALUES ($persona_id, '1.0.0', 'Launch version')
RETURNING persona_version_id;

UPDATE persona.persona SET active_version_id = $persona_version_id WHERE persona_id = $persona_id;

-- Prompts
INSERT INTO persona.prompt_block (persona_version_id, name, content_md)
VALUES
($pv,'system_default', 'You are Lilo, an AI companion for older adults. Disclose you are not a clinician. Use NURSE empathy, plain language, short replies. Offer at most one low-risk action. Never give medical or medication advice. Escalate to crisis script on risk.'),
($pv,'ingress_disclosure','I’m an AI companion, not a clinician. I can listen, support with simple steps, and help reach a person if needed.'),
($pv,'refusal_medical','I can’t provide medical or medication advice. Would you like help preparing questions for your clinician?');

-- Style
INSERT INTO persona.style_params (persona_version_id, reading_grade_target, max_sentences)
VALUES ($pv, 7, 3);

-- Phrase bank examples
INSERT INTO phrasing.phrase_bank (persona_version_id, kind, tags, text)
VALUES
($pv,'empathy', ARRAY['NURSE:Name','loneliness','late-night'], 'Evenings can feel extra quiet.'),
($pv,'empathy', ARRAY['NURSE:Understand','grief'], 'Many people feel waves of grief after a big loss.'),
($pv,'avoid',   ARRAY['tone'], 'Calm down.');

-- Knowledge card (grief at night)
INSERT INTO kb.knowledge_card (persona_version_id, topic, do_list, dont_list, empathy_examples, action_examples, escalation_rules, sources)
VALUES (
  $pv,
  'Bereavement (night-time)',
  ARRAY['Name the loss','Invite a memory','Offer one gentle ritual'],
  ARRAY['No timelines','No clichés','No diagnosis'],
  ARRAY['Nights can bring back a lot.','Your love shows in how much you miss them.'],
  ARRAY['2-minute breathing','Memory journal','Call a trusted person tomorrow'],
  '{"triggers":["self-harm intent","hopelessness+plan"],"playbook":"safe-t.v1"}',
  '[{"name":"NIA Coping With Grief","url":"https://www.nia.nih.gov/","as_of":"2025-07-15"}]'::jsonb
);

-- Tools
INSERT INTO policy.tool_catalog (key, description, params_schema_json) VALUES
('breathing_timer','Guide a timed breathing exercise','{"type":"object","properties":{"seconds":{"type":"integer"},"pattern":{"enum":["box","paced"]}},"required":["seconds"]}'),
('journaling','Prompt for short writing','{"type":"object","properties":{"kind":{"enum":["worry_shelf","gratitude","memory"]},"lines":{"type":"integer"}}}'),
('call_prompt','Invite a call to a trusted person','{"type":"object","properties":{"contact_hint":{"enum":["family","friend","staff"]}}}');

INSERT INTO policy.tool_policy (persona_version_id, tool_id, allowed)
SELECT $pv, tool_id, TRUE FROM policy.tool_catalog;

-- SAFE-T copy (skeleton)
INSERT INTO policy.safet_script (persona_version_id, name, copy_md)
VALUES
($pv,'opening', 'I’m not a clinician, but I care about your safety. If you’re in danger or thinking of harming yourself, you can call or text 988 for immediate support. Would you like me to help you reach someone you trust or share local resources?'),
($pv,'resource_offer', 'Here are ways to get help now: **988** (call/text/chat). I can also share local options.'),
($pv,'handoff', 'With your okay, I can alert a trusted person or staff now.'),
($pv,'end_session', 'I’m here when you need me. You’re not alone.');
```

---

## 10) Query patterns you’ll actually use

**A) Build a response kit for a user turn**

```sql
-- Inputs: :pv (persona_version_id), :qvec (1024-D vector), :locale
WITH kc AS (
  SELECT kc_id, topic, empathy_examples, action_examples, escalation_rules,
         1 - (embedding <#> :qvec) AS sim
  FROM kb.knowledge_card
  WHERE persona_version_id = :pv AND locale = :locale
  ORDER BY embedding <#> :qvec LIMIT 3
), em AS (
  SELECT text AS empathy_text, 1 - (embedding <#> :qvec) AS sim
  FROM phrasing.phrase_bank
  WHERE persona_version_id = :pv AND kind='empathy' AND locale = :locale
  ORDER BY embedding <#> :qvec LIMIT 5
)
SELECT * FROM kc, em;  -- app stitches best empathy_text + one action from KC
```

**B) Enforce “one tool per turn”**

```sql
SELECT key FROM policy.tool_catalog tc
JOIN policy.tool_policy tp ON tp.tool_id = tc.tool_id
WHERE tp.persona_version_id = :pv AND tp.allowed = TRUE
ORDER BY key;
```

**C) Crisis detection (pre‑gen + post‑gen)**
Fetch regex patterns from `policy.risk_trigger` once per session; apply in app. On match, skip generation and serve `policy.safet_script` copy.

---

## 11) Indexing & performance notes

* Use `ivfflat` with `vector_cosine_ops`; set `lists=100–400` depending on corpus size (start 200 for knowledge cards).
* Keep vectors **L2‑normalized** at write time for cosine distance.
* Batch embed phrase banks and KCs (32–128 per call) for speed.
* Partition by `persona_version_id` if you maintain many versions concurrently.
* Enable `RLS` for edit/admin isolation in multi‑tenant setups.

---

## 12) Governance & audit

* Every table carries `persona_version_id` → runbooks can diff versions before/after changes.
* Store source provenance in `kb.knowledge_card.sources` and include `as_of` dates.
* Log orchestration decisions separately (not covered here) with minimal PHI; link back to persona version & KC IDs used.

---

## 13) What this gives you

* **Determinism:** persona behavior is driven by database content (prompts, policies, scripts), not hidden prompt blobs.
* **Retrievability:** empathy phrasing and knowledge are fetched semantically with pgvector, keeping tone consistent.
* **Safety:** SAFE‑T scripts and tool allow/deny live in policy tables; generation is constrained by data, not just prompts.
* **Versioning:** switch personas or A/B test versions with one pointer flip.

— End of v1 —
