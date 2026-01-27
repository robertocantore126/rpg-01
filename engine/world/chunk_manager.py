import pygame
from engine.world.camera_system import Camera

__all__ = ["ChunkManager"]

class ChunkManager:
    def __init__(self, chunk_size: int, load_margin: int = 1):
        """
        :param chunk_size: dimensione di un chunk in pixel (es. 256x256).
        :param load_margin: quanti chunk extra caricare attorno alla viewport.
        """
        self.chunk_size = chunk_size
        self.load_margin = load_margin
        self.loaded_chunks = {}  # {(cx, cy): Chunk}

    def world_to_chunk(self, x: int, y: int):
        """Converte coordinate mondo in coordinate di chunk (cx, cy)."""
        return x // self.chunk_size, y // self.chunk_size

    def get_chunks_in_viewport(self, viewport: pygame.Rect):
        """Ritorna i chunk che intersecano la viewport + margine."""
        left, top = self.world_to_chunk(viewport.left, viewport.top)
        right, bottom = self.world_to_chunk(viewport.right, viewport.bottom)

        chunks = []
        for cy in range(top - self.load_margin, bottom + 1 + self.load_margin):
            for cx in range(left - self.load_margin, right + 1 + self.load_margin):
                chunks.append((cx, cy))
        return chunks

    def update(self, viewport: pygame.Rect):
        """Aggiorna i chunk caricati in base alla viewport."""
        needed = set(self.get_chunks_in_viewport(viewport))
        current = set(self.loaded_chunks.keys())

        # Scarica chunk fuori vista
        for key in current - needed:
            self.unload_chunk(key)

        # Carica nuovi chunk
        for key in needed - current:
            self.load_chunk(key)

    def load_chunk(self, coord):
        """Carica un nuovo chunk. Qui puoi generare o leggere da file."""
        cx, cy = coord
        # esempio: creiamo una superficie riempita
        surface = pygame.Surface((self.chunk_size, self.chunk_size))
        surface.fill(((cx * 50) % 255, (cy * 80) % 255, 150))  # colore fittizio
        self.loaded_chunks[coord] = {"surface": surface, "rect": pygame.Rect(
            cx * self.chunk_size, cy * self.chunk_size, self.chunk_size, self.chunk_size
        )}
        print(f"Caricato chunk {coord}")

    def unload_chunk(self, coord):
        """Rimuove un chunk dalla memoria."""
        if coord in self.loaded_chunks:
            del self.loaded_chunks[coord]
            print(f"Scaricato chunk {coord}")

    def get_visible_tiles(self, camera: Camera):
        """Ritorna i rect/surface pronti per essere disegnati con la camera."""
        for chunk in self.loaded_chunks.values():
            yield chunk["surface"], camera.apply(chunk["rect"])

