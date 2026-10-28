# Eval: guitarset / guitarset

- commit: `7628659-dirty`
- model: `riley-gaps@sha256:65483e7c0e34`
- matching: onset +-50 ms, pitch +-50 cents, no offset criterion
- tracks: 8 (with tab annotation: 8)

| | note P | note R | note F1 | tab P | tab R | tab F1 |
|---|---|---|---|---|---|---|
| **mean** | 0.886 | 0.902 | 0.892 | 0.449 | 0.462 | 0.453 |
| 00_BN1-129-Eb_comp | 0.919 | 0.857 | 0.887 | 0.919 | 0.857 | 0.887 |
| 00_BN1-129-Eb_solo | 0.970 | 0.915 | 0.942 | 0.463 | 0.437 | 0.449 |
| 01_Funk1-114-Ab_comp | 0.721 | 0.935 | 0.814 | 0.714 | 0.927 | 0.807 |
| 02_Jazz1-130-D_solo | 0.919 | 0.927 | 0.923 | 0.000 | 0.000 | 0.000 |
| 03_Rock1-90-C#_comp | 0.780 | 0.833 | 0.806 | 0.390 | 0.417 | 0.403 |
| 04_SS1-68-E_solo | 0.886 | 0.902 | 0.894 | 0.088 | 0.089 | 0.088 |
| 05_BN2-166-Ab_comp | 0.963 | 0.908 | 0.935 | 0.853 | 0.803 | 0.827 |
| 05_BN2-166-Ab_solo | 0.926 | 0.940 | 0.933 | 0.162 | 0.164 | 0.163 |

| track | ref | est | matched | tab correct | string mapping |
|---|---|---|---|---|---|
| 00_BN1-129-Eb_comp | 133 | 124 | 114 | 114 | jams data_source 0..5 (low E..high E) |
| 00_BN1-129-Eb_solo | 71 | 67 | 65 | 31 | jams data_source 0..5 (low E..high E) |
| 01_Funk1-114-Ab_comp | 232 | 301 | 217 | 215 | jams data_source 0..5 (low E..high E) |
| 02_Jazz1-130-D_solo | 110 | 111 | 102 | 0 | jams data_source 0..5 (low E..high E) |
| 03_Rock1-90-C#_comp | 204 | 218 | 170 | 85 | jams data_source 0..5 (low E..high E) |
| 04_SS1-68-E_solo | 112 | 114 | 101 | 10 | jams data_source 0..5 (low E..high E) |
| 05_BN2-166-Ab_comp | 173 | 163 | 157 | 139 | jams data_source 0..5 (low E..high E) |
| 05_BN2-166-Ab_solo | 67 | 68 | 63 | 11 | jams data_source 0..5 (low E..high E) |
