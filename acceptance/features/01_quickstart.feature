@cap_quickstart
Feature: From an empty folder to a report

  Scenario: init writes a starter suite and sample data
    Given an empty directory
    When I run "guage init"
    Then it succeeds
    And the file "guage.yaml" exists
    And the file "data/sample.jsonl" exists

  Scenario: init never overwrites existing files
    Given an empty directory
    And I have run "guage init"
    And the file "guage.yaml" with content:
      """
      name: mine
      dataset: data/sample.jsonl
      """
    When I run "guage init"
    Then it succeeds
    And the output contains "Nothing written"
    And the file "guage.yaml" contains "name: mine"

  Scenario: run evaluates the starter suite offline and writes its reports
    Given an empty directory
    And I have run "guage init"
    When I run "guage run"
    Then it succeeds
    And the output contains "Gate:"
    And the file "reports/guage-report.html" exists
    And the file "reports/guage-junit.xml" exists
    And the file "reports/guage-summary.md" contains "| metric | value |"
    And a file matching ".guage/runs/*/run.json" exists
