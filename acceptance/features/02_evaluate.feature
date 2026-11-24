@cap_evaluate
Feature: Evaluate a dataset file

  Scenario: explicit metrics with a confidence interval in JSON
    Given a fresh project
    When I run "guage run --data data/support.jsonl --target support_bot:answer --metrics token_f1,recall@3 --json --no-save"
    Then it succeeds
    And the JSON output at "summaries.recall@3.n" equals 24

  Scenario: automatic metrics are chosen from the fields present
    Given a fresh project
    And I have run "guage run --data data/support.jsonl --target support_bot:answer --json-out scored.json --no-save --fail-on never"
    When I run "guage data stats data/support.jsonl --json"
    Then it succeeds
    And the JSON output at "note" contains "run it with a target"
    Given the file "answered.jsonl" with content:
      """
      {"id": "1", "input": "Q?", "output": "Paris", "expected": "Paris", "contexts": ["Paris is in France."]}
      """
    When I run "guage data stats answered.jsonl --json"
    Then it succeeds
    And the JSON output at "auto_metrics" contains "faithfulness"

  Scenario: an unknown metric is refused with a suggestion
    Given a fresh project
    When I run "guage run --data data/support.jsonl --metrics tokn_f1 --no-save"
    Then it fails cleanly
    And the exit code is 2
    And the output contains "GK-METRIC-001"
    And the output contains "token_f1"

  Scenario: a metric the data cannot support says why instead of reporting a number
    Given a fresh project
    When I run "guage run --data data/support.jsonl --metrics recall@3 --no-save"
    Then it succeeds
    And the output contains "recall@3 has no value"
