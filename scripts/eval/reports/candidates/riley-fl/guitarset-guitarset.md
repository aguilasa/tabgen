# Eval: guitarset / guitarset

- commit: `7628659-dirty`
- model: `riley-fl@sha256:50d93dba89bd`
- matching: onset +-50 ms, pitch +-50 cents, no offset criterion
- tracks: 8 (with tab annotation: 8)

| | note P | note R | note F1 | tab P | tab R | tab F1 |
|---|---|---|---|---|---|---|
| **mean** | 0.919 | 0.931 | 0.925 | 0.466 | 0.470 | 0.468 |
| 00_BN1-129-Eb_comp | 0.938 | 0.902 | 0.920 | 0.938 | 0.902 | 0.920 |
| 00_BN1-129-Eb_solo | 0.928 | 0.901 | 0.914 | 0.449 | 0.437 | 0.443 |
| 01_Funk1-114-Ab_comp | 0.894 | 0.944 | 0.918 | 0.784 | 0.828 | 0.805 |
| 02_Jazz1-130-D_solo | 0.928 | 0.936 | 0.932 | 0.000 | 0.000 | 0.000 |
| 03_Rock1-90-C#_comp | 0.852 | 0.902 | 0.876 | 0.449 | 0.475 | 0.462 |
| 04_SS1-68-E_solo | 0.929 | 0.938 | 0.933 | 0.097 | 0.098 | 0.098 |
| 05_BN2-166-Ab_comp | 0.943 | 0.954 | 0.948 | 0.834 | 0.844 | 0.839 |
| 05_BN2-166-Ab_solo | 0.942 | 0.970 | 0.956 | 0.174 | 0.179 | 0.176 |

| track | ref | est | matched | tab correct | string mapping |
|---|---|---|---|---|---|
| 00_BN1-129-Eb_comp | 133 | 128 | 120 | 120 | jams data_source 0..5 (low E..high E) |
| 00_BN1-129-Eb_solo | 71 | 69 | 64 | 31 | jams data_source 0..5 (low E..high E) |
| 01_Funk1-114-Ab_comp | 232 | 245 | 219 | 192 | jams data_source 0..5 (low E..high E) |
| 02_Jazz1-130-D_solo | 110 | 111 | 103 | 0 | jams data_source 0..5 (low E..high E) |
| 03_Rock1-90-C#_comp | 204 | 216 | 184 | 97 | jams data_source 0..5 (low E..high E) |
| 04_SS1-68-E_solo | 112 | 113 | 105 | 11 | jams data_source 0..5 (low E..high E) |
| 05_BN2-166-Ab_comp | 173 | 175 | 165 | 146 | jams data_source 0..5 (low E..high E) |
| 05_BN2-166-Ab_solo | 67 | 69 | 65 | 12 | jams data_source 0..5 (low E..high E) |
