import os
import subprocess
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play

def text_to_audio(text, lang='en', save=False, filename="output.mp3"):
    """
    Converts text to audio, plays it by default using VLC via subprocess, and optionally saves it to a file.
    """
    try:
        # Convert text to speech using gTTS
        tts = gTTS(text=text, lang=lang)

        if save:
            # Save the converted audio to a file
            tts.save(filename)
            print(f"Saved the audio file as {filename}")
        else:
            # Save to a temporary file
            temp_filename = "/home/csseiot/Desktop/workplace/temp_audio.mp3"
            tts.save(temp_filename)

            # Play the audio using subprocess and VLC
            # subprocess.run(["cvlc", "--play-and-exit", temp_filename])
            # Load the audio file
            song = AudioSegment.from_mp3(temp_filename)

            # Play the audio file
            play(song)

            # Remove the temporary file after playback
            os.remove(temp_filename)
            print("Audio played successfully")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Example usage
    text = "Hello, welcome to the world of text-to-speech!"
    text_to_audio(text, lang='en')

