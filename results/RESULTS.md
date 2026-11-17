# Results log

Rule: every number below names the file and notebook that produced it. Nothing is added without a saved output.
Fill in the `date` and `versions` fields when you commit.

## 1. Pretrained Whisper-small, FLEURS Hindi test (418 utterances)

| Setting | WER | Note |
|---|---|---|
| A: no normalization, `raw_transcription` vs raw model output | 0.8603 | punctuation counts as errors |
| **B: `eval_norm` on both, `transcription` reference** | **0.8096** | **our main setting** |
| C: `eval_norm` on both, `raw_transcription` reference | 0.8100 | same as B within 0.0004 |
| Josh's table value | 0.83 | from the assignment sheet, method unknown |

- File: `results/predictions/fleurs_baseline_predictions.csv`
- Notebook: `notebooks/03_baseline_full.ipynb`
- Decode time on a T4: 2.8 min
- date: ____

## 2. Pretrained Whisper-small, our validation clips (618)

| Measure | Value |
|---|---|
| WER (`eval_norm`, token cap) | 1.8873 |
| Clips with runaway output (more than 3x reference words + 5) | 93 of 618 |
| Decode time on a T4 | 4.4 min |

- WER above 1 is possible: inserted words count as errors.
- File: `results/predictions/val_baseline_predictions.csv`
- Notebook: `notebooks/03_baseline_full.ipynb`
- date: ____

## 3. Pretrained Whisper-small, our training clips (5,041): pending (notebook 04)

| Measure | Value |
|---|---|
| WER | ____ |
| Runaway clips | ____ of 5,041 |
| Decode time | ____ |

- File: `results/predictions/train_baseline_predictions.csv`
- Used for Q2 (raw ASR output paired with the human reference)

## 4. Fine-tuned Whisper-small: pending

## Josh's table (Q1c) draft

| Model | Hindi |
|---|---|
| Whisper Small (Pretrained) | 0.81 (ours, setting B); Josh's sheet says 0.83 |
| FT Whisper Small (yours) | to be filled |

## Exact settings behind the numbers

- Model: `openai/whisper-small`, fp16, batch size 16, greedy decoding, `language="hi"`, `task="transcribe"`
- Normalizer `eval_norm` (applied to both reference and model output): Unicode NFC, `_` to space, strip `, . । ॥ ! ? : ; - " ' “ ” ‘ ’ ( )`, collapse whitespace, lowercase
- WER: `jiwer`, corpus level; rows with an empty reference are excluded
- Token cap (our clips only, not FLEURS): `max(10, 1.5 x 20.4 x duration + 5)` tokens, never above 440. 20.4 is the 99th percentile of reference tokens per second over clips of at least 1 s. The 1.5 and the percentile are my choices, not a standard.
- Versions (fill from the Kaggle session): python ____, torch ____, transformers ____, jiwer ____, datasets ____ (installed as `datasets<4` in notebook 03)

## Decision log

| Decision | Choice | Reason | Revisit if |
|---|---|---|---|
| Which recordings | all 102 available (12.1 h transcribed) | 2 of 104 unavailable (bucket 403); Josh's "~10 h" is approximate | Josh specifies a subset |
| `REDACTED` segments | dropped (198, 0.43 h) | label is a placeholder, audio is real speech | never |
| Train/val split | by group (folder + speaker), seed 42, 5 of 50 groups | no speaker or conversation in both splits | val too noisy to monitor training |
| Long-silence clips (114, 2.0%) | kept | labels correct (checked by listening) | fine-tuned model invents words on silence |
| Clips under 0.3 s (21) | kept for now, not inspected | tiny share | error analysis points at them |
| Baseline number to report | setting B | most defensible normalization | we learn how Josh computed 0.83 |
| Decoding | greedy for every model | fair comparison, fast | beam search tested for both models |

## Observations (sample-based, not yet counted)

- On FLEURS the pretrained model often hears the right word but spells it phonetically wrong (from 5 printed examples of the first 20 utterances).
- On very short filler clips ('हम्म', 'ब्लैंक', 'हेलो', 1 to 1.4 s) it repeats a word like 'अगर' until the token cap. Seen in 93 of 618 val clips, even with the cap.

## Open items

- Full fine-tune vs LoRA; Kaggle vs Colab for the training run
- How Josh obtained 0.83
- Q2, Q3, Q4

## Limitations

See the README. Keep the two lists identical.