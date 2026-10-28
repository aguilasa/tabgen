# Eval: egdb / egdb

- commit: `f5214b8-dirty`
- model: `riley-guitar-gaps@sha256:65483e7c0e34-guitar+bends-basic-pitch-icassp2022-onnx-tol50ms+note-2`
- matching: onset +-50 ms, pitch +-50 cents, no offset criterion
- tracks: 8 (with tab annotation: 5)
- transcriber: `riley`
- command: `.venv/bin/python scripts/eval/run.py --dataset egdb --subset scripts/eval/subsets/egdb.txt --transcriber riley`

| | note P | note R | note F1 | tab P | tab R | tab F1 |
|---|---|---|---|---|---|---|
| **mean** | 0.872 | 0.855 | 0.860 | 0.477 | 0.497 | 0.486 |
| 216 | 0.831 | 0.952 | 0.887 | 0.507 | 0.581 | 0.541 |
| 219 | 0.837 | 0.819 | 0.828 | 0.217 | 0.213 | 0.215 |
| 222 | 0.829 | 0.750 | 0.787 | 0.316 | 0.286 | 0.300 |
| 225 | 0.792 | 0.865 | 0.826 | n/a | n/a | n/a |
| 228 | 0.932 | 0.763 | 0.839 | n/a | n/a | n/a |
| 231 | 0.907 | 0.907 | 0.907 | 0.642 | 0.642 | 0.642 |
| 234 | 0.969 | 0.826 | 0.892 | n/a | n/a | n/a |
| 237 | 0.882 | 0.955 | 0.917 | 0.704 | 0.763 | 0.732 |

| track | ref | est | matched | tab correct | string mapping |
|---|---|---|---|---|---|
| 216 | 62 | 71 | 59 | 36 | by track (descending, base 6; 98.4% playable) |
| 219 | 94 | 92 | 77 | 20 | by track (descending, base 6; 98.9% playable) |
| 222 | 84 | 76 | 63 | 24 | by track (descending, base 6; 98.8% playable) |
| 225 | 303 | 331 | 262 | n/a | by track: none; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 4 mappings tie) |
| 228 | 396 | 324 | 302 | n/a | by track: none; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 2 mappings tie) |
| 231 | 151 | 151 | 137 | 97 | by track (descending, base 6; 100.0% playable) |
| 234 | 304 | 259 | 251 | n/a | by track: none; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 2 mappings tie) |
| 237 | 156 | 169 | 149 | 119 | by track (descending, base 5; 100.0% playable) |
