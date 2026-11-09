"""idearel - interpretable detection of multidimensional relationships between ideas.

Reference implementation of the framework described in
"Interpretable Detection of Multidimensional Relationships between Ideas in Crowd Ideation Platforms".
"""
from .config import load_config
from .models import Decision, Element, ElementType, Idea, Relationship
from .pipeline import Framework

__version__ = "1.0.0"
__all__ = ["Framework", "Idea", "Element", "ElementType", "Decision", "Relationship", "load_config"]
