# Contributing

Read [AGENTS.md](AGENTS.md) first: it sets the boundaries between Guage Kit and Ananke Plexus and the rules for
metrics.

1. `make install`, then make your change with tests. New metrics need a hand-computed test, and a parity test when a
   reference implementation exists.
2. `make verify` must pass (ruff, ruff format, strict mypy, pytest, licence check, generated docs).
3. If you change user-facing behaviour, add or update a scenario in `acceptance/features/` and run
   `make acceptance-wheel`. The gate must not say BLOCK.
4. Update `CHANGELOG.md` under *Unreleased* and the relevant page in `docs/`.

Commits use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`…).
