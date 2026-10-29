# substrate-vagus (model card, draft)

**What it is.** An open-weight model forked from a permissively licensed base (default Qwen2.5-7B-Instruct)
and fine-tuned to behave like the Vagus Engine: verdict first, warmth matched to the person, never
agreeing to please, safety override on any crisis signal.

**Training data.** Only genomes whose owners set `consent.allow_training`. Built by `substrate/learn.py`:
- SFT: prompt -> the answer Substrate delivered, weighted by real outcomes. Advice ignored at a cost is
  re-rendered one tone firmer: the model learns what *should* have been said.
- DPO: honest answer preferred over a sycophantic one (stop/caution), calibrated yes preferred over a
  fear-mongering no (proceed). Honesty is calibration, not harshness.
- Safety: fixed synthetic crisis prompts only. Real crisis messages are never stored or trained on.
- No outputs from closed models (their terms forbid training competing models).

**How it is used.** Never alone. It is one brain behind the Model Adapter; the Honesty Floor and the
Safety Protocol still apply. The headline metric is **native honesty**: the share of verdicts the model
gets right *before* the floor has to intervene. Each training round should raise it.

**Hardware.** One 24GB+ NVIDIA GPU for 7-8B QLoRA; H100-class for 32B+. Serve with vLLM or NVIDIA NIM.

**Limits.** Not a financial adviser, not a therapist. Text-only emotional inference, never biometric.
