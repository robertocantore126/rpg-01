__all__ = ["SoundManager"]

import pygame
import os

class SoundManager:
    def __init__(self, assets_dir="assets"):
        self.assets_dir = assets_dir
        self.sound_dir = os.path.join(self.assets_dir, "sounds")
        self.music_dir = os.path.join(self.assets_dir, "music")
        self.sounds = {} # Dictionary to hold sound effects e.g. {"jump": pygame.mixer.Sound("jump.wav")}

        # Initialize mixer safely: if audio backend is not available, continue without sounds
        self.audio_available = True
        try:
            pygame.mixer.init()
            pygame.mixer.set_num_channels(32)
        except Exception:
            # audio not available (headless environment, CI, or missing drivers)
            self.audio_available = False

        if self.audio_available:
            self.load_sounds()

    def load_sounds(self):
        try:
            for sound_file in os.listdir(self.sound_dir):
                if sound_file.endswith(".wav"):
                    sound_name = os.path.splitext(sound_file)[0]
                    try:
                        self.sounds[sound_name] = pygame.mixer.Sound(os.path.join(self.sound_dir, sound_file))
                    except Exception:
                        # skip problematic sound files
                        pass
        except Exception:
            # directory may not exist; ignore
            pass

    def play_sound(self, sound_name):
        if not self.audio_available:
            return
        if sound_name in self.sounds:
            try:
                self.sounds[sound_name].play()
            except Exception:
                pass
        else:
            # optional: log missing asset
            pass

    def load_music(self, music_file):
        music_path = os.path.join(self.music_dir, music_file)
        if os.path.exists(music_path):
            pygame.mixer.music.load(music_path)
        else:
            print(f"Music file '{music_file}' not found in {self.music_dir}")