# Eval: guitarset / guitarset

- commit: `f5214b8-dirty`
- model: `basic-pitch-icassp2022-onnx-guitar+note-2 on htdemucs_ft+htdemucs_6s guitar stem`
- matching: onset +-50 ms, pitch +-50 cents, no offset criterion
- tracks: 8 (with tab annotation: 8)
- transcriber: `basic-pitch`
- mix: guitar over MUSDB18 7-second excerpts (Zenodo record 3270814, MUSDB18-7-STEMS.zip), test/ tracks only, drums + bass streams, guitar-to-backing +0.0 dB RMS, separated by Demucs (`htdemucs_ft+htdemucs_6s`), stem `guitar`
- command: `.venv/bin/python scripts/eval/run.py --dataset guitarset --subset scripts/eval/subsets/guitarset.txt --mix`

| | note P | note R | note F1 | tab P | tab R | tab F1 |
|---|---|---|---|---|---|---|
| **mean** | 0.736 | 0.771 | 0.745 | 0.352 | 0.327 | 0.334 |
| 00_BN1-129-Eb_comp | 0.647 | 0.677 | 0.662 | 0.640 | 0.669 | 0.654 |
| 00_BN1-129-Eb_solo | 0.659 | 0.845 | 0.741 | 0.253 | 0.324 | 0.284 |
| 01_Funk1-114-Ab_comp | 0.808 | 0.509 | 0.624 | 0.795 | 0.500 | 0.614 |
| 02_Jazz1-130-D_solo | 0.693 | 0.882 | 0.776 | 0.000 | 0.000 | 0.000 |
| 03_Rock1-90-C#_comp | 0.654 | 0.686 | 0.670 | 0.206 | 0.216 | 0.211 |
| 04_SS1-68-E_solo | 0.727 | 0.902 | 0.805 | 0.072 | 0.089 | 0.080 |
| 05_BN2-166-Ab_comp | 0.807 | 0.775 | 0.791 | 0.729 | 0.699 | 0.714 |
| 05_BN2-166-Ab_solo | 0.896 | 0.896 | 0.896 | 0.119 | 0.119 | 0.119 |

| track | ref | est | matched | tab correct | string mapping |
|---|---|---|---|---|---|
| 00_BN1-129-Eb_comp | 133 | 139 | 90 | 89 | jams data_source 0..5 (low E..high E); backing: AM Contra - Heart Peripheral |
| 00_BN1-129-Eb_solo | 71 | 91 | 60 | 23 | jams data_source 0..5 (low E..high E); backing: Al James - Schoolboy Facination |
| 01_Funk1-114-Ab_comp | 232 | 146 | 118 | 116 | jams data_source 0..5 (low E..high E); backing: Angels In Amplifiers - I'm Alright |
| 02_Jazz1-130-D_solo | 110 | 140 | 97 | 0 | jams data_source 0..5 (low E..high E); backing: Arise - Run Run Run |
| 03_Rock1-90-C#_comp | 204 | 214 | 140 | 44 | jams data_source 0..5 (low E..high E); backing: BKS - Bulldozer |
| 04_SS1-68-E_solo | 112 | 139 | 101 | 10 | jams data_source 0..5 (low E..high E); backing: BKS - Too Much |
| 05_BN2-166-Ab_comp | 173 | 166 | 134 | 121 | jams data_source 0..5 (low E..high E); backing: Ben Carrigan - We'll Talk About It All Tonight |
| 05_BN2-166-Ab_solo | 67 | 67 | 60 | 8 | jams data_source 0..5 (low E..high E); backing: Bobby Nobody - Stitch Up |
