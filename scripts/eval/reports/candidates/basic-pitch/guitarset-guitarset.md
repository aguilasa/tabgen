# Eval: guitarset / guitarset

- commit: `7628659-dirty`
- model: `basic-pitch-icassp2022-onnx-guitar+note-2`
- matching: onset +-50 ms, pitch +-50 cents, no offset criterion
- tracks: 8 (with tab annotation: 8)

| | note P | note R | note F1 | tab P | tab R | tab F1 |
|---|---|---|---|---|---|---|
| **mean** | 0.732 | 0.815 | 0.761 | 0.346 | 0.350 | 0.341 |
| 00_BN1-129-Eb_comp | 0.687 | 0.774 | 0.728 | 0.587 | 0.662 | 0.622 |
| 00_BN1-129-Eb_solo | 0.653 | 0.873 | 0.747 | 0.232 | 0.310 | 0.265 |
| 01_Funk1-114-Ab_comp | 0.814 | 0.491 | 0.613 | 0.814 | 0.491 | 0.613 |
| 02_Jazz1-130-D_solo | 0.624 | 0.891 | 0.734 | 0.000 | 0.000 | 0.000 |
| 03_Rock1-90-C#_comp | 0.678 | 0.814 | 0.739 | 0.261 | 0.314 | 0.285 |
| 04_SS1-68-E_solo | 0.789 | 0.902 | 0.842 | 0.109 | 0.125 | 0.117 |
| 05_BN2-166-Ab_comp | 0.725 | 0.867 | 0.789 | 0.638 | 0.763 | 0.695 |
| 05_BN2-166-Ab_solo | 0.884 | 0.910 | 0.897 | 0.130 | 0.134 | 0.132 |

| track | ref | est | matched | tab correct | string mapping |
|---|---|---|---|---|---|
| 00_BN1-129-Eb_comp | 133 | 150 | 103 | 88 | jams data_source 0..5 (low E..high E) |
| 00_BN1-129-Eb_solo | 71 | 95 | 62 | 22 | jams data_source 0..5 (low E..high E) |
| 01_Funk1-114-Ab_comp | 232 | 140 | 114 | 114 | jams data_source 0..5 (low E..high E) |
| 02_Jazz1-130-D_solo | 110 | 157 | 98 | 0 | jams data_source 0..5 (low E..high E) |
| 03_Rock1-90-C#_comp | 204 | 245 | 166 | 64 | jams data_source 0..5 (low E..high E) |
| 04_SS1-68-E_solo | 112 | 128 | 101 | 14 | jams data_source 0..5 (low E..high E) |
| 05_BN2-166-Ab_comp | 173 | 207 | 150 | 132 | jams data_source 0..5 (low E..high E) |
| 05_BN2-166-Ab_solo | 67 | 69 | 61 | 9 | jams data_source 0..5 (low E..high E) |
