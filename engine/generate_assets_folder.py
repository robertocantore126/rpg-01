# engine/generate_assets_folder.py
import os
import json
import hashlib
from pathlib import Path

ASSET_SUBFOLDERS = ["fonts", "music", "sounds", "tilemaps", "tilesets", "sprites"]
SAVE_DIR = "saves"
SAVE_FILE = "game_data.json"
GAME_SUBFOLDER = ["entities", "scenes"]


def compute_dir_hash(directory: Path) -> str:
    """Calcola un hash SHA1 basato su nomi, dimensioni e tempi dei file nella directory."""
    sha = hashlib.sha1()
    if not directory.exists():
        return ""
    for root, _, files in os.walk(directory):
        for f in sorted(files):
            fp = Path(root) / f
            stat = fp.stat()
            sha.update(str(fp.relative_to(directory)).encode())
            sha.update(str(stat.st_size).encode())
            sha.update(str(int(stat.st_mtime)).encode())
    return sha.hexdigest()


def ensure_init_file(directory: Path):
    """Crea __init__.py in una directory se non esiste già."""
    init_file = directory / "__init__.py"
    if not init_file.exists():
        init_file.write_text("# Auto-generated init\n")


def verify_and_generate(base_dir: Path):
    assets_dir = base_dir / "assets"
    saves_dir = base_dir / SAVE_DIR
    game_dir = base_dir / "game"
    save_file = saves_dir / SAVE_FILE

    saves_dir.mkdir(exist_ok=True)

    # carica stato precedente se esiste
    if save_file.exists():
        try:
            prev_data = json.loads(save_file.read_text())
        except Exception:
            prev_data = {}
    else:
        prev_data = {}

    current_data = {"folders": {}, "hashes": {}}

    # controlla/genera sottocartelle assets
    assets_dir.mkdir(exist_ok=True)
    for sub in ASSET_SUBFOLDERS:
        folder = assets_dir / sub
        folder.mkdir(exist_ok=True)
        current_data["folders"][f"assets/{sub}"] = folder.exists()
        current_data["hashes"][f"assets/{sub}"] = compute_dir_hash(folder)

    # controlla/genera game + sottocartelle
    game_dir.mkdir(exist_ok=True)
    ensure_init_file(game_dir)

    for sub in GAME_SUBFOLDER:
        folder = game_dir / sub
        folder.mkdir(exist_ok=True)
        ensure_init_file(folder)
        current_data["folders"][f"game/{sub}"] = folder.exists()
        current_data["hashes"][f"game/{sub}"] = compute_dir_hash(folder)

    # salva game_data.json
    save_file.write_text(json.dumps(current_data, indent=4))


def generate_main_py(base_dir: Path):
    main_file = base_dir / "main.py"
    if not main_file.exists() or main_file.stat().st_size == 0:
        main_file.write_text(
            '''"""
Main entry point for the game.
"""

import engine.generate_assets_folder as gen

def main():
    print("Game started!")
    gen.verify_and_generate(Path(__file__).resolve().parent)

import game

if __name__ == "__main__":
    from pathlib import Path
    g = game.Game()
    g.game_loop()
'''
        )
        print(f"Created {main_file}")


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent.parent
    verify_and_generate(base_dir)
    generate_main_py(base_dir)
