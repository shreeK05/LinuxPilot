"""
Perception Module
AT-SPI-based GUI automation and screen perception
"""

from .atspi import ATSPIPerception
from .compress import TreeCompressor

__all__ = ["ATSPIPerception", "TreeCompressor"]
