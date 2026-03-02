# Research Statistics Artifacts

These artifacts are generated from committed raw datasets under `research/data/raw/` by:

```bash
python scripts/run_research_statistics.py --seed 42 --n-boot 2000
```

Generated files:

- `statistical_results.json`
- `statistical_summary.md`
- `links.md` (RQ-05 source link log with quoted factual claims)

The pipeline covers:

- Content Validity Index (I-CVI, S-CVI/Ave)
- Krippendorff's Alpha (ordinal) with bootstrap CI
- System Usability Scale (SUS)
- Wilcoxon signed-rank test
- Friedman test
- Cliff's Delta effect size
