"""Step 3: matching mechanism (Section 4.3).

Four techniques are applied in a cascade, ordered by the strength and reliability of their evidence:
    1. structure-based    subclass / superclass / sameAs in a knowledge graph (nouns only)
    2. linguistic-based   synonyms with Lin's measure on WordNet (threshold 0.75) and antonyms
    3. content-based      word-embedding similarity (threshold 0.80)
    4. terminology-based  string similarity with Levenshtein distance (threshold 0.85)
The cascade stops at the first matcher that establishes a link; if none does, the outcome is NO_LINK.
"""
from .cascade import Cascade, make_cascade

__all__ = ["Cascade", "make_cascade"]
