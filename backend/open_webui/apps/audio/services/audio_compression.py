import os
import subprocess
from typing import Tuple

class AudioCompressionService:
    def __init__(self):
        """
        AudioCompressionService constructor.
        
        Constructor - No state required for this service
        """

    def compress_audio(self, file_path: str, target_size: int, remove_silence: bool = False, silence_duration: int = 3) -> tuple[str, str]:
        """
        Compress the given audio file and optionally remove silence if the file size exceeds the target size.

        :param file_path: Path to the audio file to be compressed.
        :param target_size: Maximum file size in bytes.
        :param remove_silence: Boolean to remove silence or not.
        :param silence_duration: Duration of silence (in seconds) to remove if remove_silence is True.
        :return: (new_file_path, new_file_name)
        """
        original_size = os.path.getsize(file_path)
        print(f"Original size: {original_size} bytes")

        # If the file is already smaller than the target size, return it as is
        if original_size <= target_size:
            print("No compression needed.")
            return file_path, os.path.basename(file_path)

        # Define compressed file path
        compressed_file_path = f"{os.path.splitext(file_path)[0]}_compressed.mp3"

        # Start preparing the FFmpeg command
        ffmpeg_command = ['ffmpeg', '-i', file_path, '-y']  # '-y' overwrites the output file

        # Add the silence removal filter if requested
        if remove_silence:
            silence_filter = f"silenceremove=start_periods=1:start_duration={silence_duration}:start_threshold=-50dB"
            ffmpeg_command.extend(['-af', silence_filter])

        # Set compression bitrate
        ffmpeg_command.extend(['-b:a', '64k', compressed_file_path])

        try:
            # Execute FFmpeg command
            subprocess.run(ffmpeg_command, check=True)
            compressed_size = os.path.getsize(compressed_file_path)
            print(f"Compressed size: {compressed_size} bytes")

            # Check if the compression was successful
            if compressed_size <= target_size:
                print(f"Compression successful. File saved at: {compressed_file_path}")
                return compressed_file_path, os.path.basename(compressed_file_path)
            else:
                print("Compressed file still exceeds the target size.")
                os.remove(compressed_file_path)
        except subprocess.CalledProcessError as e:
            print(f"FFmpeg error: {e}")
            raise RuntimeError(f"Compression failed due to FFmpeg error: {e}")

        # If compression fails, return the original file path
        print("Compression not successful or not needed. Returning original file.")
        return file_path, os.path.basename(file_path)
