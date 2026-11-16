# Q1a: Data preprocessing

Josh's question: "Preprocess the dataset and share what you did to process the data and make it ready for training."

## 1. What we started with

`NewData.csv` (same dataset as `FT Data - data.csv`, with the new `upload_goai` URLs) lists 104 recordings. Both URL sets now return 403, so the work uses the 102 recordings downloaded earlier.

| Check | Result |
|---|---|
| Rows / unique recording_id / unique user_id | 104 / 104 / 102 |
| Duplicate rows | 0 |
| Recordings lost by the old `user_id` file naming | 2 (speakers 93626 and 147403 each have two recordings) |
| Local files | 102 |
| Audio length of those files | 20.04 h |
| Transcribed speech (sum of segment lengths) | 12.11 h |
| Segments | 5,857 (none empty, none over 30 s, longest 15 s) |
| Audio format | 44.1 kHz, mono, all 102 files |
| Transcript ends after its audio | 0 files |

The 21.89 h in the CSV is the sum of its `duration` column. That column is off from the real audio length by up to about 134 s, so it is not used. Training uses only audio that has a label, hence 12.11 h.

## 2. Steps and reasons

| Step | Problem it solves |
|---|---|
| Build groups: rows sharing a folder or a speaker stay together (50 groups) | All 52 folders hold exactly 2 recordings, probably two sides of one conversation (not confirmed). Two speakers appear in two folders. Splitting by row would put the same voice or conversation in both train and validation and inflate validation scores. |
| Resample 44.1 kHz to 16 kHz mono | Whisper expects 16 kHz audio. Speech content sits well below 8 kHz, so nothing useful is lost. |
| Cut each recording into segments using the transcript timestamps | Labels exist per segment, and all segments fit inside Whisper's 30 s window, so each segment is one example. |
| Drop segments labelled `REDACTED` (198 segments, 0.43 h) | The audio is real speech, but the label is a placeholder. Training on it would teach Hindi sound to become English text. |
| Normalize text: Unicode NFC, `_` and `-` to space, strip `, . । ! :` | Whisper does not write `_` (17 labels use it for acronyms like `सी_वी`). Hyphens appear after repeated or cut-off words (11 labels). Punctuation varies from label to label (about 750 labels contain a danda), and would count as word errors in WER. |
| Leave spellings, digits and word boundaries alone | Variants like हाँ / हां or merged words are label noise, but fixing them would mean inventing labels. Digits appear in only 8 labels. |
| Keep short backchannels ('जी', 'हम्म', 'हां') | They are real speech and common in conversation. |
| Split by group with seed 42: 5 of 50 groups to validation | Reproducible, with no speaker overlap. |

English words in the labels are already in Devanagari (कंप्यूटर साइंस, इंस्टाग्राम), matching the transcription guideline. No Roman-script words exist apart from `REDACTED`.

## 3. Result

| Split | Clips | Hours | Speakers | Groups |
|---|---|---|---|---|
| Train | 5,041 | 10.27 | 92 | 45 |
| Validation | 618 | 1.42 | 10 | 5 |
| Total | 5,659 | 11.68 | | |

The speaker overlap between train and validation is empty. Validation is only for monitoring training. Josh's evaluation uses FLEURS Hindi.

`scripts/preprocess.py` rebuilds all of this. Rerunning it on the same inputs reproduced the manifest exactly (`DataFrame.equals` returned True).

## 4. Checks on the data quality

- **Fast clips** (more than 5 words per second): listened to samples. They are real fast speech, so nothing was changed.
- **Slow clips** (over 5 s with 2 words or fewer): 114 clips, 2.0% of clips and 0.26 h. Listening confirmed the label is right and the rest of the clip is silence, so the segment boundaries are loose. These were kept. If error analysis later shows the fine-tuned model inventing short words like 'जी' on silence, this becomes a candidate fix.
- **Very short clips** (under 0.3 s): 21 clips, not yet inspected.

## 5. Limitations

- Two recordings are missing because the source bucket became inaccessible.
- Segment timestamps contain long silent padding in about 2% of clips.
- Label spelling is inconsistent, and the labels may contain errors that the model will be blamed for. This matters again in Q3 and Q4.
- Group-based validation holds only 5 groups, so the validation WER is a noisy estimate.