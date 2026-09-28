# 14 — RAG evaluation starter

This is the shortest offline path from a retrieval change to a defensible
answer. It uses the repository's stdlib-only fixtures, so it needs no API key
and does not claim production-quality semantic judging.

## 1. Run the golden retrieval set

Start with the checked-in query/document pairs:

```bash
ragpractices eval \
  --golden examples/golden-retrieval.jsonl \
  --docs examples/hybrid-docs.txt \
  --k 3
```

The report includes hit@k and MRR. To make the run a gate, set a threshold:

```bash
ragpractices eval \
  --golden examples/golden-retrieval.jsonl \
  --docs examples/hybrid-docs.txt \
  --k 3 \
  --min-hit-rate 0.6
```

The threshold form exits with status `1` when the aggregate hit rate is below
the requested value. Use that exit status in a local check or CI; do not turn a
single run into a claim about a production corpus.

## 2. Probe for index drift

Canaries answer a narrower question: does each known query still retrieve at
least one of its expected document IDs?

```bash
ragpractices canary \
  --canaries examples/canaries.jsonl \
  --docs examples/acl-docs.jsonl \
  --k 3
```

The command exits `1` if any probe misses. A failure is a signal to inspect
index contents, filters, or ranking—not proof that generation is wrong.

## 3. Check claims before showing an answer

Retrieval can succeed while an answer invents an entity. Run the claim check on
the draft and the same source file:

```bash
ragpractices claim-check \
  --answer "Refunds are within 30 days of purchase." \
  --sources examples/hybrid-docs.txt
```

The checked-in source supports `30`, while an invented value should fail
closed:

```bash
ragpractices claim-check \
  --answer "Refunds are within 99 days." \
  --sources examples/hybrid-docs.txt
```

The report distinguishes supported, weak, and unsupported claims and can return
`pass`, `rewrite`, or `abstain`. This is a deterministic overlap and
number/date/id check, not an NLI or legal decision.

## The local loop

Run the three checks in order after changing retrieval or answer assembly:

1. `eval` — did expected documents remain reachable?
2. `canary` — did known probes survive index/filter changes?
3. `claim-check` — does the draft stay within the retrieved evidence?

The same gates run on pull requests in
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml): unit tests, the
retrieval threshold, and index canaries. Keep the command output with the
change under review; do not report a metric that was not actually run.

