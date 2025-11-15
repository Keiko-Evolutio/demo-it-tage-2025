# Document Intelligence Helper

import os
from typing import Dict, Any, Optional

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

from .auth import get_auth
from .rate_limiter import get_rate_limiter


class DocumentIntelligence:
    """
    Helper-Klasse für Azure Document Intelligence (Form Recognizer).
    
    Ermöglicht Analyse von PDFs, Bildern und anderen Dokumenten.
    API Key wird automatisch aus Key Vault geladen.
    
    Beispiel:
        doc_intel = DocumentIntelligence()
        result = doc_intel.analyze_document("document.pdf")
        print(result['content'])
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None
    ):
        """
        Initialisiert den Document Intelligence Client.

        Args:
            api_key: API Key (optional, aus Key Vault oder ENV)
            endpoint: Endpoint (optional, aus ENV)
        """
        self.endpoint = endpoint or os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT", "")

        # API Key aus Parameter, ENV oder Key Vault
        if api_key:
            self.api_key = api_key
        else:
            # Versuche zuerst aus ENV
            self.api_key = os.getenv("DOCUMENT_INTELLIGENCE_API_KEY")
            if not self.api_key:
                # Fallback auf Key Vault
                self.auth = get_auth()
                self.api_key = self.auth.get_api_key("document-intelligence")

        self.rate_limiter = get_rate_limiter("document_intelligence", max_requests=15)

        # Client initialisieren
        self._client = None
    
    @property
    def client(self) -> DocumentAnalysisClient:
        """Lazy-loaded Document Analysis Client."""
        if self._client is None:
            credential = AzureKeyCredential(self.api_key)
            self._client = DocumentAnalysisClient(
                endpoint=self.endpoint,
                credential=credential
            )
        return self._client

    def analyze_document(
        self,
        document_path: str,
        model: str = "local"
    ) -> Dict[str, Any]:
        """
        Analysiert ein Dokument.

        Args:
            document_path: Pfad zum Dokument
            model: Modell-Name (default: local für lokale Extraktion mit PyPDF2)

        Returns:
            Dictionary mit 'content' (extrahierter Text) und 'pages' (Seitenanzahl)
        """
        try:
            # Lokale PDF-Extraktion mit PyPDF2
            import PyPDF2

            with open(document_path, "rb") as f:
                pdf_reader = PyPDF2.PdfReader(f)
                num_pages = len(pdf_reader.pages)

                # Text von allen Seiten extrahieren
                content = ""
                for page in pdf_reader.pages:
                    content += page.extract_text() + "\n"

            return {
                "content": content.strip(),
                "pages": num_pages,
                "status": "success"
            }

        except Exception as e:
            print(f"Fehler bei der Dokumentanalyse: {e}")
            import traceback
            traceback.print_exc()
            return {
                "content": "",
                "pages": 0,
                "status": "error",
                "error": str(e)
            }

