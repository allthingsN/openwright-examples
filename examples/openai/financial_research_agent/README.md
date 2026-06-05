# OpenAI Agents SDK — Financial Research Agent (+ OpenWright)

A runnable **multi-agent** financial research pipeline (planner → web search →
fundamentals/risk analysts-as-tools → writer → verifier) with OpenWright evidence capture.

- **Original example:**
  https://github.com/openai/openai-agents-python/tree/main/examples/financial_research_agent
- **`main.py`** here is a self-contained, runnable single-file version of that pipeline
  **with OpenWright added**. (One simplification vs. upstream: the search step uses a plain
  `function_tool` instead of the hosted `WebSearchTool`, so it runs on any chat model with
  just an `OPENAI_API_KEY`; swap in `WebSearchTool` for the real thing.)

## The exact delta vs. the original

The same three lines as any other agent — **regardless of pipeline size**:

```python
import openwright                                                                 # (1)

# after the agents are defined:
openwright.instrument("openai-agents",
                      decision_tools=["fundamentals_analysis", "risk_analysis"])   # (2) global capture

# after mgr.run / the pipeline:
openwright.get_runtime().report(out_dir="out", scope_description="Financial research agent")  # (3)
```

**This is the headline:** a 6-agent, multi-`Runner.run` pipeline takes the **same change**
as a single agent. `instrument()` installs a global tracing processor, so every planner
call, web search, analyst-tool call, writer step, and verification — across all agents — is
captured automatically. You touch none of the agent definitions.

Config is environment:
```bash
export OPENWRIGHT_CHECKPOINT_STORE="s3://your-bucket/checkpoints?lock=COMPLIANCE&days=180"  # or file://./out/cp
```

## Run

```bash
pip install -r ../../../requirements.txt
export OPENAI_API_KEY=sk-...
python main.py
openwright verify out/report.json --pubkey out/public_key.pem --deep
```

## Benefit

| Without OpenWright | With OpenWright (this file) |
|---|---|
| A report + an expiring dashboard trace | A **signed, append-only provenance record** of how the analysis was produced |
| No record of which searches/tools fed the conclusion | Every **search**, **fundamentals/risk analysis**, and **verification** captured (hashed) |
| The analytical conclusions are unattributed | `fundamentals_analysis` / `risk_analysis` recorded as **attested decisions** |
| "Trust the report" | An **offline-verifiable** evidence pack — re-derive what informed the recommendation, unaltered |
| Logs editable after the fact | A **WORM S3 checkpoint** sealing the research trail |

For a regulated advisory/research workflow this is the provenance a reviewer needs — *what
informed this recommendation, in what order, and proof it wasn't edited afterward* — without
exposing raw prompts/sources (hashes only).
