# Eval: egdb / egdb

- commit: `7628659-dirty`
- model: `riley-fl@sha256:50d93dba89bd`
- matching: onset +-50 ms, pitch +-50 cents, no offset criterion
- tracks: 8 (with tab annotation: 5)

| | note P | note R | note F1 | tab P | tab R | tab F1 |
|---|---|---|---|---|---|---|
| **mean** | 0.812 | 0.884 | 0.843 | 0.402 | 0.463 | 0.429 |
| 216 | 0.637 | 0.935 | 0.758 | 0.374 | 0.548 | 0.444 |
| 219 | 0.808 | 0.851 | 0.829 | 0.242 | 0.255 | 0.249 |
| 222 | 0.790 | 0.762 | 0.776 | 0.235 | 0.226 | 0.230 |
| 225 | 0.780 | 0.878 | 0.826 | n/a | n/a | n/a |
| 228 | 0.870 | 0.813 | 0.841 | n/a | n/a | n/a |
| 231 | 0.854 | 0.887 | 0.870 | 0.503 | 0.523 | 0.513 |
| 234 | 0.931 | 0.980 | 0.955 | n/a | n/a | n/a |
| 237 | 0.829 | 0.962 | 0.890 | 0.657 | 0.763 | 0.706 |

| track | ref | est | matched | tab correct | string mapping |
|---|---|---|---|---|---|
| 216 | 62 | 91 | 58 | 34 | by track (descending, base 6; 98.4% playable) |
| 219 | 94 | 99 | 80 | 24 | by track (descending, base 6; 98.9% playable) |
| 222 | 84 | 81 | 64 | 19 | by track (descending, base 6; 98.8% playable) |
| 225 | 303 | 341 | 266 | n/a | by track: none; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 4 mappings tie) |
| 228 | 396 | 370 | 322 | n/a | by track: none; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 2 mappings tie) |
| 231 | 151 | 157 | 134 | 79 | by track (descending, base 6; 100.0% playable) |
| 234 | 304 | 320 | 298 | n/a | by track: none; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 2 mappings tie) |
| 237 | 156 | 181 | 150 | 119 | by track (descending, base 5; 100.0% playable) |
