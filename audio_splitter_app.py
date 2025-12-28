"""
Main application window for Audio Splitter.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QSlider, QSpinBox, QDoubleSpinBox,
    QFileDialog, QMessageBox, QProgressDialog, QScrollBar, QStatusBar, QDialog
)
from PyQt6.QtCore import Qt, QTimer, QUrl, QSettings
from PyQt6.QtGui import QAction
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

from waveform_widget import WaveformWidget
from audio_processor import AudioProcessor
from marker_manager import MarkerManager
from export_dialog import ExportDialog, ConcatDialog
import os


class AudioSplitterApp(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Audio Splitter")
        self.setGeometry(100, 100, 1200, 800)
        
        # Settings persistence
        self.settings = QSettings("AudioSplitter", "AudioSplitterApp")
        
        # Core components
        self.audio_processor = AudioProcessor()
        self.marker_manager = MarkerManager()
        
        # Audio playback components
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._update_playback_position)
        
        # State
        self.current_audio_file = None
        
        self._init_ui()
        self._connect_signals()
        self._load_settings()
        
    def _init_ui(self):
        """Initialize the user interface."""
        # Create menu bar
        self._create_menu_bar()
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout()
        
        # File info section
        info_layout = QHBoxLayout()
        self.file_label = QLabel("No audio file loaded")
        self.file_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        info_layout.addWidget(self.file_label)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)
        
        # Waveform display
        self.waveform_widget = WaveformWidget()
        self.waveform_widget.setMinimumHeight(300)
        main_layout.addWidget(self.waveform_widget, 1)
        
        # Horizontal scrollbar
        self.h_scrollbar = QScrollBar(Qt.Orientation.Horizontal)
        self.h_scrollbar.setRange(0, 100)
        self.h_scrollbar.setValue(0)
        self.h_scrollbar.valueChanged.connect(self._on_h_scroll)
        main_layout.addWidget(self.h_scrollbar)
        
        # Controls section
        controls_layout = QHBoxLayout()
        
        # Playback controls
        playback_group = self._create_playback_controls()
        controls_layout.addWidget(playback_group)
        
        # Zoom controls
        zoom_group = self._create_zoom_controls()
        controls_layout.addWidget(zoom_group)
        
        # Marker controls
        marker_group = self._create_marker_controls()
        controls_layout.addWidget(marker_group)
        
        # Silence detection controls
        silence_group = self._create_silence_controls()
        controls_layout.addWidget(silence_group)
        
        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)
        
        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.addStretch()
        
        self.save_markers_button = QPushButton("Save Markers")
        self.save_markers_button.clicked.connect(self._save_markers)
        self.save_markers_button.setEnabled(False)
        action_layout.addWidget(self.save_markers_button)
        
        self.load_markers_button = QPushButton("Load Markers")
        self.load_markers_button.clicked.connect(self._load_markers)
        action_layout.addWidget(self.load_markers_button)
        
        self.export_button = QPushButton("Export Splits")
        self.export_button.clicked.connect(self._export_splits)
        self.export_button.setEnabled(False)
        self.export_button.setStyleSheet("font-weight: bold; padding: 10px;")
        action_layout.addWidget(self.export_button)

        self.concat_button = QPushButton("Concat Splits")
        self.concat_button.clicked.connect(self._concat_splits)
        self.concat_button.setEnabled(False)
        self.concat_button.setStyleSheet("font-weight: bold; padding: 10px;")
        action_layout.addWidget(self.concat_button)

        main_layout.addLayout(action_layout)
        
        central_widget.setLayout(main_layout)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        
    def _create_menu_bar(self):
        """Create menu bar."""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        load_action = QAction("Load Audio...", self)
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self._load_audio)
        file_menu.addAction(load_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Help menu
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
        
    def _create_playback_controls(self) -> QGroupBox:
        """Create playback control group."""
        group = QGroupBox("Playback")
        layout = QVBoxLayout()
        
        # Play button
        self.play_button = QPushButton("▶ Play")
        self.play_button.clicked.connect(self._play_audio)
        self.play_button.setEnabled(False)
        self.play_button.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.play_button)
        
        # Stop button
        self.stop_button = QPushButton("⏹ Stop")
        self.stop_button.clicked.connect(self._stop_audio)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)
        
        # Info label
        info_label = QLabel("Click ruler to set\nplayback position")
        info_label.setStyleSheet("font-size: 9px; color: gray;")
        layout.addWidget(info_label)
        
        group.setLayout(layout)
        return group
        
    def _create_zoom_controls(self) -> QGroupBox:
        """Create zoom control group."""
        group = QGroupBox("Zoom")
        layout = QVBoxLayout()
        
        # Horizontal zoom
        h_zoom_layout = QHBoxLayout()
        h_zoom_layout.addWidget(QLabel("Horizontal:"))
        
        self.h_zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.h_zoom_slider.setRange(1, 100)
        self.h_zoom_slider.setValue(1)
        self.h_zoom_slider.valueChanged.connect(self._on_h_zoom)
        h_zoom_layout.addWidget(self.h_zoom_slider)
        
        self.h_zoom_label = QLabel("1.0x")
        self.h_zoom_label.setMinimumWidth(50)
        h_zoom_layout.addWidget(self.h_zoom_label)
        
        layout.addLayout(h_zoom_layout)
        
        # Vertical zoom
        v_zoom_layout = QHBoxLayout()
        v_zoom_layout.addWidget(QLabel("Vertical:"))
        
        self.v_zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.v_zoom_slider.setRange(1, 50)
        self.v_zoom_slider.setValue(10)
        self.v_zoom_slider.valueChanged.connect(self._on_v_zoom)
        v_zoom_layout.addWidget(self.v_zoom_slider)
        
        self.v_zoom_label = QLabel("1.0x")
        self.v_zoom_label.setMinimumWidth(50)
        v_zoom_layout.addWidget(self.v_zoom_label)
        
        layout.addLayout(v_zoom_layout)
        
        group.setLayout(layout)
        return group
        
    def _create_marker_controls(self) -> QGroupBox:
        """Create marker control group."""
        group = QGroupBox("Markers")
        layout = QVBoxLayout()
        
        self.marker_count_label = QLabel("Markers: 0")
        layout.addWidget(self.marker_count_label)
        
        self.clear_markers_button = QPushButton("Clear All Markers")
        self.clear_markers_button.clicked.connect(self._clear_markers)
        layout.addWidget(self.clear_markers_button)
        
        info_label = QLabel("Left click: Add marker\nRight click: Remove marker\nDrag: Move marker")
        info_label.setStyleSheet("font-size: 9px; color: gray;")
        layout.addWidget(info_label)
        
        group.setLayout(layout)
        return group
        
    def _create_silence_controls(self) -> QGroupBox:
        """Create silence detection control group."""
        group = QGroupBox("Auto-Detect Silence")
        layout = QVBoxLayout()
        
        # Threshold
        threshold_layout = QHBoxLayout()
        threshold_layout.addWidget(QLabel("Threshold (dB):"))
        
        self.threshold_spinbox = QSpinBox()
        self.threshold_spinbox.setRange(-80, 0)
        self.threshold_spinbox.setValue(-40)
        self.threshold_spinbox.setSuffix(" dB")
        threshold_layout.addWidget(self.threshold_spinbox)
        
        layout.addLayout(threshold_layout)
        
        # Min duration
        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Min Duration (s):"))
        
        self.min_duration_spinbox = QDoubleSpinBox()
        self.min_duration_spinbox.setRange(0.1, 10.0)
        self.min_duration_spinbox.setValue(0.5)
        self.min_duration_spinbox.setSingleStep(0.1)
        self.min_duration_spinbox.setSuffix(" s")
        duration_layout.addWidget(self.min_duration_spinbox)
        
        layout.addLayout(duration_layout)
        
        # Detect button
        self.detect_silence_button = QPushButton("Detect Silence")
        self.detect_silence_button.clicked.connect(self._detect_silence)
        self.detect_silence_button.setEnabled(False)
        layout.addWidget(self.detect_silence_button)
        
        group.setLayout(layout)
        return group
        
    def _connect_signals(self):
        """Connect widget signals."""
        self.waveform_widget.marker_added.connect(self._on_marker_added)
        self.waveform_widget.marker_removed.connect(self._on_marker_removed)
        self.waveform_widget.marker_moved.connect(self._on_marker_moved)
        self.waveform_widget.playback_position_changed.connect(self._on_playback_position_changed)
        self.waveform_widget.scroll_offset_changed.connect(self._on_auto_scroll)
        self.waveform_widget.split_toggled.connect(self._on_split_toggled)
        
    def _load_audio(self):
        """Load an audio file."""
        # Get last used input folder
        last_input_folder = self.settings.value("folders/input", "", type=str)
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Audio File",
            last_input_folder,
            "Audio Files (*.mp3 *.wav *.flac *.ogg);;All Files (*)"
        )
        
        if not filename:
            return
        
        # Show progress
        progress = QProgressDialog("Loading audio file...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        # Process events to show dialog
        QTimer.singleShot(100, lambda: self._load_audio_delayed(filename, progress))
        
    def _load_audio_delayed(self, filename, progress):
        """Delayed audio loading to allow progress dialog to show."""
        success, message = self.audio_processor.load_audio(filename)
        
        progress.close()
        
        if not success:
            QMessageBox.critical(self, "Error", message)
            return
        
        # Save last used input folder
        self.settings.setValue("folders/input", os.path.dirname(filename))
        
        # Update UI
        self.current_audio_file = filename
        self.file_label.setText(f"File: {os.path.basename(filename)} | "
                                f"Duration: {self._format_duration(self.audio_processor.duration)} | "
                                f"Sample Rate: {self.audio_processor.sample_rate} Hz")
        
        # Generate waveform data
        waveform_data = self.audio_processor.get_waveform_data(samples_per_pixel=100)
        self.waveform_widget.set_waveform_data(waveform_data, self.audio_processor.duration)
        
        # Clear markers
        self.marker_manager.clear_markers()
        self.marker_manager.set_audio_filename(os.path.basename(filename))
        self.marker_manager.set_audio_duration(self.audio_processor.duration)
        self.waveform_widget.clear_markers()
        self._update_marker_count()
        
        # Enable controls
        self.detect_silence_button.setEnabled(True)
        self.save_markers_button.setEnabled(True)
        self.export_button.setEnabled(True)
        self.concat_button.setEnabled(True)
        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        
        # Set up media player for playback
        self.media_player.setSource(QUrl.fromLocalFile(filename))
        
        self.statusBar.showMessage(message)
        
    def _on_h_zoom(self, value):
        """Handle horizontal zoom change."""
        zoom = float(value)
        self.h_zoom_label.setText(f"{zoom:.1f}x")
        self.waveform_widget.set_horizontal_zoom(zoom)
        
        # Update scrollbar
        if zoom > 1.0:
            self.h_scrollbar.setEnabled(True)
        else:
            self.h_scrollbar.setEnabled(False)
            self.h_scrollbar.setValue(0)
            
    def _on_v_zoom(self, value):
        """Handle vertical zoom change."""
        zoom = value / 10.0
        self.v_zoom_label.setText(f"{zoom:.1f}x")
        self.waveform_widget.set_vertical_zoom(zoom)
        
    def _on_h_scroll(self, value):
        """Handle horizontal scroll."""
        offset = value / 100.0
        self.waveform_widget.set_scroll_offset(offset)
        
    def _on_marker_added(self, time):
        """Handle marker added event."""
        self.marker_manager.add_marker(time)
        self._update_marker_count()
        
    def _on_marker_removed(self, time):
        """Handle marker removed event."""
        self.marker_manager.remove_marker(time, tolerance=0.01)
        self._update_marker_count()
        
    def _on_marker_moved(self, old_time, new_time):
        """Handle marker moved event."""
        self.marker_manager.move_marker(old_time, new_time, tolerance=0.01)
        
    def _on_split_toggled(self, split_index: int):
        """Handle split toggle event."""
        # Sync exclusions from waveform widget to marker manager
        self.marker_manager.set_excluded_splits_by_ranges(self.waveform_widget.get_excluded_splits())
        
        # Determine status
        is_excluded = self.marker_manager.is_split_excluded(split_index)
        status = "excluded" if is_excluded else "included"
        self.statusBar.showMessage(f"Split {split_index + 1} {status}")
        
    def _update_marker_count(self):
        """Update marker count label."""
        count = len(self.marker_manager.get_markers())
        self.marker_count_label.setText(f"Markers: {count}")
        
    def _clear_markers(self):
        """Clear all markers."""
        reply = QMessageBox.question(
            self,
            "Clear Markers",
            "Are you sure you want to remove all markers?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.marker_manager.clear_markers()
            self.waveform_widget.clear_markers()
            self._update_marker_count()
            
    def _detect_silence(self):
        """Detect silent regions and place markers."""
        if self.audio_processor.audio_data is None:
            return
        
        threshold = float(self.threshold_spinbox.value())
        min_duration = float(self.min_duration_spinbox.value())
        
        # Show progress
        progress = QProgressDialog("Detecting silence...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.show()
        
        # Detect silence
        QTimer.singleShot(100, lambda: self._detect_silence_delayed(
            threshold, min_duration, progress
        ))
        
    def _detect_silence_delayed(self, threshold, min_duration, progress):
        """Delayed silence detection."""
        silent_regions = self.audio_processor.detect_silence(threshold, min_duration)
        
        progress.close()
        
        if not silent_regions:
            QMessageBox.information(
                self,
                "No Silence Detected",
                f"No silent regions found with threshold {threshold} dB "
                f"and minimum duration {min_duration} s."
            )
            return
        
        # Ask user for confirmation
        reply = QMessageBox.question(
            self,
            "Add Markers",
            f"Found {len(silent_regions)} silent regions.\n"
            f"Add markers at the middle of each silent region?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Clear existing markers
            self.marker_manager.clear_markers()
            
            # Add markers at middle of silent regions
            for start, end in silent_regions:
                middle = (start + end) / 2
                self.marker_manager.add_marker(middle)
            
            # Update waveform
            self.waveform_widget.set_markers(self.marker_manager.get_markers())
            self._update_marker_count()
            
            self.statusBar.showMessage(f"Added {len(silent_regions)} markers")
            
    def _save_markers(self):
        """Save markers to JSON file."""
        if not self.marker_manager.get_markers():
            QMessageBox.warning(self, "No Markers", "There are no markers to save.")
            return
        
        # Get last used markers folder
        last_markers_folder = self.settings.value("folders/markers", "", type=str)
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Markers",
            last_markers_folder,
            "JSON Files (*.json);;All Files (*)"
        )
        
        if filename:
            success, message = self.marker_manager.save_to_json(filename)
            
            if success:
                # Save last used markers folder
                self.settings.setValue("folders/markers", os.path.dirname(filename))
                self.statusBar.showMessage(message)
            else:
                QMessageBox.critical(self, "Error", message)
                
    def _load_markers(self):
        """Load markers from JSON file."""
        # Get last used markers folder
        last_markers_folder = self.settings.value("folders/markers", "", type=str)
        
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Markers",
            last_markers_folder,
            "JSON Files (*.json);;All Files (*)"
        )
        
        if not filename:
            return
        
        success, message, audio_filename = self.marker_manager.load_from_json(filename)
        
        if not success:
            QMessageBox.critical(self, "Error", message)
            return
        
        # Save last used markers folder
        self.settings.setValue("folders/markers", os.path.dirname(filename))
        
        # Update duration in marker manager if audio is loaded
        if self.audio_processor.duration > 0:
            self.marker_manager.set_audio_duration(self.audio_processor.duration)
        
        # Update waveform with markers and exclusions (as time ranges)
        self.waveform_widget.set_markers(self.marker_manager.get_markers())
        # Get exclusions as time ranges, not indices
        excluded_ranges = self.marker_manager.excluded_splits
        self.waveform_widget.set_excluded_splits(excluded_ranges)
        self._update_marker_count()
        
        # Show info about associated audio file
        if audio_filename:
            info_msg = f"{message}\nAssociated audio file: {audio_filename}"
            QMessageBox.information(self, "Markers Loaded", info_msg)
        
        self.statusBar.showMessage(message)
        
    def _export_splits(self):
        """Export audio splits."""
        if self.audio_processor.audio_data is None:
            QMessageBox.warning(self, "No Audio", "Please load an audio file first.")
            return
        
        if not self.marker_manager.get_markers():
            QMessageBox.warning(
                self,
                "No Markers",
                "Please add at least one marker to split the audio."
            )
            return
        
        # Get input audio format from file extension
        input_format = None
        if self.current_audio_file:
            input_format = os.path.splitext(self.current_audio_file)[1][1:]  # Remove the dot
        
        # Gather saved export settings
        saved_export_settings = {
            "format": self.settings.value("export/format", "", type=str),
            "sample_rate": self.settings.value("export/sample_rate", 44100, type=int),
            "channels": self.settings.value("export/channels", 2, type=int),
            "quality": self.settings.value("export/quality", "medium", type=str),
            "output_folder": self.settings.value("folders/output", "", type=str),
            "filename_prefix": self.settings.value("export/filename_prefix", "split", type=str),
            "trim_silence": self.settings.value("export/trim_silence", True, type=bool)
        }
        
        # Show export dialog with input format as default and saved settings
        dialog = ExportDialog(self, default_format=input_format, saved_settings=saved_export_settings)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = dialog.get_export_settings()
            
            # Save export settings for future use
            self.settings.setValue("export/format", settings["format"])
            self.settings.setValue("export/sample_rate", settings["sample_rate"])
            self.settings.setValue("export/channels", settings["channels"])
            self.settings.setValue("export/quality", settings["quality"])
            self.settings.setValue("folders/output", settings["output_folder"])
            self.settings.setValue("export/filename_prefix", settings["filename_prefix"])
            self.settings.setValue("export/trim_silence", settings["trim_silence"])
            
            # Show progress
            progress = QProgressDialog("Exporting splits...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()
            
            # Export
            QTimer.singleShot(100, lambda: self._export_splits_delayed(settings, progress))
            
    def _export_splits_delayed(self, settings, progress):
        """Delayed export to show progress dialog."""
        success, message = self.audio_processor.export_splits(
            split_times=self.marker_manager.get_markers(),
            output_folder=settings["output_folder"],
            filename_prefix=settings["filename_prefix"],
            output_format=settings["format"],
            sample_rate=settings["sample_rate"],
            channels=settings["channels"],
            quality=settings["quality"],
            trim_silence=settings["trim_silence"],
            excluded_splits=self.marker_manager.get_excluded_splits()
        )

        progress.close()

        if success:
            QMessageBox.information(self, "Success", message)
            self.statusBar.showMessage(message)
        else:
            QMessageBox.critical(self, "Error", message)

    def _concat_splits(self):
        """Concatenate audio splits into a single file."""
        if self.audio_processor.audio_data is None:
            QMessageBox.warning(self, "No Audio", "Please load an audio file first.")
            return

        if not self.marker_manager.get_markers():
            QMessageBox.warning(
                self,
                "No Markers",
                "Please add at least one marker to split the audio."
            )
            return

        input_format = None
        if self.current_audio_file:
            input_format = os.path.splitext(self.current_audio_file)[1][1:]

        saved_concat_settings = {
            "format": self.settings.value("concat/format", "", type=str),
            "sample_rate": self.settings.value("concat/sample_rate", 44100, type=int),
            "channels": self.settings.value("concat/channels", 2, type=int),
            "quality": self.settings.value("concat/quality", "medium", type=str),
            "output_folder": self.settings.value("folders/output", "", type=str),
            "filename": self.settings.value("concat/filename", "concatenated", type=str),
            "silence_duration": self.settings.value("concat/silence_duration", 500, type=int)
        }

        dialog = ConcatDialog(self, default_format=input_format, saved_settings=saved_concat_settings)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            settings = dialog.get_concat_settings()

            self.settings.setValue("concat/format", settings["format"])
            self.settings.setValue("concat/sample_rate", settings["sample_rate"])
            self.settings.setValue("concat/channels", settings["channels"])
            self.settings.setValue("concat/quality", settings["quality"])
            self.settings.setValue("folders/output", settings["output_folder"])
            self.settings.setValue("concat/filename", settings["filename"])
            self.settings.setValue("concat/silence_duration", settings["silence_duration"])

            progress = QProgressDialog("Concatenating splits...", "Cancel", 0, 100, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.show()

            QTimer.singleShot(100, lambda: self._concat_splits_delayed(settings, progress))

    def _concat_splits_delayed(self, settings, progress):
        """Delayed concatenation to show progress dialog."""
        # Get silence threshold from UI
        threshold = float(self.threshold_spinbox.value())

        success, message = self.audio_processor.concat_splits(
            split_times=self.marker_manager.get_markers(),
            output_folder=settings["output_folder"],
            filename=settings["filename"],
            output_format=settings["format"],
            sample_rate=settings["sample_rate"],
            channels=settings["channels"],
            quality=settings["quality"],
            silence_duration_ms=settings["silence_duration"],
            excluded_splits=self.marker_manager.get_excluded_splits(),
            silence_threshold_db=threshold
        )

        progress.close()

        if success:
            QMessageBox.information(self, "Success", message)
            self.statusBar.showMessage(message)
        else:
            QMessageBox.critical(self, "Error", message)

    def _show_about(self):
        """Show about dialog."""
        QMessageBox.about(
            self,
            "About Audio Splitter",
            "<h3>Audio Splitter</h3>"
            "<p>A powerful desktop application for splitting audio files.</p>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Load MP3, WAV, FLAC, OGG formats</li>"
            "<li>Interactive waveform visualization</li>"
            "<li>Draggable split markers</li>"
            "<li>Auto-detect silence</li>"
            "<li>Export with format and quality options</li>"
            "</ul>"
            "<p>Version 1.0</p>"
        )
        
    def _play_audio(self):
        """Start audio playback from the current playback position."""
        if self.current_audio_file is None:
            return
        
        # Get playback position from waveform widget
        position_seconds = self.waveform_widget.get_playback_position()
        position_ms = int(position_seconds * 1000)
        
        # Set position and play
        self.media_player.setPosition(position_ms)
        self.media_player.play()
        
        # Start timer to update playback position
        self.playback_timer.start(100)  # Update every 100ms
        
        self.statusBar.showMessage(f"Playing from {self._format_duration(position_seconds)}")
        
    def _stop_audio(self):
        """Stop audio playback."""
        self.media_player.stop()
        self.playback_timer.stop()
        self.statusBar.showMessage("Playback stopped")
        
    def _update_playback_position(self):
        """Update playback position indicator during playback."""
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            position_ms = self.media_player.position()
            position_seconds = position_ms / 1000.0
            self.waveform_widget.set_playback_position(position_seconds)
            
            # Auto-scroll to keep playback position visible
            self.waveform_widget.ensure_time_visible(position_seconds)
        else:
            # Stop timer if playback finished
            self.playback_timer.stop()
            
    def _on_playback_position_changed(self, position: float):
        """Handle playback position change from waveform widget."""
        # Stop if currently playing
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._stop_audio()
        
        # Always start playback from new position
        self._play_audio()
            
    def _on_auto_scroll(self, offset: float):
        """Handle auto-scroll event from waveform widget."""
        # Update scrollbar to reflect auto-scroll
        self.h_scrollbar.setValue(int(offset * 100))
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in seconds to MM:SS format."""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
        
    def _load_settings(self):
        """Load persisted settings."""
        # Restore zoom levels
        h_zoom = self.settings.value("zoom/horizontal", 1, type=int)
        v_zoom = self.settings.value("zoom/vertical", 10, type=int)
        self.h_zoom_slider.setValue(h_zoom)
        self.v_zoom_slider.setValue(v_zoom)
        
        # Restore silence detection settings
        threshold = self.settings.value("silence/threshold", -40, type=int)
        min_duration = self.settings.value("silence/min_duration", 0.5, type=float)
        self.threshold_spinbox.setValue(threshold)
        self.min_duration_spinbox.setValue(min_duration)
        
    def _save_settings(self):
        """Save current settings."""
        # Save zoom levels
        self.settings.setValue("zoom/horizontal", self.h_zoom_slider.value())
        self.settings.setValue("zoom/vertical", self.v_zoom_slider.value())
        
        # Save silence detection settings
        self.settings.setValue("silence/threshold", self.threshold_spinbox.value())
        self.settings.setValue("silence/min_duration", self.min_duration_spinbox.value())
        
    def closeEvent(self, event):
        """Handle application close event."""
        self._save_settings()
        event.accept()
