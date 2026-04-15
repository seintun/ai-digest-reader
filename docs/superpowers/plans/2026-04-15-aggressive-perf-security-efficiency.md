# Aggressive Performance/Security/Efficiency Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** aggressively improve frontend load/render, backend runtime/memory efficiency, and security posture with compact, reusable, low-noise code.

**Architecture:** audit-first coordinator model with parallel specialist subagents, then ranked waves: P0 security/correctness, P1 frontend/runtime, P1 pipeline efficiency, P2 compact modularization.

**Tech Stack:** Python (`pytest`), Astro/TypeScript (`astro check`, `astro build`), markdown docs, branch-per-wave git flow.

---

### Task 1: Coordinator setup

**Files:**
- Create: `docs/superpowers/tracking/2026-04-15-aggressive-refactor-tracker.md`
- Create: `docs/superpowers/reports/2026-04-15-aggressive-audit-baseline.md`

- [ ] Create umbrella branch `refactor/aggressive-perf-security-efficiency`
- [ ] Create phase branch map and owner lanes
- [ ] Initialize tracker board fields: `task_id`, `phase`, `lane`, `owner_agent`, `status`, `dependency`, `metric_target`, `verify_cmd`, `evidence`
- [ ] Commit setup artifacts

### Task 2: Phase 0 baseline + audit map

**Files:**
- Create: `docs/superpowers/reports/2026-04-15-aggressive-audit-baseline.md`

- [ ] Run baseline checks: `.venv/bin/python -m pytest`, `python digest.py --no-ai --limit 5`, `npm run check`, `npm run build`
- [ ] Dispatch parallel subagents: frontend profiler, pipeline profiler, security devil's advocate
- [ ] Build ranked findings matrix (P0/P1/P2)
- [ ] Commit baseline report

### Task 3: Phase 1 (P0) security + correctness

**Files:**
- Modify: `ai-digest-reader/src/pages/index.astro`
- Modify: `schema.py`
- Modify: `tests/test_*.py`

- [ ] Add safe URL policy and escaping for all untrusted rendered fields
- [ ] Replace assert-based schema validation with explicit checks
- [ ] Fix brittle test import-path hacks
- [ ] Run `pytest`, `npm run check`, `npm run build`
- [ ] Commit P0 fixes

### Task 4: Phase 2A (P1) frontend runtime optimization

**Files:**
- Modify: `ai-digest-reader/src/pages/index.astro`
- Modify: `ai-digest-reader/src/components/Controls.astro`
- Modify: `ai-digest-reader/src/components/ViewSwitcher.astro`

- [ ] Render only active view instead of rebuilding all views each update
- [ ] Remove duplicated initialization/event wiring where applicable
- [ ] Reduce repeated expensive string ops and parsing overhead
- [ ] Verify with `npm run check` and `npm run build`
- [ ] Commit frontend perf wave

### Task 5: Phase 2B (P1) pipeline/runtime efficiency

**Files:**
- Modify: `fetchers/reddit.py`
- Modify: `fetchers/hn.py`
- Modify: `formatter.py`

- [ ] Remove duplicated normalization logic where low risk
- [ ] Improve fetcher robustness/efficiency while preserving behavior
- [ ] Fix markdown formatter correctness issue
- [ ] Verify with `pytest` and `python digest.py --no-ai --limit 5`
- [ ] Commit pipeline wave

### Task 6: Phase 3 (P2) compact/modular cleanup

**Files:**
- Modify only files touched in prior waves (no speculative abstractions)

- [ ] Remove dead code/noise identified in audit
- [ ] Keep interfaces small and responsibilities explicit
- [ ] Verify full matrix and no regressions
- [ ] Commit modularization wave

### Task 7: Integration + docs + evidence

**Files:**
- Modify: `docs/technical-architecture.md`
- Modify: `ai-digest-reader/docs/ARCHITECTURE.md`
- Create: `docs/superpowers/reports/2026-04-15-aggressive-refactor-results.md`

- [ ] Merge verified wave branches into umbrella
- [ ] Run full verification matrix
- [ ] Record before/after performance and security deltas
- [ ] Update architecture/technical docs for changed boundaries
- [ ] Commit final docs and evidence
