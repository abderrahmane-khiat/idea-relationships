"""Download every local resource once (WordNet, WordNet-IC, spaCy model, GloVe vectors).

    python scripts/setup_resources.py [--vectors glove-wiki-gigaword-100] [--spacy en_core_web_md]

Other vector models from gensim-data also work, e.g. word2vec-google-news-300 (1.6 GB, the
Word2Vec model family used in the paper); set content.vectors accordingly.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from idearel.resources import setup  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--vectors", default="glove-wiki-gigaword-100")
ap.add_argument("--spacy", default="en_core_web_md")
a = ap.parse_args()
setup(a.vectors, a.spacy)
