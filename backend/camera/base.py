"""Abstract Base Class for Camera Sources.

Provides a unified interface get_photo() -> (jpeg_bytes, timestamp, camera_id, metadata).
All camera sources (simulated, esp32_pull, esp32_push, video_file) implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple


class CameraSource(ABC):
    """Abstract camera interface feeding the ShelfSense monitoring pipeline."""

    @abstractmethod
    def get_photo(self) -> Tuple[Optional[bytes], float, str, Dict[str, Any]]:
        """Fetch the latest photo from this source.

        Returns:
            Tuple of:
                - jpeg_bytes: Raw JPEG bytes (or None if unavailable)
                - timestamp: Float unix timestamp (real or virtual clock)
                - camera_id: Identifier string (e.g. 'esp32_192.168.1.50', 'simulated_gradual_depletion')
                - metadata: Dict with source details (simulated: bool, frame_index, etc.)
        """
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return diagnostic status information about the camera source."""
        pass

    def start(self):
        """Optional start lifecycle hook."""
        pass

    def stop(self):
        """Optional stop lifecycle hook."""
        pass
