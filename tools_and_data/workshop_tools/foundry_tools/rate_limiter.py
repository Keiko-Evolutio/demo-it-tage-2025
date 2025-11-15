# Rate Limiter für Workshop Tools
# Verhindert zu viele API-Aufrufe

import time
from collections import deque
from typing import Dict


class RateLimiter:
    """
    Einfacher Rate Limiter basierend auf Sliding Window.
    
    Limitiert die Anzahl der Requests pro Zeitfenster.
    """
    
    def __init__(self, max_requests: int, time_window: int = 60):
        """
        Initialisiert den Rate Limiter.
        
        Args:
            max_requests: Maximale Anzahl Requests im Zeitfenster
            time_window: Zeitfenster in Sekunden (default: 60)
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests: deque = deque()
    
    def acquire(self) -> bool:
        """
        Versucht einen Request-Slot zu bekommen.
        Wartet wenn nötig, bis ein Slot frei wird.
        
        Returns:
            True wenn Request erlaubt
        """
        now = time.time()
        
        # Entferne alte Requests außerhalb des Zeitfensters
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()
        
        # Prüfe ob Limit erreicht
        if len(self.requests) >= self.max_requests:
            # Warte bis ältester Request aus dem Fenster fällt
            sleep_time = self.requests[0] + self.time_window - now
            if sleep_time > 0:
                print(f"Rate Limit erreicht. Warte {sleep_time:.1f} Sekunden...")
                time.sleep(sleep_time)
                return self.acquire()  # Rekursiv erneut versuchen
        
        # Request erlauben
        self.requests.append(now)
        return True


# Globale Rate Limiter für verschiedene Services
_rate_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(service_name: str, max_requests: int = 60) -> RateLimiter:
    """
    Gibt den Rate Limiter für einen Service zurück.
    Erstellt ihn beim ersten Aufruf.
    
    Args:
        service_name: Name des Services
        max_requests: Maximale Requests pro Minute
        
    Returns:
        RateLimiter Instanz
    """
    if service_name not in _rate_limiters:
        _rate_limiters[service_name] = RateLimiter(max_requests)
    return _rate_limiters[service_name]

