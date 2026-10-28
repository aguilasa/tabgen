# Eval: egdb / egdb

- commit: `7628659-dirty`
- model: `basic-pitch-icassp2022-onnx-guitar+note-2`
- matching: onset +-50 ms, pitch +-50 cents, no offset criterion
- tracks: 8 (with tab annotation: 5)

| | note P | note R | note F1 | tab P | tab R | tab F1 |
|---|---|---|---|---|---|---|
| **mean** | 0.687 | 0.877 | 0.765 | 0.363 | 0.498 | 0.418 |
| 216 | 0.608 | 0.952 | 0.742 | 0.330 | 0.516 | 0.403 |
| 219 | 0.549 | 0.830 | 0.661 | 0.190 | 0.287 | 0.229 |
| 222 | 0.607 | 0.845 | 0.706 | 0.179 | 0.250 | 0.209 |
| 225 | 0.696 | 0.884 | 0.779 | n/a | n/a | n/a |
| 228 | 0.862 | 0.788 | 0.823 | n/a | n/a | n/a |
| 231 | 0.714 | 0.828 | 0.767 | 0.594 | 0.689 | 0.638 |
| 234 | 0.808 | 0.957 | 0.877 | n/a | n/a | n/a |
| 237 | 0.649 | 0.936 | 0.766 | 0.520 | 0.750 | 0.614 |

| track | ref | est | matched | tab correct | string mapping |
|---|---|---|---|---|---|
| 216 | 62 | 97 | 59 | 32 | by track (descending, base 6; 98.4% playable) |
| 219 | 94 | 142 | 78 | 27 | by track (descending, base 6; 98.9% playable) |
| 222 | 84 | 117 | 71 | 21 | by track (descending, base 6; 98.8% playable) |
| 225 | 303 | 385 | 268 | n/a | by track: none; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 4 mappings tie) |
| 228 | 396 | 362 | 312 | n/a | by track: none; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 2 mappings tie) |
| 231 | 151 | 175 | 125 | 104 | by track (descending, base 6; 100.0% playable) |
| 234 | 304 | 360 | 291 | n/a | by track: none; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 2 mappings tie) |
| 237 | 156 | 225 | 146 | 117 | by track (descending, base 5; 100.0% playable) |
