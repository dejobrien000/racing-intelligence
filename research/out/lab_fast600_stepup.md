# top_l600==1 and step_up==1  vs  top_l600==0 and step_up==1

In racing terms: horses matching "top_l600==1 and step_up==1" won 14.9% of next starts (1243 runs, 1036 horses), 1.47 times what their fields imply (95% range 1.27-1.7). The comparison group won 8.5% (A/E 0.85, 0.79-0.9).
Allowing for beaten margin and next field size, the odds of winning are 1.42 times the comparison (1.19-1.69, p 0.000): the difference is clear.
Horse-clustered errors (the same horse counts many times). Exploratory unless --since is after the question was first asked.

| split      | level          | set        |   runs |   horses |   next_win_% |   A/E |   lo95 |   hi95 |
|:-----------|:---------------|:-----------|-------:|---------:|-------------:|------:|-------:|-------:|
| all        |                | group      |   1243 |     1036 |         14.9 |  1.47 |   1.27 |   1.7  |
| all        |                | comparison |  10931 |     5814 |          8.5 |  0.85 |   0.79 |   0.9  |
| class_move | drops in class | group      |    155 |      149 |         12.3 |  1.24 |   0.75 |   1.94 |
| class_move | drops in class | comparison |   1326 |     1155 |          8   |  0.8  |   0.66 |   0.97 |
| class_move | rises in class | group      |    180 |      173 |         13.3 |  1.27 |   0.81 |   1.89 |
| class_move | rises in class | comparison |   1550 |     1322 |          7.4 |  0.72 |   0.59 |   0.86 |
| class_move | same class     | group      |    908 |      802 |         15.6 |  1.55 |   1.31 |   1.83 |
| class_move | same class     | comparison |   8055 |     4885 |          8.8 |  0.88 |   0.81 |   0.94 |
| tempo_band | average early  | group      |    307 |      293 |         12.7 |  1.25 |   0.89 |   1.71 |
| tempo_band | average early  | comparison |   2715 |     2162 |          8.9 |  0.89 |   0.78 |   1.01 |
| tempo_band | fast early     | group      |    566 |      512 |         15.4 |  1.53 |   1.23 |   1.89 |
| tempo_band | fast early     | comparison |   4011 |     2899 |          8.4 |  0.84 |   0.76 |   0.94 |
| tempo_band | slow early     | group      |    280 |      264 |         15.7 |  1.55 |   1.12 |   2.08 |
| tempo_band | slow early     | comparison |   3453 |     2602 |          8.9 |  0.89 |   0.79 |   0.99 |