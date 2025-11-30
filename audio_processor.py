"""
Audio processing module for loading, analyzing, and exporting audio files.
"""

import numpy as np
import librosa
import soundfile as sf
from pydub import AudioSegment
from typing import List, Tuple, Optional
import os


class AudioProcessor:
    """Handles all audio processing operations."""
    
    def __init__(self):
        self.audio_data: Optional[np.ndarray] = None
        self.sample_rate: int = 44100
        self.duration: float = 0.0
        self.channels: int = 1
        self.filepath: Optional[str] = None
        
    def load_audio(self, filepath: str) -> Tuple[bool, str]:
        """
        Load an audio file.
        
        Args:
            filepath: Path to the audio file
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Load audio file with librosa
            self.audio_data, self.sample_rate = librosa.load(
                filepath, 
                sr=None,  # Preserve original sample rate
                mono=False  # Preserve stereo if present
            )
            
            # Handle stereo vs mono
            if len(self.audio_data.shape) == 1:
                self.channels = 1
            else:
                self.channels = self.audio_data.shape[0]
                
            self.duration = len(self.audio_data.T if self.channels > 1 else self.audio_data) / self.sample_rate
            self.filepath = filepath
            
            return True, f"Loaded successfully: {os.path.basename(filepath)}"
            
        except Exception as e:
            return False, f"Error loading audio: {str(e)}"
    
    def get_waveform_data(self, samples_per_pixel: int = 100) -> np.ndarray:
        """
        Generate downsampled waveform data for visualization.
        
        Args:
            samples_per_pixel: Number of audio samples per display pixel
            
        Returns:
            Array of waveform data (min, max pairs for each pixel)
        """
        if self.audio_data is None:
            return np.array([])
        
        # Convert to mono for visualization if stereo
        if self.channels > 1:
            audio_mono = np.mean(self.audio_data, axis=0)
        else:
            audio_mono = self.audio_data
            
        # Calculate number of pixels needed
        num_pixels = len(audio_mono) // samples_per_pixel
        
        # Reshape and get min/max for each pixel
        waveform = []
        for i in range(num_pixels):
            start = i * samples_per_pixel
            end = start + samples_per_pixel
            chunk = audio_mono[start:end]
            waveform.append([np.min(chunk), np.max(chunk)])
            
        return np.array(waveform)
    
    def detect_silence(
        self, 
        threshold_db: float = -40.0, 
        min_silence_duration: float = 0.5
    ) -> List[Tuple[float, float]]:
        """
        Detect silent regions in the audio.
        
        Args:
            threshold_db: Silence threshold in decibels
            min_silence_duration: Minimum duration of silence in seconds
            
        Returns:
            List of (start_time, end_time) tuples for silent regions
        """
        if self.audio_data is None:
            return []
        
        # Convert to mono for silence detection
        if self.channels > 1:
            audio_mono = np.mean(self.audio_data, axis=0)
        else:
            audio_mono = self.audio_data
        
        # Calculate RMS energy in frames
        frame_length = 2048
        hop_length = 512
        
        rms = librosa.feature.rms(
            y=audio_mono, 
            frame_length=frame_length, 
            hop_length=hop_length
        )[0]
        
        # Convert to dB
        rms_db = librosa.amplitude_to_db(rms, ref=np.max)
        
        # Find frames below threshold
        silent_frames = rms_db < threshold_db
        
        # Convert frames to time
        times = librosa.frames_to_time(
            np.arange(len(rms)), 
            sr=self.sample_rate, 
            hop_length=hop_length
        )
        
        # Find continuous silent regions
        silent_regions = []
        in_silence = False
        silence_start = 0.0
        
        for i, (is_silent, time) in enumerate(zip(silent_frames, times)):
            if is_silent and not in_silence:
                # Start of silence
                silence_start = time
                in_silence = True
            elif not is_silent and in_silence:
                # End of silence
                silence_end = time
                duration = silence_end - silence_start
                
                if duration >= min_silence_duration:
                    silent_regions.append((silence_start, silence_end))
                
                in_silence = False
        
        # Handle case where audio ends in silence
        if in_silence:
            silence_end = self.duration
            duration = silence_end - silence_start
            if duration >= min_silence_duration:
                silent_regions.append((silence_start, silence_end))
        
        return silent_regions
    
    def export_splits(
        self,
        split_times: List[float],
        output_folder: str,
        filename_prefix: str,
        output_format: str = "wav",
        sample_rate: int = 44100,
        channels: int = 2,
        quality: str = "high",
        trim_silence: bool = False,
        excluded_splits: List[int] = None
    ) -> Tuple[bool, str]:
        """
        Export audio splits to files.
        
        Args:
            split_times: List of split marker times in seconds
            output_folder: Output directory path
            filename_prefix: Prefix for output filenames
            output_format: Output format (mp3, wav, flac, ogg)
            sample_rate: Output sample rate
            channels: 1 for mono, 2 for stereo
            quality: Quality setting for compressed formats
            trim_silence: Whether to trim silence from splits
            excluded_splits: List of split indices to exclude from export (0-based)
            
        Returns:
            Tuple of (success, message)
        """
        if self.audio_data is None:
            return False, "No audio loaded"
        
        try:
            # Create output folder if it doesn't exist
            os.makedirs(output_folder, exist_ok=True)
            
            # Handle excluded splits
            if excluded_splits is None:
                excluded_splits = []
            
            # Sort split times
            split_times = sorted([0.0] + split_times + [self.duration])
            
            # Calculate number of splits (excluding excluded ones)
            num_splits = len(split_times) - 1
            num_exported = num_splits - len(excluded_splits)
            num_digits = len(str(num_exported))
            
            # Track exported count for numbering
            exported_count = 0
            
            # Process each split
            for i in range(num_splits):
                # Skip excluded splits
                if i in excluded_splits:
                    continue
                
                start_time = split_times[i]
                end_time = split_times[i + 1]
                exported_count += 1
                
                # Convert times to samples
                start_sample = int(start_time * self.sample_rate)
                end_sample = int(end_time * self.sample_rate)
                
                # Extract audio segment
                if self.channels > 1:
                    segment = self.audio_data[:, start_sample:end_sample]
                else:
                    segment = self.audio_data[start_sample:end_sample]
                
                # Trim silence if requested
                if trim_silence:
                    segment = self._trim_silence(segment)
                
                # Resample if needed
                if sample_rate != self.sample_rate:
                    segment = librosa.resample(
                        segment, 
                        orig_sr=self.sample_rate, 
                        target_sr=sample_rate
                    )
                
                # Convert to mono/stereo as requested
                if channels == 1 and self.channels > 1:
                    segment = np.mean(segment, axis=0)
                elif channels == 2 and self.channels == 1:
                    segment = np.stack([segment, segment])
                
                # Generate filename using exported count
                split_number = str(exported_count).zfill(num_digits)
                filename = f"{filename_prefix}_{split_number}.{output_format}"
                output_path = os.path.join(output_folder, filename)
                
                # Export based on format
                self._export_audio(
                    segment, 
                    output_path, 
                    output_format, 
                    sample_rate, 
                    quality
                )
            
            excluded_msg = f" ({len(excluded_splits)} excluded)" if excluded_splits else ""
            return True, f"Exported {num_exported} splits successfully{excluded_msg}"
            
        except Exception as e:
            return False, f"Error exporting splits: {str(e)}"
    
    def _trim_silence(self, audio: np.ndarray, threshold_db: float = -40.0) -> np.ndarray:
        """Trim silence from the beginning and end of an audio segment."""
        # Convert to mono for analysis if stereo
        if len(audio.shape) > 1:
            audio_mono = np.mean(audio, axis=0)
        else:
            audio_mono = audio
        
        # Calculate energy
        energy = librosa.feature.rms(y=audio_mono, frame_length=2048, hop_length=512)[0]
        energy_db = librosa.amplitude_to_db(energy, ref=np.max)
        
        # Find non-silent regions
        non_silent = energy_db > threshold_db
        
        if not np.any(non_silent):
            return audio
        
        # Find first and last non-silent frames
        non_silent_indices = np.where(non_silent)[0]
        start_frame = non_silent_indices[0]
        end_frame = non_silent_indices[-1]
        
        # Convert to samples
        start_sample = start_frame * 512
        end_sample = (end_frame + 1) * 512
        
        # Trim audio
        if len(audio.shape) > 1:
            return audio[:, start_sample:end_sample]
        else:
            return audio[start_sample:end_sample]
    
    def _export_audio(
        self, 
        audio: np.ndarray, 
        output_path: str, 
        format: str, 
        sample_rate: int, 
        quality: str
    ):
        """Export audio to file in specified format."""
        # Ensure audio is in the right shape (samples, channels) for soundfile
        if len(audio.shape) == 1:
            audio_export = audio
        else:
            audio_export = audio.T
        
        if format == "wav":
            # Direct export with soundfile
            sf.write(output_path, audio_export, sample_rate, subtype='PCM_16')
            
        elif format == "flac":
            # Export as FLAC
            sf.write(output_path, audio_export, sample_rate, format='FLAC')
            
        else:
            # For MP3 and OGG, use pydub
            # First save as temporary WAV
            temp_wav = output_path + ".temp.wav"
            sf.write(temp_wav, audio_export, sample_rate, subtype='PCM_16')
            
            # Load with pydub and convert
            audio_segment = AudioSegment.from_wav(temp_wav)
            
            # Set quality/bitrate
            bitrate_map = {
                "low": "128k",
                "medium": "192k",
                "high": "320k"
            }
            bitrate = bitrate_map.get(quality, "192k")
            
            # Export in desired format
            if format == "mp3":
                audio_segment.export(output_path, format="mp3", bitrate=bitrate)
            elif format == "ogg":
                audio_segment.export(output_path, format="ogg", codec="libvorbis", bitrate=bitrate)
            
            # Remove temporary file
            os.remove(temp_wav)
