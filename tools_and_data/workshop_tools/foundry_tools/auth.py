# Authentication Helper für Workshop Tools
# Zentrale Authentifizierung für alle Workshop-Tools

import os
from typing import Optional
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.keyvault.secrets import SecretClient


class WorkshopAuth:
    """
    Zentrale Authentifizierungs-Klasse für Workshop-Tools.
    
    Verwendet automatisch die beste verfügbare Authentifizierungsmethode:
    1. Managed Identity (wenn in Azure)
    2. Service Principal (mit Client Secret)
    3. Azure CLI (für lokale Entwicklung)
    """
    
    def __init__(self):
        # Azure Konfiguration aus Environment Variables
        self.tenant_id = os.getenv("AZURE_TENANT_ID", "70b5ad7b-7d15-4ba0-a0c1-9aa0b6c0d4c1")
        self.client_id = os.getenv("AZURE_CLIENT_ID", "8dec3fe8-ec67-410c-a6a2-99920b9e80a3")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.keyvault_endpoint = os.getenv("KEYVAULT_ENDPOINT", "https://kv-ws-it-tage-2025.vault.azure.net/")
        
        # Credential initialisieren
        self._credential = None
        self._secret_client = None
    
    @property
    def credential(self):
        """
        Gibt die Azure Credential zurück.
        Verwendet DefaultAzureCredential für automatische Authentifizierung.
        """
        if self._credential is None:
            # Versuche zuerst mit Client Secret (wenn vorhanden)
            if self.client_secret:
                self._credential = ClientSecretCredential(
                    tenant_id=self.tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret
                )
            else:
                # Fallback auf DefaultAzureCredential
                # (Managed Identity, Azure CLI, etc.)
                self._credential = DefaultAzureCredential()
        
        return self._credential
    
    @property
    def secret_client(self) -> SecretClient:
        """
        Gibt den Key Vault Secret Client zurück.
        """
        if self._secret_client is None:
            self._secret_client = SecretClient(
                vault_url=self.keyvault_endpoint,
                credential=self.credential
            )
        
        return self._secret_client
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Holt ein Secret aus dem Key Vault.
        
        Args:
            secret_name: Name des Secrets im Key Vault
            
        Returns:
            Secret-Wert oder None wenn nicht gefunden
        """
        try:
            secret = self.secret_client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            print(f"Fehler beim Abrufen des Secrets '{secret_name}': {e}")
            return None
    
    def get_api_key(self, service_name: str) -> Optional[str]:
        """
        Holt einen API Key aus dem Key Vault.
        
        Args:
            service_name: Name des Services (z.B. 'bing-search', 'vision')
            
        Returns:
            API Key oder None wenn nicht gefunden
        """
        secret_name = f"{service_name}-key"
        return self.get_secret(secret_name)


# Globale Auth-Instanz für alle Tools
_global_auth = None


def get_auth() -> WorkshopAuth:
    """
    Gibt die globale Auth-Instanz zurück.
    Erstellt sie beim ersten Aufruf.
    """
    global _global_auth
    if _global_auth is None:
        _global_auth = WorkshopAuth()
    return _global_auth

