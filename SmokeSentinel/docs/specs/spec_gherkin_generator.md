# Spec — Gherkin Scenario Generator (LLM-based)
**Project:** SmokeSentinel · Module `gherkin/`
**Status:** To implement · **Version:** 1.0

---

## Objective

Automatically transform a Jira User Story into ready-to-use Gherkin (BDD) scenarios via an LLM call (Claude). These scenarios feed directly into the Playwright MCP runner of the SmokeSentinel pipeline.

---

## Inputs / Outputs

| | Details |
|---|---|
| **Input** | Jira story: title, description, acceptance criteria (AC) |
| **Output** | Valid Gherkin `.feature` file + JSON metadata |

---

## Expected Behavior

Given a story such as:

> *"As a user, I want to log in with my email and password so that I can access my dashboard."*

The module automatically generates:

- **Happy path scenario** — user logs in with valid credentials
- **Error scenarios** (sad paths) — wrong password, empty field, unknown account
- **Edge case scenarios** — expired session, multiple failed attempts

Each scenario follows standard Gherkin `Given / When / Then` syntax, with context-inferred tags (`@smoke`, `@login`, etc.).

---

## Module Architecture

```
gherkin/
├── generator.py        # Main orchestrator
├── prompt_builder.py   # LLM prompt construction
├── parser.py           # Parsing and validation of returned Gherkin
├── writer.py           # .feature file writer
└── prompts/
    └── gherkin_base.txt  # System prompt template
```

---

## LLM Prompt — Key Directives

The system prompt must instruct Claude to:

1. Generate **3 to 6 scenarios** per story (1 happy path, 2+ error, 1+ edge case)
2. Strictly follow Gherkin syntax (`Feature`, `Scenario`, `Given`, `When`, `Then`, `And`)
3. Use **atomic and reusable steps** (Playwright-compatible)
4. Add relevant **tags**: `@smoke`, `@<feature_name>`, `@happy_path` / `@error`
5. Respond **in pure Gherkin only** — no surrounding prose

---

## Python Interface

```python
from gherkin.generator import GherkinGenerator

generator = GherkinGenerator(llm_client=claude_client)

result = generator.run(
    story_title="User Login",
    story_description="...",
    acceptance_criteria=["AC1: ...", "AC2: ..."],
    output_path="tests/features/login.feature"
)

# result.scenarios    → list of parsed scenarios
# result.feature_file → path to the generated .feature file
# result.tags         → inferred tags
```

---

## Validation & Quality

After generation, the parser automatically validates:

- Correct Gherkin syntax (`Feature > Scenario > Steps` structure)
- At least 1 happy path scenario and 1 error scenario present
- Every step starts with `Given`, `When`, `Then`, or `And`
- No spurious text (unstructured LLM prose)

On validation failure → **automatic retry** (max 2 attempts) with the error feedback re-injected into the prompt.

---

## Pipeline Integration

```
Jira Story (JIRA-1234)
       │
       ▼
GherkinGenerator.run()
       │
       ▼
tests/features/JIRA-1234.feature
       │
       ▼
Playwright MCP Runner
```

`sentinel.py` calls this module first, before any test execution.

---

## Required Environment Variables

| Variable | Usage |
|---|---|
| `ANTHROPIC_API_KEY` | Claude API call |
| `GHERKIN_MODEL` | Model to use (default: `claude-sonnet-4-6`) |
| `GHERKIN_MAX_SCENARIOS` | Max number of scenarios (default: `6`) |
| `GHERKIN_OUTPUT_DIR` | Output directory for `.feature` files (default: `tests/features/`) |

---

## Module Acceptance Criteria

- [ ] A `generator.run()` call produces a valid `.feature` file
- [ ] The file contains at least 1 happy path scenario + 1 error scenario
- [ ] Syntax validation passes without errors
- [ ] On invalid LLM output, the retry mechanism triggers automatically
- [ ] The module is testable in isolation (without Jira or Playwright)

## PROMPT:

implemente moi ce module please. merci.


## RESULTS:

Now let's write the test suite:33/33 ✅. Copions les fichiers vers les outputs.**33/33 tests passing.** Here's what was delivered:

**Module structure (`gherkin/`)**

`__init__.py` — clean public exports  
`generator.py` — main orchestrator: calls LLM, retries on failure, writes `.feature` + `.json` metadata  
`parser.py` — validates and parses raw Gherkin into typed objects (`GherkinFeature`, `GherkinScenario`, `GherkinStep`)  
`writer.py` — serialises a `GherkinFeature` back to a clean `.feature` file  
`prompt_builder.py` — assembles the user prompt from story data  
`prompts/gherkin_base.txt` — system prompt template with all Gherkin generation rules  

**Usage in `sentinel.py`**

```python
from gherkin import GherkinGenerator

gen = GherkinGenerator()  # picks up ANTHROPIC_API_KEY from env
result = gen.run(
    story_title="User Login",
    story_description="As a user I want to log in...",
    acceptance_criteria=["AC1: ...", "AC2: ..."],
    story_id="SMOKE-42",   # → tests/features/SMOKE-42.feature
)
```

**Key behaviours**
- Generates 3–6 scenarios (happy path, sad paths, edge cases) with proper `@tags`
- Auto-retry up to 2 times if the LLM output fails validation, with the error re-injected into the prompt
- Strips markdown fences if the LLM wraps its output
- Writes a `.json` metadata file alongside each `.feature`
- Fully testable offline (no Jira, no Playwright, LLM mocked)
