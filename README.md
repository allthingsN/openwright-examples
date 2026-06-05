# OpenWright examples

<p>
  <a href="https://github.com/allthingsN/openwright-examples/actions"><img src="https://github.com/allthingsN/openwright-examples/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://github.com/allthingsN/openwright-examples/actions"><img src="https://raw.githubusercontent.com/allthingsN/openwright-examples/badges/coverage.svg" alt="coverage"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="License"></a>
</p>

Runnable agents from popular frameworks, each with [OpenWright](https://github.com/allthingsN/openwright)
evidence capture added — so you can see the exact code delta and what it buys you.

We **don't vendor upstream code**. Each example **links to the original**, and ships a
single self-contained, runnable file (`main.py`) that is that agent **with OpenWright
added**. The README in each folder shows the exact delta and the benefit.

The thesis: integrating OpenWright is **three lines, agent logic untouched** —
`openwright.instrument("<framework>")` registers a global processor that turns every tool
call, handoff, and decision into signed, hashed, tamper-evident, control-mapped evidence,
checkpointed WORM (e.g. S3 Object-Lock) and verifiable offline.

```mermaid
flowchart LR
    BEFORE("🤖 your agent today<br/><i>tools · handoffs · decisions</i>"):::agent
    BEFORE -->|"+ 3 lines:<br/><b>openwright.instrument(…)</b>"| AFTER("same agent, now producing<br/>signed, tamper-evident evidence"):::ow
    AFTER --> PACK("✅ offline-verifiable<br/>control-mapped evidence pack"):::verify

    classDef agent fill:#eef2ff,stroke:#6366f1,color:#312e81;
    classDef ow fill:#dcfce7,stroke:#16a34a,color:#064e3b;
    classDef verify fill:#1e3a8a,stroke:#3b82f6,color:#dbeafe;
```

## Examples

| Framework | Example | Original |
|---|---|---|
| OpenAI Agents SDK | [`examples/openai/customer_service`](examples/openai/customer_service) | [openai-agents-python · customer_service](https://github.com/openai/openai-agents-python/blob/main/examples/customer_service/main.py) |
| OpenAI Agents SDK | [`examples/openai/financial_research_agent`](examples/openai/financial_research_agent) | [openai-agents-python · financial_research_agent](https://github.com/openai/openai-agents-python/tree/main/examples/financial_research_agent) |

Both take the **same three-line change** — the financial one is a 6-agent pipeline,
showing the integration cost doesn't grow with agent complexity.

## Install & run

```bash
pip install -r requirements.txt        # openwright-core + openwright-openai-agents + openai-agents
export OPENAI_API_KEY=sk-...
export OPENWRIGHT_CHECKPOINT_STORE="s3://your-bucket/checkpoints?lock=COMPLIANCE&days=180"   # or file://./out/cp

cd examples/openai/customer_service && python main.py
openwright verify out/report.json --pubkey out/public_key.pem --deep
```

Each `main.py` is self-contained and runnable on its own (no repo-internal imports).
