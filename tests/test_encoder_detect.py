import unittest
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.encoder_detect import EncoderDetector, CodecType, EncoderVendor, Encoder
from core.ffmpeg_locator import FFmpegLocator


class TestEncoderDetect(unittest.TestCase):
    
    def setUp(self):
        self.ffmpeg = MagicMock(spec=FFmpegLocator)
        self.ffmpeg.is_available.return_value = True
        self.ffmpeg.ffmpeg_path = Path("ffmpeg.exe")
        self.detector = EncoderDetector(self.ffmpeg)
    
    def test_encoder_definitions(self):
        """Test that encoder definitions are properly configured"""
        # Check NVENC encoders
        self.assertIn("h264_nvenc", EncoderDetector.ENCODERS)
        nvenc = EncoderDetector.ENCODERS["h264_nvenc"]
        self.assertEqual(nvenc.codec, CodecType.H264)
        self.assertEqual(nvenc.vendor, EncoderVendor.NVIDIA)
        self.assertTrue(nvenc.is_hardware)
        
        # Check software encoders
        self.assertIn("libx264", EncoderDetector.ENCODERS)
        x264 = EncoderDetector.ENCODERS["libx264"]
        self.assertEqual(x264.codec, CodecType.H264)
        self.assertEqual(x264.vendor, EncoderVendor.SOFTWARE)
        self.assertFalse(x264.is_hardware)
    
    def test_encoder_display_names(self):
        """Test encoder display name generation"""
        nvenc = Encoder(
            "h264_nvenc", CodecType.H264, EncoderVendor.NVIDIA, True,
            ["p1"], ["cbr"]
        )
        self.assertEqual(nvenc.get_display_name(), "H264 (NVENC)")
        
        qsv = Encoder(
            "h264_qsv", CodecType.H264, EncoderVendor.INTEL, True,
            ["fast"], ["cbr"]
        )
        self.assertEqual(qsv.get_display_name(), "H264 (QSV)")
        
        software = Encoder(
            "libx264", CodecType.H264, EncoderVendor.SOFTWARE, False,
            ["fast"], ["crf"]
        )
        self.assertEqual(software.get_display_name(), "H264 (CPU)")
    
    @patch('subprocess.run')
    def test_detect_encoders_with_ffmpeg(self, mock_run):
        """Test encoder detection when FFmpeg is available"""
        # Mock FFmpeg encoder list output
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = """
Encoders:
 V..... h264_nvenc           NVIDIA NVENC H.264 encoder
 V..... hevc_nvenc           NVIDIA NVENC HEVC encoder
 V..... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10
        """
        
        # Mock test encoder to always succeed for software, fail for hardware
        def test_side_effect(*args, **kwargs):
            cmd = args[0]
            if "libx264" in cmd:
                result = MagicMock()
                result.returncode = 0
                return result
            else:
                result = MagicMock()
                result.returncode = 1
                return result
        
        with patch.object(self.detector, '_test_encoder', side_effect=lambda e: "lib" in e):
            encoders = self.detector.detect_encoders()
            
            # Should have at least libx264 (always added as fallback)
            self.assertIn("libx264", encoders)
    
    def test_detect_encoders_without_ffmpeg(self):
        """Test encoder detection when FFmpeg is not available"""
        self.ffmpeg.is_available.return_value = False
        
        encoders = self.detector.detect_encoders()
        
        # Should only have software encoders
        for encoder_name, encoder in encoders.items():
            self.assertEqual(encoder.vendor, EncoderVendor.SOFTWARE)
    
    def test_get_available_by_codec(self):
        """Test getting encoders by codec type"""
        # Manually add some test encoders
        self.detector.available_encoders = {
            "h264_nvenc": EncoderDetector.ENCODERS["h264_nvenc"],
            "hevc_nvenc": EncoderDetector.ENCODERS["hevc_nvenc"],
            "libx264": EncoderDetector.ENCODERS["libx264"]
        }
        self.detector._detected = True
        
        h264_encoders = self.detector.get_available_by_codec(CodecType.H264)
        self.assertEqual(len(h264_encoders), 2)
        
        h265_encoders = self.detector.get_available_by_codec(CodecType.H265)
        self.assertEqual(len(h265_encoders), 1)
        
        av1_encoders = self.detector.get_available_by_codec(CodecType.AV1)
        self.assertEqual(len(av1_encoders), 0)
    
    def test_get_hardware_encoders(self):
        """Test getting hardware encoders only"""
        # Manually add some test encoders
        self.detector.available_encoders = {
            "h264_nvenc": EncoderDetector.ENCODERS["h264_nvenc"],
            "libx264": EncoderDetector.ENCODERS["libx264"]
        }
        self.detector._detected = True
        
        hw_encoders = self.detector.get_hardware_encoders()
        self.assertEqual(len(hw_encoders), 1)
        self.assertEqual(hw_encoders[0].name, "h264_nvenc")
    
    def test_get_best_encoder(self):
        """Test best encoder selection"""
        # Add encoders in non-priority order
        self.detector.available_encoders = {
            "libx264": EncoderDetector.ENCODERS["libx264"],
            "h264_amf": EncoderDetector.ENCODERS["h264_amf"],
            "h264_nvenc": EncoderDetector.ENCODERS["h264_nvenc"]
        }
        self.detector._detected = True
        
        # Should prefer NVIDIA over AMD over software
        best = self.detector.get_best_encoder(CodecType.H264, prefer_hardware=True)
        self.assertEqual(best.name, "h264_nvenc")
        
        # Test with no hardware available
        self.detector.available_encoders = {
            "libx264": EncoderDetector.ENCODERS["libx264"]
        }
        
        best = self.detector.get_best_encoder(CodecType.H264, prefer_hardware=True)
        self.assertEqual(best.name, "libx264")
        
        # Test with no encoders for codec
        best = self.detector.get_best_encoder(CodecType.AV1, prefer_hardware=True)
        self.assertIsNone(best)
    
    @patch('subprocess.run')
    def test_test_encoder(self, mock_run):
        """Test the encoder testing functionality"""
        # Test successful encoder
        mock_run.return_value.returncode = 0
        result = self.detector._test_encoder("h264_nvenc")
        self.assertTrue(result)
        
        # Test failed encoder
        mock_run.return_value.returncode = 1
        result = self.detector._test_encoder("h264_nvenc")
        self.assertFalse(result)
        
        # Test timeout
        mock_run.side_effect = subprocess.TimeoutExpired("cmd", 5)
        result = self.detector._test_encoder("h264_nvenc")
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()