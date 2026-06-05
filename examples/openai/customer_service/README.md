# OpenAI Agents SDK — Customer Service (+ OpenWright)

A runnable airline customer-service agent (Triage → FAQ / Seat-Booking handoffs, tools
`faq_lookup_tool` + `update_seat`) with OpenWright evidence capture.

- **Original example:**
  https://github.com/openai/openai-agents-python/blob/main/examples/customer_service/main.py
- **`main.py`** here is a self-contained, runnable version of that agent **with OpenWright added**.

## The exact delta vs. the original

Three lines — the agents, tools, handoffs, and the `Runner.run` call are unchanged:

```python
import openwright                                                      # (1)

# after the agents are defined:
openwright.instrument("openai-agents", decision_tools=["update_seat"]) # (2) global capture

# after the conversation loop:
openwright.get_runtime().report(out_dir="out")                          # (3) emit the signed pack
```

`instrument()` registers a global tracing processor, so every tool call and handoff is
captured automatically — no hooks, no wrapping of `Runner.run`. Config is environment:

```bash
export OPENWRIGHT_CHECKPOINT_STORE="s3://your-bucket/checkpoints?lock=COMPLIANCE&days=180"  # or file://./out/cp
export OPENWRIGHT_SIGNING_KEY_FILE=./key.pem        # or OPENWRIGHT_SIGNING_KEY / a KMS ref
```

## Run

```bash
pip install -r ../../../requirements.txt    # openwright-core + openwright-openai-agents + openai-agents
export OPENAI_API_KEY=sk-...
python main.py        # interactive; non-interactive replays a scripted seat change
openwright verify out/report.json --pubkey out/public_key.pem --deep
```

## Benefit

| Without OpenWright | With OpenWright (this file) |
|---|---|
| Console output + an expiring dashboard trace | A **signed, append-only Merkle log** of every tool call + handoff |
| The seat change leaves no durable proof | `update_seat` recorded as an **attested decision** (what changed, when, on which booking) |
| Raw I/O in logs | **Hashes only** (`sha256:` refs) — privacy-safe |
| "Trust us" | An **offline-verifiable** evidence pack |
| Logs editable after the fact | A **WORM S3 checkpoint** — not even the root account can rewrite it |

When a customer disputes *"your agent changed my seat without asking,"* you produce
cryptographic proof of exactly what the agent did, in order, unaltered.
