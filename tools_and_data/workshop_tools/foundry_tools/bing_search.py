# Bing Search Helper

import os
import requests
from typing import List, Dict, Any, Optional

from .auth import get_auth
from .rate_limiter import get_rate_limiter


class BingSearch:
    """
    Helper-Klasse für Bing Search API.
    
    Ermöglicht Web-Suche, News-Suche und Entity-Suche.
    API Key wird automatisch aus Key Vault geladen.
    
    Beispiel:
        bing = BingSearch()
        results = bing.search("Azure AI", count=5)
        for result in results:
            print(result['name'], result['url'])
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None
    ):
        """
        Initialisiert den Bing Search Client.
        
        Args:
            api_key: Bing Search API Key (optional, aus Key Vault)
            endpoint: Bing Search Endpoint (optional, aus ENV)
        """
        # Konfiguration
        self.endpoint = endpoint or os.getenv(
            "BING_SEARCH_ENDPOINT",
            "https://api.bing.microsoft.com/v7.0/search"
        )
        self.market = os.getenv("BING_SEARCH_MARKET", "de-DE")
        self.safe_search = os.getenv("BING_SEARCH_SAFE_SEARCH", "Moderate")
        
        # API Key aus Key Vault oder Parameter
        self.auth = get_auth()
        self.api_key = api_key or self.auth.get_api_key("bing-search")
        
        # Rate Limiter (60 Requests/Minute)
        self.rate_limiter = get_rate_limiter("bing_search", max_requests=60)
    
    def search(
        self,
        query: str,
        count: int = 10,
        offset: int = 0,
        search_type: str = "web"
    ) -> List[Dict[str, Any]]:
        """
        Führt eine Bing-Suche durch.
        
        Args:
            query: Suchbegriff
            count: Anzahl der Ergebnisse (max 50)
            offset: Offset für Pagination
            search_type: Art der Suche ('web', 'news', 'images')
            
        Returns:
            Liste von Suchergebnissen
        """
        # Rate Limiting
        self.rate_limiter.acquire()
        
        # Headers
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key
        }
        
        # Parameter
        params = {
            "q": query,
            "count": min(count, 50),
            "offset": offset,
            "mkt": self.market,
            "safeSearch": self.safe_search
        }
        
        try:
            # Request
            response = requests.get(
                self.endpoint,
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            # Parse Response
            data = response.json()
            
            # Extrahiere Ergebnisse basierend auf Typ
            if search_type == "web" and "webPages" in data:
                return data["webPages"].get("value", [])
            elif search_type == "news" and "news" in data:
                return data["news"].get("value", [])
            elif search_type == "images" and "images" in data:
                return data["images"].get("value", [])
            else:
                return []
                
        except Exception as e:
            print(f"Fehler bei Bing Search: {e}")
            return []
    
    def search_news(
        self,
        query: str,
        count: int = 10,
        freshness: str = "Day"
    ) -> List[Dict[str, Any]]:
        """
        Sucht nach News-Artikeln.
        
        Args:
            query: Suchbegriff
            count: Anzahl der Ergebnisse
            freshness: Aktualität ('Day', 'Week', 'Month')
            
        Returns:
            Liste von News-Artikeln
        """
        # Rate Limiting
        self.rate_limiter.acquire()
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key
        }
        
        params = {
            "q": query,
            "count": min(count, 50),
            "mkt": self.market,
            "freshness": freshness,
            "safeSearch": self.safe_search
        }
        
        try:
            endpoint = self.endpoint.replace("/search", "/news/search")
            response = requests.get(
                endpoint,
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("value", [])
            
        except Exception as e:
            print(f"Fehler bei News Search: {e}")
            return []
    
    def search_images(
        self,
        query: str,
        count: int = 10,
        image_type: str = "Photo"
    ) -> List[Dict[str, Any]]:
        """
        Sucht nach Bildern.
        
        Args:
            query: Suchbegriff
            count: Anzahl der Ergebnisse
            image_type: Bildtyp ('Photo', 'Clipart', 'Line', 'AnimatedGif')
            
        Returns:
            Liste von Bildern
        """
        # Rate Limiting
        self.rate_limiter.acquire()
        
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key
        }
        
        params = {
            "q": query,
            "count": min(count, 50),
            "mkt": self.market,
            "imageType": image_type,
            "safeSearch": self.safe_search
        }
        
        try:
            endpoint = self.endpoint.replace("/search", "/images/search")
            response = requests.get(
                endpoint,
                headers=headers,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            return data.get("value", [])
            
        except Exception as e:
            print(f"Fehler bei Image Search: {e}")
            return []

