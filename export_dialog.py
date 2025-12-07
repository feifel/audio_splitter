"""
Export dialog for configuring audio split export settings.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QComboBox, QLineEdit, QPushButton, QFileDialog, QCheckBox,
    QLabel, QMessageBox, QProgressDialog, QSpinBox
)
from PyQt6.QtCore import Qt
from typing import Dict, Any


class ExportDialog(QDialog):
    """Dialog for configuring export settings."""
    
    def __init__(self, parent=None, default_format: str = None, saved_settings: dict = None):
        super().__init__(parent)
        
        self.setWindowTitle("Export Audio Splits")
        self.setMinimumWidth(500)
        
        self.export_settings = None
        self.default_format = default_format
        self.saved_settings = saved_settings or {}
        
        self._init_ui()
        
    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()
        
        # Format settings group
        format_group = QGroupBox("Format Settings")
        format_layout = QFormLayout()
        
        # Output format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["wav", "mp3", "flac", "ogg"])
        # Set format: prefer saved settings, then input format, then default to "wav"
        if "format" in self.saved_settings:
            self.format_combo.setCurrentText(self.saved_settings["format"])
        elif self.default_format and self.default_format.lower() in ["wav", "mp3", "flac", "ogg"]:
            self.format_combo.setCurrentText(self.default_format.lower())
        else:
            self.format_combo.setCurrentText("wav")
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        format_layout.addRow("Output Format:", self.format_combo)
        
        # Sample rate
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems([
            "8000", "16000", "22050", "24000", "44100", "48000", "96000", "192000"
        ])
        saved_sample_rate = str(self.saved_settings.get("sample_rate", "44100"))
        self.sample_rate_combo.setCurrentText(saved_sample_rate)
        format_layout.addRow("Sample Rate (Hz):", self.sample_rate_combo)
        
        # Channels
        self.channels_combo = QComboBox()
        self.channels_combo.addItems(["Stereo", "Mono"])
        saved_channels = "Stereo" if self.saved_settings.get("channels", 2) == 2 else "Mono"
        self.channels_combo.setCurrentText(saved_channels)
        format_layout.addRow("Channels:", self.channels_combo)
        
        # Quality/Compression (for MP3, OGG)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Low (128 kbps)", "Medium (192 kbps)", "High (320 kbps)"])
        quality_map_reverse = {"low": "Low (128 kbps)", "medium": "Medium (192 kbps)", "high": "High (320 kbps)"}
        saved_quality = quality_map_reverse.get(self.saved_settings.get("quality", "medium"), "Medium (192 kbps)")
        self.quality_combo.setCurrentText(saved_quality)
        self.quality_label = QLabel("Quality/Bitrate:")
        format_layout.addRow(self.quality_label, self.quality_combo)
        
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)
        
        # Output settings group
        output_group = QGroupBox("Output Settings")
        output_layout = QVBoxLayout()
        
        # Output folder
        folder_layout = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Select output folder...")
        saved_output_folder = self.saved_settings.get("output_folder", "")
        if saved_output_folder:
            self.folder_edit.setText(saved_output_folder)
        self.folder_button = QPushButton("Browse...")
        self.folder_button.clicked.connect(self._browse_folder)
        folder_layout.addWidget(QLabel("Output Folder:"))
        folder_layout.addWidget(self.folder_edit, 1)
        folder_layout.addWidget(self.folder_button)
        output_layout.addLayout(folder_layout)
        
        # Filename prefix
        prefix_layout = QHBoxLayout()
        self.prefix_edit = QLineEdit()
        saved_prefix = self.saved_settings.get("filename_prefix", "split")
        self.prefix_edit.setText(saved_prefix)
        self.prefix_edit.setPlaceholderText("Enter filename prefix...")
        prefix_layout.addWidget(QLabel("Filename Prefix:"))
        prefix_layout.addWidget(self.prefix_edit, 1)
        output_layout.addLayout(prefix_layout)
        
        # Info label
        info_label = QLabel("Files will be named: prefix_001.ext, prefix_002.ext, etc.")
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        output_layout.addWidget(info_label)
        
        output_group.setLayout(output_layout)
        layout.addWidget(output_group)
        
        # Processing options group
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout()
        
        self.trim_silence_checkbox = QCheckBox("Trim silence from beginning and end of each split")
        saved_trim_silence = self.saved_settings.get("trim_silence", True)
        self.trim_silence_checkbox.setChecked(saved_trim_silence)
        options_layout.addWidget(self.trim_silence_checkbox)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        self.export_button = QPushButton("Export")
        self.export_button.clicked.connect(self._on_export)
        self.export_button.setDefault(True)
        button_layout.addWidget(self.export_button)
        
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Initial state update
        self._on_format_changed(self.format_combo.currentText())
        
    def _on_format_changed(self, format_name: str):
        """Handle format change event."""
        # Show/hide quality options based on format
        compressed_formats = ["mp3", "ogg"]
        is_compressed = format_name in compressed_formats
        
        self.quality_label.setVisible(is_compressed)
        self.quality_combo.setVisible(is_compressed)
        
    def _browse_folder(self):
        """Open folder browser dialog."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            "",
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            self.folder_edit.setText(folder)
            
    def _on_export(self):
        """Handle export button click."""
        # Validate settings
        if not self.folder_edit.text():
            QMessageBox.warning(
                self,
                "Invalid Settings",
                "Please select an output folder."
            )
            return
        
        if not self.prefix_edit.text():
            QMessageBox.warning(
                self,
                "Invalid Settings",
                "Please enter a filename prefix."
            )
            return
        
        # Get quality setting
        quality_map = {
            "Low (128 kbps)": "low",
            "Medium (192 kbps)": "medium",
            "High (320 kbps)": "high"
        }
        quality = quality_map[self.quality_combo.currentText()]
        
        # Get channels setting
        channels = 2 if self.channels_combo.currentText() == "Stereo" else 1
        
        # Store export settings
        self.export_settings = {
            "format": self.format_combo.currentText(),
            "sample_rate": int(self.sample_rate_combo.currentText()),
            "channels": channels,
            "quality": quality,
            "output_folder": self.folder_edit.text(),
            "filename_prefix": self.prefix_edit.text(),
            "trim_silence": self.trim_silence_checkbox.isChecked()
        }
        
        self.accept()
        
    def get_export_settings(self) -> Dict[str, Any]:
        """Get the configured export settings."""
        return self.export_settings


class ConcatDialog(QDialog):
    """Dialog for configuring concatenation settings."""

    def __init__(self, parent=None, default_format: str = None, saved_settings: dict = None):
        super().__init__(parent)

        self.setWindowTitle("Concatenate Audio Splits")
        self.setMinimumWidth(500)

        self.concat_settings = None
        self.default_format = default_format
        self.saved_settings = saved_settings or {}

        self._init_ui()

    def _init_ui(self):
        """Initialize the user interface."""
        layout = QVBoxLayout()

        # Format settings group
        format_group = QGroupBox("Format Settings")
        format_layout = QFormLayout()

        # Output format
        self.format_combo = QComboBox()
        self.format_combo.addItems(["wav", "mp3", "flac", "ogg"])
        if "format" in self.saved_settings:
            self.format_combo.setCurrentText(self.saved_settings["format"])
        elif self.default_format and self.default_format.lower() in ["wav", "mp3", "flac", "ogg"]:
            self.format_combo.setCurrentText(self.default_format.lower())
        else:
            self.format_combo.setCurrentText("wav")
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        format_layout.addRow("Output Format:", self.format_combo)

        # Sample rate
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems([
            "8000", "16000", "22050", "24000", "44100", "48000", "96000", "192000"
        ])
        saved_sample_rate = str(self.saved_settings.get("sample_rate", "44100"))
        self.sample_rate_combo.setCurrentText(saved_sample_rate)
        format_layout.addRow("Sample Rate (Hz):", self.sample_rate_combo)

        # Channels
        self.channels_combo = QComboBox()
        self.channels_combo.addItems(["Stereo", "Mono"])
        saved_channels = "Stereo" if self.saved_settings.get("channels", 2) == 2 else "Mono"
        self.channels_combo.setCurrentText(saved_channels)
        format_layout.addRow("Channels:", self.channels_combo)

        # Quality/Compression (for MP3, OGG)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Low (128 kbps)", "Medium (192 kbps)", "High (320 kbps)"])
        quality_map_reverse = {"low": "Low (128 kbps)", "medium": "Medium (192 kbps)", "high": "High (320 kbps)"}
        saved_quality = quality_map_reverse.get(self.saved_settings.get("quality", "medium"), "Medium (192 kbps)")
        self.quality_combo.setCurrentText(saved_quality)
        self.quality_label = QLabel("Quality/Bitrate:")
        format_layout.addRow(self.quality_label, self.quality_combo)

        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # Output settings group
        output_group = QGroupBox("Output Settings")
        output_layout = QVBoxLayout()

        # Output folder
        folder_layout = QHBoxLayout()
        self.folder_edit = QLineEdit()
        self.folder_edit.setPlaceholderText("Select output folder...")
        saved_output_folder = self.saved_settings.get("output_folder", "")
        if saved_output_folder:
            self.folder_edit.setText(saved_output_folder)
        self.folder_button = QPushButton("Browse...")
        self.folder_button.clicked.connect(self._browse_folder)
        folder_layout.addWidget(QLabel("Output Folder:"))
        folder_layout.addWidget(self.folder_edit, 1)
        folder_layout.addWidget(self.folder_button)
        output_layout.addLayout(folder_layout)

        # Filename
        filename_layout = QHBoxLayout()
        self.filename_edit = QLineEdit()
        saved_filename = self.saved_settings.get("filename", "concatenated")
        self.filename_edit.setText(saved_filename)
        self.filename_edit.setPlaceholderText("Enter filename...")
        filename_layout.addWidget(QLabel("Filename:"))
        filename_layout.addWidget(self.filename_edit, 1)
        output_layout.addLayout(filename_layout)

        # Info label
        info_label = QLabel("File will be named: filename.ext")
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        output_layout.addWidget(info_label)

        output_group.setLayout(output_layout)
        layout.addWidget(output_group)

        # Processing options group
        options_group = QGroupBox("Processing Options")
        options_layout = QVBoxLayout()

        # Silence duration spinner
        silence_layout = QHBoxLayout()
        silence_label = QLabel("Trim each split and insert unified silence of")
        self.silence_spinbox = QSpinBox()
        self.silence_spinbox.setRange(1, 1000)
        saved_silence = self.saved_settings.get("silence_duration", 500)
        self.silence_spinbox.setValue(saved_silence)
        self.silence_spinbox.setSuffix(" ms")
        silence_layout.addWidget(silence_label)
        silence_layout.addWidget(self.silence_spinbox)
        silence_layout.addStretch()
        options_layout.addLayout(silence_layout)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        self.concat_button = QPushButton("Concatenate")
        self.concat_button.clicked.connect(self._on_concat)
        self.concat_button.setDefault(True)
        button_layout.addWidget(self.concat_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Initial state update
        self._on_format_changed(self.format_combo.currentText())

    def _on_format_changed(self, format_name: str):
        """Handle format change event."""
        compressed_formats = ["mp3", "ogg"]
        is_compressed = format_name in compressed_formats

        self.quality_label.setVisible(is_compressed)
        self.quality_combo.setVisible(is_compressed)

    def _browse_folder(self):
        """Open folder browser dialog."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            "",
            QFileDialog.Option.ShowDirsOnly
        )

        if folder:
            self.folder_edit.setText(folder)

    def _on_concat(self):
        """Handle concatenate button click."""
        if not self.folder_edit.text():
            QMessageBox.warning(
                self,
                "Invalid Settings",
                "Please select an output folder."
            )
            return

        if not self.filename_edit.text():
            QMessageBox.warning(
                self,
                "Invalid Settings",
                "Please enter a filename."
            )
            return

        quality_map = {
            "Low (128 kbps)": "low",
            "Medium (192 kbps)": "medium",
            "High (320 kbps)": "high"
        }
        quality = quality_map[self.quality_combo.currentText()]

        channels = 2 if self.channels_combo.currentText() == "Stereo" else 1

        self.concat_settings = {
            "format": self.format_combo.currentText(),
            "sample_rate": int(self.sample_rate_combo.currentText()),
            "channels": channels,
            "quality": quality,
            "output_folder": self.folder_edit.text(),
            "filename": self.filename_edit.text(),
            "silence_duration": self.silence_spinbox.value()
        }

        self.accept()

    def get_concat_settings(self) -> Dict[str, Any]:
        """Get the configured concatenation settings."""
        return self.concat_settings
