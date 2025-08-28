import unittest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.command_builder import CommandBuilder, RecordingConfig, RateControl, Container
from core.encoder_detect import Encoder, CodecType, EncoderVendor


class TestCommandBuilder(unittest.TestCase):
    
    def setUp(self):
        self.builder = CommandBuilder(Path("ffmpeg.exe"))
        self.config = RecordingConfig()
    
    def test_basic_command(self):
        """Test basic command generation"""
        output = Path("output.mp4")
        cmd = self.builder.build_command(self.config, output)
        
        self.assertIsInstance(cmd, list)
        self.assertEqual(cmd[0], "ffmpeg.exe")
        self.assertIn("-f", cmd)
        self.assertIn("d3d11grab", cmd)
        self.assertIn(str(output), cmd)
    
    def test_video_input_settings(self):
        """Test video input configuration"""
        self.config.fps = 30
        self.config.show_cursor = False
        self.config.region = (100, 200, 1920, 1080)
        
        output = Path("output.mp4")
        cmd = self.builder.build_command(self.config, output)
        
        self.assertIn("-framerate", cmd)
        self.assertIn("30", cmd)
        self.assertIn("-draw_mouse", cmd)
        self.assertIn("0", cmd)
        self.assertIn("-offset_x", cmd)
        self.assertIn("100", cmd)
        self.assertIn("-offset_y", cmd)
        self.assertIn("200", cmd)
        self.assertIn("-video_size", cmd)
        self.assertIn("1920x1080", cmd)
    
    def test_nvenc_encoder(self):
        """Test NVENC encoder settings"""
        self.config.encoder = Encoder(
            "h264_nvenc", CodecType.H264, EncoderVendor.NVIDIA, True,
            ["p1", "p2", "p3", "p4", "p5"], ["cbr", "vbr"]
        )
        self.config.preset = "p5"
        self.config.rate_control = RateControl.CBR
        self.config.bitrate = 10000
        
        output = Path("output.mp4")
        cmd = self.builder.build_command(self.config, output)
        
        self.assertIn("-c:v", cmd)
        self.assertIn("h264_nvenc", cmd)
        self.assertIn("-preset", cmd)
        self.assertIn("p5", cmd)
        self.assertIn("-rc", cmd)
        self.assertIn("cbr", cmd)
        self.assertIn("-b:v", cmd)
        self.assertIn("10000k", cmd)
    
    def test_audio_mixing(self):
        """Test audio mixing configuration"""
        self.config.system_audio_enabled = True
        self.config.system_audio_device = "speakers"
        self.config.mic_enabled = True
        self.config.mic_device = "microphone"
        
        output = Path("output.mp4")
        cmd = self.builder.build_command(self.config, output)
        
        # Check for WASAPI inputs
        self.assertEqual(cmd.count("-f"), 3)  # 1 video + 2 audio
        self.assertEqual(cmd.count("wasapi"), 2)
        
        # Check for filter complex
        self.assertIn("-filter_complex", cmd)
        filter_idx = cmd.index("-filter_complex") + 1
        self.assertIn("amix", cmd[filter_idx])
    
    def test_container_options(self):
        """Test container-specific options"""
        self.config.container = Container.MP4
        
        output = Path("output.mp4")
        cmd = self.builder.build_command(self.config, output)
        
        self.assertIn("-movflags", cmd)
        self.assertIn("+faststart", cmd)
    
    def test_scaling(self):
        """Test video scaling"""
        self.config.scale = (1280, 720)
        
        output = Path("output.mp4")
        cmd = self.builder.build_command(self.config, output)
        
        self.assertIn("-vf", cmd)
        vf_idx = cmd.index("-vf") + 1
        self.assertIn("scale=1280:720", cmd[vf_idx])
    
    def test_software_encoder_fallback(self):
        """Test software encoder fallback"""
        self.config.encoder = None
        self.config.encoder_name = "libx264"
        self.config.rate_control = RateControl.CRF
        self.config.crf = 23
        
        output = Path("output.mp4")
        cmd = self.builder.build_command(self.config, output)
        
        self.assertIn("-c:v", cmd)
        self.assertIn("libx264", cmd)
        self.assertIn("-crf", cmd)
        self.assertIn("23", cmd)


if __name__ == "__main__":
    unittest.main()