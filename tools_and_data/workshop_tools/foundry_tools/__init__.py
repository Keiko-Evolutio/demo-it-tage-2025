# Workshop Tools - IT-Tage 2025
# Helper-Bibliothek für Workshop-Teilnehmer

# Always import notebook utilities (no external dependencies)
from .notebook_utils import ensure_notebook_env

# Optional imports - only fail if actually used
__all__ = ["ensure_notebook_env"]

try:
    from .vector_db import VectorDB
    __all__.append("VectorDB")
except ImportError as e:
    VectorDB = None
    print(f"Warning: VectorDB not available: {e}")

try:
    from .bing_search import BingSearch
    __all__.append("BingSearch")
except ImportError as e:
    BingSearch = None
    print(f"Warning: BingSearch not available: {e}")

try:
    from .document_intelligence import DocumentIntelligence
    __all__.append("DocumentIntelligence")
except ImportError as e:
    DocumentIntelligence = None
    print(f"Warning: DocumentIntelligence not available: {e}")

try:
    from .vision import Vision
    __all__.append("Vision")
except ImportError as e:
    Vision = None
    print(f"Warning: Vision not available: {e}")

try:
    from .language import Language
    __all__.append("Language")
except ImportError as e:
    Language = None
    print(f"Warning: Language not available: {e}")

try:
    from .translator import Translator
    __all__.append("Translator")
except ImportError as e:
    Translator = None
    print(f"Warning: Translator not available: {e}")

try:
    from .content_safety import ContentSafety
    __all__.append("ContentSafety")
except ImportError as e:
    ContentSafety = None
    print(f"Warning: ContentSafety not available: {e}")

try:
    from .blob_storage import BlobStorage
    __all__.append("BlobStorage")
except ImportError as e:
    BlobStorage = None
    print(f"Warning: BlobStorage not available: {e}")

try:
    from .vector_pipeline import VectorSearchPipeline
    __all__.append("VectorSearchPipeline")
except ImportError as e:
    VectorSearchPipeline = None
    print(f"Warning: VectorSearchPipeline not available: {e}")

__version__ = "1.0.0"
