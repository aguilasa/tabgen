# Eval: egdb / egdb

- commit: `f5214b8-dirty`
- model: `riley-guitar-gaps@sha256:65483e7c0e34-guitar+bends-basic-pitch-icassp2022-onnx-tol50ms+note-2 on htdemucs_ft+htdemucs_6s guitar stem`
- matching: onset +-50 ms, pitch +-50 cents, no offset criterion
- tracks: 8 (with tab annotation: 5)
- transcriber: `riley`
- mix: guitar over MUSDB18 7-second excerpts (Zenodo record 3270814, MUSDB18-7-STEMS.zip), test/ tracks only, drums + bass streams, guitar-to-backing +0.0 dB RMS, separated by Demucs (`htdemucs_ft+htdemucs_6s`), stem `guitar`
- command: `.venv/bin/python scripts/eval/run.py --dataset egdb --subset scripts/eval/subsets/egdb.txt --mix --transcriber riley`

| | note P | note R | note F1 | tab P | tab R | tab F1 |
|---|---|---|---|---|---|---|
| **mean** | 0.772 | 0.647 | 0.691 | 0.400 | 0.311 | 0.336 |
| 216 | 0.125 | 0.032 | 0.051 | 0.125 | 0.032 | 0.051 |
| 219 | 0.857 | 0.766 | 0.809 | 0.214 | 0.191 | 0.202 |
| 222 | 0.823 | 0.774 | 0.798 | 0.304 | 0.286 | 0.294 |
| 225 | 0.799 | 0.842 | 0.820 | n/a | n/a | n/a |
| 228 | 0.925 | 0.687 | 0.788 | n/a | n/a | n/a |
| 231 | 0.815 | 0.351 | 0.491 | 0.615 | 0.265 | 0.370 |
| 234 | 0.948 | 0.786 | 0.860 | n/a | n/a | n/a |
| 237 | 0.885 | 0.936 | 0.910 | 0.739 | 0.782 | 0.760 |

| track | ref | est | matched | tab correct | string mapping |
|---|---|---|---|---|---|
| 216 | 62 | 16 | 2 | 2 | by track (descending, base 6; 98.4% playable); backing: AM Contra - Heart Peripheral |
| 219 | 94 | 84 | 72 | 18 | by track (descending, base 6; 98.9% playable); backing: Al James - Schoolboy Facination |
| 222 | 84 | 79 | 65 | 24 | by track (descending, base 6; 98.8% playable); backing: Angels In Amplifiers - I'm Alright |
| 225 | 303 | 319 | 255 | n/a | by track: none; backing: Arise - Run Run Run; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 4 mappings tie) |
| 228 | 396 | 294 | 272 | n/a | by track: none; backing: BKS - Bulldozer; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 2 mappings tie) |
| 231 | 151 | 65 | 53 | 40 | by track (descending, base 6; 100.0% playable); backing: BKS - Too Much |
| 234 | 304 | 252 | 239 | n/a | by track: none; backing: Ben Carrigan - We'll Talk About It All Tonight; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 2 mappings tie) |
| 237 | 156 | 165 | 146 | 122 | by track (descending, base 5; 100.0% playable); backing: Bobby Nobody - Stitch Up |
