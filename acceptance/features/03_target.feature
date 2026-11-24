@cap_target
Feature: Run the user's system under test

  Scenario: the suite's target answers every question and is scored
    Given a fresh project
    When I run "guage run --json --no-save"
    Then it succeeds
    And the JSON output at "target.name" equals "support_bot:answer"
    And the JSON output at "summaries.recall@3.n" equals 24
    And the JSON output at "samples" has at least 24 items

  Scenario: a target that cannot be imported fails with a code
    Given a fresh project
    When I run "guage run --target support_bot:missing --no-save"
    Then it fails cleanly
    And the output contains "GK-TARGET-001"
