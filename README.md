# Maya ChargeHub — Feasibility Audit: Monte Carlo Visuals

Monte Carlo sensitivity visuals for the *Conditional Feasibility of a Multi-Type
Electric Motorcycle Charging Hub* audit paper.

Reproduces the audit model (Table 1 + Equations 1–3): 10,000 draws, seed `20261019`.

**Deterministic anchors reproduce the paper exactly:**
- NPV at α=1 (full advertising): **+44.31 B IDR**
- NPV at α=0 (no advertising): **−49.79 B IDR**
- Break-even advertising share: **α\* = 0.53**
- Advertising rank-correlation with NPV: **0.97** (dominant driver)

## Files (`docs/revisi-audit/`)
| File | Chart |
|------|-------|
| `mc_histogram.svg` | Distribution of NPV across 10,000 draws |
| `mc_npv_vs_alpha.svg` | NPV vs advertising realization share α |
| `mc_tornado.svg` | Driver ranking (Spearman rank correlation) |
| `mc_conditional.svg` | P(NPV>0) conditional on α |
| `index.html` | All four charts on one page |
| `montecarlo.py` | Source model (stdlib only) + self-check |

> ⚠️ The Monte Carlo *spread* (P(NPV>0), median, percentiles) uses reconstructed
> distribution parameters, since the original paper did not publish them. The
> deterministic figures above are exact; the distribution shape is illustrative
> until the authors' real parameters/seed are supplied.

Run: `python3 docs/revisi-audit/montecarlo.py`
