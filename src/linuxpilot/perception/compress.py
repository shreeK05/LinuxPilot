"""
Tree Compression Module
Compresses AT-SPI tree to stay within token budget for LLM
"""

from typing import List, Dict, Any
import logging

from linuxpilot.config import settings

logger = logging.getLogger(__name__)


class TreeCompressor:
    """
    Compresses accessibility tree to reduce token usage
    Target: ~1,200 tokens per perception message
    """
    
    def __init__(
        self,
        max_elements: int = None,
        name_truncate: int = None,
    ):
        self.max_elements = max_elements or settings.ATSPI_COMPRESSION_MAX_ELEMENTS
        self.name_truncate = name_truncate or settings.ATSPI_NAME_TRUNCATE
    
    def compress(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Compress the accessibility tree
        
        Strategy:
        1. Keep only showing elements with actions or editable fields
        2. Keep elements with important roles (label, table cell, list item)
        3. Truncate names
        4. Group repeated patterns (e.g., file lists)
        5. Cap total elements
        """
        if not elements:
            return []
        
        # Filter important elements
        important_roles = {
            "label", "table cell", "list item", "menu item",
            "push button", "check box", "radio button", "text",
            "entry", "combo box", "tree table", "table row"
        }
        
        filtered = []
        for elem in elements:
            # Keep if has actions or is editable
            if elem.get("actions") or elem.get("editable"):
                filtered.append(elem)
            # Keep if important role
            elif elem.get("role") in important_roles:
                filtered.append(elem)
        
        # Truncate names
        for elem in filtered:
            if elem.get("name"):
                elem["name"] = elem["name"][:self.name_truncate]
        
        # Group repeated patterns (simple heuristic)
        grouped = self._group_repeated(filtered)
        
        # Cap total elements
        if len(grouped) > self.max_elements:
            # Keep first N and add summary
            kept = grouped[:self.max_elements]
            kept.append({
                "id": "summary",
                "role": "summary",
                "name": f"... and {len(grouped) - self.max_elements} more elements",
                "actions": [],
                "editable": False,
                "rect": None,
            })
            return kept
        
        return grouped
    
    def _group_repeated(self, elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Group repeated patterns (e.g., file lists with similar structure)
        """
        # Simple implementation: if we see many similar consecutive elements,
        # group them with a count
        if len(elements) < 10:
            return elements
        
        grouped = []
        i = 0
        
        while i < len(elements):
            current = elements[i]
            
            # Check if next 5+ elements have same role
            same_role_count = 1
            j = i + 1
            while j < len(elements) and elements[j]["role"] == current["role"]:
                same_role_count += 1
                j += 1
            
            if same_role_count >= 5:
                # Group them
                grouped.append({
                    "id": f"group_{i}",
                    "role": current["role"],
                    "name": f"{same_role_count} items (first shown)",
                    "actions": current["actions"],
                    "editable": current["editable"],
                    "rect": current["rect"],
                    "group_count": same_role_count,
                })
                # Show first 2 actual items
                for k in range(min(2, same_role_count)):
                    grouped.append(elements[i + k])
                i += same_role_count
            else:
                grouped.append(current)
                i += 1
        
        return grouped
    
    def estimate_tokens(self, elements: List[Dict[str, Any]]) -> int:
        """
        Estimate token count for compressed elements
        Rough estimate: ~4 chars per token
        """
        total_chars = 0
        for elem in elements:
            # Estimate based on serialized representation
            elem_str = str(elem)
            total_chars += len(elem_str)
        
        return total_chars // 4
