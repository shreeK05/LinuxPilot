"""
AT-SPI Perception Module
Provides access to the Linux accessibility tree for GUI automation
"""

import hashlib
from typing import Optional, List, Dict, Any
import logging

try:
    import gi
    gi.require_version("Atspi", "2.0")
    from gi.repository import Atspi
    ATSPI_AVAILABLE = True
except (ImportError, ValueError):
    ATSPI_AVAILABLE = False
    Atspi = None

from linuxpilot.config import settings

logger = logging.getLogger(__name__)


class ATSPIPerception:
    """
    AT-SPI-based perception for GUI automation
    Captures the accessibility tree of running applications
    """
    
    def __init__(self, max_depth: int = None):
        self.max_depth = max_depth or settings.ATSPI_MAX_DEPTH
        
        if not ATSPI_AVAILABLE:
            logger.warning("AT-SPI not available - GUI automation will be limited")
    
    def is_available(self) -> bool:
        """Check if AT-SPI is available"""
        return ATSPI_AVAILABLE
    
    def snapshot(self, app_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Capture a snapshot of the accessibility tree
        
        Args:
            app_filter: Optional application name to filter by
        
        Returns:
            List of accessibility element dictionaries
        """
        if not ATSPI_AVAILABLE:
            return []
        
        try:
            desktop = Atspi.get_desktop(0)
            elements = []
            
            for i in range(desktop.get_child_count()):
                app = desktop.get_child_at_index(i)
                if app_filter and app.get_name() != app_filter:
                    continue
                
                self._walk_tree(app, [i], elements, self.max_depth)
            
            logger.debug(f"Captured {len(elements)} accessibility elements")
            return elements
            
        except Exception as e:
            logger.error(f"AT-SPI snapshot failed: {e}")
            return []
    
    def _walk_tree(
        self,
        node,
        path: List[int],
        elements: List[Dict[str, Any]],
        max_depth: int,
    ):
        """Recursively walk the accessibility tree"""
        if len(path) > max_depth:
            return
        
        try:
            state_set = node.get_state_set()
            
            # Only include showing elements
            if state_set.contains(Atspi.StateType.SHOWING):
                element = self._extract_element(node, path)
                if element:
                    elements.append(element)
            
            # Recurse into children
            for j in range(node.get_child_count()):
                child = node.get_child_at_index(j)
                self._walk_tree(child, path + [j], elements, max_depth)
                
        except Exception as e:
            logger.debug(f"Error walking tree node: {e}")
    
    def _extract_element(self, node, path: List[int]) -> Optional[Dict[str, Any]]:
        """Extract relevant information from an accessibility element"""
        try:
            # Get component interface for bounding box
            component = node.get_component_iface()
            rect = None
            if component:
                extents = component.get_extents(Atspi.CoordType.SCREEN)
                rect = {
                    "x": extents.x,
                    "y": extents.y,
                    "width": extents.width,
                    "height": extents.height,
                }
            
            # Get action interface
            action_iface = node.get_action_iface()
            actions = []
            if action_iface:
                for i in range(action_iface.get_n_actions()):
                    actions.append(action_iface.get_action_name(i))
            
            # Check if editable
            editable_text = node.get_editable_text_iface()
            is_editable = editable_text is not None
            
            # Get element info
            name = (node.get_name() or "")[:settings.ATSPI_NAME_TRUNCATE]
            role = node.get_role_name()
            
            return {
                "id": self._stable_id(path, node),
                "role": role,
                "name": name,
                "actions": actions,
                "editable": is_editable,
                "rect": rect,
                "path": path,
            }
            
        except Exception as e:
            logger.debug(f"Error extracting element: {e}")
            return None
    
    def _stable_id(self, path: List[int], node) -> str:
        """
        Generate a stable ID for an element
        Hash of (app, role, name, index-path)
        """
        try:
            role = node.get_role_name()
            name = node.get_name() or ""
            
            id_string = f"{role}:{name}:{':'.join(map(str, path))}"
            return hashlib.sha256(id_string.encode()).hexdigest()[:16]
            
        except Exception:
            return f"node_{'_'.join(map(str, path))}"
    
    def find_element(
        self,
        elements: List[Dict[str, Any]],
        role: Optional[str] = None,
        name: Optional[str] = None,
        action: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Find an element in the snapshot by criteria
        
        Args:
            elements: Element list from snapshot()
            role: Optional role to match
            name: Optional name to match (partial match)
            action: Optional action to match
        
        Returns:
            Matching element or None
        """
        for element in elements:
            match = True
            
            if role and element["role"] != role:
                match = False
            
            if name and name.lower() not in element["name"].lower():
                match = False
            
            if action and action not in element["actions"]:
                match = False
            
            if match:
                return element
        
        return None
    
    def get_tree_hash(self, elements: List[Dict[str, Any]]) -> str:
        """
        Generate a hash of the tree structure for quiescence detection
        """
        # Create a simplified representation for hashing
        tree_repr = []
        for elem in elements:
            tree_repr.append(f"{elem['id']}:{elem['role']}:{elem['name']}")
        
        tree_str = "|".join(sorted(tree_repr))
        return hashlib.sha256(tree_str.encode()).hexdigest()
