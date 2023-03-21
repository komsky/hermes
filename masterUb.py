import logging
from datetime import datetime
import os, os.path
from VoiceActivityDetection import VADAudio
import openai
import requests
from dotenv import load_dotenv
from halo import Halo
import ChatGptClient

logging.basicConfig(level=20)

activation_command = "Hey Hermes!"
load_dotenv()
api_key = os.getenv("CHATGPT_API_KEY")
openai.api_key = api_key

def HermesCommand(text):
    responseFromChat = ChatGptClient.call_chatgpt(text)
    print(responseFromChat)

def main(ARGS):
    # Start audio with VAD
    vad_audio = VADAudio(aggressiveness=ARGS.vad_aggressiveness,
                         device=ARGS.device,
                         input_rate=ARGS.rate,
                         file=ARGS.file)
    print("Listening (ctrl-C to exit)...")
    frames = vad_audio.vad_collector()

    # Stream from microphone using VAD
    spinner = None
    if not ARGS.nospinner:
        spinner = Halo(spinner='line')
    wav_data = bytearray()
    is_next_command_for_hermes = False
    for frame in frames:
        if frame is not None:
            if spinner: spinner.start()
            logging.debug("streaming frame")
            wav_data.extend(frame)
        else:
            if spinner: spinner.stop()
            logging.debug("end utterance")

            date_piece = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f.wav")
            saved_file = os.path.join(ARGS.savewav, f'savewav_{date_piece}')
            vad_audio.write_wav(saved_file, wav_data)
            with open(saved_file, "rb") as audio_file:
                apiResponse = openai.Audio.transcribe("whisper-1", audio_file)
                print("Recognized: %s" % apiResponse.text)
                if(is_next_command_for_hermes):
                    HermesCommand(apiResponse.text)
                is_next_command_for_hermes = IsHermesActivation(apiResponse.text,is_next_command_for_hermes)
                
            if(apiResponse.text == ""):
                os.remove(saved_file)
            else:
                new_filename = f"{apiResponse.text}_{date_piece}"
                new_full_path = os.path.join(ARGS.savewav, new_filename)
                os.rename(saved_file, new_full_path)
            wav_data = bytearray()
def IsHermesActivation(text, last_status):
    if(last_status and text ==""):
        return True
    return text.lower() ==  activation_command.lower()

if __name__ == '__main__':
    DEFAULT_SAMPLE_RATE = 16000

    import argparse
    parser = argparse.ArgumentParser(description="Stream from microphone using VAD and OpenAI Whisper API")

    parser.add_argument('-v', '--vad_aggressiveness', type=int, default=2,
                        help="Set aggressiveness of VAD: an integer between 0 and 3, 0 being the least aggressive about filtering out non-speech, 3 the most aggressive. Default: 3")
    parser.add_argument('--nospinner', action='store_true',
                        help="Disable spinner")
    parser.add_argument('-w', '--savewav',default='/home/komsky/audio/saved/',
                        help="Save .wav files of utterances to given directory")
    parser.add_argument('-f', '--file',
                        help="Read from .wav file instead of microphone")

    parser.add_argument('-d', '--device', type=int, default=None,
                        help="Device input index (Int) as listed by pyaudio.PyAudio.get_device_info_by_index(). If not provided, falls back to PyAudio.get_default_device().")
    parser.add_argument('-r', '--rate', type=int, default=DEFAULT_SAMPLE_RATE,
                        help=f"Input device sample rate. Default: {DEFAULT_SAMPLE_RATE}. Your device may require 44100.")

    ARGS = parser.parse_args()
    if ARGS.savewav: os.makedirs(ARGS.savewav, exist_ok=True)
    main(ARGS)

