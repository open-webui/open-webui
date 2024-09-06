import os
from pydub import AudioSegment

def compress_audio(file_path, target_size):
    # Load the audio file
    audio = AudioSegment.from_file(file_path)
    
    # Get the original file size
    original_size = os.path.getsize(file_path)
    print(f"Original size: {original_size} bytes")
    
    # If the file is already smaller than the target size, no compression is needed
    if original_size <= target_size:
        print("No compression needed.")
        return file_path, os.path.basename(file_path)

    # Define the path for the compressed file
    compressed_file_path = f"{os.path.splitext(file_path)[0]}_compressed.mp3"
    
    # Start with a medium quality (64kbps) and gradually reduce
    for bitrate in [64, 32, 16]:
        audio.export(compressed_file_path, format="mp3", bitrate=f"{bitrate}k")
        compressed_size = os.path.getsize(compressed_file_path)
        print(f"Compressed size at {bitrate}kbps: {compressed_size} bytes")
        
        if compressed_size <= target_size:
            print(f"Compression successful at {bitrate}kbps. File saved at: {compressed_file_path}")
            return compressed_file_path, os.path.basename(compressed_file_path)
    
    # If we've tried all bitrates and still can't meet the target size
    print("Could not compress to target size. Returning original file.")
    if os.path.exists(compressed_file_path):
        os.remove(compressed_file_path)
    return file_path, os.path.basename(file_path)
