@cap_ananke
Feature: Built on Ananke Plexus

  Scenario: doctor confirms a compatible harness
    When I run "guage doctor --json"
    Then it succeeds
    And the JSON output at "harness.compatible" equals true
    And the JSON output at "ananke_evaluators" equals 77

  Scenario: Ananke evaluators are listed as metrics
    When I run "guage metrics list --family ananke --json"
    Then it succeeds
    And the JSON output has at least 70 items

  Scenario: Ananke trajectory evaluators score recorded tool calls
    Given an empty directory
    And the file "agent.jsonl" with content:
      """
      {"id": "a", "input": "refund 42", "tool_calls": [{"name": "lookup_order", "arguments": {"order_id": "42"}}, {"name": "issue_refund", "arguments": {"order_id": "42"}}], "expected_tool_calls": [{"name": "lookup_order", "arguments": {"order_id": "42"}}, {"name": "issue_refund", "arguments": {"order_id": "42"}}]}
      {"id": "b", "input": "refund 43", "tool_calls": [{"name": "issue_refund", "arguments": {"order_id": "43"}}], "expected_tool_calls": [{"name": "lookup_order", "arguments": {"order_id": "43"}}, {"name": "issue_refund", "arguments": {"order_id": "43"}}]}
      """
    When I run "guage run --data agent.jsonl --metrics ananke.trajectory.strict,tool_call_f1 --markdown summary.md --no-save"
    Then it succeeds
    And the file "summary.md" contains "| ananke.trajectory.strict ↑ | 0.500 |"

  Scenario: an evidence bundle is written for Ananke
    Given a fresh project
    When I run "guage run --evidence --fail-on never"
    Then it succeeds
    And a file matching ".ananke/evidence/*/eval/policy-decision.json" exists
    And a file matching ".ananke/evidence/*/eval/reports/junit.xml" exists
