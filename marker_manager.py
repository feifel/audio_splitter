"""
Marker management and JSON persistence module.
"""

import json
import os
from typing import List, Tuple, Optional


class MarkerManager:
    """Manages split markers and their persistence."""
    
    def __init__(self):
        self.markers: List[float] = []  # List of marker positions in seconds
        self.excluded_splits: List[Tuple[float, float]] = []  # List of excluded split time ranges (start, end)
        self.audio_filename: Optional[str] = None
        self.audio_duration: float = 0.0  # Total audio duration
        
    def add_marker(self, time: float) -> bool:
        """
        Add a marker at the specified time.
        
        Args:
            time: Time position in seconds
            
        Returns:
            True if marker was added, False if it already exists
        """
        # Check if marker already exists at this position (with small tolerance)
        tolerance = 0.01  # 10ms tolerance
        for existing_time in self.markers:
            if abs(existing_time - time) < tolerance:
                return False
        
        self.markers.append(time)
        self.markers.sort()
        return True
    
    def remove_marker(self, time: float, tolerance: float = 0.1) -> bool:
        """
        Remove a marker near the specified time.
        
        Args:
            time: Time position in seconds
            tolerance: Maximum distance to find marker
            
        Returns:
            True if a marker was removed, False otherwise
        """
        for marker_time in self.markers:
            if abs(marker_time - time) < tolerance:
                self.markers.remove(marker_time)
                return True
        return False
    
    def move_marker(self, old_time: float, new_time: float, tolerance: float = 0.1) -> bool:
        """
        Move a marker from old position to new position.
        
        Args:
            old_time: Current marker position
            new_time: New marker position
            tolerance: Maximum distance to find marker
            
        Returns:
            True if marker was moved, False otherwise
        """
        for i, marker_time in enumerate(self.markers):
            if abs(marker_time - old_time) < tolerance:
                self.markers[i] = new_time
                self.markers.sort()
                return True
        return False
    
    def get_marker_at_position(self, time: float, tolerance: float = 0.1) -> Optional[float]:
        """
        Get marker at or near the specified position.
        
        Args:
            time: Time position to search
            tolerance: Maximum distance to find marker
            
        Returns:
            Marker time if found, None otherwise
        """
        for marker_time in self.markers:
            if abs(marker_time - time) < tolerance:
                return marker_time
        return None
    
    def clear_markers(self):
        """Remove all markers."""
        self.markers = []
        self.excluded_splits = []
    
    def set_markers(self, markers: List[float]):
        """
        Set markers from a list.
        
        Args:
            markers: List of marker times in seconds
        """
        self.markers = sorted(markers)
    
    def get_markers(self) -> List[float]:
        """Get all markers."""
        return self.markers.copy()
    
    def save_to_json(self, filepath: str) -> Tuple[bool, str]:
        """
        Save markers and audio filename to JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Ensure .json extension
            if not filepath.lower().endswith('.json'):
                filepath = filepath + '.json'
            
            # Convert excluded splits to serializable format (list of [start, end] pairs)
            excluded_splits_serialized = [[start, end] for start, end in self.excluded_splits]
            
            data = {
                "audio_filename": self.audio_filename,
                "markers": self.markers,
                "excluded_splits": excluded_splits_serialized,
                "audio_duration": self.audio_duration
            }
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            return True, f"Markers saved to {os.path.basename(filepath)}"
            
        except Exception as e:
            return False, f"Error saving markers: {str(e)}"
    
    def load_from_json(self, filepath: str) -> Tuple[bool, str, Optional[str]]:
        """
        Load markers and audio filename from JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            Tuple of (success, message, audio_filename)
        """
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            self.audio_filename = data.get("audio_filename")
            self.markers = sorted(data.get("markers", []))
            self.audio_duration = data.get("audio_duration", 0.0)
            
            # Convert excluded splits from list format to tuples
            excluded_splits_data = data.get("excluded_splits", [])
            if excluded_splits_data and isinstance(excluded_splits_data[0], list):
                # New format: list of [start, end] pairs
                self.excluded_splits = [(start, end) for start, end in excluded_splits_data]
            else:
                # Old format: list of indices - convert to empty (backward compatibility)
                self.excluded_splits = []
            
            return True, f"Loaded {len(self.markers)} markers", self.audio_filename
            
        except Exception as e:
            return False, f"Error loading markers: {str(e)}", None
    
    def set_audio_filename(self, filename: str):
        """Set the associated audio filename."""
        self.audio_filename = filename
    
    def get_audio_filename(self) -> Optional[str]:
        """Get the associated audio filename."""
        return self.audio_filename
        
    def set_audio_duration(self, duration: float):
        """Set the total audio duration."""
        self.audio_duration = duration
        
    def _get_splits(self) -> List[Tuple[float, float]]:
        """Calculate split segments from markers."""
        if not self.markers:
            return []
        
        splits = []
        
        # First split: from start to first marker
        splits.append((0.0, self.markers[0]))
        
        # Middle splits: between consecutive markers
        for i in range(len(self.markers) - 1):
            splits.append((self.markers[i], self.markers[i + 1]))
        
        # Last split: from last marker to end
        splits.append((self.markers[-1], self.audio_duration))
        
        return splits
        
    def toggle_split_exclusion(self, split_index: int) -> bool:
        """
        Toggle exclusion state of a split by index.
        
        Args:
            split_index: Index of the split (0-based)
            
        Returns:
            True if now excluded, False if now included
        """
        # Get current splits
        splits = self._get_splits()
        if split_index >= len(splits):
            return False
            
        split_range = splits[split_index]
        
        # Check if this time range is already excluded
        if split_range in self.excluded_splits:
            self.excluded_splits.remove(split_range)
            return False
        else:
            self.excluded_splits.append(split_range)
            return True
            
    def is_split_excluded(self, split_index: int) -> bool:
        """Check if a split is excluded by index."""
        splits = self._get_splits()
        if split_index >= len(splits):
            return False
        split_range = splits[split_index]
        return split_range in self.excluded_splits
        
    def get_excluded_splits(self) -> List[int]:
        """Get list of excluded split indices based on current markers."""
        splits = self._get_splits()
        excluded_indices = []
        
        for i, split_range in enumerate(splits):
            if split_range in self.excluded_splits:
                excluded_indices.append(i)
        
        return excluded_indices
        
    def set_excluded_splits_by_indices(self, excluded_indices: List[int]):
        """Set the excluded splits by indices (converts to time ranges)."""
        splits = self._get_splits()
        self.excluded_splits = []
        
        for idx in excluded_indices:
            if idx < len(splits):
                self.excluded_splits.append(splits[idx])
                
    def set_excluded_splits_by_ranges(self, excluded_ranges: List[Tuple[float, float]]):
        """Set the excluded splits by time ranges directly."""
        self.excluded_splits = excluded_ranges.copy()
