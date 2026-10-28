# Eval: guitarset / guitarset

- commit: `f5214b8-dirty`
- model: `riley-guitar-gaps@sha256:65483e7c0e34-guitar+bends-basic-pitch-icassp2022-onnx-tol50ms+note-2 on htdemucs_ft+htdemucs_6s guitar stem`
- matching: onset +-50 ms, pitch +-50 cents, no offset criterion
- tracks: 8 (with tab annotation: 8)
- transcriber: `riley`
- mix: guitar over MUSDB18 7-second excerpts (Zenodo record 3270814, MUSDB18-7-STEMS.zip), test/ tracks only, drums + bass streams, guitar-to-backing +0.0 dB RMS, separated by Demucs (`htdemucs_ft+htdemucs_6s`), stem `guitar`
- command: `.venv/bin/python scripts/eval/run.py --dataset guitarset --subset scripts/eval/subsets/guitarset.txt --mix --transcriber riley`

| | note P | note R | note F1 | tab P | tab R | tab F1 |
|---|---|---|---|---|---|---|
| **mean** | 0.896 | 0.866 | 0.879 | 0.481 | 0.465 | 0.472 |
| 00_BN1-129-Eb_comp | 0.881 | 0.782 | 0.829 | 0.881 | 0.782 | 0.829 |
| 00_BN1-129-Eb_solo | 0.968 | 0.859 | 0.910 | 0.556 | 0.493 | 0.522 |
| 01_Funk1-114-Ab_comp | 0.793 | 0.922 | 0.853 | 0.781 | 0.909 | 0.841 |
| 02_Jazz1-130-D_solo | 0.927 | 0.927 | 0.927 | 0.000 | 0.000 | 0.000 |
| 03_Rock1-90-C#_comp | 0.799 | 0.779 | 0.789 | 0.407 | 0.397 | 0.402 |
| 04_SS1-68-E_solo | 0.935 | 0.902 | 0.918 | 0.093 | 0.089 | 0.091 |
| 05_BN2-166-Ab_comp | 0.924 | 0.844 | 0.882 | 0.791 | 0.723 | 0.755 |
| 05_BN2-166-Ab_solo | 0.938 | 0.910 | 0.924 | 0.338 | 0.328 | 0.333 |

| track | ref | est | matched | tab correct | string mapping |
|---|---|---|---|---|---|
| 00_BN1-129-Eb_comp | 133 | 118 | 104 | 104 | jams data_source 0..5 (low E..high E); backing: AM Contra - Heart Peripheral |
| 00_BN1-129-Eb_solo | 71 | 63 | 61 | 35 | jams data_source 0..5 (low E..high E); backing: Al James - Schoolboy Facination |
| 01_Funk1-114-Ab_comp | 232 | 270 | 214 | 211 | jams data_source 0..5 (low E..high E); backing: Angels In Amplifiers - I'm Alright |
| 02_Jazz1-130-D_solo | 110 | 110 | 102 | 0 | jams data_source 0..5 (low E..high E); backing: Arise - Run Run Run |
| 03_Rock1-90-C#_comp | 204 | 199 | 159 | 81 | jams data_source 0..5 (low E..high E); backing: BKS - Bulldozer |
| 04_SS1-68-E_solo | 112 | 108 | 101 | 10 | jams data_source 0..5 (low E..high E); backing: BKS - Too Much |
| 05_BN2-166-Ab_comp | 173 | 158 | 146 | 125 | jams data_source 0..5 (low E..high E); backing: Ben Carrigan - We'll Talk About It All Tonight |
| 05_BN2-166-Ab_solo | 67 | 65 | 61 | 22 | jams data_source 0..5 (low E..high E); backing: Bobby Nobody - Stitch Up |
