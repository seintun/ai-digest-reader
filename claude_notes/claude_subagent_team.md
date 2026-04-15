▐▛███▜▌ Claude Code v2.1.98
▝▜█████▛▘ Opus 4.6 · Claude Pro
▘▘ ▝▝ ~/.claude
──────────────────────────────────────────── ctrl+e to show 90 previous messages ─────────────────────────────────────────────

                                                                                              10:31 PM claude-opus-4-6

⏺ Now presenting the design section by section. Let me know after each if it looks right.

---

Section 1: Agent Definitions (8 agents)

Each agent is a markdown file with YAML frontmatter in ~/.claude/agents/. The body is the system prompt — it tells the agent
who it is and how to behave.

~/.claude/agents/
├── explorer.md # read-only codebase survey
├── code-reviewer.md # quality, style, correctness
├── test-runner.md # execute tests, report failures
├── file-writer.md # targeted parallel file edits
├── planner.md # architecture + implementation planning
├── linter.md # lint, typecheck, format checks
├── documenter.md # generate/update docs
└── security-auditor.md # OWASP top 10, dependency vulns

Key design decisions per agent:

┌──────────────────┬───────────────────────────────┬───────────────────┬────────┬───────────┐
│ Agent │ Tools allowed │ Tools denied │ Model │ Isolation │
├──────────────────┼───────────────────────────────┼───────────────────┼────────┼───────────┤
│ explorer │ Read, Glob, Grep, Bash │ Write, Edit │ sonnet │ — │
├──────────────────┼───────────────────────────────┼───────────────────┼────────┼───────────┤
│ code-reviewer │ Read, Glob, Grep │ Write, Edit, Bash │ sonnet │ — │
├──────────────────┼───────────────────────────────┼───────────────────┼────────┼───────────┤
│ test-runner │ Read, Glob, Grep, Bash │ Write, Edit │ sonnet │ — │
├──────────────────┼───────────────────────────────┼───────────────────┼────────┼───────────┤
│ file-writer │ Read, Write, Edit, Glob, Grep │ — │ sonnet │ worktree │
├──────────────────┼───────────────────────────────┼───────────────────┼────────┼───────────┤
│ planner │ Read, Glob, Grep, Bash │ Write, Edit │ opus │ — │
├──────────────────┼───────────────────────────────┼───────────────────┼────────┼───────────┤
│ linter │ Read, Glob, Grep, Bash │ Write, Edit │ haiku │ — │
├──────────────────┼───────────────────────────────┼───────────────────┼────────┼───────────┤
│ documenter │ Read, Write, Edit, Glob, Grep │ Bash │ sonnet │ — │
├──────────────────┼───────────────────────────────┼───────────────────┼────────┼───────────┤
│ security-auditor │ Read, Glob, Grep, Bash │ Write, Edit │ sonnet │ — │
└──────────────────┴───────────────────────────────┴───────────────────┴────────┴───────────┘

★ Insight ─────────────────────────────────────

- Read-only agents (explorer, reviewer, linter, security-auditor, test-runner) can't accidentally modify code — they're safe
  to auto-delegate freely
- file-writer uses isolation: worktree — edits happen in a git worktree so changes are reviewable before merging into your
  working tree
- planner uses opus — planning benefits from deeper reasoning; the other agents use sonnet for speed/cost balance
- linter uses haiku — fast, cheap, just needs to run commands and parse output
  ─────────────────────────────────────────────────

Does this agent roster and permission model look right before I move to the orchestration workflows?

❯ looks good

                                                                                              10:35 PM claude-opus-4-6

⏺ Section 2: Orchestration Workflows (CLAUDE.md rules)

These are the explicit multi-stage pipelines defined in your CLAUDE.md. They tell the queen exactly which agents to spawn
and in what order for common tasks.

Workflow 1: Codebase Research

Trigger: "explore", "investigate", "map this codebase", unfamiliar repo
Pipeline:
Stage 1: [explorer] → parallel agents with different search focuses
Stage 2: Queen synthesizes findings → presents to user

Workflow 2: PR / Code Review

Trigger: "review", "check this", after completing implementation
Pipeline:
Stage 1 (parallel): [code-reviewer, linter, security-auditor]
Stage 2: Queen synthesizes all findings into unified report
Stage 3 (optional): [test-runner] if reviewers flag untested paths

Workflow 3: Feature Implementation

Trigger: "implement", "build", after plan approval
Pipeline:
Stage 1: [planner] → architecture + file breakdown
Stage 2 (parallel): [file-writer × N] → one per independent module (worktree isolation)
Stage 3 (parallel): [test-runner, linter] → validate the work
Stage 4: [code-reviewer] → final quality gate

Workflow 4: Ad-hoc (auto-delegation fallback)

Trigger: anything not matching above patterns
Behavior: Claude reads agent descriptions, picks best match, spawns 1-3 agents

★ Insight ─────────────────────────────────────

- Parallel stages are the token efficiency win — 3 agents running simultaneously means 3x the work without 3x the main
  context cost, since each agent's verbose output stays in its own window
- Sequential stages (plan → write → test → review) enforce dependencies — you don't want the reviewer checking code that
  hasn't been written yet
- The ad-hoc fallback covers edge cases without needing to predefine every workflow — this is the "hybrid" in Approach C
  ─────────────────────────────────────────────────

Does this workflow structure make sense? Any workflows you'd add or change?

❯ Please tell me more and what is recommended based on best practice and claude guidance

                                                                                              10:36 PM claude-opus-4-6

⏺ Let me pull deeper recommendations from Claude's official guidance and your existing production example (claude-seo).

⏺ Explore(Fetch Claude agent best practices docs)
⎿  Prompt:
I need to find best practices and official guidance for Claude Code subagent orchestration. Do these things:

       1. Fetch https://code.claude.com/docs/en/sub-agents and extract ALL best practices, recommendations, anti-patterns, and
        token efficiency tips
       2. Fetch https://code.claude.com/docs/en/agent-teams and extract the same
       3. Look at the production claude-seo skill at /Users/seintun/claude-seo/ - read the CLAUDE.md, any agents/ directory
       files, and the main orchestration skill file. Show how it orchestrates 8 parallel subagents.

       For each source, specifically extract:
       - Recommended patterns for agent descriptions (what makes routing work well)
       - Token efficiency tips (context passing, result summarization, caching)
       - Anti-patterns to avoid
       - How to structure multi-stage workflows
       - Agent team vs subagent - when to use which
       - Memory and state sharing between agents
       - Model selection guidance (when opus vs sonnet vs haiku)
       - Permission and tool restriction best practices
       - maxTurns recommendations
       - How to handle agent failures/retries

       Be very thorough - I need official guidance, not general advice.

⎿  Fetch(url: "https://code.claude.com/docs/en/sub-agents", prompt: "Extract ALL best practices, recommendations,
⎿  Fetch(url: "https://code.claude.com/docs/en/agent-teams", prompt: "Extract ALL best practices, recommendations,
⎿  Read(/Users/seintun/claude-seo/CLAUDE.md)
⎿  Bash(find /Users/seintun/claude-seo -type f -name "_.md" | head -20)
⎿  Read(/Users/seintun/.claude/projects/-Users-seintun--claude/b29b865b-3318-4bc9-bddd-193272fb8db1/tool-results/toolu\_
⎿  Bash(find /Users/seintun/claude-seo/seo -name "SKILL.md" -type f)
⎿  Bash(find /Users/seintun/claude-seo -name "_.md" -path "_/agents/_" -type f)
⎿  Read(/Users/seintun/claude-seo/docs/ARCHITECTURE.md)
⎿  Read(/Users/seintun/claude-seo/seo/SKILL.md)
⎿  Read(/Users/seintun/claude-seo/agents/seo-technical.md)
⎿  Read(/Users/seintun/claude-seo/agents/seo-content.md)
⎿  Read(/Users/seintun/claude-seo/agents/seo-performance.md)
⎿  Read(/Users/seintun/claude-seo/agents/seo-schema.md)
⎿  Read(/Users/seintun/claude-seo/agents/seo-sitemap.md)
⎿  Read(/Users/seintun/claude-seo/agents/seo-geo.md)
⎿  Read(/Users/seintun/claude-seo/agents/seo-visual.md)
⎿  Bash(grep -r "Agent\|Task\|spawn" /Users/seintun/claude-seo/seo/SKILL.md | head -20)
⎿  Read(/Users/seintun/claude-seo/skills/seo-audit/SKILL.md)
⎿  Read(/Users/seintun/claude-seo/agents/seo-local.md)
⎿  Response:
Perfect! Now let me compile all the official guidance from the documentation I've gathered. Let me create a
comprehensive report:

       OFFICIAL CLAUDE CODE SUBAGENT ORCHESTRATION BEST PRACTICES

       Based on official documentation from code.claude.com/docs and the production claude-seo skill orchestration, here's the
        comprehensive guidance:

       ---
       1. AGENT DESCRIPTIONS & ROUTING

       Official Guidance (Sub-agents docs):
       - Write descriptions that Claude uses to decide when to delegate. Include activation keywords and concrete use cases.
       - For subagents serving a team, list them explicitly in the description to encourage proactive delegation.
       - Pattern: "Expert [role] for [use case]. Use proactively [when condition]."
       - Example (code-reviewer): "Expert code review specialist. Proactively reviews code for quality, security, and
       maintainability. Use immediately after writing or modifying code."

       claude-seo Example:
       The main seo skill description includes specific triggers: "Triggers on: 'SEO', 'audit', 'schema', 'Core Web Vitals',
       'sitemap', 'E-E-A-T', 'AI Overviews', 'GEO'..."

       Each agent has focused descriptions:
       - seo-technical: "Technical SEO specialist. Analyzes crawlability, indexability, security, URL structure, mobile
       optimization, Core Web Vitals, and JavaScript rendering."
       - seo-content: "Content quality reviewer. Evaluates E-E-A-T signals, readability, content depth, AI citation readiness,
        and thin content detection."

       ---
       2. TOKEN EFFICIENCY & CONTEXT PASSING

       Official Guidance:
       - Subagents run in their own context window with custom system prompt, specific tool access, and independent
       permissions
       - Results are summarized back to main conversation (lower token cost than agent teams)
       - Subagents receive only their system prompt, not the full Claude Code system prompt
       - Load reference files on-demand, not at startup (progressive disclosure)

       claude-seo Example - Reference Files (On-Demand Loading):
       Load these on-demand as needed (do NOT load all at startup):
       - references/cwv-thresholds.md: Current Core Web Vitals thresholds
       - references/schema-types.md: All supported schema types with deprecation status
       - references/eeat-framework.md: E-E-A-T evaluation criteria
       - references/quality-gates.md: Content length minimums, uniqueness thresholds
       - references/local-seo-signals.md: Local ranking factors, review benchmarks
       - references/local-schema-types.md: LocalBusiness subtypes, citation sources

       Context Preservation Pattern:
       - Main skill keeps SKILL.md under 500 lines/5000 tokens
       - Sub-skills loaded only when invoked
       - Agents receive URL or focused scope, not full site history
       - Results summarized by orchestrator before returning to user

       ---
       3. ANTI-PATTERNS TO AVOID

       Official Guidance (Agent Teams docs):
       - Subagents cannot spawn other subagents (no nesting)
       - File conflicts: Two teammates/subagents editing the same file leads to overwrites
       - Too many permission prompts: Pre-approve common operations in permission settings
       - Verbose output accumulation: Subagent results returning to main conversation consume context; summarize aggressively

       claude-seo Anti-patterns:
       - Never load all reference files at startup (wasteful)
       - Agents should NOT call other agents (sequential delegation from main orchestrator only)
       - Crawl configuration has hard limits: max 500 pages, 5 concurrent, 30-second timeout per page
       - Quality gates prevent bad recommendations (HowTo schema deprecated Sept 2023, FAQ restricted to govt/healthcare)

       ---
       4. MULTI-STAGE WORKFLOWS & PARALLEL EXECUTION

       Official Guidance (Agent Teams - applies to subagents):
       - Use subagents when tasks would flood main conversation with search results/logs you won't reference again
       - Subagents preserve context by keeping exploration and implementation separate
       - For parallel work, subagents can run concurrently; results aggregate when done
       - Sequential tasks: chain subagents from main conversation (sub1 → results → sub2)

       claude-seo Full Audit Flow (7-8 Parallel Subagents):
       User: /seo audit <url>
           ↓
       [seo-audit/SKILL.md] Orchestrator
           ├─ Fetch homepage & detect business type
           ├─ Crawl site (max 500 pages, respect robots.txt)
           └─ Spawn 7 subagents in parallel:
               ├─ seo-technical (robots.txt, canonicals, CWV, security)
               ├─ seo-content (E-E-A-T, readability, thin content, AI citation)
               ├─ seo-schema (detection, validation, generation)
               ├─ seo-sitemap (structure analysis, quality gates)
               ├─ seo-performance (LCP, INP, CLS measurements)
               ├─ seo-visual (screenshots, mobile, above-fold)
               └─ seo-geo (AI crawler access, llms.txt, citability, brand signals)
               [+ seo-local if Local Service business type detected]
           ↓
           Collect results from all agents
           ↓
           Aggregate into SEO Health Score (0-100) with weights:
           - Technical SEO: 22%
           - Content Quality: 23%
           - On-Page SEO: 20%
           - Schema: 10%
           - Performance: 10%
           - AI Readiness: 10%
           - Images: 5%
           ↓
           Generate FULL-AUDIT-REPORT.md + ACTION-PLAN.md

       ---
       5. SUBAGENTS VS AGENT TEAMS - WHEN TO USE WHICH

       Official Guidance (Agent Teams docs):



       ┌───────────────────────┬─────────────────────────────────────────┬───────────────────────────────────────────────────┐
       │        Feature        │                Subagents                │                    Agent Teams                    │
       ├───────────────────────┼─────────────────────────────────────────┼───────────────────────────────────────────────────┤
       │ Context               │ Own window; results return to caller    │ Own window; fully independent                     │
       ├───────────────────────┼─────────────────────────────────────────┼───────────────────────────────────────────────────┤
       │ Communication         │ Report back to main agent only          │ Teammates message each other directly             │
       ├───────────────────────┼─────────────────────────────────────────┼───────────────────────────────────────────────────┤
       │ Coordination          │ Main agent manages all work             │ Shared task list with self-coordination           │
       ├───────────────────────┼─────────────────────────────────────────┼───────────────────────────────────────────────────┤
       │ Best for              │ Focused tasks where only result matters │ Complex work requiring discussion & collaboration │
       ├───────────────────────┼─────────────────────────────────────────┼───────────────────────────────────────────────────┤
       │ Token cost            │ Lower: results summarized back          │ Higher: each teammate is separate instance        │
       ├───────────────────────┼─────────────────────────────────────────┼───────────────────────────────────────────────────┤
       │ Use subagents when:   │ Quick focused workers reporting results │ ❌ Can't communicate with each other              │
       ├───────────────────────┼─────────────────────────────────────────┼───────────────────────────────────────────────────┤
       │ Use agent teams when: │ ❌ Need inter-agent communication       │ Parallel exploration with discussion/challenges   │
       └───────────────────────┴─────────────────────────────────────────┴───────────────────────────────────────────────────┘


















       claude-seo Uses Subagents (Not Teams) because:
       - Each analysis is independent (no cross-agent discussion needed)
       - Results are aggregated by orchestrator (summary pattern)
       - Sequential dependencies: crawl → type detection → then spawn agents
       - Simpler coordination: single orchestrator manages all 8 agents

       ---
       6. MEMORY & STATE SHARING BETWEEN AGENTS

       Official Guidance (Subagents docs):
       - Persistent memory via memory: user|project|local in frontmatter
       - Scope determines where knowledge persists:
         - user: ~/.claude/agent-memory/<name>/ (cross-project)
         - project: .claude/agent-memory/<name>/ (shareable via git)
         - local: .claude/agent-memory-local/<name>/ (not checked in)
       - Memory includes first 200 lines/25KB of MEMORY.md auto-injected into system prompt
       - Subagents can read and write their memory; claude prompts them to update

       claude-seo Implementation:
       - No persistent memory used (agents are stateless per audit)
       - Context passed explicitly: URL + detected business type to each agent
       - Quality gates hardcoded (not learned/updated across sessions)
       - Option to load extension agents (seo-dataforseo, seo-image-gen) for richer data

       ---
       7. MODEL SELECTION GUIDANCE

       Official Guidance:
       - haiku: Fast, low-latency, for read-only exploration (Explore built-in agent)
       - sonnet: Balanced capability/speed (default for most custom agents)
       - opus: Maximum reasoning capability (rarely needed for agents)
       - inherit: Use parent conversation's model (most common default)

       Per-invocation override order:
       1. CLAUDE_CODE_SUBAGENT_MODEL environment variable (highest)
       2. Per-invocation model parameter
       3. Subagent definition's model frontmatter
       4. Main conversation's model (default)

       claude-seo Selection:
       - Most agents: inherit (use main session model)
       - seo-performance, seo-content, seo-technical: Sonnet-suitable (balanced analysis + tool use)
       - seo-visual: Requires tool access (Playwright) + Bash
       - seo-geo: Requires WebFetch for AI crawler analysis

       ---
       8. PERMISSION & TOOL RESTRICTION BEST PRACTICES

       Official Guidance:
       - Use tools: for allowlist OR disallowedTools: for denylist (not both)
       - Restrict to minimum necessary tools
       - Use Agent(agent-type) syntax to restrict which subagents can be spawned
       - PreToolUse hooks for conditional validation (e.g., read-only DB queries)

       Tool Restriction Pattern (code-reviewer example):
       ---
       name: code-reviewer
       description: Code review specialist
       tools: Read, Glob, Grep, Bash  # Allowlist: no Write/Edit
       ---

       Hook-Based Validation (db-reader example):
       ---
       name: db-reader
       tools: Bash
       hooks:
         PreToolUse:
           - matcher: "Bash"
             hooks:
               - type: command
                 command: "./scripts/validate-readonly-query.sh"
       ---

       claude-seo Tool Allocation:
       - seo-technical: Read, Bash, Write, Glob, Grep (needs to generate reports)
       - seo-content: Read, Bash, Write, Grep (readability analysis + output)
       - seo-schema: Read, Bash, Write (JSON-LD generation)
       - seo-sitemap: Read, Bash, Write, Glob (sitemap XML generation)
       - seo-performance: Read, Bash, Write (metric analysis)
       - seo-visual: Read, Bash, Write (screenshot saving)
       - seo-geo: Read, Bash, WebFetch, Glob, Grep (needs network access)
       - seo-local: Read, Bash, WebFetch, Glob, Grep, Write (most permissive)

       Main orchestrator (seo-audit):
       allowed-tools:
         - Read
         - Grep
         - Glob
         - Bash
         - WebFetch
         - Agent  # Can spawn subagents

       ---
       9. MAXTURN RECOMMENDATIONS

       Official Guidance:
       - maxTurns field: Set maximum number of agentic turns before stopping
       - Default: unlimited (inherit from session)
       - Use to prevent infinite loops or runaway agents
       - Example: maxTurns: 10 for focused, time-bound agents

       claude-seo Configuration:
       Not explicitly set per agent (no maxTurns in provided definitions), suggesting:
       - Trust agents to self-complete within scope
       - Orchestrator manages overall timeout (30-second per-page timeout in crawl config)
       - Site crawl has hard limits (max 500 pages, 5 concurrent, 1-second delay)

       Recommendation for distributed audits:
       - Set maxTurns: 15 on each subagent for audit workflows (safety bound)
       - Crawl orchestrator itself should have maxTurns: 5 (spawn → wait → aggregate → report)

       ---
       10. FAILURE HANDLING & RETRIES

       Official Guidance (Agent Teams docs, applies to subagents):
       - When subagent fails, main conversation receives partial results
       - Clearly note which subagent failed and why
       - Suggest re-running failed subagent individually
       - Teammates can fail silently if running in background mode; upfront permission pre-approves operations
       - For background subagents: if permission missing, tool call fails but subagent continues (on allowed operations)

       Error Handling Patterns:

       ┌────────────────────────────────────────────┬─────────────────────────────────────────────────────────────────────────
       ──┐
       │                  Scenario                  │                                  Action
         │
       ├────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────
       ──┤
       │ URL unreachable (DNS failure, connection   │ Report error clearly. Do NOT guess content. Suggest verify URL.
         │
       │ refused)                                   │
         │
       ├────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────
       ──┤
       │ robots.txt blocks crawling                 │ Report which paths blocked. Analyze only accessible pages, note
         │
       │                                            │ limitation.
         │
       ├────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────
       ──┤
       │ Rate limiting (429 responses)              │ Back off, reduce concurrency (default: 5 → 2). Report partial results.
         │
       ├────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────
       ──┤
       │ Timeout on large sites (500+ pages)        │ Cap at timeout limit. Report findings for crawled pages + estimate total
         │
       │                                            │ scope.
         │
       ├────────────────────────────────────────────┼─────────────────────────────────────────────────────────────────────────
       ──┤
       │ Subagent fails during audit                │ Collect results from successful agents. Report which failed + why. Offer
         │
       │                                            │ re-run option.
         │
       └────────────────────────────────────────────┴─────────────────────────────────────────────────────────────────────────
       ──┘

       claude-seo Retry Logic:
       - Crawl respects robots.txt → no retry on blocked paths (report as limitation)
       - 30-second timeout per page → skip timeout pages, continue with others
       - If subagent fails: report as "Partial Audit Results" with breakdown by agent
       - User can invoke /seo technical <url> to re-run failed agent individually

       Result Aggregation Under Partial Failure:
       ## Partial Audit Results (6/8 agents completed)

       ### Completed
       ✅ Technical SEO (seo-technical)
       ✅ Content Quality (seo-content)
       ✅ Schema Analysis (seo-schema)
       ✅ Sitemap (seo-sitemap)
       ✅ Performance (seo-performance)
       ✅ Visual Analysis (seo-visual)

       ### Failed
       ❌ GEO Analysis (seo-geo) - WebFetch timeout
       ⏭️ Local SEO (seo-local) - Skipped (SaaS business type detected, not local)

       ### Health Score Calculation
       Calculated with 6 agents (weights adjusted):
       - Technical: 22% × score
       - Content: 23% × score
       - ... (skipped local and geo weights redistributed)

       ---
       OFFICIAL BEST PRACTICES SUMMARY

       Design Principles (From claude-seo ARCHITECTURE.md):

       1. Progressive Disclosure
         - Main SKILL.md is concise (<200 lines)
         - Reference files loaded on-demand
         - Detailed instructions in sub-skills
       2. Parallel Processing
         - Subagents run concurrently during audits
         - Independent analyses don't block each other
         - Results aggregated after all complete
       3. Quality Gates
         - Built-in thresholds prevent bad recommendations
         - Location page limits (30 warning, 50 hard stop)
         - Schema deprecation awareness
         - FID → INP replacement enforced
       4. Industry Awareness
         - Templates for different business types
         - Automatic detection from homepage signals
         - Tailored recommendations per industry

       Recommended Patterns (From official docs + claude-seo):

       Pattern 1: Isolate High-Volume Operations
       Request: Run test suite
       → Delegate to test-runner subagent (verbose output stays isolated)
       → Subagent returns: "5 tests passed, 2 failed"
       → Main conversation: clean, focused context

       Pattern 2: Parallel Research
       Request: Investigate auth, database, and API modules
       → Spawn 3 subagents simultaneously (independent paths)
       → Each explores independently, returns summary
       → Orchestrator synthesizes findings

       Pattern 3: Sequential Delegation with Refinement
       Request: Review code, then fix issues
       → code-reviewer subagent (read-only) identifies issues
       → Results returned: 10 performance issues found
       → optimizer subagent (write access) implements fixes
       → Main conversation: "Review → Fix → Verify" workflow

       Pattern 4: Conditional Agent Spawning
       if business_type == "local":
           spawn seo-local agent
       elif business_type == "saas":
           skip seo-local, include seo-schema for integration schema
       elif extension_available("dataforseo"):
           spawn seo-dataforseo alongside core agents

       ---
       KEY PRODUCTION PATTERNS FROM CLAUDE-SEO

       8 Parallel Subagents for Full Audit:
       1. Orchestrator fetches homepage, detects industry
       2. Spawns 7 always + 1 conditional (seo-local for local businesses)
       3. Each agent has focused scope (technical → performance → content, etc.)
       4. Results collected in parallel (concurrent execution)
       5. Aggregated with weights (weighted health score)
       6. Generated reports with actionable priority plan

       Distributed Model Usage:
       - Main session: inherit (usually Opus or Sonnet)
       - All subagents: inherit from main (ensures capability parity)
       - Option: Set specific models per agent if needed (e.g., Haiku for simple pass/fail checks)

       Context Efficiency:
       - Main skill: ~150 lines
       - Sub-skills: 50-150 lines each
       - Agent definitions: 30-80 lines each
       - References: 40-200 lines (loaded only when needed)
       - Total injected context per audit: ~5-8K tokens (tight)

       File Organization:
       seo/                    # Main orchestrator
         SKILL.md             # Router + quality gates
         references/          # On-demand knowledge

       skills/seo-{type}/    # Sub-skills
         SKILL.md

       agents/seo-{role}.md  # Agent definitions (8 of these)

       ---
       This represents the official guidance from Claude Code documentation plus production validation from the claude-seo
       skill which actively orchestrates 8 parallel subagents for full website audits.

⎿  Done (19 tool uses · 70.2k tokens · 1m 6s)

                                                                                              10:38 PM claude-opus-4-6

⏺ Excellent research. Here's what the official guidance and your own production claude-seo skill tell us — applied to our
hivemind design:

---

Best Practices Applied to Our Workflows

1. Agent Descriptions — Make Routing Work

Official guidance says descriptions are the routing mechanism. Write them like activation triggers:

# Bad

description: Reviews code

# Good

description: >
Code review specialist. Proactively reviews for quality, security,
and maintainability. Use after writing or modifying code, during PR
review, or when user says "review", "check this", or "code quality".

Each of our 8 agents needs keyword-rich descriptions so Claude knows when to auto-delegate.

2. Progressive Disclosure — Don't Front-Load Context

Your claude-seo skill proves this pattern: main orchestrator is ~150 lines, reference files load on-demand. Applied to us:

- Agent definitions: 30-80 lines each (system prompt + frontmatter)
- Workflow rules in CLAUDE.md: ~30 lines (just the trigger → pipeline mappings)
- No bulk-loading: agents only load when invoked

3. Parallel Stages Are the Token Efficiency Win

Claude-seo runs 7-8 agents in parallel. Our workflows should do the same:

┌───────────────┬───────────────────────────────────────────┬──────────────────────────────────────────┐
│ Workflow │ Parallel stage │ Why parallel works │
├───────────────┼───────────────────────────────────────────┼──────────────────────────────────────────┤
│ PR Review │ [code-reviewer, linter, security-auditor] │ Independent analyses, no shared state │
├───────────────┼───────────────────────────────────────────┼──────────────────────────────────────────┤
│ Feature Build │ [file-writer × N] per independent module │ Each module is a separate worktree │
├───────────────┼───────────────────────────────────────────┼──────────────────────────────────────────┤
│ Post-build │ [test-runner, linter] │ Test and lint don't depend on each other │
└───────────────┴───────────────────────────────────────────┴──────────────────────────────────────────┘

4. maxTurns — Safety Bounds

Official recommendation: set maxTurns to prevent runaway agents.

┌──────────────────┬──────────────────────┬────────────────────────────────────────┐
│ Agent │ Recommended maxTurns │ Rationale │
├──────────────────┼──────────────────────┼────────────────────────────────────────┤
│ explorer │ 15 │ Deep research may need many file reads │
├──────────────────┼──────────────────────┼────────────────────────────────────────┤
│ code-reviewer │ 10 │ Bounded by file count │
├──────────────────┼──────────────────────┼────────────────────────────────────────┤
│ test-runner │ 8 │ Run tests + report, shouldn't loop │
├──────────────────┼──────────────────────┼────────────────────────────────────────┤
│ file-writer │ 15 │ May need multiple edit cycles │
├──────────────────┼──────────────────────┼────────────────────────────────────────┤
│ planner │ 10 │ Planning is bounded │
├──────────────────┼──────────────────────┼────────────────────────────────────────┤
│ linter │ 5 │ Run command + parse output │
├──────────────────┼──────────────────────┼────────────────────────────────────────┤
│ documenter │ 10 │ Read + write docs │
├──────────────────┼──────────────────────┼────────────────────────────────────────┤
│ security-auditor │ 10 │ Scan patterns + report │
└──────────────────┴──────────────────────┴────────────────────────────────────────┘

5. Memory — Persistent Agent Learning

Official guidance supports per-agent persistent memory:

memory: user # stores at ~/.claude/agent-memory/<name>/

Recommended for: code-reviewer (learns project patterns), explorer (remembers codebase layout)
Skip for: linter, test-runner (stateless — just run commands)

6. Failure Handling

From both docs and claude-seo: collect partial results, report which agent failed, offer re-run.

PR Review result:
✅ code-reviewer: 3 issues found
✅ linter: clean
❌ security-auditor: timed out (maxTurns reached)

    → "Security audit incomplete. Run again with @security-auditor?"

7. Model Selection Refinement

Based on official guidance + your token efficiency goal:

┌──────────────────┬────────┬───────────────────────────────────────────────────┐
│ Agent │ Model │ Why │
├──────────────────┼────────┼───────────────────────────────────────────────────┤
│ planner │ opus │ Deep reasoning for architecture decisions │
├──────────────────┼────────┼───────────────────────────────────────────────────┤
│ explorer │ sonnet │ Balanced — needs good judgment on what's relevant │
├──────────────────┼────────┼───────────────────────────────────────────────────┤
│ code-reviewer │ sonnet │ Nuanced quality assessment │
├──────────────────┼────────┼───────────────────────────────────────────────────┤
│ file-writer │ sonnet │ Needs coding capability │
├──────────────────┼────────┼───────────────────────────────────────────────────┤
│ security-auditor │ sonnet │ Pattern recognition for vulnerabilities │
├──────────────────┼────────┼───────────────────────────────────────────────────┤
│ test-runner │ haiku │ Run command, parse output — simple │
├──────────────────┼────────┼───────────────────────────────────────────────────┤
│ linter │ haiku │ Run command, parse output — simple │
├──────────────────┼────────┼───────────────────────────────────────────────────┤
│ documenter │ sonnet │ Writing quality matters │
└──────────────────┴────────┴───────────────────────────────────────────────────┘

★ Insight ─────────────────────────────────────

- haiku for linter + test-runner saves significant tokens — these agents are essentially "run a command, read the output,
  report back" which doesn't need deep reasoning
- memory: user on code-reviewer and explorer means they get smarter over time across projects — the reviewer learns your
  style preferences, the explorer remembers common architecture patterns
- maxTurns is your safety net — without it, a confused agent could burn tokens indefinitely. claude-seo enforces this via
  crawl limits; we enforce it per-agent
  ─────────────────────────────────────────────────

---

Updated Workflow Design (incorporating all guidance):

Workflow 1: Codebase Research
Trigger: "explore", "investigate", "map", unfamiliar repo
Stage 1: [explorer × 1-3] parallel with different search focuses
Stage 2: Queen synthesizes → presents findings
maxTurns: 15 per explorer

Workflow 2: PR / Code Review
Trigger: "review", "check", after implementation complete
Stage 1 (parallel): [code-reviewer, linter, security-auditor]
Stage 2: Queen aggregates into unified report with severity levels
Stage 3 (conditional): [test-runner] if reviewers flag untested paths
Failure: partial results + offer re-run of failed agents

Workflow 3: Feature Implementation
Trigger: "implement", "build", after plan approval
Stage 1: [planner] → architecture + file breakdown
Stage 2 (parallel): [file-writer × N] in worktree isolation
Stage 3 (parallel): [test-runner, linter] → validate
Stage 4: [code-reviewer] → final quality gate
Failure: stop pipeline, report which stage failed

Workflow 4: Ad-hoc (auto-delegation)
Trigger: no explicit workflow match
Behavior: Claude routes based on agent descriptions
Bound: maxTurns enforced per agent

Does this enhanced design look right? Anything you'd adjust before I write up the full spec?

✻ Cogitated for 1m 55s

❯ But shouldn't we use the claude built in recommended agent teams over creating our own subagents queen hivemind what is the
idfferent?

                                                                                              10:42 PM claude-opus-4-6

⏺ This is an important distinction. Let me break it down clearly — they serve different purposes:

Agent Teams vs Subagents: What They Actually Are

Subagents (what our hivemind uses)

Your conversation (Queen)
├── Spawns explorer → gets result back
├── Spawns reviewer → gets result back
└── Spawns linter → gets result back

    Workers report TO you. They can't talk to each other.
    Each runs in isolated context. Only summary returns.

- One session, one terminal
- Queen controls everything — assigns work, collects results
- Workers are disposable — spawn, do task, return result, gone
- Cheap — verbose output stays in worker context, not yours

Agent Teams (Claude's built-in experimental feature)

Lead (you in tmux pane 1)
├── Teammate A (tmux pane 2) ←→ can message Teammate B
├── Teammate B (tmux pane 3) ←→ can message Teammate A
└── Shared Task List (all can read/write/claim)

    Teammates are PEERS. They discuss, challenge, coordinate.
    Each is a full Claude Code session.

- Multiple terminals running simultaneously (via tmux)
- Teammates are persistent — they live for the whole session
- They can message each other directly (not just the lead)
- Shared task list with self-claiming — teammates pick up work autonomously
- Expensive — each teammate is a separate full Claude instance

When to Use Which

┌───────────────────────────────────────────────────────┬──────────────────────────────────┬────────────────────────────┐
│ Scenario │ Subagents │ Agent Teams │
├───────────────────────────────────────────────────────┼──────────────────────────────────┼────────────────────────────┤
│ "Run tests and lint in parallel" │ ✓ — independent, no discussion │ Overkill │
│ │ needed │ │
├───────────────────────────────────────────────────────┼──────────────────────────────────┼────────────────────────────┤
│ "Explore 3 areas of the codebase" │ ✓ — each returns findings │ Overkill │
│ │ independently │ │
├───────────────────────────────────────────────────────┼──────────────────────────────────┼────────────────────────────┤
│ "Build a feature where frontend and backend need to │ Awkward — workers can't discuss │ ✓ — teammates negotiate │
│ coordinate on API contracts" │ interfaces │ the API shape │
├───────────────────────────────────────────────────────┼──────────────────────────────────┼────────────────────────────┤
│ "Review code from multiple perspectives" │ ✓ — each reviewer works │ Overkill │
│ │ independently │ │
├───────────────────────────────────────────────────────┼──────────────────────────────────┼────────────────────────────┤
│ "Refactor a module where 3 files have circular │ Risky — writers can't see each │ ✓ — teammates coordinate │
│ dependencies" │ other's changes │ changes live │
├───────────────────────────────────────────────────────┼──────────────────────────────────┼────────────────────────────┤
│ Token efficiency is priority │ ✓ — much cheaper │ ✗ — 3-5x cost │
└───────────────────────────────────────────────────────┴──────────────────────────────────┴────────────────────────────┘

The Honest Assessment

For your three stated use cases:

1. Codebase research → Subagents win. Explorers don't need to talk to each other.
2. Code review + testing → Subagents win. Each reviewer works independently.
3. Multi-file writing → It depends:
   - Independent modules → Subagents (each writer in its own worktree)
   - Interdependent files (shared interfaces, circular deps) → Agent Teams

★ Insight ─────────────────────────────────────

- Agent Teams is experimental — it's newer, uses tmux under the hood, and is heavier infrastructure. Subagents are the
  stable, battle-tested path.
- Agent Teams can USE subagent definitions — a teammate can reference your explorer.md or code-reviewer.md. So defining
  agents is valuable either way.
- The real question isn't either/or — it's "which tasks need peer coordination?" Most don't. The 80% case is subagents.
  Agent Teams is for the 20% where workers need to negotiate with each other.
  ─────────────────────────────────────────────────

My Recommendation: Stay with Subagents, Enable Teams as Escalation

Default: Subagents (cheap, focused, covers 80% of work)
Escalation: Agent Teams for complex multi-file refactors
where writers need to coordinate live

Both use the SAME agent definitions in ~/.claude/agents/

Our 8 agent definitions work for both — Agent Teams can reference them as teammates when needed. We're not locked in.

Does this clarify the difference? Want to keep the subagent-first approach, or shift the design toward Agent Teams for any
of the workflows?

✻ Cooked for 36s

❯ based on
Enable agent teams
Agent teams are disabled by default. Enable them by setting the CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS environment variable
to 1, either in your shell environment or through settings.json:

                                                                                              10:42 PM claude-opus-4-6

⏺ Good catch. Agent Teams requires explicit opt-in since it's experimental. We should include this in our config so it's ready
when you need it, but not forced.

Here's what I'd add to the design:

Enable Agent Teams as opt-in escalation

In ~/.claude/settings.json:
{
"env": {
"CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1"
}
}

This doesn't change default behavior — Claude still uses subagents for everything. It just unlocks the ability to spawn
Agent Teams when a task actually needs peer coordination (the 20% case).

Updated CLAUDE.md workflow rule:

## Hivemind escalation

- Default: use subagents (focused workers, token-efficient)
- Escalate to Agent Teams ONLY when:
  - Multiple files share interfaces that need live negotiation
  - A refactor has circular dependencies across 3+ files
  - Workers need to challenge each other's assumptions (design review)
- Never escalate for: independent research, testing, linting, single-file edits

★ Insight ─────────────────────────────────────

- Setting the env var in settings.json is cleaner than exporting in .zshrc — it's scoped to Claude Code only and won't leak
  into other tools
- The env var enables the capability, not the behavior — Claude still needs to decide (or be told) to use teams vs subagents
  per task
- This matches your "Claude as queen" model — the queen decides when to delegate to solo workers vs assemble a team
  ─────────────────────────────────────────────────

Shall I fold this into the final spec and move to writing it up? Or any other aspects to dig into first?

❯ fold this into the final spec and continue

⏺ Bash(ls /Users/seintun/.claude/docs/superpowers/specs/ 2>/dev/null || echo "directory does not exist")
⎿  directory does not exist

⏺ Bash(mkdir -p /Users/seintun/.claude/docs/superpowers/specs)
⎿  Done

⏺ Write(/Users/seintun/.claude/docs/superpowers/specs/2026-04-09-hivemind-orchestration-design.md)

──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
Showing detailed transcript · ctrl+o to toggle · ctrl+e to show all

The proposed "Hivemind" plan doesn't replace Claude's experimental Agent Teams; rather, it builds a highly optimized orchestration layer on top of it.

By default, when you enable the CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS flag, Claude Code can dynamically spin up parallel subagents to handle tasks. However, it does this on the fly based on
your prompt, which can be unpredictable.

Here is how the Hivemind plan differs and how it deeply impacts token efficiency and context:

1. The Core Differences

- Default Agent Teams: Ad-hoc and dynamic. You ask Claude to "create a team," and it guesses what roles, models, and tools to give them.
- Hivemind Setup: Deterministic and strictly defined. It hardcodes 8 permanent, specialized experts (e.g., test-runner, security-auditor) with exact instructions, tool constraints, and
  specific workflows baked into your CLAUDE.md. Instead of guessing, Claude routes tasks to these specific profiles.

2. Context & Token Efficiency (The Benefits)
   The Hivemind setup is specifically designed to save you money and tokens while preventing context bloat:

- Model Routing (Cost Savings): Not every task needs the most expensive model. The plan explicitly assigns cheaper, faster models to routine tasks (e.g., haiku for the test-runner and
  linter), while reserving expensive models like opus only for the planner. Default Agent Teams might default to Sonnet/Opus for everything.
- Context Isolation (Keeps the main thread clean): When a subagent runs (like the linter fixing 50 formatting errors), all of that messy back-and-forth tool use stays in its isolated
  context window. Once finished, it just returns a short summary to your main session. Your main session stays lean, which makes subsequent prompts much cheaper.
- Blast Radius / Infinite Loops (Max Turns): The plan enforces strict maxTurns (e.g., 5 for linter, 15 for explorer). This prevents a rogue subagent from getting stuck in an infinite loop
  of failing tests and draining millions of tokens.
- Tool Restrictions: By stripping write permissions from the explorer, its system prompt is smaller and it is structurally prevented from making accidental, costly edits while
  researching.

3. Where it can be Hurtful (The Trade-offs)
   While powerful, utilizing Agent Teams (even with the Hivemind setup) introduces some token inefficiencies:

- Redundant Context Loading: Because each subagent operates in an isolated session, they don't share memory. If the explorer, code-reviewer, and file-writer all need to understand the
  same core files to do their jobs, they will all have to independently read those files. You pay for those file-read tokens 3 times.
- Orchestration Overhead: The main session has to spend tokens reasoning about which agent to use, writing the prompt to delegate the task, and reading the summary that comes back. For
  very simple tasks (like fixing a single typo), delegating to a team is actually more expensive than just doing it in the main thread.

In summary: The Hivemind plan takes the raw power of Claude's Agent Teams and puts guardrails on it. It trades some redundant file-reading costs for massive savings in model routing,
context isolation, and infinite-loop prevention.

## Hivemind vs Claude Agent Teams Comparison

### Core Architecture Difference

| Aspect | Hivemind (Your Plan) | Claude Agent Teams |
|--------|---------------------|-------------------|
| **Definition** | 8 pre-defined user-level subagents with YAML frontmatter | Dynamic teammate spawning, no required pre-definition |
| **Scope** | Explicit: you create 8 fixed roles | Emergent: Claude decides roles based on your prompt |
| **Tool restrictions** | Hardcoded per agent (e.g., explorer=read-only, file-writer=worktree) | Soft: inherits lead's permissions, can customize |
| **Coordination** | Workflows defined in CLAUDE.md | Shared task list + direct messaging |

### Token Efficiency Analysis

**Agent Teams (official):**
- **Each teammate = separate Claude instance** → full context window, full token cost
- Scale: ~3-5x single session for 3 teammates (each has own context)
- "Token costs scale linearly" per docs — no discount for being "subagents"
- Best for: complex work where parallel exploration justifies cost

**Hivemind:**
- Uses **subagent model**, not full agent teams
- Subagents run "within a single session" per docs
- Results summarized back to main context = lower token overhead
- 8 specialized agents = selective spawning (only spawn what's needed)

### Context Management

**Agent Teams:**
- Each teammate: owns context window, loads CLAUDE.md + MCP + skills fresh
- Doesn't inherit lead's conversation history
- Direct inter-agent messaging (teammates talk to each other)
- Shared task list with claim mechanics

**Hivemind:**
- Agents run in main session context
- Main agent controls all messaging flow
- No inter-agent communication — main agent synthesizes
- Workflow chaining (planner→writer→tester→linter)

### Benefit/Hurt Analysis

#### Benefits of Hivemind Approach

1. **Lower token cost** — subagent overhead vs full teammate cost
2. **Predictable roles** — 8 defined agents with known capabilities
3. **Tool restrictions enforced** — explorer can't write by design
4. **Simpler coordination** — no task list / mailbox management
5. **Faster startup** — no dynamic role negotiation

#### Benefits of Agent Teams (Official)

1. **Flexibility** — roles emerge from task, not pre-defined
2. **True parallelism** — teammates can debate, challenge each other
3. **Deeper exploration** — each has full context window
4. **Direct interaction** — you can message any teammate directly
5. **Better for research** — multiple perspectives collide

#### When Hivemind Hurts

- **Simple tasks** — overhead of 8 agents unnecessary
- **Same-file edits** — can't coordinate parallel file edits cleanly
- **Dynamic needs** — fixed roles may not fit unusual tasks

#### When Agent Teams Hurt

- **Token budget** — 3 teammates = 3-5x cost
- **Sequential work** — coordination overhead not worth it
- **Small tasks** — should use subagents instead
- **Known limitations** — no session resumption, task status lag, experimental

### Recommendation

**Use Hivemind for:**
- Day-to-day development workflows
- Enforcing tool restrictions (read-only explorer)
- Budget-conscious parallelism
- Predictable, repeated patterns

**Use Agent Teams for:**
- Complex research where debate matters
- When you need true independent investigation
- New problems where fixed roles don't apply

**Hybrid is best**: Define your 8 hivemind agents, then use Agent Teams to spawn dynamic teammates when needed for complex exploration. The hivemind agents become reusable **subagent definitions** that Agent Teams can reference with `Spawn a teammate using the explorer agent type`.