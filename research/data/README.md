# Research Data Dictionary

This directory contains raw tabular inputs used by `scripts/run_research_statistics.py`.

- `cvi_expert_ratings.csv`: columns `item_id`, `expert_id`, `rating` (1-4 scale).
- `krippendorff_annotations.csv`: columns `unit_id`, `rater_id`, `value` (ordinal labels).
- `sus_responses.csv`: columns `participant_id`, `q1..q10` (SUS 1-5 responses).
- `wilcoxon_paired_scores.csv`: columns `participant_id`, `before`, `after`.
- `friedman_repeated_scores.csv`: columns `participant_id`, `condition_a`, `condition_b`, `condition_c`.
- `cliffs_delta_groups.csv`: columns `group` (`baseline|medf`), `value`.

All files are committed to support deterministic, auditable reproduction of reported statistics.
