# EchoScript

Hindi conversational speech-to-text: fine-tuning Whisper-small on real Hindi conversations, measuring it against the pretrained model, and cleaning up the output.

Work in progress. It started as a take-home assignment from Josh Talks (AI Researcher Intern, Speech & Audio), and this repo holds my own code and write-ups for it. It is not affiliated with or endorsed by Josh Talks.

## Status

| Part | Status |
|---|---|
| Q1a: data checks and preprocessing | Done |
| Q1b/c: baseline and fine-tuned Whisper-small, WER on FLEURS Hindi | Not started |
| Q1d-g: error analysis, taxonomy, fixes | Not started |
| Q2: number normalization, `[EN]` tagging | Not started |
| Q3: spelling validation of the unique-word list | Not started |
| Q4: lattice-based WER | Not started |
| FastAPI + Streamlit demo (own extra, not in the assignment) | Not started |

No model results are reported yet. They will be added only once the runs exist.

## Data 

Audio and speaker metadata are not in this repo (size, and the metadata describes individual speakers). Transcripts, the manifest and the CSVs used in the write-ups are included. The audio comes from the dataset provided with the assignment.

## Preprocessing (`scripts/preprocess.py`)

Raw recordings become 16 kHz mono clips plus a manifest.

| Step | Why |
|---|---|
| Group recordings that share a folder or a speaker (50 groups) | Prevents the same voice or conversation appearing in both train and validation |
| Resample 44.1 kHz to 16 kHz, cut into segments using transcript timestamps | Whisper expects 16 kHz audio and the labels are per segment |
| Drop 198 segments whose label is the placeholder `REDACTED` (0.43 h) | The audio is real speech, so the label would teach the wrong text |
| Unicode NFC, `_` and `-` to space, strip `, . । ! :` | Whisper never outputs `_`; inconsistent punctuation would count as word errors |
| Leave spellings, digits and word boundaries unchanged | Changing them would mean inventing labels |
| Split by group, seed 42, 5 of 50 groups to validation | No speaker overlap between splits |

Result: 5,659 clips, 11.68 h. Train 5,041 clips (10.27 h, 92 speakers, 45 groups), validation 618 clips (1.42 h, 10 speakers, 5 groups).

## Reproduce

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# place your licensed copy of the dataset under data/ (audios/, transcripts/, NewData.csv)
python scripts/preprocess.py            # skips if data_clean/manifest.csv exists
python scripts/preprocess.py --force    # rebuild
```

## Layout

```
notebooks/   data checks (outputs stripped before commit)
scripts/     download, URL rewrite, preprocessing
docs/        write-ups
```

## Known limitations

- 2 of 104 recordings are missing (bucket locked). The download scripts name files by `user_id`, which collides when a speaker has two recordings; this is what lost those 2 files originally and is not fixed.
- About 2% of clips (114 clips, 0.26 h) have long silent padding around a short utterance. Listening to samples confirmed the labels are correct, so they were kept.
- Some digits remain in 8 labels, and label spellings are inconsistent (e.g. हाँ / हां). Both are left as they are.
- CSV `duration` values differ from the real audio length by up to about 134 s and are not used.