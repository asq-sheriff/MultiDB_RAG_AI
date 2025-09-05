# Final Recommendation — Frontend Build & Test Tooling (Therapeutic AI Platform)
---

## 1) Executive summary

* **Build the frontend with:** **Windsurf (Enterprise Hybrid)** — use its **Cascade** agent for safe, reviewable multi‑file changes across your **mobile-first** codebase: **React Native + Expo (Tamagui or RN Paper for tokens)** and, for web, **React + TypeScript + Mantine v7**. All agent indexes/memories/audit artifacts stay **inside your tenant** in Hybrid.
* **Keep Claude Code on backend/contracts:** Use Claude Code to drive **OpenAPI/Proto** changes, gateway policy, RBAC, and to generate a typed **TS SDK** consumed by the web app.
* **Test the UI with:** **Playwright + Applitools Eyes + axe‑core.** Playwright handles cross‑browser e2e (Chromium, Firefox, WebKit); Applitools adds Visual AI diffs (large fonts/contrast and crisis visuals) and **axe‑core** enforces WCAG.
* **Why it fits:** Meets your constraints (strict CSP, no client‑side PHI, HTTPS‑only voice, senior‑first accessibility), supports HIPAA posture, and gives auditable PRs with human‑in‑the‑loop gates.

---

## 2) Target stack & ownership model

| Layer                                                                                       | Primary tool                           | What it owns                                                                                               | Notes                                                     |
| ------------------------------------------------------------------------------------------- | -------------------------------------- | ---------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| API contracts & backend services                                                            | **Claude Code**                        | OpenAPI/GraphQL, gateway routes, RBAC/consent/audit, typed SDK generation                                  | Contract‑first, repo‑wide reasoning over Go/Python/infra. |
| **Frontend UI — Web (React 18 + TS + Mantine v7) & Mobile (React Native + Expo + Tamagui)** | **Windsurf (Cascade)**                 | Components & screens, theming/token refactors, accessibility passes, CSP‑safe/web + mobile‑secure patterns | Autonomous **multi‑file** edits with review checkpoints.  |
| Quality gates                                                                               | **Playwright + Applitools + axe‑core** | Cross‑browser e2e, visual regression, accessibility                                                        | Neutral, deterministic checks in CI/CD.                   |

---

## 3) How this maps to your non‑negotiables

* **CSP & Storage:** Enforce strict `Content‑Security‑Policy` and **forbid IndexedDB/WebSQL**. Cascade recipes codify lint rules + CI checks to block regressions.
* **No client‑side PHI:** UI stores only non‑PHI ephemeral state (auth token, UI prefs); PHI stays server‑side behind gateway and consent/audit services.
* **Senior‑first accessibility:** Default large font sizes, high contrast, visible focus outlines, full keyboard/ARIA coverage; visual diffs validate crisis palettes and banners.
* **Crisis UI flows:** Emergency FAB always visible; Crisis Modal overlays with explicit actions and auto‑logging; Playwright/axe snapshots cover each state.
* **HTTPS‑only voice:** Voice input enabled via secure contexts and gated by user preference.

---

## 4) Implementation plan (30/60/90)

### Day 0–7 (Foundation)

1. **Pick Windsurf Enterprise Hybrid**; connect SSO (SAML). Enable **zero‑data‑retention** and create a repo‑root **ignore** file to fence PHI‑touching paths from agent access.
2. Monorepo layout:

   ```
   /contracts/            # OpenAPI/GraphQL schemas
   /packages/api-sdk/     # Generated TS client (npm internal)
   /apps/web/             # Frontend (Vite or Next) + Mantine v7
   /apps/gateway/         # CSP, authn/z headers, filters
   /services/*            # Go/Python microservices
   /tests/e2e/            # Playwright + Applitools + axe
   ```
3. CI policy: PRs labeled by tool of record (`tool:claude` vs `tool:windsurf`), required checks = unit + e2e + visual + a11y.

### Day 8–30 (Contracts → SDK → UI)

1. **Claude Code**: Add/modify endpoints (e.g., `POST /alerts/emergency`, consent read/ack), regenerate server stubs and **typed TS SDK**.
2. **Windsurf (Cascade)**: Upgrade `@org/api-sdk`, refactor UI to SDK calls (no ad‑hoc `fetch`).
3. Implement **Emergency FAB** and **Crisis Modal**; wire to gateway/consent/audit.
4. Add e2e specs with **axe assertions** + **Eyes** snapshots for: *default*, *crisis\_open*, *error*, *success*.

### Day 31–60 (Hardening & Accessibility)

* Theming pass to **Mantine v7 tokens**; codemods for typography/contrast.
* CSP hardening: ban inline eval, ensure `connect‑src` only to gateway; add e2e header assertions.
* Build hygiene: Vite prod **sourcemaps off**, chunking, HTTPS dev server.

### Day 61–90 (Operations & scale)

* Visual baselines for all critical screens (Applitools branches per env).
* Error budgets: flake rate <1%, a11y violations = 0 blocker, 0 critical.
* Playwright trace retention on failures; dashboard in CI.

---

## 5) Windsurf Cascade — ready‑to‑run recipes

> Paste into Windsurf as a **Change Plan**; it will propose diffs and open a PR.

**Recipe A — CSP & Storage Sweep**

1. Search entire web app for `localStorage`, `sessionStorage`, `indexedDB`, `openDatabase`; remove/replace to enforce policy.
2. Add ESLint rules and a CI script to fail on banned storage APIs.
3. Tighten `vite.config` to disable prod sourcemaps; assert CSP headers via e2e test.

**Recipe B — Emergency & Crisis UI**

1. Create `components/EmergencyFab.tsx`, `components/CrisisModal.tsx`, `features/alerts/useCreateEmergency.ts`.
2. Apply **Mantine v7** tokens for large typography and high contrast.
3. Add Playwright specs with **axe** and **Applitools** snapshots across states.

**Recipe C — Accessibility Pass**

* Add keyboard traps/esc handling, focus outlines, ARIA roles/labels.
* Lint for alt‑text and color contrast; add unit tests for `prefers-reduced-motion`.

---

## 6) CI/CD blueprint (GitHub Actions sketch)

```yaml
name: ci
on: [pull_request]
jobs:
  web:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci
      - run: npm run -w packages/api-sdk build
      - run: npm run -w apps/web typecheck && npm run -w apps/web build
      - run: npx playwright install --with-deps
      - run: npm run -w tests/e2e test:ci
        env:
          APPLITOOLS_API_KEY: ${{ secrets.APPLITOOLS_API_KEY }}
```

**Required checks:** `typecheck`, unit tests, Playwright (w/ traces), **axe** violations = fail, **Applitools** diff review.

---

## 7) Governance & data minimization

* **Hybrid deployment**: indexes/memories/audit logs stay in your cloud; only outbound tunnel to compute.
* **Synthetic fixtures** only; no real PHI in tests or agent context.
* **Auditability**: each PR includes `changeplan.md` summarizing intent, touched files, risk controls.
* **Access control**: SSO/SAML, scoped seats, and zero‑retention defaults.

---

## 8) Decision matrix (abridged)

| Capability                             | Windsurf (Hybrid + Cascade) | Claude Code      | Playwright       | Applitools | axe‑core |
| -------------------------------------- | --------------------------- | ---------------- | ---------------- | ---------- | -------- |
| Multi‑file, plan‑execute‑diff edits    | **Excellent**               | Good (CLI‑first) | —                | —          | —        |
| In‑tenant retention (Hybrid)           | **Yes**                     | N/A              | —                | —          | —        |
| Self‑host option                       | Yes (reduced features)      | N/A              | —                | —          | —        |
| Cross‑browser e2e                      | —                           | —                | **Yes**          | —          | —        |
| Visual AI diffs (large fonts/contrast) | —                           | —                | Pixel diffs only | **Yes**    | —        |
| Automated WCAG checks                  | —                           | —                | —                | —          | **Yes**  |

---

## 9) Prompt pack (copy/paste)

**Claude — Contract→SDK**

> Update `/contracts/openapi.yaml` to add `GET /user/consent/status` and `POST /user/consent/ack`. Regenerate Go handlers + validations, update gateway routes & auth scopes, emit audit events. Generate the TypeScript client in `/packages/api-sdk` and publish a minor version. Add contract + unit tests. Open a PR with a migration note.

**Windsurf (Cascade) — UI Integration**

> In `/apps/web`, use `@org/api-sdk` to implement `ConsentBanner`, `ConsentDialog`, and a `useConsent` hook. Apply Mantine v7 tokens (large type, high contrast, reduced motion), ensure ARIA/keyboard nav. Add Playwright specs and axe checks; include Applitools snapshots for closed/open/accepted/declined. Forbid client storage of PHI. Open a PR with `changeplan.md`.

---

## 10) Risks & mitigations

* **Vendor feature drift:** Lock SLAs and export paths in MSA; maintain fallbacks for CLI‑only flows.
* **Agent mis‑edits:** Use guarded recipes, path fencing, and mandatory review. Keep small, composable PRs.
* **A11y regressions:** Treat **axe** blockers as merge‑stoppers; baseline visual states in Applitools for crisis views.
* **CSP regressions:** CI header assertions and lint rules; forbid inline script eval.

---

## 11) Mobile‑first tooling & prescriptive framework

### 11.1 Build (mobile)

**Framework & libraries**

* **React Native + Expo** (monorepo via Turborepo)
* **Design system:** Export web tokens → **/packages/design** (Style Dictionary). Consume in mobile via **Tamagui** (preferred) or **React Native Paper**.
* **Navigation:** **Expo Router** (file‑based routes)
* **Data layer:** **@org/api-sdk** (typed client) + **TanStack Query** (React Query)
* **Forms:** **React Hook Form** + Zod (schema validation)
* **Secure storage:** **expo-secure-store** (iOS Keychain / Android Keystore)
* **Voice (optional):** Native speech APIs first; otherwise HIPAA‑eligible STT behind gateway
* **TLS pinning:** `react-native-cert-pinner` (or equivalent)
* **Feature flags (optional):** ConfigCat or LaunchDarkly (no PHI in flags)

**Project structure**

```
/contracts/
/packages/api-sdk/
/packages/design/
/apps/web/
/apps/mobile/
/tests/e2e-mobile/
```

**Prescriptive build steps**

1. Scaffold `/apps/mobile` with Expo; install Tamagui/RN Paper, React Query, SecureStore.
2. Import **@org/api-sdk**; create `api/client.ts` wrapper that enables **certificate pinning**, request IDs, and error typing.
3. Implement **token handling** with SecureStore (no AsyncStorage for auth/PHI).
4. Build high‑priority flows: **Emergency FAB → Crisis Modal**, **Consent read/ack**, **Accessibility wizard** (font scale, contrast, voice toggle).
5. Apply tokens from `/packages/design` for large typography, spacing, and color contrast; verify TalkBack/VoiceOver.
6. Add Android **FLAG\_SECURE** on PHI screens and iOS preview‑obscure logic.

---

### 11.2 Test (mobile)

**Component/unit:** **Jest + React Native Testing Library** (focus order, roles/labels, reduced‑motion)

**End‑to‑end:** **Detox** on iOS/Android simulators for:

* Login + token lifecycle (create/refresh/revoke)
* **Emergency flow:** open/submit/cancel; error/success banners
* Consent accept/decline
* Voice enable/disable with permission prompts

**Performance budgets:**

* App cold start ≤ **2.5s** (mid‑tier device)
* Crisis Modal open ≤ **350ms** post‑tap
* Network P95 for `POST /alerts/emergency` ≤ **600ms** (excluding network)

**Crash/telemetry:** **Sentry/Bugsnag** with **PII scrubbing**; never log PHI.

---

### 11.3 Integrate (CI/CD)

**Pipeline (GitHub Actions + EAS Build)**

```yaml
name: mobile-ci
on: [pull_request]
jobs:
  mobile:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 20 }
      - run: npm ci
      - run: npm run -w packages/api-sdk build
      - run: npm run -w apps/mobile typecheck
      - name: Detox iOS
        run: |
          npx expo prebuild -p ios --clean
          npx detox build -c ios.sim.release
          npx detox test -c ios.sim.release --headless
      - name: Detox Android
        run: |
          npx expo prebuild -p android --clean
          npx detox build -c android.emu.release
          npx detox test -c android.emu.release --headless
```

**Release**

* **Build:** EAS Build → **TestFlight** (iOS), **Closed Testing** (Play Console)
* **Channels:** `internal` → `beta` → `production`
* **Secrets:** stored in Expo/EAS or GitHub OIDC; never committed
* **OTA updates:** EAS Update (for non‑PHI, non‑contract UI tweaks). For SDK or policy changes, ship full builds

---

### 11.4 Quality gating (required checks)

* **Static:** ESLint + TypeScript strict; custom rule to **fail on disallowed storage** (localStorage/AsyncStorage for PHI), and to require **TLS pinning** config present
* **Security:** SCA (`npm audit`/Snyk) + dependency review; OPA/Rego policy to enforce domain allowlist for network egress
* **Accessibility:** selected‑screen a11y suite must pass (RN Testing Library)
* **Detox:** required scenarios must pass; flake rate < **1%** (tracked)
* **Performance:** enforce budgets via Detox performance hooks or custom native probes
* **Compliance hooks:** block merge if any test logs contain PHI markers

---

### 11.5 Hosting & distribution

* **App Stores:** Apple App Store (iOS/iPadOS) & Google Play (Android)
* **Enterprise/Clinic iPads:** support **MDM** (Guided Access/kiosk), remote wipe, managed configs
* **Push notifications:** APNs/FCM with **silent payloads**; content fetched on open with auth
* **Device integrity:** Android **Play Integrity**, iOS **DeviceCheck/Attest**; deny service on failing signals for PHI views
* **Regionalization:** ensure endpoints and CDNs are region‑locked per compliance (e.g., US‑only)

---

### 11.6 Role of Windsurf & Claude (mobile)

* **Claude Code:** contract changes → server stubs → gateway policy → publish **@org/api-sdk**
* **Windsurf (Cascade):** consumes SDK to implement/refactor screens, migrate to SecureStore, add pinning, add Detox tests, and open PRs with `changeplan.md`.

---

## 12) Solo‑founder licensing & budget (mobile‑first)

**Context:** Single developer (you), backend contracts already built/tested, HIPAA‑aware product. Prices are public as of this document’s date and may change.

| Tool                              | Solo plan to use now                                  |                   Est. cost | Why this tier now                                                                                                       | When to upgrade                                                                                                 |
| --------------------------------- | ----------------------------------------------------- | --------------------------: | ----------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| **Windsurf (primary UI builder)** | **Pro**                                               |                 **\$15/mo** | Full editor + **Cascade** with enough monthly credits for a solo founder; fastest way to do multi‑file RN/Expo changes. | Teams/Enterprise **Hybrid** when you truly need in‑tenant indexes/memories/SSO or multiple seats.               |
| **Expo EAS (mobile builds/CI)**   | **Starter** (or Free for local protos)                |                 **\$19/mo** | Smooth **TestFlight/Play** pipelines + a small pool of cloud builds.                                                    | **Production** if you’re shipping often (daily builds/OTAs), multiple envs, or need more concurrency.           |
| **End‑to‑end (mobile)**           | **Detox**                                             |                     **\$0** | Open‑source RN e2e; runs on simulators/emulators in CI.                                                                 | Add a device cloud later (e.g., real devices) if you need hardware coverage.                                    |
| **Unit/Component**                | **Jest + React Native Testing Library**               |                     **\$0** | Mature, MIT‑licensed; great a11y queries for senior‑first UI.                                                           | N/A.                                                                                                            |
| **Visual regression (mobile)**    | **Argos Hobby** or **Percy Free**                     |                     **\$0** | \~**5,000** screenshots/month free is plenty early; or use Detox screenshot diffs.                                      | Consider **paid Argos** or **Applitools Eyes** when you need AI‑assisted diffs at scale or enterprise features. |
| **Crash/telemetry**               | **Sentry Developer / Team**                           |             **\$0–\$26/mo** | Start free or low‑cost **with strict PII/PHI scrubbing**.                                                               | **Business** when you must sign a **BAA** (and/or need SAML & retention controls).                              |
| **App store accounts**            | **Apple Developer Program** + **Google Play Console** | **\$99/yr + \$25 one‑time** | Required to ship to iOS/iPadOS & Android.                                                                               | N/A.                                                                                                            |

**Baseline monthly cash:** ~~\$**34/mo** (Windsurf Pro + EAS Starter).
**Annual/one‑time:** Apple **\$99/yr** (~~\$8.25/mo equivalent), Google Play **\$25 one‑time**.

**Compliance notes (solo):**

* Keep **PHI out of tool prompts/logs**. Windsurf/Cascade change plans should exclude PHI paths; commit only synthetic fixtures.
* If you ever must capture PHI in error events, move Sentry to **Business** and execute the BAA; otherwise, stay on Developer/Team and keep PHI‑free telemetry.
* Re‑evaluate Windsurf **Hybrid** only when customers require in‑tenant agent artifacts (indexes/memories/audit logs).

---

## 13) Final call

Adopt **Windsurf (Enterprise Hybrid)** as the **frontend builder**, keep **Claude Code** as the **backend/contract steward**, and enforce **Playwright + Applitools + axe** as the **neutral quality gate**. This maximizes velocity **and** compliance for your senior‑first, healthcare‑regulated UI.
