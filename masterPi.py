import time, logging
from datetime import datetime
import threading, collections, queue, os, os.path
import deepspeech
import numpy as np
import pyaudio
import webrtcvad
from halo import Halo
from scipy import signal
from AudioModule import Audio
from VoiceActivityDetection import VADAudio

logging.basicConfig(level=20)

activation_command = "activation"

def HermesCommand(text):
    print(f"Now I should do something, because you want me to {text}, but you have to program this yourself")

def main(ARGS):
    # Load DeepSpeech model
    if os.path.isdir(ARGS.model):
        model_dir = ARGS.model
        ARGS.model = os.path.join(model_dir, 'output_graph.pb')
        ARGS.scorer = os.path.join(model_dir, ARGS.scorer)

    print('Initializing model...')
    logging.info("ARGS.model: %s", ARGS.model)
    model = deepspeech.Model(ARGS.model)
    if ARGS.scorer:
        logging.info("ARGS.scorer: %s", ARGS.scorer)
        model.enableExternalScorer(ARGS.scorer)

    # Start audio with VAD
    vad_audio = VADAudio(aggressiveness=ARGS.vad_aggressiveness,
                         device=ARGS.device,
                         input_rate=ARGS.rate,
                         file=ARGS.file)
    print("Listening (ctrl-C to exit)...")
    frames = vad_audio.vad_collector()

    # Stream from microphone to DeepSpeech using VAD
    spinner = None
    if not ARGS.nospinner:
        spinner = Halo(spinner='line')
    stream_context = model.createStream()
    wav_data = bytearray()
    is_next_command_for_hermes = False
    for frame in frames:
        if frame is not None:
            if spinner: spinner.start()
            logging.debug("streaming frame")
            stream_context.feedAudioContent(np.frombuffer(frame, np.int16))
            if ARGS.savewav: wav_data.extend(frame)
        else:
            if spinner: spinner.stop()
            logging.debug("end utterence")
            if ARGS.savewav:
                date_piece = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f.wav")
                saved_file = os.path.join(ARGS.savewav, f'savewav_{date_piece}')
                vad_audio.write_wav(saved_file, wav_data)
                wav_data = bytearray()
            text = stream_context.finishStream()
            print("Recognized: %s" % text)
            if(is_next_command_for_hermes):
                HermesCommand(text)
            is_next_command_for_hermes = IsHermesActivation(text,is_next_command_for_hermes)
            if ARGS.savewav:
                if(text == ""):
                    os.remove(saved_file)
                else:
                    new_filename = f"{text}_{date_piece}"
                    new_full_path = os.path.join(ARGS.savewav, new_filename)   
                    os.rename(saved_file, new_full_path)
            stream_context = model.createStream()
def IsHermesActivation(text, last_status):
    if(last_status and text ==""):
        return True
    return text.lower() ==  activation_command.lower()

if __name__ == '__main__':
    DEFAULT_SAMPLE_RATE = 16000

    import argparse
    parser = argparse.ArgumentParser(description="Stream from microphone to DeepSpeech using VAD")

    parser.add_argument('-v', '--vad_aggressiveness', type=int, default=2,
                        help="Set aggressiveness of VAD: an integer between 0 and 3, 0 being the least aggressive about filtering out non-speech, 3 the most aggressive. Default: 3")
    parser.add_argument('--nospinner', action='store_true',
                        help="Disable spinner")
    parser.add_argument('-w', '--savewav',default='/home/pi/dspeech/saved/',
                        help="Save .wav files of utterences to given directory")
    parser.add_argument('-f', '--file',
                        help="Read from .wav file instead of microphone")

    parser.add_argument('-m', '--model', required=False, default='/home/pi/dspeech/deepspeech-0.9.3-models.tflite',
                        help="Path to the model (protocol buffer binary file, or entire directory containing all standard-named files for model)")
    parser.add_argument('-s', '--scorer', required=False, default='/home/pi/dspeech/deepspeech-0.9.3-models.scorer',
                        help="Path to the external scorer file.")
    parser.add_argument('-d', '--device', type=int, default=None,
                        help="Device input index (Int) as listed by pyaudio.PyAudio.get_device_info_by_index(). If not provided, falls back to PyAudio.get_default_device().")
    parser.add_argument('-r', '--rate', type=int, default=DEFAULT_SAMPLE_RATE,
                        help=f"Input device sample rate. Default: {DEFAULT_SAMPLE_RATE}. Your device may require 44100.")

    ARGS = parser.parse_args()
    if ARGS.savewav: os.makedirs(ARGS.savewav, exist_ok=True)
    main(ARGS)
