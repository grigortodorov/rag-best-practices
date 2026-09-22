# Contributing

Thanks for improving this educational guide on RAG best practices.

## How to propose improvements

1. Open an issue describing the gap, outdated advice, or unclear section (see [.github/ISSUE_TEMPLATE/doc-improvement.yml](.github/ISSUE_TEMPLATE/doc-improvement.yml)).
2. Or submit a pull request with concrete doc edits (see [.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md)).
3. Keep changes **practical and accurate**. Prefer examples and tradeoffs over marketing language.

## Content guidelines

- Educational content only; no fabricated stars, download counts, dependents, or vendor eligibility claims
- Do not add badges that imply metrics we do not have (License MIT is fine)
- Prefer clear structure, tables, checklists, and worked examples
- Call out uncertainty where the field is still evolving
- Never commit secrets, API keys, tokens, or real customer data in examples

## Doc scope

Primary paths:

- `docs/` — numbered guides (`01`–`11`)
- `examples/` — checklists, heuristics, rubrics, schemas, and pipeline sketches
- `README.md` — navigation and TOC
- `CODE_OF_CONDUCT.md` — community standards
- `.github/` — issue and pull request templates
- `.gitignore` — ignore local junk and secrets

## Review checklist for PRs

- [ ] Links in README TOC still resolve
- [ ] Examples contain no real credentials
- [ ] Advice distinguishes retrieval vs generation failure modes
- [ ] New anti-patterns (if any) include a concrete fix

## Code of conduct

By participating, you agree to uphold the [Code of Conduct](CODE_OF_CONDUCT.md). Report concerns by opening an issue.

## License

By contributing, you agree that your contributions are licensed under the MIT License (see [LICENSE](LICENSE)).
