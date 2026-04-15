# Hivemind Agent Orchestration Design

## Context

Currently, `~/.agents/AGENTS.md` serves as a portable instruction hub across Claude Code, Gemini CLI, OpenCode, and KiloCode. But there is no subagent orchestration layer — no defined worker agents, no multi-stage workflows, no parallel execution patterns.

This design adds a **hivemind** layer: Claude Code as the queen orchestrator, spawning specialized subagents for codebase research, code review + testing, and multi-file implementation. Agent definitions live at user-level (`~/.claude/agents/`) with project-level overrides available. Agent Teams is enabled as an escalation path for complex coordination tasks.

## Architecture

### Agent Scope: User-level core + project overrides

```
~/.claude/agents/              ← shared core (available in all projects)
  ├── explorer.md
  ├── code-reviewer.md
  ├── test-runner.md
  ├── file-writer.md
  ├── planner.md
  ├── linter.md
  ├── documenter.md
  └── security-auditor.md

<project>/.claude/agents/      ← project-specific overrides/additions
  └── django-reviewer.md       (example)
```

- User-level agents add **zero context cost** until invoked
- Agent definitions load only when Claude delegates a task (via description matching or @mention)
- Each agent runs in its own isolated context window; only the summary returns to main conversation

### Coordination: Hybrid (auto-delegation + explicit workflows)

- **Explicit workflows** in CLAUDE.md for common multi-stage patterns (PR review, feature build, research)
- **Auto-delegation fallback** for ad-hoc tasks — Claude routes based on agent `description` fields
- **Agent Teams** enabled via env var as escalation for tasks requiring peer coordination

## Agent Definitions

### File Format

Each agent is a markdown file with YAML frontmatter:

```yaml
---
name: <agent-name>
description: >
  <Keyword-rich description for routing. Include activation triggers,
  use cases, and when to invoke proactively.>
tools: <allowlist of tools>
disallowedTools: <denylist — use tools OR disallowedTools, not both>
model: <haiku|sonnet|opus>
maxTurns: <safety bound>
memory: <user|project|none>
isolation: <worktree — only for write-capable agents>
---

<System prompt: who the agent is, how it should behave, what to return>
```

### Agent Roster (8 agents)

| Agent | Role | Tools | Model | maxTurns | Memory | Isolation |
|---|---|---|---|---|---|---|
| `explorer` | Read-only codebase survey | Read, Glob, Grep, Bash | sonnet | 15 | user | — |
| `code-reviewer` | Quality, style, correctness | Read, Glob, Grep | sonnet | 10 | user | — |
| `test-runner` | Execute tests, report failures | Read, Glob, Grep, Bash | haiku | 8 | — | — |
| `file-writer` | Targeted parallel file edits | Read, Write, Edit, Glob, Grep | sonnet | 15 | — | worktree |
| `planner` | Architecture + implementation planning | Read, Glob, Grep, Bash | opus | 10 | — | — |
| `linter` | Lint, typecheck, format checks | Read, Glob, Grep, Bash | haiku | 5 | — | — |
| `documenter` | Generate/update documentation | Read, Write, Edit, Glob, Grep | sonnet | 10 | — | — |
| `security-auditor` | OWASP top 10, dependency vulns | Read, Glob, Grep, Bash | sonnet | 10 | — | — |

### Design Rationale

- **Read-only agents** (explorer, reviewer, linter, security-auditor, test-runner) cannot modify code — safe to auto-delegate freely
- **file-writer uses `isolation: worktree`** — edits happen in a git worktree, reviewable before merging
- **planner uses opus** — planning benefits from deeper reasoning
- **linter and test-runner use haiku** — "run command, parse output" tasks don't need deep reasoning
- **memory: user on explorer and code-reviewer** — they learn patterns across projects (codebase layouts, style preferences)
- **maxTurns enforced on all agents** — prevents runaway token burn

### Agent Description Best Practices

Descriptions are the routing mechanism. Write them as activation triggers:

```yaml
# Good: keyword-rich, specific about when to invoke
description: >
  Code review specialist. Proactively reviews for quality, security,
  and maintainability. Use after writing or modifying code, during PR
  review, or when user says "review", "check this", or "code quality".

# Bad: vague, won't route well
description: Reviews code
```

## Orchestration Workflows

### CLAUDE.md Workflow Rules

Added to `~/.claude/CLAUDE.md` under a `## Hivemind workflows` section:

#### Workflow 1: Codebase Research
```
Trigger: "explore", "investigate", "map", unfamiliar repo
Stage 1: [explorer x 1-3] parallel with different search focuses
Stage 2: Queen synthesizes findings, presents to user
maxTurns: 15 per explorer
```

#### Workflow 2: PR / Code Review
```
Trigger: "review", "check", after implementation complete
Stage 1 (parallel): [code-reviewer, linter, security-auditor]
Stage 2: Queen aggregates into unified report with severity levels
Stage 3 (conditional): [test-runner] if reviewers flag untested paths
Failure: partial results + offer re-run of failed agents
```

#### Workflow 3: Feature Implementation
```
Trigger: "implement", "build", after plan approval
Stage 1: [planner] → architecture + file breakdown
Stage 2 (parallel): [file-writer x N] in worktree isolation, one per independent module
Stage 3 (parallel): [test-runner, linter] → validate
Stage 4: [code-reviewer] → final quality gate
Failure: stop pipeline, report which stage failed
```

#### Workflow 4: Ad-hoc (auto-delegation fallback)
```
Trigger: no explicit workflow match
Behavior: Claude routes based on agent descriptions
Bound: maxTurns enforced per agent
```

### Escalation to Agent Teams

```
Default: subagents (cheap, focused, covers 80% of work)
Escalate to Agent Teams ONLY when:
  - Multiple files share interfaces that need live negotiation
  - A refactor has circular dependencies across 3+ files
  - Workers need to challenge each other's assumptions
Never escalate for: independent research, testing, linting, single-file edits
```

## Configuration Changes

### ~/.claude/settings.json additions

```json
{
  "env": {
    "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
  }
}
```

Enables Agent Teams capability without changing default behavior. Claude still uses subagents by default; teams are used only when explicitly warranted.

### ~/.claude/CLAUDE.md additions

A `## Hivemind workflows` section containing the 4 workflow definitions above, plus the escalation rule.

## Token Efficiency Design

1. **Progressive disclosure**: agent definitions are 30-80 lines each; only loaded when invoked
2. **Isolated context windows**: verbose exploration stays in agent context, only summary returns
3. **haiku for simple agents**: linter + test-runner use cheapest model
4. **maxTurns bounds**: prevents runaway token burn on all agents
5. **Parallel execution**: 3 agents running simultaneously = 3x work without 3x main context cost
6. **On-demand reference files**: agents load project-specific references only when needed
7. **Agent Teams env var in settings.json**: scoped to Claude Code only, doesn't leak into shell

## Failure Handling

```
Parallel stage result:
  ✅ code-reviewer: 3 issues found (2 medium, 1 low)
  ✅ linter: clean
  ❌ security-auditor: timed out (maxTurns reached)

  → Queen reports partial results
  → Offers: "Security audit incomplete. Run again with @security-auditor?"
```

- Collect results from all completed agents
- Report which agents failed and why
- Offer re-run of individual failed agents via @mention
- Never silently drop failed results

## Cross-Tool Portability (Phase 2, future)

Current scope is Claude Code only. Agent definitions can later be ported to:
- `~/.gemini/agents/*.md` (YAML frontmatter — similar format)
- `~/.opencode/agents/*.md` (may need JSON adaptation)

The same 8 agent definitions serve as source templates. Manual sync required (same pattern as AGENTS.md → GEMINI.md today).

## Files to Create/Modify

### Create (8 new files)
- `~/.claude/agents/explorer.md`
- `~/.claude/agents/code-reviewer.md`
- `~/.claude/agents/test-runner.md`
- `~/.claude/agents/file-writer.md`
- `~/.claude/agents/planner.md`
- `~/.claude/agents/linter.md`
- `~/.claude/agents/documenter.md`
- `~/.claude/agents/security-auditor.md`

### Modify (2 existing files)
- `~/.claude/settings.json` — add `env.CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS: "1"`
- `~/.claude/CLAUDE.md` — add `## Hivemind workflows` section

## Verification

1. **Agent discovery**: Run Claude Code, ask "what agents do you have?" — should list all 8
2. **Auto-delegation**: Say "explore this codebase" — should spawn explorer without explicit @mention
3. **Explicit invocation**: Say "@code-reviewer check this file" — should invoke code-reviewer
4. **Parallel workflow**: Say "review this PR" — should spawn code-reviewer + linter + security-auditor in parallel
5. **Tool restrictions**: Verify explorer cannot Write/Edit, file-writer runs in worktree
6. **maxTurns**: Verify linter stops after 5 turns max
7. **Agent Teams**: Verify `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` is set, teams can be spawned for complex refactors
8. **Memory persistence**: After using code-reviewer across 2 projects, check `~/.claude/agent-memory/code-reviewer/` exists
