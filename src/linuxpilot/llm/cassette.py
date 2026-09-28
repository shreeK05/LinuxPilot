"""
Cassette manager for recording and replaying LLM responses
Provides deterministic, offline testing capabilities
"""

import json
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CassetteManager:
    """
    Manages cassette recording and replay for LLM responses
    """
    
    def __init__(self, cassette_dir: Path, mode: str = "off"):
        """
        Args:
            cassette_dir: Directory to store cassette files
            mode: "off" (normal), "record" (save responses), "replay" (use saved responses)
        """
        self.cassette_dir = Path(cassette_dir)
        self.mode = mode
        
        if self.mode != "off":
            self.cassette_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Cassette mode: {self.mode}, dir: {self.cassette_dir}")
    
    def _get_cassette_path(self, key: str) -> Path:
        """Get the file path for a cassette key"""
        return self.cassette_dir / f"{key}.json"
    
    def record(self, key: str, response: str):
        """Record a response to a cassette file"""
        if self.mode != "record":
            return
        
        cassette_path = self._get_cassette_path(key)
        cassette_data = {
            "key": key,
            "response": response,
        }
        
        with open(cassette_path, "w") as f:
            json.dump(cassette_data, f, indent=2)
        
        logger.debug(f"Recorded cassette: {key}")
    
    def get(self, key: str) -> Optional[str]:
        """Get a response from a cassette file"""
        if self.mode != "replay":
            return None
        
        cassette_path = self._get_cassette_path(key)
        
        if not cassette_path.exists():
            logger.warning(f"Cassette not found: {key}")
            return None
        
        with open(cassette_path, "r") as f:
            cassette_data = json.load(f)
        
        logger.debug(f"Replayed cassette: {key}")
        return cassette_data["response"]
    
    def clear(self):
        """Clear all cassette files"""
        if not self.cassette_dir.exists():
            return
        
        for cassette_file in self.cassette_dir.glob("*.json"):
            cassette_file.unlink()
        
        logger.info(f"Cleared all cassettes from {self.cassette_dir}")
