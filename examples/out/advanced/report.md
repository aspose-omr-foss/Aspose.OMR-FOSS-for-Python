# Advanced template -- degradation robustness report

Template: `examples/advanced-exam.txt` -> A4 PNG + `.omr`  |  answer-key fields: 14

**12/12 degradations recovered the answer key with 100% accuracy.**

| # | degradation | result | fields recovered |
|---|-------------|--------|------------------|
| 1 | `rotate_090` | PASS (100%) | 14/14 |
| 2 | `rotate_180` | PASS (100%) | 14/14 |
| 3 | `rotate_270` | PASS (100%) | 14/14 |
| 4 | `skew_+15` | PASS (100%) | 14/14 |
| 5 | `skew_-12` | PASS (100%) | 14/14 |
| 6 | `skew_+6` | PASS (100%) | 14/14 |
| 7 | `phone_shot` | PASS (100%) | 14/14 |
| 8 | `scanner_lines` | PASS (100%) | 14/14 |
| 9 | `smudges_scribbles` | PASS (100%) | 14/14 |
| 10 | `torn_corner_br` | PASS (100%) | 14/14 |
| 11 | `torn_corner_tl` | PASS (100%) | 14/14 |
| 12 | `combined` | PASS (100%) | 14/14 |

Images: `examples/out/advanced/<name>.png`, montage: `montage.png`.
