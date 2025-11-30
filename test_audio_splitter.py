#!/usr/bin/env python3
"""
Test script for Audio Splitter application.
Validates core functionality without requiring GUI interaction.
"""

import numpy as np
import soundfile as sf
import os
import tempfile
from audio_processor import AudioProcessor
from marker_manager import MarkerManager


def create_test_audio(filename, duration=10.0, sample_rate=44100):
    """Create a test audio file with some tone."""
    print(f"Creating test audio file: {filename}")
    
    # Generate a simple tone (440 Hz sine wave)
    t = np.linspace(0, duration, int(duration * sample_rate))
    
    # Add multiple tones and some silence
    audio = np.zeros_like(t)
    
    # Tone 1: 0-3 seconds (440 Hz)
    mask1 = (t >= 0) & (t < 3)
    audio[mask1] = 0.5 * np.sin(2 * np.pi * 440 * t[mask1])
    
    # Silence: 3-4 seconds
    
    # Tone 2: 4-7 seconds (880 Hz)
    mask2 = (t >= 4) & (t < 7)
    audio[mask2] = 0.5 * np.sin(2 * np.pi * 880 * t[mask2])
    
    # Silence: 7-8 seconds
    
    # Tone 3: 8-10 seconds (220 Hz)
    mask3 = (t >= 8) & (t <= 10)
    audio[mask3] = 0.5 * np.sin(2 * np.pi * 220 * t[mask3])
    
    # Save as WAV
    sf.write(filename, audio, sample_rate)
    print(f"  ✓ Created {duration}s test audio at {sample_rate} Hz")


def test_audio_loading():
    """Test audio loading functionality."""
    print("\n--- Test 1: Audio Loading ---")
    
    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
        test_file = tmp.name
    
    try:
        # Create test audio
        create_test_audio(test_file)
        
        # Load audio
        processor = AudioProcessor()
        success, message = processor.load_audio(test_file)
        
        assert success, f"Failed to load audio: {message}"
        assert processor.duration > 0, "Duration should be > 0"
        assert processor.sample_rate > 0, "Sample rate should be > 0"
        assert processor.audio_data is not None, "Audio data should not be None"
        
        print(f"  ✓ Audio loaded successfully")
        print(f"    Duration: {processor.duration:.2f}s")
        print(f"    Sample rate: {processor.sample_rate} Hz")
        print(f"    Channels: {processor.channels}")
        
        return processor, test_file
        
    except Exception as e:
        if os.path.exists(test_file):
            os.remove(test_file)
        raise e


def test_waveform_generation(processor):
    """Test waveform data generation."""
    print("\n--- Test 2: Waveform Generation ---")
    
    waveform = processor.get_waveform_data(samples_per_pixel=100)
    
    assert len(waveform) > 0, "Waveform data should not be empty"
    assert waveform.shape[1] == 2, "Waveform should have min/max pairs"
    
    print(f"  ✓ Waveform generated successfully")
    print(f"    Shape: {waveform.shape}")
    print(f"    Min value: {np.min(waveform):.3f}")
    print(f"    Max value: {np.max(waveform):.3f}")


def test_silence_detection(processor):
    """Test silence detection."""
    print("\n--- Test 3: Silence Detection ---")
    
    silent_regions = processor.detect_silence(threshold_db=-40.0, min_silence_duration=0.5)
    
    print(f"  ✓ Detected {len(silent_regions)} silent regions:")
    for i, (start, end) in enumerate(silent_regions):
        print(f"    Region {i+1}: {start:.2f}s - {end:.2f}s (duration: {end-start:.2f}s)")
    
    assert len(silent_regions) > 0, "Should detect at least one silent region"
    
    return silent_regions


def test_marker_management():
    """Test marker management."""
    print("\n--- Test 4: Marker Management ---")
    
    manager = MarkerManager()
    
    # Add markers
    manager.add_marker(5.0)
    manager.add_marker(10.5)
    manager.add_marker(15.3)
    
    markers = manager.get_markers()
    assert len(markers) == 3, "Should have 3 markers"
    assert markers == [5.0, 10.5, 15.3], "Markers should be sorted"
    
    print(f"  ✓ Added 3 markers: {markers}")
    
    # Move marker
    success = manager.move_marker(10.5, 12.0)
    assert success, "Should successfully move marker"
    assert 12.0 in manager.get_markers(), "Marker should be at new position"
    
    print(f"  ✓ Moved marker from 10.5s to 12.0s")
    
    # Remove marker
    success = manager.remove_marker(5.0)
    assert success, "Should successfully remove marker"
    assert len(manager.get_markers()) == 2, "Should have 2 markers after removal"
    
    print(f"  ✓ Removed marker at 5.0s")
    
    return manager


def test_marker_persistence(manager):
    """Test marker save/load to JSON."""
    print("\n--- Test 5: Marker Persistence ---")
    
    with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
        json_file = tmp.name
    
    try:
        # Set audio filename
        manager.set_audio_filename("test_audio.wav")
        
        # Save markers
        success, message = manager.save_to_json(json_file)
        assert success, f"Failed to save markers: {message}"
        print(f"  ✓ Saved markers to JSON")
        
        # Load markers
        new_manager = MarkerManager()
        success, message, audio_filename = new_manager.load_from_json(json_file)
        assert success, f"Failed to load markers: {message}"
        assert audio_filename == "test_audio.wav", "Audio filename should match"
        assert new_manager.get_markers() == manager.get_markers(), "Markers should match"
        
        print(f"  ✓ Loaded markers from JSON")
        print(f"    Audio file: {audio_filename}")
        print(f"    Markers: {new_manager.get_markers()}")
        
    finally:
        if os.path.exists(json_file):
            os.remove(json_file)


def test_export_splits(processor, test_file):
    """Test exporting audio splits."""
    print("\n--- Test 6: Export Splits ---")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create markers at silent regions
        markers = [3.5, 7.5]
        
        # Export splits
        success, message = processor.export_splits(
            split_times=markers,
            output_folder=tmpdir,
            filename_prefix="test_split",
            output_format="wav",
            sample_rate=44100,
            channels=1,
            quality="high",
            trim_silence=False
        )
        
        assert success, f"Failed to export splits: {message}"
        print(f"  ✓ {message}")
        
        # Check output files
        output_files = sorted([f for f in os.listdir(tmpdir) if f.endswith('.wav')])
        assert len(output_files) == 3, f"Should have 3 split files, got {len(output_files)}"
        
        print(f"  ✓ Generated {len(output_files)} files:")
        for filename in output_files:
            filepath = os.path.join(tmpdir, filename)
            data, sr = sf.read(filepath)
            duration = len(data) / sr
            print(f"    {filename}: {duration:.2f}s")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Audio Splitter - Functionality Tests")
    print("=" * 60)
    
    try:
        # Test 1: Load audio
        processor, test_file = test_audio_loading()
        
        # Test 2: Generate waveform
        test_waveform_generation(processor)
        
        # Test 3: Detect silence
        test_silence_detection(processor)
        
        # Test 4: Marker management
        manager = test_marker_management()
        
        # Test 5: Marker persistence
        test_marker_persistence(manager)
        
        # Test 6: Export splits
        test_export_splits(processor, test_file)
        
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nThe Audio Splitter application is working correctly.")
        print("Run 'python main.py' to start the GUI application.")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
