Feature: Credentials and clean errors

  @cap_secrets @adversarial
  Scenario: doctor reports which keys are set without printing them
    Given the environment variable "ANTHROPIC_API_KEY" is "test-value-do-not-print-7f3a"
    When I run "guage doctor"
    Then it succeeds
    And the output contains "ANTHROPIC_API_KEY set"
    And the output does not contain "test-value-do-not-print-7f3a"

  @cap_secrets
  Scenario: doctor without keys (legitimate twin)
    When I run "guage doctor --json"
    Then it succeeds
    And the JSON output at "credentials_present.OPENAI_API_KEY" equals false

  @cap_cli_ux
  Scenario Outline: errors carry a stable code and no traceback
    Given an empty directory
    When I run "<command>"
    Then it fails cleanly
    And the exit code is 2
    And the output contains "<code>"

    Examples:
      | command                                   | code          |
      | guage run                                 | GK-CONFIG-001 |
      | guage run --data missing.jsonl            | GK-DATA-001   |
      | guage report nope                         | GK-RUN-001    |
      | guage metrics show nope                   | GK-METRIC-001 |
      | guage data validate missing.csv           | GK-DATA-001   |

  @cap_cli_ux
  Scenario: a malformed gate is refused
    Given a fresh project
    When I run "guage run --gate recall --no-save"
    Then it fails cleanly
    And the output contains "GK-CONFIG-001"
