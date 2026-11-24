@cap_datasets
Feature: Datasets

  Scenario: validate, convert, split and sample
    Given a fresh project
    When I run "guage data validate data/support.jsonl"
    Then it succeeds
    And the output contains "24 samples"
    Given I have run "guage data convert data/support.jsonl data/support.yaml"
    And I have run "guage data split data/support.jsonl --fraction 0.25"
    And I have run "guage data sample data/support.jsonl -n 5 -o small.jsonl"
    Then the file "data/support.yaml" exists
    And the file "data/support.a.jsonl" exists
    And the file "small.jsonl" exists

  Scenario: a broken line is reported with its line number
    Given an empty directory
    And the file "bad.jsonl" with content:
      """
      {"id": 1, "input": "ok"}
      {broken
      """
    When I run "guage data validate bad.jsonl"
    Then it fails cleanly
    And the output contains "GK-DATA-003"
    And the output contains "bad.jsonl:2"

  Scenario: duplicate ids are refused
    Given an empty directory
    And the file "dup.jsonl" with content:
      """
      {"id": 1, "input": "a"}
      {"id": 1, "input": "b"}
      """
    When I run "guage data validate dup.jsonl"
    Then it fails cleanly
    And the output contains "duplicate sample ids"
