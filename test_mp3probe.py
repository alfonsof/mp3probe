import unittest
from unittest.mock import patch, MagicMock
import mp3probe

class TestMp3Probe(unittest.TestCase):

    def test_format_duration(self):
        """Tests formatting seconds to HH:MM:SS"""
        self.assertEqual(mp3probe.format_duration(3661), "01:01:01")
        self.assertEqual(mp3probe.format_duration(65), "00:01:05")
        self.assertEqual(mp3probe.format_duration(0), "00:00:00")
        self.assertEqual(mp3probe.format_duration(3599), "00:59:59")

    def test_describe_channel_layout(self):
        """Tests channel layout description"""
        self.assertEqual(mp3probe.describe_channel_layout("stereo"), "Stereo (2 channels: FL, FR)")
        self.assertEqual(mp3probe.describe_channel_layout("mono"), "Mono (1 channel)")
        self.assertEqual(mp3probe.describe_channel_layout("5.1"), "5.1 Surround (6 channels: FL, FR, FC, LFE, SL, SR)")
        self.assertEqual(mp3probe.describe_channel_layout("unknown_layout"), "Unknown layout: unknown_layout")
        self.assertEqual(mp3probe.describe_channel_layout(None), "Layout not specified")

    def test_get_mp3_metadata(self):
        """Tests ID3 metadata extraction"""
        mock_data = {
            "format": {
                "tags": {
                    "title": "Test Title",
                    "artist": "Test Artist",
                    "album": "Test Album",
                    "date": "2023",
                    "track": "1",
                    "genre": "Rock"
                }
            }
        }
        result = mp3probe.get_mp3_metadata(mock_data)
        self.assertEqual(result["Title"], "Test Title")
        self.assertEqual(result["Artist"], "Test Artist")
        self.assertEqual(result["Album"], "Test Album")
        self.assertEqual(result["Year"], "2023")
        self.assertEqual(result["Genre"], "Rock")

    def test_get_info_lyrics(self):
        """Tests lyrics extraction"""
        # Case with lyrics
        mock_data_with_lyrics = {
            "format": {
                "tags": {
                    "lyrics": "La la la",
                    "title": "Song"
                }
            }
        }
        self.assertEqual(mp3probe.get_info_lyrics(mock_data_with_lyrics)["Lyrics"], "La la la")

        # Case without lyrics
        mock_data_no_lyrics = {
            "format": {
                "tags": {
                    "title": "Song"
                }
            }
        }
        self.assertEqual(mp3probe.get_info_lyrics(mock_data_no_lyrics)["Lyrics"], "N/A")

    @patch('mp3probe.detect_mp3_codification')
    @patch('mp3probe.get_mp3_mode_from_header')
    def test_get_mp3_tech_info(self, mock_get_mode, mock_detect_codification):
        """Tests technical info extraction mocking file reading functions"""
        
        # Configure mocks to avoid reading real files
        mock_get_mode.return_value = "Joint Stereo"
        mock_detect_codification.return_value = "CBR (Constant Bitrate)"

        # Simulated ffprobe data (parsed JSON)
        mock_data = {
            "streams": [{
                "codec_type": "audio",
                "codec_name": "mp3",
                "codec_long_name": "MP3 (MPEG audio layer 3)",
                "bit_rate": "320000",
                "sample_rate": "44100",
                "channels": 2,
                "channel_layout": "stereo",
                "tags": {"encoder": "LAME"}
            }],
            "format": {
                "size": "5000000",
                "duration": "125.5"
            }
        }

        # Call function with dummy path (mocks prevent usage)
        info = mp3probe.get_mp3_tech_info("dummy_path.mp3", mock_data)

        # Assertions
        self.assertEqual(info["Codec"], "mp3")
        self.assertEqual(info["Bitrate"], "320 kbps")
        self.assertEqual(info["Sample Rate"], "44100 Hz")
        self.assertEqual(info["Duration"], "00:02:05 (125.50 seconds)")
        self.assertEqual(info["Channel Mode"], "Joint Stereo")
        self.assertEqual(info["Bitrate Type"], "CBR (Constant Bitrate)")

if __name__ == '__main__':
    unittest.main()
