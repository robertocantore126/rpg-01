"""
Caratteristiche principali che implementerò qui:
Azioni componibili (Sequence, Parallel) e primitive: MoveTo, SetPos, PlayAnimation, CameraPan, ShowText, Wait, Callback.
Ogni azione è non-bloccante e tick-based (usa update(dt)); permette interpolazioni fluide.
CutsceneManager gestisce lo stato (start/stop/update/is_playing/skip).
Lock automatico input (il player perde il controllo) e invulnerabilità dei player durante la cutscene; alla fine tutto viene ripristinato.
API per definire cutscenes con una struttura JSON/Python-friendly (sequence/parallel).
Event hooks (on_start, on_end, on_step) e possibilità di chiamare callback personalizzate.
Sistema per mostrare testo a schermo (il renderer/scene può leggere cutscene.get_active_texts() e disegnarli).


Spiegazione di design e integrazione
Ctx (context): ogni Action riceve un ctx con riferimenti utili: world, game, event_bus, cutscene_texts. Questo permette alle azioni di essere indipendenti dall'engine e di lavorare solo sui componenti dati.
Lock input / Invulnerability: CutsceneManager.start() prova a chiamare game.lock_input() / unlock_input() se il tuo Game li espone; in assenza imposta un componente cutscene_lock (entity id 0 usata come "global store") — i sistemi (input/physics/damage) dovrebbero controllare questo flag. Per invulnerabilità aggiunge o modifica il componente invulnerable sui player passati.
Non-blocking: tutto è tick-based. Chiama cutscene_manager.update(dt) nel tuo loop dopo world.update(dt) (o prima, a seconda del flusso).
Rebuild spatial index: azioni che muovono entità aggiornano la posizione nei componenti; la quadtree la ricostruisci come fai normalmente (es. world.rebuild_quadtree()), tipicamente ogni frame o ogni N frame.
Renderer: per mostrare testi, il renderer dovrebbe leggere cutscene_manager.get_active_texts() e disegnarli. Per animazioni/graphics, l'animation component che PlayAnimationAction imposta sarà usato dal sistema grafico per avviare l'animazione e impostare animation.done quando termina.
Skip: puoi chiamare cutscene_manager.skip() per terminare subito.


Note pratiche / best-practices
Sistemi (damage/input) devono rispettare i flag invulnerable e cutscene_lock. Implementa queste verifiche nella logica dei sistemi.
Sync multiplayer: in multiplayer server-authoritative, il server esegue le cutscenes che alterano lo stato condiviso; i client riproducono localmente le azioni su comando del server (es. server invia start_cutscene con la stessa definizione o con una serie di comandi di sincronizzazione). Se vuoi riprodurre cutscene sincronizzate su client, invia un evento start_cutscene con la definizione (o solo un id e parametri) e fai partire un Cutscene locale su ciascun client. Per eventi che cambiano lo stato del mondo (posizioni, health), lascia che il server sia autoritativo.
Animazioni e sincronizzazione: considera l'uso di timestamp / tick per assicurare che i client avviino le azioni nello stesso istante relativo.
Easing: puoi passare funzioni di easing a MoveToAction/CameraPanAction per avere movimento più naturale (es. ease_out_quad).
Serializzazione: le cutscenes possono essere definite in JSON e tradotte in oggetti Action al runtime (mapper). Ciò permette editing esterno. Io ho progettato l'API in modo che la conversione sia semplice.
"""

# cutscene.py
"""
Cutscene framework modulare, tick-based, non-bloccante.
Integrazione:
- Chiamare cutscene_manager.update(dt) nel game loop.
- Quando si avvia una cutscene: cutscene_manager.start(my_cutscene)
- Il renderer può leggere cutscene_manager.get_active_texts() per disegnare testi.
- Il world/game dovrebbe fornire:
    * accesso al world/component store (per spostare entità, impostare invulnerabilità)
    * una camera object (con get_position/set_position) oppure passarlo al CameraPanAction
    * input_manager lock/unlock (opzionale). Se assente, CutsceneManager imposta `world.components` flags.
"""

__all__= [
    "Action", "SequenceAction", "ParallelAction", "WaitAction", "WaitForConditionAction", 
    "CallbackAction", "MoveToAction", "SetPositionAction", "PlayAnimationAction",
    "CameraPanAction", "ShowTextAction", "Cutscene", "CutsceneManager"
          ]

import time
from typing import List, Callable, Any, Dict, Optional, Tuple

# ------------------------
# Action base classes
# ------------------------
class Action:
    def __init__(self):
        self.started = False
        self.finished = False

    def start(self, ctx: Dict[str, Any]):
        """ctx contiene riferimenti utili: world, game, camera, event_bus, etc."""
        self.started = True

    def update(self, dt: float, ctx: Dict[str, Any]):
        """Eseguito ogni frame finché finished == False"""
        raise NotImplementedError()

    def is_finished(self) -> bool:
        return self.finished

    def force_finish(self, ctx: Dict[str, Any]):
        """Forza completamento (utile per skip)"""
        self.finished = True

# ------------------------
# Composite Actions
# ------------------------
class SequenceAction(Action):
    def __init__(self, actions: List[Action]):
        super().__init__()
        self.actions = actions
        self.current = 0

    def start(self, ctx):
        super().start(ctx)
        if self.actions:
            self.actions[0].start(ctx)

    def update(self, dt, ctx):
        if self.finished:
            return
        if self.current >= len(self.actions):
            self.finished = True
            return
        action = self.actions[self.current]
        if not action.started:
            action.start(ctx)
        action.update(dt, ctx)
        if action.is_finished():
            self.current += 1
            if self.current < len(self.actions):
                self.actions[self.current].start(ctx)
            else:
                self.finished = True

    def force_finish(self, ctx):
        for a in self.actions:
            a.force_finish(ctx)
        self.finished = True

class ParallelAction(Action):
    def __init__(self, actions: List[Action]):
        super().__init__()
        self.actions = actions

    def start(self, ctx):
        super().start(ctx)
        for a in self.actions:
            a.start(ctx)

    def update(self, dt, ctx):
        if self.finished:
            return
        all_done = True
        for a in self.actions:
            if not a.started:
                a.start(ctx)
            if not a.is_finished():
                a.update(dt, ctx)
            if not a.is_finished():
                all_done = False
        if all_done:
            self.finished = True

    def force_finish(self, ctx):
        for a in self.actions:
            a.force_finish(ctx)
        self.finished = True

# ------------------------
# Primitive Actions
# ------------------------
class WaitAction(Action):
    def __init__(self, duration: float):
        super().__init__()
        self.duration = duration
        self.elapsed = 0.0

    def start(self, ctx):
        super().start(ctx)
        self.elapsed = 0.0

    def update(self, dt, ctx):
        self.elapsed += dt
        if self.elapsed >= self.duration:
            self.finished = True

class WaitForConditionAction(Action):
    def __init__(self, condition_fn: Callable[[Dict[str,Any]], bool], timeout: Optional[float] = None):
        super().__init__()
        self.condition_fn = condition_fn
        self.timeout = timeout
        self.elapsed = 0.0

    def update(self, dt, ctx):
        self.elapsed += dt
        if self.condition_fn(ctx):
            self.finished = True
            return
        if self.timeout is not None and self.elapsed >= self.timeout:
            self.finished = True  # timeout reached

class CallbackAction(Action):
    def __init__(self, fn: Callable[[Dict[str,Any]], Any]):
        super().__init__()
        self.fn = fn
        self.called = False

    def update(self, dt, ctx):
        if not self.called:
            self.fn(ctx)
            self.called = True
            self.finished = True

# Move entity from current position to target over duration (linear or eased)
class MoveToAction(Action):
    def __init__(self, entity_id: int, target: Tuple[float,float], duration: float, ease: Optional[Callable[[float],float]] = None):
        super().__init__()
        self.entity_id = entity_id
        self.target = target
        self.duration = duration
        self.ease = ease or (lambda t: t)
        self.elapsed = 0.0
        self.start_pos = None

    def start(self, ctx):
        super().start(ctx)
        world = ctx.get("world")
        pos = world.get_component(self.entity_id, "position")
        if pos is None:
            # create if missing
            world.add_component(self.entity_id, "position", {"x": self.target[0], "y": self.target[1]})
            self.start_pos = (self.target[0], self.target[1])
            self.finished = True
            return
        self.start_pos = (pos["x"], pos["y"])
        self.elapsed = 0.0

    def update(self, dt, ctx):
        if self.finished:
            return
        self.elapsed += dt
        t = min(self.elapsed / max(self.duration, 1e-6), 1.0)
        eased = self.ease(t)
        sx, sy = self.start_pos
        tx, ty = self.target
        nx = sx + (tx - sx) * eased
        ny = sy + (ty - sy) * eased
        world = ctx.get("world")
        pos = world.get_component(self.entity_id, "position")
        pos["x"], pos["y"] = nx, ny
        # update quadtree later when rebuilding or we can push updates to quadtree here
        if t >= 1.0:
            self.finished = True

class SetPositionAction(Action):
    def __init__(self, entity_id: int, pos: Tuple[float,float]):
        super().__init__()
        self.entity_id = entity_id
        self.pos = pos

    def update(self, dt, ctx):
        world = ctx.get("world")
        p = world.get_component(self.entity_id, "position")
        if p is None:
            world.add_component(self.entity_id, "position", {"x": self.pos[0], "y": self.pos[1]})
        else:
            p["x"], p["y"] = self.pos
        self.finished = True

class PlayAnimationAction(Action):
    def __init__(self, entity_id: int, animation_name: str, wait_for_end: bool = True):
        super().__init__()
        self.entity_id = entity_id
        self.animation_name = animation_name
        self.wait_for_end = wait_for_end
        self.started_anim = False

    def start(self, ctx):
        super().start(ctx)
        world = ctx.get("world")
        anim = world.get_component(self.entity_id, "animation")
        # set animation component or flag
        world.add_component(self.entity_id, "animation", {"name": self.animation_name, "playing": True})
        self.started_anim = True
        if not self.wait_for_end:
            self.finished = True

    def update(self, dt, ctx):
        if self.finished:
            return
        # we need a way to detect animation end: either animation system writes a flag `animation_done` or duration provided.
        world = ctx.get("world")
        anim = world.get_component(self.entity_id, "animation")
        # fallback: if anim has 'done' flag, use it
        if anim and anim.get("done"):
            self.finished = True

class CameraPanAction(Action):
    def __init__(self, camera_obj, target: Tuple[float,float], duration: float, ease: Optional[Callable[[float],float]] = None):
        super().__init__()
        self.camera = camera_obj
        self.target = target
        self.duration = duration
        self.ease = ease or (lambda t: t)
        self.elapsed = 0.0
        self.start_pos = None

    def start(self, ctx):
        super().start(ctx)
        if hasattr(self.camera, "get_position"):
            self.start_pos = tuple(self.camera.get_position())
        else:
            # assume camera is a dict-like with x,y
            self.start_pos = (getattr(self.camera, "x", 0), getattr(self.camera, "y", 0))
        self.elapsed = 0.0

    def update(self, dt, ctx):
        self.elapsed += dt
        t = min(self.elapsed / max(self.duration, 1e-6), 1.0)
        e = self.ease(t)
        sx, sy = self.start_pos
        tx, ty = self.target
        nx = sx + (tx - sx) * e
        ny = sy + (ty - sy) * e
        if hasattr(self.camera, "set_position"):
            self.camera.set_position((nx, ny))
        else:
            if hasattr(self.camera, "x"):
                self.camera.x, self.camera.y = nx, ny
            else:
                # dict
                self.camera["x"], self.camera["y"] = nx, ny
        if t >= 1.0:
            self.finished = True

class ShowTextAction(Action):
    def __init__(self, text: str, duration: float, pos: Tuple[int,int] = None, style: dict = None):
        super().__init__()
        self.text = text
        self.duration = duration
        self.pos = pos
        self.style = style or {}
        self.elapsed = 0.0

    def start(self, ctx):
        super().start(ctx)
        # register active text in ctx.cutscene_texts (so renderer can pick it)
        texts = ctx.setdefault("cutscene_texts", [])
        texts.append({"text": self.text, "pos": self.pos, "style": self.style, "id": id(self)})

    def update(self, dt, ctx):
        self.elapsed += dt
        if self.elapsed >= self.duration:
            # remove text
            texts = ctx.get("cutscene_texts", [])
            texts[:] = [t for t in texts if t.get("id") != id(self)]
            self.finished = True

    def force_finish(self, ctx):
        # remove immediately
        texts = ctx.get("cutscene_texts", [])
        texts[:] = [t for t in texts if t.get("id") != id(self)]
        self.finished = True

# ------------------------
# Cutscene and Manager
# ------------------------
class Cutscene:
    def __init__(self, root_action: Action, name: str = ""):
        self.root = root_action
        self.name = name

    def start(self, ctx):
        self.root.start(ctx)

    def update(self, dt, ctx):
        self.root.update(dt, ctx)

    def is_finished(self) -> bool:
        return self.root.is_finished()

    def force_finish(self, ctx):
        self.root.force_finish(ctx)

class CutsceneManager:
    def __init__(self, world, game=None, event_bus=None):
        """
        world: your World instance (used for components)
        game: optional reference to game (for input locking e.g. game.lock_input()/unlock_input())
        event_bus: optional event dispatcher
        """
        self.world = world
        self.game = game
        self.event_bus = event_bus
        self.current: Optional[Cutscene] = None
        self.ctx = {"world": world, "game": game, "event_bus": event_bus, "cutscene_texts": []}
        self.locked_players: List[int] = []
        self.saved_player_input_state = None
        self.on_start: Optional[Callable[[Cutscene], None]] = None
        self.on_end: Optional[Callable[[Cutscene], None]] = None
        self.on_step: Optional[Callable[[Action], None]] = None

    def start(self, cutscene: Cutscene, affected_players: Optional[List[int]] = None, make_players_invulnerable: bool = True):
        """
        Avvia la cutscene:
        - lock input (game.lock_input() if presente, or set world flag)
        - set invulnerable component to players (if provided)
        - call on_start
        """
        if self.current:
            # optionally stop running cutscene
            self.stop()

        # lock input
        if self.game and hasattr(self.game, "lock_input"):
            self.game.lock_input()
            self.saved_player_input_state = True
        else:
            # fallback: set a flag in world (systems should check this)
            self.world.add_component(0, "cutscene_lock", {"locked": True})

        # invulnerable players
        self.locked_players = affected_players or []
        if make_players_invulnerable:
            for pid in self.locked_players:
                inv = self.world.get_component(pid, "invulnerable")
                if inv is None:
                    self.world.add_component(pid, "invulnerable", {"active": True})
                else:
                    inv["_cutscene_prev"] = inv.get("active", False)
                    inv["active"] = True

        # populate ctx
        self.ctx["cutscene_start_time"] = time.time()
        self.ctx["cutscene_name"] = cutscene.name

        self.current = cutscene
        self.current.start(self.ctx)

        if self.on_start:
            self.on_start(cutscene)

        # emit event
        if self.event_bus:
            self.event_bus.publish("cutscene_started", {"name": cutscene.name})

    def update(self, dt: float):
        if not self.current:
            return
        # update cutscene
        self.current.update(dt, self.ctx)
        if self.on_step:
            self.on_step(self.current.root)
        if self.current.is_finished():
            self._end_current()

    def _end_current(self):
        # restore invulnerability
        for pid in self.locked_players:
            inv = self.world.get_component(pid, "invulnerable")
            if inv is not None:
                prev = inv.pop("_cutscene_prev", None)
                if prev is None:
                    # remove the component if it was created by us
                    self.world.remove_component(pid, "invulnerable")
                else:
                    inv["active"] = prev

        # unlock input
        if self.game and hasattr(self.game, "unlock_input"):
            self.game.unlock_input()
        else:
            try:
                self.world.remove_component(0, "cutscene_lock")
            except Exception:
                pass

        if self.on_end:
            self.on_end(self.current) # type: ignore

        if self.event_bus:
            self.event_bus.publish("cutscene_ended", {"name": self.current.name}) # type: ignore

        self.current = None

    def stop(self):
        if not self.current:
            return
        self.current.force_finish(self.ctx)
        self._end_current()

    # helper for renderer
    def get_active_texts(self) -> List[Dict]:
        return list(self.ctx.get("cutscene_texts", []))

    def is_playing(self) -> bool:
        return self.current is not None

    def skip(self):
        self.stop()


# =================================================0

"""# esempio_usage.py
from cutscene import CutsceneManager, Cutscene, SequenceAction, MoveToAction, WaitAction, ShowTextAction, CameraPanAction, ParallelAction

# supponiamo tu abbia `world` e `game` già inizializzati
cutman = CutsceneManager(world, game, event_bus=None)

# crea sequenza:
seq = SequenceAction([
    ParallelAction([
        CameraPanAction(game.camera, target=(400,200), duration=1.2),
        MoveToAction(player_entity, target=(320,240), duration=1.2),
    ]),
    WaitAction(0.2),
    ShowTextAction("Hai trovato un oggetto raro!", duration=2.5, pos=(20, 500)),
    WaitAction(0.3),
    CallbackAction(lambda ctx: print("cutscene callback called")),
    # esempio animazione che aspetta la fine:
    PlayAnimationAction(npc_entity, "surprised", wait_for_end=True),
    WaitAction(0.5),
])

cutscene = Cutscene(seq, name="intro_scene")

# start: lock player(s) and make invulnerable
cutman.start(cutscene, affected_players=[player_entity], make_players_invulnerable=True)

# nel game loop:
# dt = clock.tick() / 1000.0
# update world (physic, ai, etc) - note: server-authoritative logic still applies
cutman.update(dt)

# renderer usa:
texts = cutman.get_active_texts()
# draw each text
"""