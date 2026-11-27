"""Fine-tune a causal LM with LoRA for three evidence tools; score held-out prompts."""

import json
import os
import random
import numpy as np
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, PeftModel, get_peft_model
from core import GUIDE, ROOT, TOOLS

MODEL = "HuggingFaceTB/SmolLM2-135M-Instruct"
REV = "12fd25f77366fa6b3b4b768ec3050bf629380bac"


class Router:
    def __init__(self, trained=False):
        name = os.getenv("BASE_MODEL", MODEL)
        self.device = "mps" if torch.backends.mps.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(
            name, revision=REV, padding_side="left"
        )
        self.tokenizer.pad_token = self.tokenizer.eos_token
        base = AutoModelForCausalLM.from_pretrained(name, revision=REV)
        base.config.use_cache = False
        cfg = LoraConfig(
            r=8,
            lora_alpha=16,
            target_modules=["q_proj", "v_proj"],
            task_type="CAUSAL_LM",
        )
        self.model = (
            PeftModel.from_pretrained(base, ROOT / "adapter")
            if trained
            else get_peft_model(base, cfg)
        ).to(self.device)
        labels = [
            self.tokenizer.encode(" " + c, add_special_tokens=False) for c in "ABC"
        ]
        assert all(len(label) == 1 for label in labels)
        self.ids = [label[0] for label in labels]

    @classmethod
    def from_adapter(cls):
        return cls(trained=True)

    def scores(self, questions):
        prompts = [
            f"{GUIDE} A=failures B=matrix C=unknown. Request: {q}\nTool letter:"
            for q in questions
        ]
        enc = self.tokenizer(prompts, padding=True, return_tensors="pt").to(self.device)
        enc["position_ids"] = (enc["attention_mask"].cumsum(-1) - 1).clamp(min=0)
        return self.model(**enc).logits[:, -1, self.ids]

    @torch.no_grad()
    def predict(self, qs):
        self.model.eval()
        return [TOOLS[i] for i in self.scores(qs).argmax(-1).tolist()]


def main():
    torch.manual_seed(41)
    torch.set_num_threads(2)
    rng = random.Random(41)
    data = json.loads((ROOT / "routing_data.json").read_text())

    def split(name):
        return [(q, k) for k in TOOLS for q in data[k][name]]

    train, test = split("train"), split("test")
    router = Router()

    def evaluate():
        determined = []
        for i in range(0, len(test), 3):
            determined.extend(router.predict([q for q, _ in test[i : i + 3]]))
        expected = [k for _, k in test]
        return {
            "correct": int(np.sum(np.asarray(expected) == determined)),
            "total": len(test),
            "predictions": determined,
        }

    before = evaluate()
    opt = torch.optim.AdamW(
        [p for p in router.model.parameters() if p.requires_grad], lr=0.0008
    )
    for epoch in range(3):
        rng.shuffle(train)
        router.model.train()
        for i in range(0, len(train), 3):
            batch = train[i : i + 3]
            scores = router.scores([q for q, _ in batch])
            labels = torch.tensor(
                [TOOLS.index(k) for _, k in batch], device=router.device
            )
            opt.zero_grad()
            torch.nn.functional.cross_entropy(scores, labels).backward()
            opt.step()
    after = evaluate()
    router.model.save_pretrained(ROOT / "adapter")
    report = dict(
        model=MODEL,
        revision=REV,
        seed=41,
        train=len(train),
        epochs=3,
        base=before,
        tuned=after,
    )
    (ROOT / "routing_scores.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report)


if __name__ == "__main__":
    main()
