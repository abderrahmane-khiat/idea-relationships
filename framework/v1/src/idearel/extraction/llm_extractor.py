"""Local LLM extractors: ADELIE (HuggingFace) and any model served by Ollama.

No API key and no external service: the model runs on the user's machine.
The prompt is the one used for the GPT-4o extractor comparison (Reviewer 3, comment 8).
"""
from __future__ import annotations

import json
import re
import urllib.request

from ..models import Element, ElementType
from .base import Extractor, accept_subject, classify_without_triple

PROMPT = ("Extract ONE subject-predicate-object triple from the phrase below. Use words from the phrase. "
          "Keep subject and object short noun phrases. The predicate is the verb or relation. "
          "If the phrase has no clear subject AND predicate AND object, answer NONE.\n"
          "Answer exactly in the form: subject | predicate | object\n"
          "Phrase: {phrase}\nAnswer:")


def parse_answer(answer: str):
    line = answer.strip().splitlines()[0] if answer.strip() else ""
    if "NONE" in line.upper() and "|" not in line:
        return None
    parts = [p.strip(" .\"'") for p in line.split("|")]
    if len(parts) == 3 and all(parts) and all(p.upper() != "NONE" for p in parts):
        return parts
    m = re.match(r"\(?\s*(.+?)\s*[;,]\s*(.+?)\s*[;,]\s*(.+?)\s*\)?$", line)
    return [m.group(1), m.group(2), m.group(3)] if m else None


class _LLMExtractor(Extractor):
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

    def _extract(self, text: str, pattern_name: str, context: dict) -> Element:
        triple = parse_answer(self.generate(PROMPT.format(phrase=text)))
        if triple:
            s = accept_subject(triple[0], self.cfg, context)
            if s:
                return Element(ElementType.TRIPLE, text=text, subject=s, predicate=triple[1], object=triple[2], source=self.name)
        return classify_without_triple(text, has_verb=len(text.split()) > 2, source=self.name)


class AdelieExtractor(_LLMExtractor):
    """ADELIE (Qi et al., 2024), an LLM aligned for information extraction. Needs `transformers` and `torch`."""
    name = "adelie"

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        from transformers import AutoModelForCausalLM, AutoTokenizer
        model_id = cfg.get("adelie", {}).get("model", "THU-KEG/ADELIE-SFT-3B")
        self.max_new = int(cfg.get("adelie", {}).get("max_new_tokens", 64))
        self.tok = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(model_id)

    def generate(self, prompt: str) -> str:
        ids = self.tok(prompt, return_tensors="pt")
        out = self.model.generate(**ids, max_new_tokens=self.max_new, do_sample=False)
        return self.tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True)


class OllamaExtractor(_LLMExtractor):
    """Any local model served by Ollama (https://ollama.com), e.g. `ollama run llama3.1`."""
    name = "ollama"

    def __init__(self, cfg: dict):
        super().__init__(cfg)
        o = cfg.get("ollama", {})
        self.url, self.model = o.get("url", "http://localhost:11434"), o.get("model", "llama3.1")

    def generate(self, prompt: str) -> str:
        body = json.dumps({"model": self.model, "prompt": prompt, "stream": False, "options": {"temperature": 0}}).encode()
        req = urllib.request.Request(f"{self.url}/api/generate", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode()).get("response", "")
