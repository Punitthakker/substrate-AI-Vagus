#!/usr/bin/env python3
"""Train substrate-vagus: fork an open-weight model and teach it the Vagus Engine.

Stage 1  SFT  (LoRA / QLoRA)  - learn Substrate's voice, empathy and verdict-first delivery
Stage 2  DPO                  - prefer the honest answer over the sycophantic one, and the calibrated
                                yes over the fear-mongering no
Stage 3  merge + export       - merged weights for vLLM / NVIDIA NIM, GGUF for Ollama

Hardware: one NVIDIA GPU with 24GB+ (L4, A10, RTX 4090) for 7-8B QLoRA; an H100 trains the 32B.
Runs on any cloud GPU or NVIDIA DGX. This script does not run in Substrate's API container.

    pip install "transformers>=4.46" "trl>=0.12" "peft>=0.13" datasets accelerate bitsandbytes
    python -m substrate.learn training/data                  # ledger -> sft.jsonl + dpo.jsonl
    python scripts/train_vagus.py --base Qwen/Qwen2.5-7B-Instruct --data training/data --out out/substrate-vagus-7b

Base models we fork (open weights, licenses permit fine-tuning; check each license for your use):
    Qwen/Qwen2.5-7B-Instruct, Qwen/Qwen2.5-32B-Instruct, meta-llama/Llama-3.1-8B-Instruct,
    mistralai/Mistral-Nemo-Instruct-2407, nvidia/Llama-3.1-Nemotron-70B-Instruct-HF
"""
from __future__ import annotations

import argparse
import json
import math
import os


def load_rows(path: str) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def upsample(rows: list[dict]) -> list[dict]:
    """Outcome weights become repetition: a 2.0-weight lesson is seen twice."""
    out = []
    for r in rows:
        out.extend([r] * max(1, int(math.floor(r.get("weight", 1.0) + 0.5))))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=os.environ.get("BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct"))
    ap.add_argument("--data", default="training/data")
    ap.add_argument("--out", default="out/substrate-vagus")
    ap.add_argument("--epochs", type=float, default=3)
    ap.add_argument("--dpo-beta", type=float, default=0.1)
    ap.add_argument("--qlora", action="store_true", default=True)
    ap.add_argument("--skip-dpo", action="store_true")
    a = ap.parse_args()

    import torch
    from datasets import Dataset
    from peft import LoraConfig, prepare_model_for_kbit_training
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
    from trl import DPOConfig, DPOTrainer, SFTConfig, SFTTrainer

    tok = AutoTokenizer.from_pretrained(a.base)
    tok.pad_token = tok.pad_token or tok.eos_token
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
                               bnb_4bit_compute_dtype=torch.bfloat16) if a.qlora else None
    model = AutoModelForCausalLM.from_pretrained(a.base, quantization_config=quant, torch_dtype=torch.bfloat16,
                                                 device_map="auto")
    if a.qlora:
        model = prepare_model_for_kbit_training(model)
    lora = LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, target_modules="all-linear", task_type="CAUSAL_LM")

    # ---------------- stage 1: SFT
    sft_rows = upsample(load_rows(os.path.join(a.data, "sft.jsonl")))
    sft_ds = Dataset.from_list([{"messages": r["messages"]} for r in sft_rows])
    sft = SFTTrainer(model=model, processing_class=tok, train_dataset=sft_ds, peft_config=lora,
                     args=SFTConfig(output_dir=f"{a.out}/sft", num_train_epochs=a.epochs, per_device_train_batch_size=2,
                                    gradient_accumulation_steps=8, learning_rate=2e-4, lr_scheduler_type="cosine",
                                    warmup_ratio=0.05, logging_steps=5, bf16=True, max_seq_length=2048, report_to=[]))
    sft.train()
    sft.save_model(f"{a.out}/sft")

    # ---------------- stage 2: DPO, honesty over flattery, calibration over fear
    if not a.skip_dpo:
        dpo_rows = upsample(load_rows(os.path.join(a.data, "dpo.jsonl")))
        dpo_ds = Dataset.from_list([{"prompt": r["prompt"], "chosen": [{"role": "assistant", "content": r["chosen"]}],
                                     "rejected": [{"role": "assistant", "content": r["rejected"]}]} for r in dpo_rows])
        dpo = DPOTrainer(model=sft.model, ref_model=None, processing_class=tok, train_dataset=dpo_ds,
                         args=DPOConfig(output_dir=f"{a.out}/dpo", beta=a.dpo_beta, num_train_epochs=1,
                                        per_device_train_batch_size=1, gradient_accumulation_steps=8,
                                        learning_rate=5e-6, logging_steps=5, bf16=True, report_to=[]))
        dpo.train()
        dpo.save_model(f"{a.out}/dpo")
        final = dpo.model
    else:
        final = sft.model

    # ---------------- stage 3: merge for serving (vLLM / NIM); GGUF for Ollama via llama.cpp
    merged = final.merge_and_unload() if hasattr(final, "merge_and_unload") else final
    merged.save_pretrained(f"{a.out}/merged", safe_serialization=True)
    tok.save_pretrained(f"{a.out}/merged")
    print(f"""
Done. Serve it:
  vLLM:   vllm serve {a.out}/merged --served-model-name substrate-vagus
          then  SUBSTRATE_MODEL=vllm VLLM_URL=http://gpu-host:8000/v1 VLLM_MODEL=substrate-vagus
  Ollama: python llama.cpp/convert_hf_to_gguf.py {a.out}/merged --outfile substrate-vagus.gguf
          ollama create substrate-vagus -f training/Modelfile
          then  SUBSTRATE_MODEL=ollama OLLAMA_MODEL=substrate-vagus
Evaluate:  python -m substrate.evals   (native honesty = verdicts right before the Honesty Floor)
""")


if __name__ == "__main__":
    main()
