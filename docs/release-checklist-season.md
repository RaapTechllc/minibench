# Publish New Cabinet Season Checklist

Use this checklist before changing the live default cabinet or publishing a new
MiniBench season. ADR 0001 requires season rotation, item pruning, and private
holdout refresh as explicit release gates.

## 1. Freeze the candidate season

- Confirm the candidate task suite is committed and the working tree is clean.
- Record the suite id, season label, generator seed hash, grader version, and
  expected publish target in the release notes.
- Do not change the live leaderboard default, homepage copy, or published season
  config during candidate validation.

## 2. Refresh the private holdout

- Generate a fresh high-entropy private seed for the new season holdout.
- Keep the seed out of committed files and public logs; publish only the
  `seed_sha256`/provenance recorded by result artifacts.
- Run every release-candidate model against the same private holdout split and
  decoding settings.
- Archive the previous season holdout according to ADR 0001's season rotation
  policy; do not reuse it for the new season.

## 3. Run mechanical validity gates

- Run the usual budget and dry-run smoke checks before spending frontier tokens.
- Reject the sweep if any result has infra errors, canary flags, mismatched
  grader versions, mismatched decoding settings, or non-comparable task/trial
  sets.
- Run pairwise comparison only after mechanical validity passes:
  `python -m agentbench.compare agentbench/results/<season-sweep-*.json>`

## 4. Audit item discrimination

- Run the item-discrimination report on the comparable frontier sweep:
  `python -m agentbench.item_stats agentbench/results/<season-sweep-*.json>`
- Run the release-blocking ceiling gate:
  `python -m agentbench.check_ceiling_items agentbench/results/<season-sweep-*.json>`
- Treat any item at or above the ceiling threshold (90% pass by default) as a
  publish blocker for the new season.
- Review floor, low-discrimination, negative-discrimination, and missing-model
  flags from `item_stats.py`; resolve broken or non-discriminating items before
  publish.
- Resolve ceiling items by pruning, rewriting, or moving the candidate to a
  harder season. Never prune based on which model an item favors.

## 5. Publish explicitly

- Publish only after the holdout refresh and item-pruning gates pass.
- Make the live leaderboard/default-cabinet change in a separate explicit publish
  step with release notes that name the season and suite id.
- Preserve prior-season results as Classic/previous cabinet data; do not mutate
  old scores to fit the new season.
- After publish, verify the live board points at the intended suite and that the
  previous cabinet remains accessible for regression/history.
