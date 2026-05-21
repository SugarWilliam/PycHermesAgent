# Phase 2 — Toward Usable Product (v0.2.2+)

**Status:** Approved execution plan
**Supersedes:** Previous working draft (v0.2.1 草案)
**Authority:** `docs/Project_Development_and_Release_Governance.md`
**Phase target:** From "boundary-correct engineering preview" to "usable, visible, value-proven local analysis workbench"
**Parallel tracks:** Analysis substantiation + Interactive product + Engineering hardening

---

## 0. Design Decisions (Locked)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Desktop framework | React 18 + Vite + electron-vite | Richest Markdown rendering ecosystem |
| Desktop language | JavaScript (JSX) | Team consistency |
| Desktop directory | Replace `desktop/`, rebuild from scratch | Old shell is 323-line health probe, no retention value |
| UI style reference | **Dify** — three-column layout, card-based, clean whitespace | Best-in-class LLM app UI |
| Chart trigger | ` ```echarts ` / ` ```mermaid ` fenced code blocks | LLM naturally outputs fenced blocks; unified parsing |
| ECharts config | LLM generates ECharts option JSON directly | Maximum flexibility |
| Benchmark baseline | Same LLM direct answer (skip MetaHarness) | Real comparison, reproducible |
| Content transport | SSE Markdown stream + desktop-side parsing/rendering | Keeps sidecar thin |
| Layout | Three-column: Session Sidebar + Chat + Context Panel | Dify standard for analysis products |
| Theme | Light/dark, system-follow + manual toggle | Modern desktop app standard |

---

## 1. Architecture Delta (Phase 1 → Phase 2)

```
Phase 1:                              Phase 2:
┌──────────────┐                      ┌────────────────────────────────┐
│ Health Probe │                      │     Desktop Conversation App    │
│ (raw JSON)   │                      │  React + Markdown + Charts      │
└──────┬───────┘                      └──────────────┬─────────────────┘
       │ GET /health                                  │ SSE + REST
┌──────┴───────┐                      ┌──────────────┴─────────────────┐
│   Sidecar    │         →            │        Sidecar (hardened)       │
│ (monolithic) │                      │  health-state-machine + modes   │
└──────────────┘                      └────────────────────────────────┘
```

**New boundary rules:**
- Desktop owns rendering logic, not analysis logic
- Sidecar outputs Markdown text stream, never HTML
- Charts/formulas identified from Markdown fenced blocks by desktop renderer
- Desktop never calls LLM directly; all requests go through sidecar AgentLoop

---

## 2. Workstreams

### Track A: Engineering Hardening

**Goal:** Eliminate Phase 1 tech debt; establish concurrency and integration test foundations.

| ID | Task | Target | Acceptance |
|----|------|--------|------------|
| A1 | Split `hermes_engine/runtime.py` (1395 lines) | → `runtime/discovery.py`, `runtime/git_probe.py`, `runtime/facade.py`, `runtime/constants.py` | No single file >400 lines |
| A2 | Split `sidecar_api/service.py` (869 lines) | → `services/chat_service.py`, `services/mrag_service.py`, `services/meta_service.py`, `services/skill_service.py` | No single file >300 lines; module-level mutable state eliminated |
| A3 | Thread safety fix | `_MRAG_SERVICES` dict → locked registry or single-thread async | Concurrency tests pass |
| A4 | numpy lazy import | `meta_harness/bridge/runtime.py` | `import pyc_hermes_agent` no longer triggers numpy load |
| A5 | Contract `__post_init__` validation | `MetaAnalysisRequest`, `ChatCompletionRequest`, `AgentLoopRequest` | Empty/invalid construction raises clear error |
| A6 | Concurrency tests | `tests/concurrency/` | MRAG lock contention, multi-request concurrency, service state isolation |
| A7 | Integration test skeleton | `tests/integration/` | Real HTTP → AgentLoop → response, at least 5 scenarios |

### Track B: Analysis Value Chain

**Goal:** Make MetaHarness produce measurable quality improvement on the agent main path.

| ID | Task | Detail | Acceptance |
|----|------|--------|------------|
| B1 | AgentLoop `analysis_mode` | Three modes: `casual` (pure chat), `structured` (require structured output), `formal` (trigger full MetaHarness) | Contract tests cover mode switching |
| B2 | MethodJudge substantiation | From fixed templates → rule-based review: detect data gaps, unmet preconditions, overclaiming | Judge output varies by request (not fixed text) |
| B3 | Method catalog cleanup | A-13/14/15/18 permanently disabled → mark `status: planned` or remove from registry | Only executable methods appear in selector scoring |
| B4 | External benchmark | 3 categories × 5 cases = 15 cases; each via MetaHarness and raw LLM; compare: structure completeness, risk coverage, overclaim detection, degraded accuracy | Benchmark script CI-runnable; MetaHarness wins on ≥3 metrics |
| B5 | Three-layer memory | `session`: current conversation continuity; `preference`: user style/conservatism/language; `knowledge`: MRAG long-term knowledge | All layers viewable/deletable; preference persists cross-session |
| B6 | Sidecar health state machine | Four states: `ready` / `ready_with_warnings` / `degraded` / `unavailable`; every route returns consistent envelope | Health endpoint returns state enum + degradation reason list |
| B7 | Structured output enhancement | `formal` mode AgentLoop final output auto-includes: method / assumptions / evidence_grade / risks / degraded_state | Desktop can parse and display analysis result cards |

**B4 Benchmark Design:**

```
benchmarks/
├── meta_harness/
│   ├── cases/
│   │   ├── fact_integration_01.json
│   │   ├── structural_analysis_01.json
│   │   └── risk_boundary_01.json
│   └── expected/
├── scripts/
│   └── run_meta_benchmarks.py
└── results/
```

Execution flow:
```python
for case in cases:
    raw_result = llm_gateway.execute_chat(case.prompt)        # Skip MetaHarness
    guided_result = agent_loop.start(case.prompt, analysis_mode="formal")  # Via MetaHarness
    score_raw = evaluate(raw_result, case.expected)
    score_guided = evaluate(guided_result, case.expected)
    # Compare: structure_completeness, risk_coverage, overclaim_detection, degraded_accuracy
```

### Track C: Desktop Interactive Product

**Goal:** Build Cursor/ChatGPT/Dify-level conversation analysis workbench from scratch.

#### C0: Project Structure

```
desktop/
├── package.json
├── vite.config.js
├── electron.vite.config.js
├── electron/
│   ├── main.js
│   ├── preload.js
│   └── sidecar-manager.js
├── src/
│   ├── main.jsx
│   ├── App.jsx
│   ├── components/
│   │   ├── Chat/
│   │   │   ├── ChatView.jsx
│   │   │   ├── MessageList.jsx
│   │   │   ├── MessageBubble.jsx
│   │   │   ├── InputArea.jsx
│   │   │   └── StreamingIndicator.jsx
│   │   ├── Renderer/
│   │   │   ├── MarkdownRenderer.jsx
│   │   │   ├── CodeBlock.jsx
│   │   │   ├── MermaidBlock.jsx
│   │   │   ├── EChartsBlock.jsx
│   │   │   ├── MathBlock.jsx
│   │   │   └── CitationBlock.jsx
│   │   ├── Analysis/
│   │   │   ├── AnalysisCard.jsx
│   │   │   ├── RiskList.jsx
│   │   │   └── EvidenceGrade.jsx
│   │   ├── Sidebar/
│   │   │   ├── SessionList.jsx
│   │   │   ├── SkillPanel.jsx
│   │   │   └── SettingsPanel.jsx
│   │   └── Layout/
│   │       └── AppLayout.jsx
│   ├── hooks/
│   │   ├── useSSE.js
│   │   ├── useSidecar.js
│   │   └── useSession.js
│   ├── stores/
│   │   └── appStore.js
│   ├── services/
│   │   └── sidecarClient.js
│   └── styles/
│       └── tailwind.css
├── public/
└── index.html
```

#### C Task Details

| ID | Task | Core Dependency | Acceptance |
|----|------|-----------------|------------|
| C1 | Project initialization | electron-vite, React 18, Tailwind, Zustand | `npm run dev` starts empty shell |
| C2 | Sidecar connection layer | `services/sidecarClient.js` | Connect/disconnect/reconnect/health polling |
| C3 | Chat UI skeleton | ChatView + MessageList + InputArea | Send message → call sidecar → display plain text reply |
| C4 | SSE streaming consumption | `useSSE.js` hook | Token-by-token display, typewriter effect |
| C5 | Markdown rendering | `react-markdown` + `remark-gfm` + `rehype-raw` | Headers/lists/tables/quotes/bold/links render correctly |
| C6 | Code highlighting | Shiki + custom `CodeBlock` component | 200+ language highlighting, line numbers, copy button |
| C7 | Mermaid diagrams | ` ```mermaid ` block → SVG rendering | flowchart/sequence/class/gantt correct |
| C8 | ECharts data visualization | ` ```echarts ` block → JSON parse → ECharts render | Line/bar/pie/scatter renderable |
| C9 | LaTeX formulas | KaTeX, `$...$` inline + `$$...$$` block | Complex formulas render correctly |
| C10 | Analysis result panel | `formal` mode returns → display structured cards | method/evidence/risks/degraded sections |
| C11 | Session management | Sidebar session list + create/switch/delete | Persisted to sidecar session store |
| C12 | Settings panel | Model selection, sidecar URL, analysis_mode default, theme | Settings save and take effect |
| C13 | Dark/light theme | Tailwind dark mode | System-follow + manual toggle |
| C14 | Three-column adaptive layout | Left/right panels collapsible, responsive | Resize gracefully at 1024-1920px |
| C15 | Evidence Context Panel | Right panel shows MRAG citation sources | Source, page, relevance score displayed |
| C16 | Analysis Card component | formal mode results as Dify-style cards | method/CE/SR/risks/assumptions/degraded |
| C17 | Slash Command selector | Type `/` to open skill/command menu | Menu appears, selection inserts |
| C18 | Callout/Admonition rendering | `> [!WARNING]` / `> [!NOTE]` style blocks | Colored callout boxes render |

### Track D: MRAG Evolution

| ID | Task | Acceptance |
|----|------|------------|
| D1 | SQLite/FTS5 storage engine | Replace JSON O(n) traversal; query <50ms (1000 chunks) |
| D2 | Migration script completion | JSON → SQLite auto-migration, `--backup-to` preserved |
| D3 | PDF text extraction | `pymupdf` or `pdfplumber`; page-level citation |
| D4 | Citation UI | Desktop click-to-source in context panel |

### Track E: Skills System

| ID | Task | Acceptance |
|----|------|------------|
| E1 | Prompt Skills | Writing style/report templates/analysis frameworks definable as skills |
| E2 | Analysis Skills | SWOT, causal analysis, comparison frameworks bound to `formal` mode |
| E3 | Desktop skill management | View/activate/deactivate skills in UI panel |
| E4 | Skills audit | Activation records + usage counts persisted |

### Track F: Release Hardening

| ID | Task | Acceptance |
|----|------|------------|
| F1 | Windows upgrade path test | v0.2.1 → v0.3.0 data directory compatible |
| F2 | electron-builder full packaging | Can generate Windows installer (NSIS) |
| F3 | Auto-update mechanism | `electron-updater` checks GitHub Releases |

---

## 3. Execution Waves

### Wave 1 (Weeks 1-4): Foundation + Skeleton

```
Track A: A1, A2, A3, A4          (parallel, no external deps)
Track B: B1, B6                  (analysis_mode + health)
Track C: C1, C2, C3, C4          (init → connect → chat → stream)
```

**Wave 1 exit gate:**
- No >400 line single files (Track A)
- Desktop can converse with sidecar and stream plain text
- AgentLoop supports analysis_mode switching
- Concurrency-safe MRAG services

### Wave 2 (Weeks 5-8): Rendering + Analysis

```
Track B: B2, B3, B4, B5, B7      (MethodJudge + catalog + benchmark + memory + structured output)
Track C: C5, C6, C8, C9          (Markdown + code + ECharts + LaTeX)
Track D: D1, D2                  (SQLite migration)
```

**Wave 2 exit gate:**
- Markdown/code/formulas render correctly in desktop
- ECharts from LLM output renderable
- MethodJudge output is non-fixed text
- Benchmark 15 cases runnable; MetaHarness ≥3 metrics better than raw LLM
- SQLite storage available

### Wave 3 (Weeks 9-12): Product Completion

```
Track C: C7, C10-C18             (Mermaid + analysis panel + sessions + settings + theme + layout + context + slash)
Track D: D3, D4                  (PDF + citation UI)
Track E: E1, E2, E3              (Skills)
Track A: A5, A6, A7              (validation + concurrency + integration tests)
```

**Wave 3 exit gate:**
- Full rendering (Markdown + code + Mermaid + ECharts + LaTeX)
- Sessions manageable (create/switch/delete)
- Skills activatable in desktop
- Integration tests cover core paths

### Wave 4 (Weeks 13-15): Hardening + Release

```
Track E: E4                      (Skills audit)
Track F: F1, F2, F3              (upgrade + packaging + updater)
Full regression + docs update
```

**Wave 4 exit gate:**
- Windows installer generatable
- Upgrade path tests pass
- All docs consistent with implementation

---

## 4. Desktop Dependencies

```json
{
  "dependencies": {
    "react": "^18.3",
    "react-dom": "^18.3",
    "react-markdown": "^9.0",
    "remark-gfm": "^4.0",
    "remark-math": "^6.0",
    "rehype-katex": "^7.0",
    "katex": "^0.16",
    "shiki": "^1.0",
    "mermaid": "^11.0",
    "echarts": "^5.5",
    "echarts-for-react": "^3.0",
    "zustand": "^4.5",
    "tailwindcss": "^3.4",
    "@radix-ui/react-dialog": "^1.0",
    "@radix-ui/react-tabs": "^1.0",
    "@radix-ui/react-scroll-area": "^1.0"
  },
  "devDependencies": {
    "electron": "^33.2",
    "electron-vite": "^2.3",
    "electron-builder": "^25.1",
    "vite": "^5.4",
    "@vitejs/plugin-react": "^4.3",
    "autoprefixer": "^10.4",
    "postcss": "^8.4"
  }
}
```

---

## 5. UI Design Specification (Dify Style)

### Layout

```
┌──────────────────────────────────────────────────────────────┐
│  Logo   │ Analysis Mode [casual ▾]  │ Model [gpt-4o ▾] │ ⚙  │  ← Top bar
├─────────┼────────────────────────────────────────────┼───────┤
│         │                                            │       │
│ Session │         Main Chat Area                     │Context│
│  List   │                                            │ Panel │
│         │  ┌─────────────────────────────────────┐   │       │
│ ──────  │  │ User message                        │   │Evidence│
│ Today   │  └─────────────────────────────────────┘   │       │
│  • s1   │                                            │ MRAG  │
│  • s2   │  ┌─────────────────────────────────────┐   │Sources│
│ ──────  │  │ Assistant:                          │   │       │
│ Earlier │  │   [Markdown + Code + Charts]         │   │Risks  │
│  • s3   │  │                                     │   │       │
│         │  │   ┌── Analysis Card ──────────┐     │   │Degraded│
│ ──────  │  │   │ Method: A-22 Network Sci  │     │   │State  │
│ Skills  │  │   │ Evidence: CE-C1            │     │   │       │
│  [+]    │  │   │ Risks: [2 items]           │     │   │       │
│         │  │   └────────────────────────────┘     │   │       │
│         │  └─────────────────────────────────────┘   │       │
│         │                                            │       │
│         │  ┌─────────────────────────────────────┐   │       │
│         │  │ Input area (multi-line)         [➤] │   │       │
│         │  └─────────────────────────────────────┘   │       │
└─────────┴────────────────────────────────────────────┴───────┘
```

### Design Tokens

```css
:root {
  --bg-primary: #ffffff;
  --bg-secondary: #f9fafb;
  --bg-tertiary: #f3f4f6;
  --border: #e5e7eb;
  --text-primary: #111827;
  --text-secondary: #6b7280;
  --accent: #2563eb;
  --success: #059669;
  --warning: #d97706;
  --danger: #dc2626;
  --radius-sm: 6px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
  --shadow-md: 0 4px 6px -1px rgba(0,0,0,0.1);
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', 'Fira Code', monospace;
}

[data-theme="dark"] {
  --bg-primary: #1f2937;
  --bg-secondary: #111827;
  --bg-tertiary: #374151;
  --border: #374151;
  --text-primary: #f9fafb;
  --text-secondary: #9ca3af;
}
```

### Interaction Patterns (Dify Reference)

| Dify Feature | PycHermes Equivalent | Implementation |
|-------------|---------------------|----------------|
| App Type Selector | Analysis Mode Selector | Top bar dropdown: `casual`/`structured`/`formal` |
| Model Selector | Model Selector | Top bar dropdown, from sidecar `/models` |
| Conversation Variables | Session Context | Right panel shows session vars/prefs |
| Knowledge Base Citations | MRAG Evidence Panel | Right panel shows sources, confidence, page |
| Node Output Streaming | Streaming Blocks | Token-by-token + instant chart/code render on block complete |
| Log/Debug Panel | Analysis Card | Inline card in `formal` mode messages |
| Environment Variables | Preferences | Settings panel manages user preferences |

### Input Area

- Multi-line auto-resize
- Bottom toolbar: Attach (future), Skills shortcut, mode override, Send
- `Ctrl+Enter` sends, `Enter` newline
- `/` slash triggers skill/command selector

---

## 6. Sidecar API Extensions (Phase 2 New Routes)

| Route | Method | Purpose | Track |
|-------|--------|---------|-------|
| `POST /chat` | POST | Existing; add `analysis_mode` field | B1 |
| `GET /chat/stream` | SSE | Existing; maintain | — |
| `GET /health` | GET | Extend to state machine output | B6 |
| `GET /sessions` | GET | Session list | C11 |
| `DELETE /sessions/{id}` | DELETE | Delete session | C11 |
| `GET /preferences` | GET | User preferences | B5 |
| `PUT /preferences` | PUT | Update preferences | B5 |
| `GET /skills` | GET | Existing; extend activation state | E3 |
| `POST /skills/{id}/activate` | POST | Activate skill | E3 |
| `POST /skills/{id}/deactivate` | POST | Deactivate skill | E3 |
| `GET /settings` | GET | Desktop settings (model/mode/theme) | C12 |
| `PUT /settings` | PUT | Save settings | C12 |

---

## 7. Phase 2 Done Definition

Phase 2 is complete when ALL of the following pass:

- [ ] **Interaction**: Users can conduct multi-turn conversations in desktop, with session management
- [ ] **Rendering**: Markdown + code highlighting + Mermaid + ECharts + LaTeX all render correctly
- [ ] **Streaming**: Responses stream token-by-token, charts/code blocks render instantly on completion
- [ ] **Analysis value**: Benchmark proves `formal` mode MetaHarness ≥3 metrics better than raw LLM
- [ ] **Structured output**: `formal` mode produces analysis cards with method/evidence/risks/degraded
- [ ] **Stability**: No >400 line single files, concurrency tests pass, integration tests ≥5 scenarios
- [ ] **Skills**: prompt skills + analysis skills activatable in desktop
- [ ] **MRAG**: SQLite/FTS5 storage available, PDF importable
- [ ] **Packaging**: `electron-builder` can generate Windows installer

---

## 8. Explicit Exclusions (Not in Phase 2)

| Excluded | Reason | Deferred To |
|----------|--------|-------------|
| Code signing | Requires certificate purchase and CI key management | Phase 3 |
| PyPI publication | Requires package name registration and maintenance commitment | Phase 3 |
| Neural embeddings (sentence-transformers) | Model download and GPU dependency too heavy | Phase 3 |
| Multi-modal (image OCR) | PDF first | Phase 3 |
| Self-learning loop | High risk, memory system must be validated first | Phase 3 |
| Mobile/web | Desktop first | Phase 4+ |
| Multi-user/permissions | Local single-user product | Not planned |

---

## 9. Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Benchmark proves MetaHarness has no gain | Medium | High (product positioning collapse) | Iterate MethodJudge and routing policy until advantage measurable; worst case degrade to structured output tool |
| ECharts config from LLM unstable quality | Medium | Medium | Provide schema validation + fallback rendering (show raw JSON + error) |
| Desktop rebuild exceeds estimate | Medium | Medium | Wave 1 only skeleton+stream; Wave 2 adds rendering; incremental delivery |
| SQLite migration causes data loss | Low | High | `--backup-to` mandatory + pre-migration verification + rollback script |

---

## 10. Compatibility Matrix Update (Phase 2)

| Axis | Phase 2 target | Notes |
|------|---------------|-------|
| `app_version` | `0.3.0` | Phase 2 Wave 4 tag |
| `sidecar_api_version` | `0.6` | New routes: sessions, preferences, settings, skill activate |
| `contract_version` | Bump on `analysis_mode` addition | Additive field |
| `desktop_ipc_version` | `1.0` | First stable desktop ↔ sidecar contract |

---

*Maintainers: update `Execution_Blueprint_v0.2.0.md` "Next waves" links when modifying this file.*
