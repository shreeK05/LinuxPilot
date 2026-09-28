"""
Postcondition Verifier
Verifies machine-checkable postconditions after each step
"""

import os
from pathlib import Path
from typing import List, Optional
import logging
import time

from linuxpilot.models import Postcondition, VerificationResult

logger = logging.getLogger(__name__)


class PostconditionVerifier:
    """
    Verifies postconditions after each step
    Implements the "Consistency" property of ACID
    """
    
    def __init__(self):
        pass
    
    def verify(
        self,
        postconditions: List[Postcondition],
        timeout: int = 5,
    ) -> VerificationResult:
        """
        Verify all postconditions
        
        Args:
            postconditions: List of postconditions to verify
            timeout: Timeout for each check in seconds
        
        Returns:
            Verification result
        """
        failed = []
        
        for pc in postconditions:
            try:
                result = self._verify_single(pc, timeout)
                if not result:
                    failed.append(f"Postcondition failed: {pc}")
            except Exception as e:
                failed.append(f"Postcondition error: {pc} - {e}")
        
        if failed:
            return VerificationResult(
                success=False,
                error="; ".join(failed),
                details={"failed_count": len(failed), "total_count": len(postconditions)},
            )
        
        return VerificationResult(
            success=True,
            details={"verified_count": len(postconditions)},
        )
    
    def _verify_single(self, pc: Postcondition, timeout: int) -> bool:
        """Verify a single postcondition"""
        # Use wait_until pattern for polling
        start = time.time()
        
        while time.time() - start < timeout:
            try:
                if pc.type == "fs.exists":
                    return self._verify_fs_exists(pc)
                elif pc.type == "fs.not_exists":
                    return self._verify_fs_not_exists(pc)
                elif pc.type == "fs.count":
                    return self._verify_fs_count(pc)
                elif pc.type == "ui.element":
                    return self._verify_ui_element(pc)
                elif pc.type == "xlsx.cell":
                    return self._verify_xlsx_cell(pc)
                elif pc.type == "http.record":
                    return self._verify_http_record(pc)
                else:
                    logger.warning(f"Unknown postcondition type: {pc.type}")
                    return False
            except Exception as e:
                logger.debug(f"Postcondition check failed (will retry): {e}")
                time.sleep(0.2)
        
        return False
    
    def _verify_fs_exists(self, pc) -> bool:
        """Verify that a file/directory exists"""
        path = Path(pc.path).expanduser()
        return path.exists()
    
    def _verify_fs_not_exists(self, pc) -> bool:
        """Verify that a file/directory does not exist"""
        path = Path(pc.path).expanduser()
        return not path.exists()
    
    def _verify_fs_count(self, pc) -> bool:
        """Verify file count in directory"""
        dir_path = Path(pc.dir).expanduser()
        if not dir_path.exists():
            return False
        
        files = list(dir_path.glob(pc.glob))
        return len(files) == pc.eq
    
    def _verify_ui_element(self, pc) -> bool:
        """Verify UI element exists (requires AT-SPI)"""
        try:
            from linuxpilot.perception.atspi import ATSPIPerception
            
            perception = ATSPIPerception()
            elements = perception.snapshot()
            
            for elem in elements:
                if elem["role"] == pc.role:
                    if pc.name is None or pc.name in elem["name"]:
                        if pc.showing:  # Element should be showing
                            return True
                        elif not pc.showing:  # Element should not be showing
                            return False
            
            return not pc.showing  # If we want it not showing and didn't find it
            
        except Exception as e:
            logger.error(f"UI verification failed: {e}")
            return False
    
    def _verify_xlsx_cell(self, pc) -> bool:
        """Verify Excel cell value"""
        try:
            from openpyxl import load_workbook
            
            file_path = Path(pc.file).expanduser()
            workbook = load_workbook(file_path, data_only=True)
            sheet = workbook[pc.sheet]
            cell = sheet[pc.cell]
            
            return str(cell.value) == pc.equals
            
        except Exception as e:
            logger.error(f"XLSX verification failed: {e}")
            return False
    
    def _verify_http_record(self, pc) -> bool:
        """Verify HTTP record (requires server access)"""
        try:
            import httpx
            
            response = httpx.get(pc.url, timeout=5)
            data = response.json()
            
            # Check if field exists and equals expected value
            if pc.field in data:
                return str(data[pc.field]) == pc.equals
            
            return False
            
        except Exception as e:
            logger.error(f"HTTP verification failed: {e}")
            return False
