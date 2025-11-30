"""
Interactive waveform display widget with draggable markers.
"""

import numpy as np
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPoint, QRect, pyqtSignal, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPolygonF
from typing import List, Optional, Tuple


class WaveformWidget(QWidget):
    """Widget for displaying waveform with interactive markers."""
    
    # Signals
    marker_added = pyqtSignal(float)  # Emitted when marker is added
    marker_removed = pyqtSignal(float)  # Emitted when marker is removed
    marker_moved = pyqtSignal(float, float)  # Emitted when marker is moved (old_pos, new_pos)
    playback_position_changed = pyqtSignal(float)  # Emitted when playback position is moved
    scroll_offset_changed = pyqtSignal(float)  # Emitted when scroll offset changes (for auto-scroll)
    split_toggled = pyqtSignal(int)  # Emitted when a split is toggled (split_index)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Waveform data
        self.waveform_data: Optional[np.ndarray] = None
        self.duration: float = 0.0
        
        # Markers
        self.markers: List[float] = []
        self.dragging_marker: Optional[float] = None
        self.marker_hover: Optional[float] = None
        
        # Playback position
        self.playback_position: float = 0.0  # Current playback position in seconds
        self.dragging_playback: bool = False  # Whether user is dragging the playback icon
        self.playback_hover: bool = False  # Whether mouse is hovering over playback icon
        
        # Zoom and scroll
        self.h_zoom: float = 1.0  # Horizontal zoom factor
        self.v_zoom: float = 1.0  # Vertical zoom factor
        self.scroll_offset: float = 0.0  # Horizontal scroll offset (0.0 to 1.0)
        
        # Excluded splits
        self.excluded_splits: List[Tuple[float, float]] = []  # List of excluded split time ranges
        
        # Display settings
        self.ruler_height = 30  # Height of the ruler lane
        self.splits_lane_height = 40  # Height of the splits preview lane
        self.background_color = QColor(30, 30, 30)
        self.ruler_color = QColor(40, 40, 40)
        self.splits_lane_color = QColor(35, 35, 35)
        self.waveform_color = QColor(100, 200, 255)
        self.marker_color = QColor(255, 100, 100)
        self.marker_hover_color = QColor(255, 150, 150)
        self.playback_color = QColor(100, 255, 100)
        self.playback_hover_color = QColor(150, 255, 150)
        self.split_included_color = QColor(80, 180, 80)
        self.split_excluded_color = QColor(100, 100, 100)
        self.split_hover_color = QColor(120, 220, 120)
        self.marker_width = 2
        self.marker_grab_distance = 10  # pixels
        self.hover_split_index: Optional[int] = None  # Index of split being hovered
        
        # Mouse tracking
        self.setMouseTracking(True)
        self.setMinimumHeight(270)  # Increased to accommodate ruler lane and splits lane
        
    def set_waveform_data(self, waveform_data: np.ndarray, duration: float):
        """Set the waveform data to display."""
        self.waveform_data = waveform_data
        self.duration = duration
        self.update()
        
    def set_markers(self, markers: List[float]):
        """Set the marker positions."""
        self.markers = markers.copy()
        self.update()
        
    def add_marker(self, time: float):
        """Add a marker at the specified time."""
        if time not in self.markers:
            self.markers.append(time)
            self.markers.sort()
            self.update()
            
    def remove_marker(self, time: float):
        """Remove a marker at the specified time."""
        if time in self.markers:
            self.markers.remove(time)
            self.update()
            
    def clear_markers(self):
        """Remove all markers."""
        self.markers = []
        self.excluded_splits = []
        self.update()
        
    def set_excluded_splits(self, excluded_ranges: List[Tuple[float, float]]):
        """Set the excluded splits list by time ranges."""
        self.excluded_splits = excluded_ranges.copy()
        self.update()
        
    def get_excluded_splits(self) -> List[Tuple[float, float]]:
        """Get the excluded splits list as time ranges."""
        return self.excluded_splits.copy()
        
    def set_horizontal_zoom(self, zoom: float):
        """Set horizontal zoom factor (1.0 = normal, >1.0 = zoomed in)."""
        self.h_zoom = max(1.0, zoom)
        self.update()
        
    def set_vertical_zoom(self, zoom: float):
        """Set vertical zoom factor (1.0 = normal, >1.0 = zoomed in)."""
        self.v_zoom = max(0.1, zoom)
        self.update()
        
    def set_scroll_offset(self, offset: float):
        """Set horizontal scroll offset (0.0 to 1.0)."""
        self.scroll_offset = max(0.0, min(1.0, offset))
        self.update()
        
    def set_playback_position(self, position: float):
        """Set the playback position in seconds."""
        self.playback_position = max(0.0, min(self.duration, position))
        self.update()
        
    def get_playback_position(self) -> float:
        """Get the current playback position in seconds."""
        return self.playback_position
        
    def ensure_time_visible(self, time: float) -> bool:
        """
        Ensure the given time is visible by auto-scrolling if necessary.
        
        Args:
            time: Time in seconds to make visible
            
        Returns:
            True if scroll was adjusted, False otherwise
        """
        if self.duration == 0 or self.h_zoom <= 1.0:
            return False
            
        visible_duration = self.duration / self.h_zoom
        start_time = self.scroll_offset * (self.duration - visible_duration)
        end_time = start_time + visible_duration
        
        # Add small margins (10% of visible duration) to keep icon away from edges
        margin = visible_duration * 0.1
        
        # Check if time is outside visible range or too close to edges
        if time < start_time + margin:
            # Scroll left to center the time
            new_start_time = max(0, time - visible_duration / 2)
            self.scroll_offset = new_start_time / (self.duration - visible_duration)
            self.scroll_offset_changed.emit(self.scroll_offset)
            self.update()
            return True
        elif time > end_time - margin:
            # Scroll right to center the time
            new_start_time = min(self.duration - visible_duration, time - visible_duration / 2)
            self.scroll_offset = new_start_time / (self.duration - visible_duration)
            self.scroll_offset_changed.emit(self.scroll_offset)
            self.update()
            return True
            
        return False
        
    def get_time_at_x(self, x: int) -> float:
        """Convert x pixel coordinate to time in seconds."""
        if self.duration == 0:
            return 0.0
        
        width = self.width()
        visible_duration = self.duration / self.h_zoom
        
        # Account for scroll offset
        start_time = self.scroll_offset * (self.duration - visible_duration)
        
        # Calculate time at x position
        time = start_time + (x / width) * visible_duration
        return max(0.0, min(self.duration, time))
        
    def get_x_at_time(self, time: float) -> int:
        """Convert time in seconds to x pixel coordinate."""
        if self.duration == 0:
            return 0
        
        width = self.width()
        visible_duration = self.duration / self.h_zoom
        start_time = self.scroll_offset * (self.duration - visible_duration)
        
        # Calculate x position
        x = ((time - start_time) / visible_duration) * width
        return int(x)
        
    def paintEvent(self, event):
        """Paint the waveform and markers."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Fill background
        painter.fillRect(self.rect(), self.background_color)
        
        # Draw ruler lane
        self._draw_ruler_lane(painter)
        
        if self.waveform_data is None or len(self.waveform_data) == 0:
            # Draw placeholder text
            painter.setPen(QColor(150, 150, 150))
            painter.setFont(QFont("Arial", 14))
            waveform_rect = QRect(0, self.ruler_height, self.width(), self.height() - self.ruler_height)
            painter.drawText(waveform_rect, Qt.AlignmentFlag.AlignCenter, "No audio loaded")
            return
        
        # Draw splits preview lane
        self._draw_splits_lane(painter)
        
        # Draw waveform
        self._draw_waveform(painter)
        
        # Draw markers
        self._draw_markers(painter)
        
        # Draw time axis
        self._draw_time_axis(painter)
        
        # Draw playback position icon
        self._draw_playback_icon(painter)
        
    def _draw_ruler_lane(self, painter: QPainter):
        """Draw the ruler lane at the top."""
        # Draw ruler background
        ruler_rect = QRect(0, 0, self.width(), self.ruler_height)
        painter.fillRect(ruler_rect, self.ruler_color)
        
        # Draw border line
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawLine(0, self.ruler_height, self.width(), self.ruler_height)
        
    def _draw_splits_lane(self, painter: QPainter):
        """Draw the splits preview lane below the ruler."""
        # Draw lane background
        lane_y = self.ruler_height
        lane_rect = QRect(0, lane_y, self.width(), self.splits_lane_height)
        painter.fillRect(lane_rect, self.splits_lane_color)
        
        # Draw border line
        painter.setPen(QPen(QColor(80, 80, 80), 1))
        painter.drawLine(0, lane_y + self.splits_lane_height, self.width(), lane_y + self.splits_lane_height)
        
        if not self.markers:
            # Draw placeholder text
            painter.setPen(QColor(120, 120, 120))
            painter.setFont(QFont("Arial", 9))
            painter.drawText(lane_rect, Qt.AlignmentFlag.AlignCenter, "No splits - Add markers to create splits")
            return
        
        # Calculate splits (segments between markers and boundaries)
        splits = self._get_splits()
        
        # Draw each split as a block
        padding = 3  # Padding between splits
        block_y = lane_y + padding
        block_height = self.splits_lane_height - 2 * padding
        
        for i, (start_time, end_time) in enumerate(splits):
            start_x = self.get_x_at_time(start_time)
            end_x = self.get_x_at_time(end_time)
            
            # Only draw if visible
            if end_x < 0 or start_x > self.width():
                continue
            
            # Clamp to visible area
            start_x = max(0, start_x)
            end_x = min(self.width(), end_x)
            
            block_width = end_x - start_x - 2 * padding
            if block_width < 1:
                continue
            
            # Choose color based on exclusion state and hover
            split_range = (start_time, end_time)
            is_excluded = split_range in self.excluded_splits
            is_hovering = i == self.hover_split_index
            
            if is_hovering and not is_excluded:
                color = self.split_hover_color
            elif is_excluded:
                color = self.split_excluded_color
            else:
                color = self.split_included_color
            
            # Draw block
            block_rect = QRect(int(start_x + padding), int(block_y), int(block_width), int(block_height))
            painter.fillRect(block_rect, color)
            
            # Draw border
            painter.setPen(QPen(QColor(50, 50, 50), 1))
            painter.drawRect(block_rect)
            
            # Draw split number
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Arial", 9, QFont.Weight.Bold))
            split_text = f"{i + 1}"
            if is_excluded:
                split_text += " (X)"
            painter.drawText(block_rect, Qt.AlignmentFlag.AlignCenter, split_text)
            
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
        splits.append((self.markers[-1], self.duration))
        
        return splits
        
    def _draw_playback_icon(self, painter: QPainter):
        """Draw the playback position icon in the ruler lane."""
        if self.duration == 0:
            return
            
        x = self.get_x_at_time(self.playback_position)
        
        # Only draw if visible
        if 0 <= x <= self.width():
            # Choose color based on hover/drag state
            if self.playback_hover or self.dragging_playback:
                color = self.playback_hover_color
            else:
                color = self.playback_color
            
            # Draw play icon (triangle)
            icon_size = 12
            icon_y = self.ruler_height / 2
            
            # Create triangle pointing right
            triangle = QPolygonF([
                QPointF(x - icon_size/2, icon_y - icon_size/2),
                QPointF(x - icon_size/2, icon_y + icon_size/2),
                QPointF(x + icon_size/2, icon_y)
            ])
            
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.drawPolygon(triangle)
            
            # Draw vertical line from icon to bottom of waveform
            painter.setPen(QPen(color, 1, Qt.PenStyle.DashLine))
            painter.drawLine(x, self.ruler_height, x, self.height())
    
    def _draw_waveform(self, painter: QPainter):
        """Draw the waveform."""
        width = self.width()
        height = self.height()
        waveform_top = self.ruler_height + self.splits_lane_height
        waveform_height = height - waveform_top
        center_y = waveform_top + waveform_height / 2
        
        # Calculate visible range
        visible_duration = self.duration / self.h_zoom
        start_time = self.scroll_offset * (self.duration - visible_duration)
        end_time = start_time + visible_duration
        
        # Calculate sample indices using float precision to avoid jumps
        total_samples = len(self.waveform_data)
        start_idx = int((start_time / self.duration) * total_samples)
        end_idx = int((end_time / self.duration) * total_samples)
        
        # Ensure we have at least one sample
        end_idx = max(start_idx + 1, end_idx)
        
        # Get visible waveform data
        visible_data = self.waveform_data[start_idx:end_idx]
        
        if len(visible_data) == 0:
            return
        
        # Set up drawing
        painter.setPen(QPen(self.waveform_color, 1))
        painter.setBrush(QBrush(self.waveform_color))
        
        # Draw waveform with smooth scaling - use float division to avoid jumps
        samples_per_pixel = len(visible_data) / width
        
        for x in range(width):
            # Use float index to get smoother scaling
            sample_start_idx = int(x * samples_per_pixel)
            sample_end_idx = int((x + 1) * samples_per_pixel)
            
            # Ensure we don't go out of bounds
            sample_end_idx = min(sample_end_idx, len(visible_data))
            
            if sample_start_idx >= len(visible_data):
                break
            
            # Get min/max for this pixel range
            if sample_end_idx > sample_start_idx:
                chunk = visible_data[sample_start_idx:sample_end_idx]
                if len(chunk) > 0:
                    min_val = np.min(chunk[:, 0])
                    max_val = np.max(chunk[:, 1])
                else:
                    continue
            else:
                min_val = visible_data[sample_start_idx, 0]
                max_val = visible_data[sample_start_idx, 1]
            
            # Scale to display height with vertical zoom
            half_height = waveform_height / 2
            min_y = center_y - (min_val * half_height * 0.8 * self.v_zoom)
            max_y = center_y - (max_val * half_height * 0.8 * self.v_zoom)
            
            # Clamp to widget bounds (waveform area only)
            min_y = max(waveform_top, min(height, min_y))
            max_y = max(waveform_top, min(height, max_y))
            
            # Draw vertical line for this pixel
            painter.drawLine(x, int(min_y), x, int(max_y))
            
    def _draw_markers(self, painter: QPainter):
        """Draw split markers."""
        height = self.height()
        waveform_top = self.ruler_height + self.splits_lane_height
        
        for marker_time in self.markers:
            x = self.get_x_at_time(marker_time)
            
            # Only draw if visible
            if 0 <= x <= self.width():
                # Choose color based on hover state
                if self.marker_hover == marker_time:
                    color = self.marker_hover_color
                    width = self.marker_width + 1
                else:
                    color = self.marker_color
                    width = self.marker_width
                
                # Draw marker line (from splits lane to bottom)
                painter.setPen(QPen(color, width))
                painter.drawLine(x, waveform_top, x, height)
                
                # Draw time label in the waveform area
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.setFont(QFont("Arial", 9))
                time_text = self._format_time(marker_time)
                text_rect = QRect(x - 50, waveform_top + 5, 100, 20)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, time_text)
                
    def _draw_time_axis(self, painter: QPainter):
        """Draw time axis at the bottom."""
        height = self.height()
        width = self.width()
        
        # Draw axis line
        painter.setPen(QPen(QColor(150, 150, 150), 1))
        painter.drawLine(0, height - 20, width, height - 20)
        
        # Draw time labels
        painter.setPen(QPen(QColor(200, 200, 200)))
        painter.setFont(QFont("Arial", 8))
        
        visible_duration = self.duration / self.h_zoom
        start_time = self.scroll_offset * (self.duration - visible_duration)
        
        # Determine appropriate time interval for labels
        intervals = [0.1, 0.5, 1, 2, 5, 10, 30, 60, 120, 300]
        target_labels = 10
        interval = visible_duration / target_labels
        
        # Find closest interval
        time_interval = min(intervals, key=lambda x: abs(x - interval))
        
        # Draw labels
        first_label = int(start_time / time_interval) * time_interval
        current_time = first_label
        
        while current_time <= start_time + visible_duration:
            x = self.get_x_at_time(current_time)
            if 0 <= x <= width:
                painter.drawLine(x, height - 20, x, height - 15)
                time_text = self._format_time(current_time)
                text_rect = QRect(x - 30, height - 15, 60, 15)
                painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, time_text)
            
            current_time += time_interval
            
    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to MM:SS.ms format."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 100)
        return f"{minutes:02d}:{secs:02d}.{millis:02d}"
        
    def mousePressEvent(self, event):
        """Handle mouse press events."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Check if clicking in ruler lane (for playback position)
            if event.pos().y() <= self.ruler_height:
                # Check if clicking on playback icon
                if self._is_on_playback_icon(event.pos().x()):
                    self.dragging_playback = True
                else:
                    # Click anywhere in ruler to set playback position
                    time = self.get_time_at_x(event.pos().x())
                    self.playback_position = time
                    self.playback_position_changed.emit(time)
                    self.update()
            # Check if clicking in splits lane
            elif event.pos().y() <= self.ruler_height + self.splits_lane_height:
                split_index = self._get_split_at_position(event.pos().x(), event.pos().y())
                if split_index is not None:
                    # Get the split time range
                    splits = self._get_splits()
                    if split_index < len(splits):
                        split_range = splits[split_index]
                        # Toggle split exclusion by time range
                        if split_range in self.excluded_splits:
                            self.excluded_splits.remove(split_range)
                        else:
                            self.excluded_splits.append(split_range)
                        self.split_toggled.emit(split_index)
                        self.update()
            else:
                # Clicking in waveform area
                time = self.get_time_at_x(event.pos().x())
                
                # Check if clicking on existing marker
                marker = self._get_marker_at_x(event.pos().x())
                
                if marker is not None:
                    # Start dragging marker
                    self.dragging_marker = marker
                else:
                    # Add new marker
                    self.markers.append(time)
                    self.markers.sort()
                    self.marker_added.emit(time)
                    self.update()
                
        elif event.button() == Qt.MouseButton.RightButton:
            # Remove marker (only in waveform area, not in ruler or splits lane)
            if event.pos().y() > self.ruler_height + self.splits_lane_height:
                marker = self._get_marker_at_x(event.pos().x())
                if marker is not None:
                    self.markers.remove(marker)
                    self.marker_removed.emit(marker)
                    self.update()
                
    def mouseMoveEvent(self, event):
        """Handle mouse move events."""
        if self.dragging_playback:
            # Update playback position
            new_time = self.get_time_at_x(event.pos().x())
            self.playback_position = new_time
            self.playback_position_changed.emit(new_time)
            self.update()
        elif self.dragging_marker is not None:
            # Update marker position
            old_time = self.dragging_marker
            new_time = self.get_time_at_x(event.pos().x())
            
            # Update marker
            idx = self.markers.index(old_time)
            self.markers[idx] = new_time
            self.markers.sort()
            
            self.dragging_marker = new_time
            self.marker_moved.emit(old_time, new_time)
            self.update()
        else:
            # Update hover state for playback icon
            old_playback_hover = self.playback_hover
            if event.pos().y() <= self.ruler_height:
                self.playback_hover = self._is_on_playback_icon(event.pos().x())
            else:
                self.playback_hover = False
            
            # Update hover state for splits
            old_split_hover = self.hover_split_index
            if self.ruler_height < event.pos().y() <= self.ruler_height + self.splits_lane_height:
                self.hover_split_index = self._get_split_at_position(event.pos().x(), event.pos().y())
            else:
                self.hover_split_index = None
                
            # Update hover state for markers
            old_hover = self.marker_hover
            if event.pos().y() > self.ruler_height + self.splits_lane_height:
                self.marker_hover = self._get_marker_at_x(event.pos().x())
            else:
                self.marker_hover = None
            
            if old_hover != self.marker_hover or old_playback_hover != self.playback_hover or old_split_hover != self.hover_split_index:
                self.update()
                
            # Update cursor
            if self.playback_hover:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            elif self.hover_split_index is not None:
                self.setCursor(Qt.CursorShape.PointingHandCursor)
            elif self.marker_hover is not None:
                self.setCursor(Qt.CursorShape.SizeHorCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
                
    def mouseReleaseEvent(self, event):
        """Handle mouse release events."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging_marker = None
            self.dragging_playback = False
            
    def _get_marker_at_x(self, x: int) -> Optional[float]:
        """Get marker at or near the specified x coordinate."""
        for marker_time in self.markers:
            marker_x = self.get_x_at_time(marker_time)
            if abs(marker_x - x) <= self.marker_grab_distance:
                return marker_time
        return None
        
    def _is_on_playback_icon(self, x: int) -> bool:
        """Check if the given x coordinate is on the playback icon."""
        playback_x = self.get_x_at_time(self.playback_position)
        icon_size = 12
        return abs(playback_x - x) <= icon_size
        
    def _get_split_at_position(self, x: int, y: int) -> Optional[int]:
        """Get the split index at the given position, or None if not in splits lane."""
        # Check if y is in splits lane
        if y < self.ruler_height or y > self.ruler_height + self.splits_lane_height:
            return None
        
        # Get time at x position
        time = self.get_time_at_x(x)
        
        # Find which split this time belongs to
        splits = self._get_splits()
        for i, (start_time, end_time) in enumerate(splits):
            if start_time <= time <= end_time:
                return i
        
        return None
