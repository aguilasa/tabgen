# Eval: egdb / egdb

- commit: `f5214b8-dirty`
- model: `basic-pitch-icassp2022-onnx-guitar+note-2 on htdemucs_ft+htdemucs_6s guitar stem`
- matching: onset +-50 ms, pitch +-50 cents, no offset criterion
- tracks: 8 (with tab annotation: 5)
- transcriber: `basic-pitch`
- mix: guitar over MUSDB18 7-second excerpts (Zenodo record 3270814, MUSDB18-7-STEMS.zip), test/ tracks only, drums + bass streams, guitar-to-backing +0.0 dB RMS, separated by Demucs (`htdemucs_ft+htdemucs_6s`), stem `guitar`
- command: `.venv/bin/python scripts/eval/run.py --dataset egdb --subset scripts/eval/subsets/egdb.txt --mix`

| | note P | note R | note F1 | tab P | tab R | tab F1 |
|---|---|---|---|---|---|---|
| **mean** | 0.598 | 0.662 | 0.615 | 0.212 | 0.250 | 0.224 |
| 216 | 0.104 | 0.081 | 0.091 | 0.021 | 0.016 | 0.018 |
| 219 | 0.553 | 0.777 | 0.646 | 0.121 | 0.170 | 0.142 |
| 222 | 0.529 | 0.762 | 0.624 | 0.157 | 0.226 | 0.185 |
| 225 | 0.692 | 0.845 | 0.761 | n/a | n/a | n/a |
| 228 | 0.885 | 0.679 | 0.769 | n/a | n/a | n/a |
| 231 | 0.596 | 0.351 | 0.442 | 0.213 | 0.126 | 0.158 |
| 234 | 0.747 | 0.914 | 0.822 | n/a | n/a | n/a |
| 237 | 0.680 | 0.885 | 0.769 | 0.547 | 0.712 | 0.618 |

| track | ref | est | matched | tab correct | string mapping |
|---|---|---|---|---|---|
| 216 | 62 | 48 | 5 | 1 | by track (descending, base 6; 98.4% playable); backing: AM Contra - Heart Peripheral |
| 219 | 94 | 132 | 73 | 16 | by track (descending, base 6; 98.9% playable); backing: Al James - Schoolboy Facination |
| 222 | 84 | 121 | 64 | 19 | by track (descending, base 6; 98.8% playable); backing: Angels In Amplifiers - I'm Alright |
| 225 | 303 | 370 | 256 | n/a | by track: none; backing: Arise - Run Run Run; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 4 mappings tie) |
| 228 | 396 | 304 | 269 | n/a | by track: none; backing: BKS - Bulldozer; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 2 mappings tie) |
| 231 | 151 | 89 | 53 | 19 | by track (descending, base 6; 100.0% playable); backing: BKS - Too Much |
| 234 | 304 | 372 | 278 | n/a | by track: none; backing: Ben Carrigan - We'll Talk About It All Tonight; tab n/a: no unique track->string mapping makes >= 95% of notes playable (best 100.0%; ambiguous: 2 mappings tie) |
| 237 | 156 | 203 | 138 | 111 | by track (descending, base 5; 100.0% playable); backing: Bobby Nobody - Stitch Up |
