# Security policy

## Reporting a vulnerability

Report vulnerabilities privately through
[GitHub security advisories](https://github.com/Neo-Pragnya/Guage-Kit/security/advisories/new). Please don't open a
public issue. We aim to acknowledge reports within five working days.

## What Guage Kit promises

- **Reports are inert.** An HTML report runs no command and makes no network request: its Content Security Policy
  is `default-src 'none'` with the inline script and style allowed only by hash. Dataset and model text is shown as
  text, never parsed as HTML. The `public` profile removes all sample text before sharing.
- **Judge prompts separate instructions from content.** Evaluated text is placed in marked untrusted blocks that it
  cannot close, with an instruction to treat it as data.
- **Credentials stay in the environment.** API keys are read from environment variables (or the provider SDK's own
  credential chain), never from `guage.yaml`, and are never written to runs, caches or reports. `guage doctor` says
  only whether a key is set.
- **Nothing runs that you didn't name.** Targets and providers are imported only from the module paths you give.
  Metrics never execute model output (`python_syntax` parses, it doesn't run).

Each release is checked by `make scan` (secrets, vulnerable dependencies, malicious-code heuristics), the licence
check and the acceptance gate against the built wheel.
