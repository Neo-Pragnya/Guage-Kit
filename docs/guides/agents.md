---
title: Agents
description: Score what an agent did - tool choice, arguments, order, errors, success - with Guage Kit's tool metrics and Ananke Plexus's 77 trace evaluators.
---

# Evaluating agents

An agent is judged on its actions as much as its final answer. Guage Kit scores actions in two ways:

- **Tool-call metrics** compare the calls the agent made (`tool_calls`) with the calls it should have made
  (`expected_tool_calls`).
- **Ananke evaluators** score the whole trace: loops, forbidden steps, budgets, safety boundaries, planning,
  recovery and multi-agent hand-offs. They are registered as metrics named `ananke.<dimension>.<name>`.

## Recording what the agent did

Give each sample its tool calls, or a recorded trace:

```json
{"id": "a1", "input": "Refund order 42, it arrived broken.",
 "tool_calls": [{"name": "lookup_order", "arguments": {"order_id": "42"}},
                {"name": "issue_refund", "arguments": {"order_id": "42", "reason": "damaged"}}],
 "expected_tool_calls": [{"name": "lookup_order", "arguments": {"order_id": "42"}},
                         {"name": "issue_refund", "arguments": {"order_id": "42", "reason": "damaged"}}],
 "metadata": {"success": true}}
```

A tool call has `name`, `arguments`, and optionally `output` and `error` (a failed call). A target can return
`tool_calls` (see [Targets](targets.md)).

A `trace` is any trace Ananke can normalise: an object with `spans`, each with `span_id`, `kind` (`tool`,
`retrieval`, `model`, `planning`, `subagent`, `approval`, `shell`, …), `name`, `start_time`, and optionally `input`,
`output`, `attributes` and `parent_span_id`, plus `usage` and `final_output`. When a sample has a trace but no
`tool_calls`, the tool-call metrics read the trace's `tool` spans. When a sample has no trace, Ananke evaluators get one
built from its contexts (a retrieval span), tool calls, output, usage and latency.

## Tool-call metrics

| Metric | Value |
| --- | --- |
| `tool_call_f1` | F1 over tool names as multisets; details list missing and unexpected tools |
| `tool_args_accuracy` | for each expected call, the share of its arguments the best matching actual call got right (strings compared case- and whitespace-insensitively) |
| `tool_sequence_match` | longest common subsequence of tool names ÷ the longer sequence (order-aware) |
| `tool_calls_exact` | 1 when the calls match exactly, in order, with the expected arguments |
| `tool_error_rate` | share of calls with an error (lower is better) |
| `redundant_tool_calls` | share of calls repeating an earlier call with the same arguments (lower is better) |
| `goal_success` | `metadata.success` from your environment check |

```python
import guage_kit as gk
from guage_kit import Sample, ToolCall

expected = [ToolCall(name="lookup_order", arguments={"order_id": "42"}),
            ToolCall(name="issue_refund", arguments={"order_id": "42", "reason": "damaged"})]
did = [ToolCall(name="issue_refund", arguments={"order_id": "42", "reason": "damaged"})]
run = gk.evaluate([Sample(id="a1", input="Refund order 42, it arrived broken.", tool_calls=did,
                          expected_tool_calls=expected)],
                  ["tool_call_f1", "tool_sequence_match", "tool_args_accuracy",
                   "ananke.trajectory.required_step",
                   {"name": "ananke.tool_use.tool_denylist", "params": {"denied": ["delete_account"]}}])
for k, v in run.summaries.items():
    print(f"{k:34} {v.value:.3f}")
```

```text
tool_call_f1                       0.667
tool_sequence_match                0.500
tool_args_accuracy                 0.500
ananke.trajectory.required_step    1.000
ananke.tool_use.tool_denylist      1.000
```

The agent skipped the lookup. It still reached the goal action (`required_step` passes) and called nothing forbidden.

## Ananke evaluators

Guage Kit discovers the evaluators in the installed Ananke Plexus, so a newer Ananke brings new evaluators without a
Guage Kit release. In this release there are 77, in these dimensions:

| Dimension | Examples |
| --- | --- |
| `ananke.trajectory` | `strict`, `ordered_subset`, `unordered_subset`, `superset`, `required_step`, `forbidden_step`, `loop_detection`, `step_efficiency`, `graph` |
| `ananke.tool_use` | `tool_selection`, `tool_allowlist`, `tool_denylist`, `tool_schema`, `tool_order`, `duplicate_side_effect`, `idempotency`, `tool_retry` |
| `ananke.efficiency` | `token_budget`, `cost_budget`, `latency`, `tool_call_count`, `model_call_count`, `wall_clock`, `retry_count`, `cache_efficiency` |
| `ananke.safety` | `permission_boundary`, `filesystem_scope`, `secret_access`, `secret_leakage`, `approval_gate`, `shell_policy`, `agent_authority`, `dependency_approval` |
| `ananke.planning` | `plan_coverage`, `plan_dependency`, `plan_feasibility`, `plan_risk`, `plan_adherence`, `plan_revision_quality` |
| `ananke.resilience` | `failure_recognition`, `recovery_path`, `repeated_failure`, `checkpoint_usage`, `rollback`, `partial_failure_containment` |
| `ananke.multi_agent` | `delegation_accuracy`, `role_boundary`, `handoff_completeness`, `shared_context_consistency`, `cyclic_delegation`, `message_duplication` |
| `ananke.outcome`, `ananke.retrieval`, `ananke.architecture` | exact and schema matching, task completion, context precision and recall, spec and architecture conformance |

```bash
guage metrics list --family ananke            # all of them, with what they need
guage metrics show ananke.trajectory.loop_detection
```

### Configuring an evaluator

Many evaluators take arguments (a list of forbidden tools, a token budget). Guage Kit resolves each argument in this
order:

1. **Metric parameters**, in code or `guage.yaml`:
   `{name: ananke.efficiency.token_budget, params: {max_tokens: 20000}}`.
2. **The sample's `metadata.ananke`** mapping, for per-sample configuration, either flat
   (`{"denied": ["delete_account"]}`) or keyed by evaluator id
   (`{"ananke.tool_use.tool_denylist": {"denied": [...]}}`).
3. **Sample fields**: `expected`, `required`, `expected_tools` and `allowed` come from the names in
   `expected_tool_calls` (an argument typed as a single string, such as `required_step`'s `required`, gets the last
   expected call, the goal action); `optimal_steps` is the number of expected calls; any other argument is read from
   `metadata.<argument>`.
4. The evaluator's own default.

An evaluator whose required argument cannot be resolved skips the sample and says which argument is missing. An
evaluator that returns several scores is averaged; it passes only when all of them pass. Ananke's statuses, values
and evidence are kept in the score's details.

## Tips

- Put `success` in metadata from a real environment check (was the refund issued?), and gate on `goal_success`.
- Use `ananke.trajectory.loop_detection` and `redundant_tool_calls` together to catch agents that thrash.
- Budgets (`ananke.efficiency.*`) read the trace's usage. Report tokens and cost from your target so they work.
- The demo includes an agent: `guage demo`, then open `support-agent.html`.
