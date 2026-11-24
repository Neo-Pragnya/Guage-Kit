Feature: Catalogue, judges, probes, synthetic data and the demo

  @cap_catalogue
  Scenario: browse metrics
    When I run "guage metrics show faithfulness"
    Then it succeeds
    And the output contains "rag"

  @cap_judges
  Scenario: the offline judge grades and agrees with human labels
    Given an empty directory
    And the file "labelled.jsonl" with content:
      """
      {"id": "1", "input": "Capital of France?", "output": "Paris is the capital of France.", "expected": "Paris is the capital of France.", "metadata": {"human_score": 5}}
      {"id": "2", "input": "Capital of France?", "output": "Berlin.", "expected": "Paris is the capital of France.", "metadata": {"human_score": 1}}
      {"id": "3", "input": "Capital of Spain?", "output": "Madrid is the capital of Spain.", "expected": "Madrid is the capital of Spain.", "metadata": {"human_score": 5}}
      {"id": "4", "input": "Capital of Spain?", "output": "Lisbon.", "expected": "Madrid is the capital of Spain.", "metadata": {"human_score": 1}}
      """
    When I run "guage judge calibrate labelled.jsonl --json"
    Then it succeeds
    And the JSON output at "n" equals 4

  @cap_probes
  Scenario: red-team set and robustness against the user's target
    Given a fresh project
    When I run "guage probe redteam -o rt.jsonl"
    Then it succeeds
    And the file "rt.jsonl" contains "GK-CANARY-"
    Given I have run "guage data sample data/support.jsonl -n 4 -o four.jsonl"
    When I run "guage probe robustness four.jsonl --target support_bot:answer --kinds lowercase,filler --metrics recall@3 --json"
    Then it succeeds
    And the JSON output at "perturbations.lowercase.n" equals 4

  @cap_synth
  Scenario: questions from documents, offline
    Given an empty directory
    And the file "docs/help.md" with content:
      """
      Lumen Notes was released in 2019 in Lisbon. The Pro plan costs 6 dollars per month and includes 100 GB of storage.
      Shared notebooks can be opened by up to 20 collaborators, and owners can grant view, comment or edit access.
      """
    When I run "guage synth docs -o synthetic.jsonl --corpus corpus.jsonl"
    Then it succeeds
    And the file "synthetic.jsonl" contains "Fill in the blank"
    And the file "corpus.jsonl" exists

  @cap_probes
  Scenario: perturbed variants of a dataset
    Given a fresh project
    When I run "guage probe perturb data/support.jsonl -o perturbed.jsonl --kinds typos,uppercase"
    Then it succeeds
    And the file "perturbed.jsonl" contains "perturbation"

  @cap_packaging
  Scenario: version names Guage Kit and Ananke
    When I run "guage version"
    Then it succeeds
    And the output contains "ananke-plexus"

  @cap_demo
  Scenario: the demo writes its reports offline
    Given an empty directory
    When I run "guage demo -o demo"
    Then it succeeds
    And the file "demo/support-assistant-v1-vs-v2.html" exists
    And the file "demo/summary.md" contains "Support agent"
