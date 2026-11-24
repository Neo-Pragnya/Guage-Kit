@cap_compare
Feature: Baselines and comparisons

  Scenario: a baseline is set and compared with itself without regressions
    Given a fresh project
    And I have run "guage run"
    And I have run "guage baseline set"
    When I run "guage compare baseline:main latest --json -o cmp.html"
    Then it succeeds
    And the JSON output at "same_data" equals true
    And the file "cmp.html" contains "comparison"

  Scenario: a worse candidate is reported as a regression
    Given a fresh project
    And I have run "guage run"
    And I have run "guage baseline set"
    And the file "support_bot.py" with content:
      """
      def answer(question):
          return {"output": "I do not know.", "contexts": [], "retrieved_ids": ["kb-none"]}
      """
    And I have run "guage run --fail-on never"
    And I have run "guage runs"
    And I have run "guage baseline show"
    When I run "guage compare baseline:main latest --fail-on-regression"
    Then the exit code is 1
    And the output contains "regressed"

  Scenario: an unknown baseline fails with a code
    Given a fresh project
    When I run "guage compare baseline:nope latest"
    Then it fails cleanly
    And the output contains "GK-RUN-001"
