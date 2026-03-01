# mp3probe.py
# This utility extracts information from an MP3 file

import sys
import os
import argparse
import subprocess
import json


def format_duration(seconds):
    """
    Converts duration from seconds to HH:MM:SS format.
    """
    hours = int(seconds // 3600)
    seconds %= 3600
    minutes = int(seconds // 60)
    seconds %= 60
    remaining_seconds = int(seconds)
    return f"{hours:02d}:{minutes:02d}:{remaining_seconds:02d}"


def detect_mp3_codification_manually(file_path, max_frames=50):
    """
    Detect MP3 bitrate mode manually.
    """
    BITRATE_TABLE = {
        (1, 3): [None, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
        (2, 3): [None, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
    }
    SAMPLE_RATE_TABLE = {
        0: [44100, 22050],
        1: [48000, 24000],
        2: [32000, 16000],
    }

    def parse_header(header):
        if len(header) < 4 or header[0] != 0xFF or (header[1] & 0xE0) != 0xE0:
            return None
        version_id = (header[1] >> 3) & 0x03
        layer = (header[1] >> 1) & 0x03
        bitrate_index = (header[2] >> 4) & 0x0F
        sample_rate_index = (header[2] >> 2) & 0x03
        padding = (header[2] >> 1) & 0x01

        if version_id == 1 or layer != 1 or bitrate_index in [0, 15] or sample_rate_index == 3:
            return None

        version = 2 if version_id == 2 else 1
        bitrate = BITRATE_TABLE.get((version, 3), [None]*15)[bitrate_index]
        sample_rate = SAMPLE_RATE_TABLE.get(sample_rate_index, [None, None])[version - 1]
        frame_size = int((144000 * bitrate) // sample_rate + padding)
        return bitrate, frame_size

    with open(file_path, 'rb') as f:
        # Skip ID3 header if it exists
        if f.read(3) == b'ID3':
            f.seek(3, 1)
            size_bytes = f.read(4)
            tag_size = sum((b & 0x7F) << (7 * (3 - i)) for i, b in enumerate(size_bytes))
            f.seek(tag_size, 1)

        bitrates = []
        while len(bitrates) < max_frames:
            pos = f.tell()
            header = f.read(4)
            result = parse_header(header)
            if result:
                bitrate, frame_size = result
                bitrates.append(bitrate)
                f.seek(frame_size - 4, 1)
            else:
                f.seek(pos + 1)

        if not bitrates:
            return "No valid frames were found"
        if all(b == bitrates[0] for b in bitrates):
            return "CBR (Constant Bitrate)"
        elif len(set(bitrates)) <= 3:
            return "ABR (Average Bitrate)"
        else:
            return "VBR (Variable Bitrate)"


def detect_mp3_codification(file_path, info, max_frames=50):
    """
    Detect MP3 bitrate mode.
    """
    stream = next((s for s in info.get('streams', []) if s.get('codec_name') == 'mp3'), {})
    format_info = info.get('format', {})
    tags = format_info.get('tags', {})
    encoder = tags.get('encoder', '').lower()
    bit_rate_stream = stream.get('bit_rate')
    bit_rate_format = format_info.get('bit_rate')
    codec_tag = stream.get('codec_tag_string', '').lower()
    mp3_mode = stream.get('mp3_mode', '').lower()  # ffprobe may include this in recent versions

    # Additional heuristics
    if 'vbr' in encoder or 'xing' in encoder or mp3_mode == 'vbr':
        return 'VBR (Variable Bitrate)'
    elif 'abr' in encoder or mp3_mode == 'abr':
        return 'ABR (Average Bitrate)'
    elif mp3_mode == 'cbr':
        return 'CBR (Constant Bitrate)'
    elif bit_rate_stream and bit_rate_format and bit_rate_stream == bit_rate_format:
        return 'CBR (Constant Bitrate)'
    elif codec_tag == '0x0055' and not encoder:
        return 'Probably CBR (without encoder metadata)'
    else:
        return detect_mp3_codification_manually(file_path, max_frames)


def get_mp3_mode_from_header(filepath):
    with open(filepath, "rb") as f:
        header = f.read(10)

        # Detect ID3v2 header
        if header[0:3] == b"ID3":
            # ID3v2 size is in the last 4 bytes (syncsafe)
            size_bytes = header[6:10]
            tag_size = (
                (size_bytes[0] & 0x7F) << 21 |
                (size_bytes[1] & 0x7F) << 14 |
                (size_bytes[2] & 0x7F) << 7  |
                (size_bytes[3] & 0x7F)
            )
            # Skip header + tag
            f.seek(10 + tag_size)
        else:
            # No ID3v2, back to top
            f.seek(0)

        # Read MPEG frame
        frame = f.read(4)
        if len(frame) < 4:
            return "File too small"

        b1, b2, b3, b4 = frame

        # Check sync bits (first 11 bits = 1)
        if not (b1 == 0xFF and (b2 & 0xE0) == 0xE0):
            return "No valid MPEG frame was found"

        # Extract bits 7 and 6 from the fourth byte
        mode_bits = (b4 >> 6) & 0b11

        modes = {
            0: "Stereo",
            1: "Joint Stereo",
            2: "Dual Channel",
            3: "Mono"
        }

        return modes.get(mode_bits, "Unknown")


def describe_channel_layout(layout):
    # Table of standard layouts and their meaning
    standard_layouts = {
        "mono": "Mono (1 channel)",
        "stereo": "Stereo (2 channels: FL, FR)",
        "2.1": "2.1 (3 channels: FL, FR, LFE)",
        "3.0": "3.0 (3 channels: FL, FR, FC)",
        "4.0": "4.0 (4 channels: FL, FR, FC, BC)",
        "5.0": "5.0 (5 channels: FL, FR, FC, SL, SR)",
        "5.1": "5.1 Surround (6 channels: FL, FR, FC, LFE, SL, SR)",
        "6.1": "6.1 (7 channels: FL, FR, FC, LFE, SL, SR, BC)",
        "7.1": "7.1 Surround (8 channels: FL, FR, FC, LFE, SL, SR, BL, BR)",
    }

    # If it's a standard layout, return it directly
    if layout in standard_layouts:
        return standard_layouts[layout]

    # If it is N/A or empty
    if layout in (None, "", "N/A"):
        return "Layout not specified"

    # If it is a channel list type FL+FR+FC+LFE
    if "+" in layout:
        channels = layout.split("+")
        return f"Custom layout ({len(channels)} channels: {', '.join(channels)})"

    # If it doesn't match anything known
    return f"Unknown layout: {layout}"


def get_file_data(file_path):
    """
    Extracts information from an MP3 file
    using the ffprobe application.
    """
    command = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        data = json.loads(result.stdout)
        return data
    except FileNotFoundError:
        print("Error: 'ffprobe' not found. Please ensure FFmpeg is installed and in your PATH.")
        sys.exit(1)
    except (subprocess.CalledProcessError, json.JSONDecodeError):
        print("Error: Failed to analyze file with ffprobe.")
        sys.exit(1)


def get_mp3_tech_info(file_path, data):
    """
    Extracts technical audio information
    from data obtained using the ffprobe application.
    """
    # Extract data from the first audio stream
    audio_stream = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    format_info = data.get("format", {})

    if audio_stream:
        encoder = audio_stream.get("tags", {}).get("encoder", "N/A")
        file_size = int(format_info.get("size", 0))
        bitrate = int(audio_stream.get("bit_rate", 0)) // 1000
        sample_rate = int(audio_stream.get("sample_rate", 0))
        duration_formatted = format_duration(float(format_info.get("duration", 0)))
        duration_seconds = float(format_info.get("duration", 0))
        channel_layout = describe_channel_layout(audio_stream.get("channel_layout", "N/A"))
        channel_mode = get_mp3_mode_from_header(file_path)
        channels = int(audio_stream.get("channels", 0))
        # Bit Rate Type (CBR, VBR, ABR)
        bitrate_mode = detect_mp3_codification(file_path, data)

        return {
            "Codec": audio_stream.get("codec_name"),
            "Codec Type": audio_stream.get("codec_type"),
            "Codec Long Name": audio_stream.get("codec_long_name"),
            "Encoder (Code)": encoder,
            "Size": f"{file_size/1024:.2f} KB ({file_size} bytes)",
            "Bitrate": f"{bitrate} kbps",
            "Sample Rate": f"{sample_rate} Hz",
            "Duration": f"{duration_formatted} ({duration_seconds:.2f} seconds)",
            "Bitrate Type": f"{bitrate_mode}",
            "Channel Layout": channel_layout,
            "Channel Mode": channel_mode,
            "Channels": channels
        }

    else:
        return {"Error": "No audio stream found in the file"}


def get_mp3_metadata(data):
    """
    Extracts metadata information (ID3 Tags)
    from data obtained using the ffprobe application.
    """
    # Extract data from tags
    format_info = data.get("format", {})

    if format_info:
        return {
            "Title": format_info.get("tags", {}).get("title", "N/A"),
            "Artist": format_info.get("tags", {}).get("artist", "N/A"),
            "Album": format_info.get("tags", {}).get("album", "N/A"),
            "Album artist": format_info.get("tags", {}).get("album_artist", "N/A"),
            "Year": format_info.get("tags", {}).get("date", "N/A"),
            "Genre": format_info.get("tags", {}).get("genre", "N/A"),
            "Track Number": format_info.get("tags", {}).get("track", 0),
            "Disc Number": format_info.get("tags", {}).get("disc", 0),
            "Composer": format_info.get("tags", {}).get("composer", "N/A"),
            "Comment": format_info.get("tags", {}).get("comment", "N/A"),
            "Encoded by": format_info.get("tags", {}).get("encoded_by", "N/A")
        }
    else:
        return {"Error": "Tags not found in the file"}


def get_info_lyrics(data):
    """
    Extracts lyrics
    from data obtained using the ffprobe application.
    """
    tags = data.get("format", {}).get("tags", {})
    if not tags:
        return {"Lyrics": "N/A"}

    # Search for keywords that contain "lyrics"
    for key, value in tags.items():
        if key.lower().startswith("lyrics"):
            return {"Lyrics": value}

    return {"Lyrics": "N/A"}


def get_info_cover(file_path, data):
    """
    Retrieves information from the image embedded in an MP3.
    - MIME type
    - Size in KB
    - Width and height
    """

    # Find the stream that contains the embedded image, stream type "attached_pic"
    stream_img = next(
        (
            s for s in data.get("streams", [])
            if s.get("codec_type") == "video"
            and s.get("disposition", {}).get("attached_pic") == 1
        ),
        None
    )

    if not stream_img:
        return {"Embedded Image": "Not found"}

    # Standardized MIME
    codec = stream_img.get("codec_name", "N/A")
    mime_type = f"image/{'jpeg' if codec == 'mjpeg' else codec}"

    # Extract the image to memory
    process = subprocess.run(
        [
            "ffmpeg",
            "-i", file_path,
            "-an",
            "-vcodec", "copy",
            "-f", "image2pipe",
            "-vframes", "1",
            "pipe:1"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    img_data = process.stdout
    if not img_data:
        return {"Embedded Image": "Not found"}

    size = f"{len(img_data) / 1024:.2f} KB"

    return {
        "MIME Type": mime_type,
        "Size": size,
        "Width": stream_img.get("width", "N/A"),
        "Height": stream_img.get("height", "N/A")
    }


def print_content(variable):
    """
    Prints the content of a dictionary.
    """

    for key, value in variable.items():
        print(f"{key.ljust(15)}: {value}")


def print_raw_data(data):
    """
    Prints the metadata in JSON format.
    """
    print("\nRAW DATA")
    print("-" * 8)
    print(json.dumps(data, indent=2))
    print("-" * 30)


def get_mp3_info(file_path, debug=False):
    """
    Extracts and displays technical audio information and ID3 metadata
    from an MP3 file using the ffprobe application.
    """
    print(f"\n{'='*50}")
    print(f"   📋 ANALYZING FILE: {os.path.basename(file_path)}")
    print(f"{'='*50}\n")

    data = get_file_data(file_path)  # Read data using ffprobe application

    if debug:
        print_raw_data(data)

    print("\n🔊 TECHNICAL AUDIO INFORMATION")
    print("-" * 30)

    tech_info = get_mp3_tech_info(file_path, data)
    print_content(tech_info)

    print("\n📝 METADATA (ID3 TAGS)")
    print("-" * 22)

    tags = get_mp3_metadata(data)
    print_content(tags)

    print(f"\nLyrics:")
    lyrics = get_info_lyrics(data)
    print_content(lyrics)

    print("\nAlbum Art - Embedded Image:")
    cover_info = get_info_cover(file_path, data)
    print_content(cover_info)

    print(f"\n{'='*50}\n")


if __name__ == "__main__":
    # Command-line argument parser setup
    parser = argparse.ArgumentParser(
        description="Extracts and displays technical information and ID3 metadata from an MP3 file."
    )
    parser.add_argument(
        "mp3_file", 
        type=str, 
        help="The full path to the MP3 file to analyze."
    )
    parser.add_argument(
        "-d", "--debug",
        action="store_true",
        help="Print raw JSON data from ffprobe."
    )
    
    args = parser.parse_args()
    
    mp3_file = args.mp3_file
    
    if not os.path.exists(mp3_file):
        print(f"❌ Error: The file '{mp3_file}' was not found.")
        sys.exit(1)

    get_mp3_info(mp3_file, args.debug)
