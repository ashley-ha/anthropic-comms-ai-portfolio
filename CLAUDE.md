# Comms AI Portfolio — Project Instructions

## What This Is
Portfolio project for the **AI Solutions Architect, Communications** role at Anthropic.
See `role.md` for the full job description. Every feature should map back to the role's four pillars: Discover, Build, Train, Catalogue.

## Representative Projects (from role.md)
1. Daily press clips digest — `press_digest.py` (BUILT)
2. Rapid-response monitoring — `rapid_response.py` (BUILT)
3. Briefing generator — `briefing_generator.py` (BUILT)
4. Internal comms workflow tool — `internal_comms.py` (BUILT)
5. Message pull-through tracker — `pull_through_tracker.py` (BUILT)
6. Comms Automation Playbook — `playbook/` (DRAFT)

## Tech Stack
- Python 3.9+, Anthropic SDK
- Claude tool_use for structured outputs (article analysis, event assessment)
- Direct generation for long-form (briefings)
- Eval harness with human-labeled ground truth

## Key Patterns
- All Claude calls go through `claude_client.py` — single point of control
- Model is configurable via `CLAUDE_MODEL` env var (default: claude-sonnet-4-20250514)
- Outputs go to `outputs/` (gitignored except .gitkeep)
- Mock data in `data/` — synthetic, safe for public sharing

## Running
```bash
source .venv/bin/activate
python scripts/run_press_digest.py
python scripts/run_rapid_response.py
python scripts/run_briefing.py
python scripts/run_pull_through.py
python scripts/run_internal_comms.py
python evals/eval_runner.py
python -m unittest discover -s tests -p 'test_*.py'
```

## Testing Standards
- Tests call the real Claude API (no mocks)
- Eval harness scores against human-labeled datasets
- Target metrics defined in `evals/*.yaml`
