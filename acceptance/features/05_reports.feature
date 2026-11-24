@cap_reports
Feature: Reports

  Scenario: every configured report is written
    Given a fresh project
    When I run "guage run"
    Then it succeeds
    And the file "reports/report.html" contains "Content-Security-Policy"
    And the file "reports/junit.xml" contains "<testsuite"
    And the file "reports/summary.md" contains "Gate:"

  Scenario: a saved run renders again, also as a public report without sample text
    Given a fresh project
    And I have run "guage run"
    When I run "guage report latest -o public.html --profile public"
    Then it succeeds
    And the file "public.html" contains ""profile":"public""
    And the file "public.html" does not contain "How often does Lumen Notes sync"
