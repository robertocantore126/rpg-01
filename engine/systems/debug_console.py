__all__ = ["DebugConsole"]

from functools import wraps
import threading
import queue
import time
import psutil
import pygame
from rich.console import Console
from rich.table import Table

class DebugConsole:
    def __init__(self):
        self.console = Console()
        self.data = {}
        self.running = True
        self.update_interval = 0.5  # refresh terminale

        # coda per i comandi inviati dal gioco
        self.command_queue = queue.Queue()

        # thread che aggiorna il terminale
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

        # overlay state
        self.overlay_active = False
        self.input_text = ""

        # process info
        self.process = psutil.Process()

        # metriche performance aggiuntive
        self.last_frame_time = None
        self.avg_frame_time = 0
        self.frame_counter = 0

        self._add_basic_log_data()

    def _run(self):
        """Aggiorna il terminale in background con una tabella persistente"""
        while self.running:
            self._update_resource_usage()

            self.console.clear()
            table = Table(title="Debug Data")

            table.add_column("Key", style="cyan")
            table.add_column("Value", style="magenta")

            for k, v in self.data.items():
                table.add_row(k, str(v))

            self.console.print(table)
            time.sleep(self.update_interval)

    def _add_basic_log_data(self):
        self.log("Debug thread alive", self.thread.is_alive())
        
    def _update_resource_usage(self):
        """Aggiorna RAM/CPU e performance frame"""
        try:
            mem = self.process.memory_info().rss / (1024 * 1024)  # MB
            cpu = self.process.cpu_percent(interval=None)         # %
            self.log("RAM (MB)", f"{mem:.2f}")
            self.log("CPU (%)", f"{cpu:.1f}")
            if self.avg_frame_time > 0:
                fps = 1000.0 / self.avg_frame_time
                self.log("Frame time (ms)", f"{self.avg_frame_time:.2f}")
                self.log("FPS (avg)", f"{fps:.1f}")
        except Exception as e:
            self.log("Resource Error", str(e))

    def log(self, key, value):
        """Aggiorna un valore da mostrare nella tabella"""
        self.data[key] = value

    def stop(self):
        self.running = False
        self.thread.join()

    @staticmethod
    def draw_debug_grid(screen, player_pos, chunk_size, radius, camera):
        cx, cy = player_pos[0] // chunk_size, player_pos[1] // chunk_size
        for dx in range(-radius, radius+1):
            for dy in range(-radius, radius+1):
                rect = pygame.Rect(
                    (cx+dx)*chunk_size,
                    (cy+dy)*chunk_size,
                    chunk_size,
                    chunk_size
                )
                pygame.draw.rect(screen, (0, 255, 0), camera.apply(rect), 1)


    # --------------------------
    # Overlay console in-game
    # --------------------------
    def toggle_overlay(self):
        self.overlay_active = not self.overlay_active
        self.input_text = ""

    def handle_event(self, event):
        if not self.overlay_active:
            return
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.command_queue.put(self.input_text)
                self.input_text = ""
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                self.input_text += event.unicode

    def render_overlay(self, surface):
        """Disegna la console nel gioco"""
        if not self.overlay_active:
            return
        font = pygame.font.SysFont("Consolas", 20)
        text_surface = font.render("> " + self.input_text, True, (0, 255, 0))
        surface.blit(text_surface, (10, surface.get_height() - 30))

    def poll_command(self):
        """Recupera un comando dalla coda (se presente)"""
        try:
            return self.command_queue.get_nowait()
        except queue.Empty:
            return None

    # --------------------------
    # Performance hooks
    # --------------------------
    def mark_frame(self):
        """Chiama questa dal main loop a fine frame per calcolare tempi draw"""
        now = time.perf_counter() * 1000  # ms
        if self.last_frame_time is not None:
            dt = now - self.last_frame_time
            # media mobile semplice
            self.frame_counter += 1
            alpha = 0.1
            self.avg_frame_time = (1 - alpha) * self.avg_frame_time + alpha * dt
        self.last_frame_time = now

    def profile(self, name=None):
        """
        Decoratore per misurare i tempi di funzione.
        Usa: @debug_console.profile("UpdateSystem")
        """
        def decorator(func):
            label = name or func.__name__

            @wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter() * 1000
                result = func(*args, **kwargs)
                elapsed = (time.perf_counter() * 1000) - start

                # log tabella
                self.log(f"{label} (ms)", f"{elapsed:.2f}")

                # log file
                # with open(self.log_file, "a", encoding="utf-8") as f:
                #     f.write(f"{label},{elapsed:.2f},{time.time()}\n")

                return result
            return wrapper
        return decorator
    
    