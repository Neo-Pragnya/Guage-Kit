@cap_gates
Feature: Quality gates and exit codes

  Scenario: a passing gate exits 0
    Given a fresh project
    When I run "guage run --no-save --gate recall@3:min=0.5"
    Then it succeeds
    And the output contains "PASS"

  Scenario: a blocking gate exits 1 and says why
    Given a fresh project
    When I run "guage run --no-save --gate 'token_f1>=0.99'"
    Then the exit code is 1
    And the output contains "BLOCK"
    And the output contains "misses"

  Scenario: a warn gate passes by default but fails with --fail-on warn
    Given a fresh project
    When I run "guage run --no-save --gate token_f1:min=0.99:warn --fail-on warn"
    Then the exit code is 1
    And the output contains "WARN"

  Scenario: --fail-on never reports without failing the build
    Given a fresh project
    When I run "guage run --no-save --gate token_f1:min=0.99 --fail-on never"
    Then it succeeds
    And the output contains "BLOCK"

  Scenario: a gate on a metric that was not computed never passes
    Given a fresh project
    When I run "guage run --no-save --metrics mrr --gate faithfulness:min=0.1"
    Then the exit code is 1
    And the output contains "no value"

  Scenario: the quoted comparison form works too
    Given a fresh project
    When I run "guage run --no-save --gate 'recall@3>=0.5'"
    Then it succeeds

  Scenario: a gate without a bound is refused
    Given a fresh project
    When I run "guage run --no-save --gate recall@3:warn"
    Then it fails cleanly
    And the output contains "GK-CONFIG-001"
