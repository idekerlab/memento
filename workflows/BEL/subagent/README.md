# Paper-Processor Subagent

Context-isolated subagent that reads one paper and returns structured BEL tuples + summary. See [SUBAGENT.md](SUBAGENT.md) for the full spec.

## Files

- [SUBAGENT.md](SUBAGENT.md) — authoritative spec: input contract, output contract, protocol, failure modes
- [output_schema.json](output_schema.json) — strict JSON schema the output must validate against
- [examples/](examples/) — representative outputs from real invocations

## One-line invocation from a main agent

The main agent (rzenith, rgiskard, …) calls the subagent via the `Agent` tool, passes a JSON task spec, and persists the returned JSON as an analysis network in NDEx. Full caller pattern is in [SUBAGENT.md § Caller pattern](SUBAGENT.md#caller-pattern-main-agent-side).

## Rationale

Full-text paper reading floods a main agent's context window within 2-3 papers. The subagent takes all of that context pressure on itself, hands back a ~2KB JSON, and lets the main agent stay oriented to its broader goals. This is the only reason the subagent exists — it is not a new capability, just a context-isolation tool.
