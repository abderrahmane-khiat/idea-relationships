"""Check and download the local resources (no API key, everything offline after setup)."""
from __future__ import annotations

import importlib
import os

NLTK_DATA = ["wordnet", "omw-1.4", "wordnet_ic", "averaged_perceptron_tagger_eng", "punkt_tab"]


def _ok(msg):
    print(f"  [ok]      {msg}")


def _miss(msg, fix):
    print(f"  [missing] {msg}\n            fix: {fix}")


def check(cfg: dict) -> bool:
    print("Resources for the configured pipeline:")
    good = True
    try:
        import nltk
        for name, path in (("wordnet", "corpora/wordnet"), ("wordnet_ic", "corpora/wordnet_ic")):
            try:
                nltk.data.find(path); _ok(f"NLTK {name}")
            except LookupError:
                good = False; _miss(f"NLTK {name}", "python scripts/setup_resources.py")
    except ImportError:
        good = False; _miss("nltk", "pip install -r requirements.txt")
    ext = cfg.get("extractor", "spacy")
    if ext == "spacy":
        try:
            import spacy
            spacy.load(cfg.get("spacy_model", "en_core_web_md")); _ok(f"spaCy model {cfg.get('spacy_model', 'en_core_web_md')}")
        except Exception:
            good = False; _miss("spaCy model", "python -m spacy download en_core_web_md  (or use --extractor heuristic)")
    elif ext == "corenlp":
        import urllib.request
        try:
            urllib.request.urlopen(cfg["corenlp"]["url"], timeout=3); _ok(f"CoreNLP server {cfg['corenlp']['url']}")
        except Exception:
            good = False; _miss("CoreNLP server", "see README, section 'Stanford OpenIE (as in the paper)'")
    c = cfg.get("content", {})
    if c.get("vectors_file"):
        (_ok if os.path.exists(c["vectors_file"]) else lambda m: _miss(m, "check content.vectors_file"))(f"vectors {c['vectors_file']}")
    elif c.get("backend", "gensim") == "gensim":
        try:
            import gensim.downloader as api
            path = os.path.join(api.BASE_DIR, c.get("vectors", "glove-wiki-gigaword-100"))
            if os.path.isdir(path):
                _ok(f"word vectors {c.get('vectors')}")
            else:
                good = False; _miss(f"word vectors {c.get('vectors')}", "python scripts/setup_resources.py")
        except ImportError:
            good = False; _miss("gensim", "pip install -r requirements.txt")
    for mod in ("fastapi", "uvicorn"):
        try:
            importlib.import_module(mod); _ok(f"{mod} (web version)")
        except ImportError:
            _miss(f"{mod} (only needed for the web version)", "pip install -r requirements.txt")
    print("All required resources are available." if good else "Some resources are missing (see above).")
    return good


def setup(vectors: str = "glove-wiki-gigaword-100", spacy_model: str = "en_core_web_md"):
    import nltk
    for name in NLTK_DATA:
        print("NLTK:", name); nltk.download(name, quiet=True)
    try:
        import spacy
        try:
            spacy.load(spacy_model); print("spaCy model already installed:", spacy_model)
        except OSError:
            from spacy.cli import download
            download(spacy_model)
    except ImportError:
        print("spaCy not installed; the heuristic extractor will be used")
    import gensim.downloader as api
    print("word vectors:", vectors, "(about 130 MB for the 100d GloVe model)")
    api.load(vectors)
    print("done")
