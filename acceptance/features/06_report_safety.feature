@cap_report_safety
Feature: Hostile text stays inert in reports

  @adversarial
  Scenario: a sample that tries to close the data block cannot inject markup
    Given an empty directory
    And the file "evil.jsonl" with content:
      """
      {"id": "x", "input": "</script><script>window.__pwned=1</script>", "output": "<img src=x onerror=alert(1)>", "expected": "safe"}
      """
    When I run "guage run --data evil.jsonl --metrics token_f1 --html r.html --no-save"
    Then it succeeds
    And the file "r.html" does not contain "<script>window.__pwned"
    And the file "r.html" does not contain "<img src=x"
    And the file "r.html" contains "connect-src 'none'"

  Scenario: ordinary text is kept and shown (legitimate twin)
    Given an empty directory
    And the file "ok.jsonl" with content:
      """
      {"id": "y", "input": "Where is Paris?", "output": "Paris is in France.", "expected": "France"}
      """
    When I run "guage run --data ok.jsonl --metrics token_f1 --html r.html --no-save"
    Then it succeeds
    And the file "r.html" contains "Paris is in France."
