# ui_manager.py
# Gestione UI per pygame con EventBus.
# - UiManager: mantiene componenti, focus, hover, eventi mouse
# - Componenti: UiComponent, Container, Label, Button, HealthBar, FloatingText, DialogBox
# - Theming leggero e integrazione con EventBus
# - Coordinate: si assume che gli eventi mouse arrivino già in spazio "game canvas" (non screen scalato)

from __future__ import annotations
import pygame
from typing import Callable, Optional, List, Tuple, Dict, Any


__all__ = ["UITheme", "UiComponent", "Button", "Label", "Container", "HealthBar", "FloatingText", "DialogBox", "UiManager"]

# ----------------------------
# Event types (dipendono dal tuo constants.py)
# ----------------------------
from engine.world.constants import EventType


# ----------------------------
# Helper per compat con diversi EventBus
# ----------------------------
def _edata(event: Any) -> Dict[str, Any]:
    """Estrae un dict dati da un evento. Supporta oggetti con .data o un dict diretto."""
    if isinstance(event, dict):
        return event
    if hasattr(event, "data"):
        return getattr(event, "data") or {}
    return {}

# ----------------------------
# Theme (colori, font, paddings)
# ----------------------------
class UITheme:
    def __init__(
        self,
        font_name: str = "arial",
        font_size: int = 18,
        color_bg=(20, 20, 20),
        color_fg=(230, 230, 230),
        color_primary=(70, 140, 255),
        color_accent=(255, 200, 40),
        color_panel=(40, 40, 40),
        color_border=(80, 80, 80),
        button_bg=(70, 70, 70),
        button_bg_hover=(90, 90, 90),
        button_bg_pressed=(110, 110, 110),
        button_text=(240, 240, 240),
        health_bg=(100, 20, 20),
        health_fg=(20, 200, 20),
    ):
        self.font_name = font_name
        self.font_size = font_size
        self.font = pygame.font.SysFont(font_name, font_size)

        self.color_bg = color_bg
        self.color_fg = color_fg
        self.color_primary = color_primary
        self.color_accent = color_accent
        self.color_panel = color_panel
        self.color_border = color_border

        self.button_bg = button_bg
        self.button_bg_hover = button_bg_hover
        self.button_bg_pressed = button_bg_pressed
        self.button_text = button_text

        self.health_bg = health_bg
        self.health_fg = health_fg

# ----------------------------
# Base classes
# ----------------------------
class UiComponent:
    """Base per tutti i componenti UI."""
    def __init__(self, rect: pygame.Rect, z: int = 0):
        self.rect = rect
        self.z = z
        self.visible = True
        self.enabled = True

        # stati interazione
        self.hovered = False
        self.pressed = False
        self.focused = False

        self.parent: Optional[Container] = None
        self.theme: Optional[UITheme] = None
        self.event_bus = None  # opzionale: set dal manager

    # --- ciclo di vita
    def attach(self, manager_theme: UITheme, event_bus):
        """Chiamato da UiManager quando il componente viene registrato."""
        self.theme = manager_theme
        self.event_bus = event_bus

    def detach(self):
        """Chiamato da UiManager quando viene rimosso."""
        self.theme = None
        self.event_bus = None

    # --- input
    def on_mouse_move(self, pos: Tuple[int, int]):
        pass

    def on_mouse_down(self, pos: Tuple[int, int], button: int):
        pass

    def on_mouse_up(self, pos: Tuple[int, int], button: int):
        pass

    def on_focus_changed(self, focused: bool):
        self.focused = focused

    # --- update/draw
    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        pass

    # --- utility
    def global_rect(self) -> pygame.Rect:
        """Rect in coordinate globali (se il componente è dentro container con offset)."""
        if self.parent:
            pr = self.parent.global_rect()
            r = self.rect.copy()
            r.topleft = (pr.x + self.rect.x, pr.y + self.rect.y)
            return r
        return self.rect

    def hit_test(self, pos: Tuple[int, int]) -> bool:
        return self.global_rect().collidepoint(pos)

class Container(UiComponent):
    """Container con lista di figli (gestisce draw/update dei figli)."""
    def __init__(self, rect: pygame.Rect, z: int = 0, padding: int = 0, draw_panel: bool = False, panel_border: bool = True):
        super().__init__(rect, z)
        self.children: List[UiComponent] = []
        self.padding = padding
        self.draw_panel = draw_panel
        self.panel_border = panel_border

    def attach(self, manager_theme: UITheme, event_bus):
        super().attach(manager_theme, event_bus)
        for c in self.children:
            c.parent = self
            c.attach(manager_theme, event_bus)

    def add(self, comp: UiComponent):
        comp.parent = self
        if self.theme and self.event_bus:
            comp.attach(self.theme, self.event_bus)
        self.children.append(comp)
        # mantiene z-order locale
        self.children.sort(key=lambda c: c.z)

    def remove(self, comp: UiComponent):
        if comp in self.children:
            comp.detach()
            comp.parent = None
            self.children.remove(comp)

    def update(self, dt: float):
        if not self.visible: return
        for c in self.children:
            c.update(dt)

    def draw(self, surface: pygame.Surface):
        if not self.visible: return
        abs_rect = self.global_rect()
        if self.draw_panel and self.theme:
            pygame.draw.rect(surface, self.theme.color_panel, abs_rect)
            if self.panel_border:
                pygame.draw.rect(surface, self.theme.color_border, abs_rect, 2)
        # disegna figli in z-order
        for c in sorted(self.children, key=lambda x: x.z):
            c.draw(surface)

    # Propagazione input ai figli (top-most first)
    def on_mouse_move(self, pos: Tuple[int, int]):
        if not self.visible or not self.enabled: return
        for c in reversed(self.children):  # top-most prima
            if c.visible and c.enabled:
                if c.hit_test(pos):
                    if not c.hovered:
                        c.hovered = True
                    c.on_mouse_move(pos)
                else:
                    if c.hovered:
                        c.hovered = False

    def on_mouse_down(self, pos: Tuple[int, int], button: int):
        if not self.visible or not self.enabled: return
        for c in reversed(self.children):
            if c.visible and c.enabled and c.hit_test(pos):
                c.pressed = True
                c.on_mouse_down(pos, button)
                break

    def on_mouse_up(self, pos: Tuple[int, int], button: int):
        if not self.visible or not self.enabled: return
        for c in reversed(self.children):
            if c.visible and c.enabled:
                c.on_mouse_up(pos, button)

# ----------------------------
# Components
# ----------------------------
class Label(UiComponent):
    def __init__(self, rect: pygame.Rect, text: str, color=None, z: int = 0):
        super().__init__(rect, z)
        self.text = text
        self.color = color  # se None usa theme.color_fg
        self._cached_surf: Optional[pygame.Surface] = None
        self._cached_key = None

    def update(self, dt: float):
        pass

    def draw(self, surface: pygame.Surface):
        if not self.visible or not self.theme: return
        color = self.color or self.theme.color_fg
        # caching: re-render only when text/font/color changes
        font = self.theme.font
        key = (self.text, (self.theme.font_name, self.theme.font_size), font.get_height(), tuple(color) if hasattr(color, '__iter__') else (color,))
        if key != self._cached_key or self._cached_surf is None:
            try:
                ts = font.render(self.text, True, color)
            except Exception:
                ts = self.theme.font.render(self.text, True, color)
            self._cached_surf = ts
            self._cached_key = key
        gr = self.global_rect()
        surface.blit(self._cached_surf, self._cached_surf.get_rect(midleft=(gr.left, gr.centery)))

class Button(UiComponent):
    def __init__(self, rect: pygame.Rect, text: str, on_click: Optional[Callable[[], None]] = None, z: int = 0):
        super().__init__(rect, z)
        self.text = text
        self.on_click = on_click

    def draw(self, surface: pygame.Surface):
        if not self.visible or not self.theme: return
        gr = self.global_rect()
        # stato colore
        if not self.enabled:
            bg = (60, 60, 60)
        elif self.pressed:
            bg = self.theme.button_bg_pressed
        elif self.hovered:
            bg = self.theme.button_bg_hover
        else:
            bg = self.theme.button_bg
        pygame.draw.rect(surface, bg, gr, border_radius=8)
        pygame.draw.rect(surface, self.theme.color_border, gr, 2, border_radius=8)

        # testo centrato
        font = self.theme.font
        ts = font.render(self.text, True, self.theme.button_text)
        surface.blit(ts, ts.get_rect(center=gr.center))

    def on_mouse_down(self, pos: Tuple[int, int], button: int):
        # pressed già settato dal container/manager
        pass

    def on_mouse_up(self, pos: Tuple[int, int], button: int):
        if not self.enabled or not self.visible:
            return
        if self.hit_test(pos) and self.pressed:
            # Click!
            if self.on_click:
                self.on_click()
            if self.event_bus:
                self.event_bus.publish(EventType.UI_BUTTON_CLICKED, {"component": self, "text": self.text})
        self.pressed = False

class HealthBar(UiComponent):
    def __init__(self, rect: pygame.Rect, max_value: float, value: Optional[float] = None, smooth_speed: float = 10.0, show_text: bool = True, z: int = 0):
        super().__init__(rect, z)
        self.max_value = float(max_value)
        self.value = float(value if value is not None else max_value)
        self._display_value = self.value  # per smoothing
        self.smooth_speed = smooth_speed
        self.show_text = show_text

    def set_value(self, value: float):
        self.value = max(0.0, min(self.max_value, float(value)))
        if self.event_bus:
            self.event_bus.publish(EventType.UI_VALUE_CHANGED, {"component": self, "value": self.value})

    def update(self, dt: float):
        # smoothing (lerp critico)
        diff = self.value - self._display_value
        if abs(diff) > 0.001:
            self._display_value += diff * min(1.0, self.smooth_speed * dt)
        else:
            self._display_value = self.value

    def draw(self, surface: pygame.Surface):
        if not self.visible or not self.theme: return
        gr = self.global_rect()
        # sfondo
        pygame.draw.rect(surface, self.theme.health_bg, gr, border_radius=6)
        # barra
        pct = 0.0 if self.max_value <= 0 else (self._display_value / self.max_value)
        inner_w = max(0, int(gr.width * pct))
        inner_rect = pygame.Rect(gr.x, gr.y, inner_w, gr.height)
        pygame.draw.rect(surface, self.theme.health_fg, inner_rect, border_radius=6)
        pygame.draw.rect(surface, self.theme.color_border, gr, 2, border_radius=6)

        if self.show_text:
            txt = f"{int(self._display_value)}/{int(self.max_value)}"
            ts = self.theme.font.render(txt, True, (255, 255, 255))
            surface.blit(ts, ts.get_rect(center=gr.center))

class FloatingText(UiComponent):
    """Testo temporaneo che svanisce (utile per nomi oggetto/NPC o feedback)."""
    def __init__(self, pos: Tuple[int, int], text: str, duration_ms: int = 1200, rise_px: int = 10, color=(255,255,255), z: int = 1000):
        super().__init__(pygame.Rect(pos[0], pos[1], 1, 1), z)
        self.text = text
        self.duration = duration_ms
        self.elapsed = 0
        self.rise_px = rise_px
        self.color = color

    def update(self, dt: float):
        self.elapsed += int(dt * 1000)

    def draw(self, surface: pygame.Surface):
        if not self.visible or not self.theme: return
        t = min(1.0, self.elapsed / max(1, self.duration))
        alpha = int(255 * (1.0 - t))
        yoff = int(self.rise_px * t)
        ts = self.theme.font.render(self.text, True, self.color)
        if alpha < 255:
            ts = ts.copy()
            ts.set_alpha(alpha)
        pos = (self.rect.x, self.rect.y - yoff)
        surface.blit(ts, ts.get_rect(midbottom=pos))

    def is_dead(self) -> bool:
        return self.elapsed >= self.duration

class DialogBox(Container):
    """Box dialoghi stile VN: nome + testo con wrapping e 'typewriter'."""
    def __init__(self, rect: pygame.Rect, z: int = 10, bg_alpha: int = 180, type_speed_cps: int = 40):
        super().__init__(rect, z, draw_panel=True, panel_border=True)
        self.bg_alpha = bg_alpha
        self.type_speed_cps = type_speed_cps  # caratteri al secondo
        self.character_name = ""
        self.full_text = ""
        self._visible_chars = 0.0  # contatore per typewriter
        self._cached_lines: List[pygame.Surface] = []

    def set_dialog(self, name: str, text: str):
        self.character_name = name
        self.full_text = text
        self._visible_chars = 0.0
        self._cached_lines.clear()

    def _wrap_text(self, text: str, max_width: int, font: pygame.font.Font) -> List[str]:
        words = text.split()
        lines: List[str] = []
        cur = ""
        for w in words:
            test = w if cur == "" else cur + " " + w
            if font.size(test)[0] <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines

    def update(self, dt: float):
        if not self.visible: return
        # Avanza typewriter
        self._visible_chars += self.type_speed_cps * dt

    def draw(self, surface: pygame.Surface):
        if not self.visible or not self.theme: return
        gr = self.global_rect()

        # sfondo semitrasparente
        panel_surf = pygame.Surface((gr.width, gr.height), pygame.SRCALPHA)
        panel_surf.fill((*self.theme.color_panel, self.bg_alpha))
        surface.blit(panel_surf, gr.topleft)
        pygame.draw.rect(surface, self.theme.color_border, gr, 2, border_radius=8)

        # nome
        name_surf = self.theme.font.render(self.character_name, True, self.theme.color_accent)
        surface.blit(name_surf, (gr.x + 12, gr.y + 8))

        # testo con wrapping
        inner_x = gr.x + 12
        inner_y = gr.y + 8 + name_surf.get_height() + 6
        inner_w = gr.width - 24

        # calcola quanti caratteri mostrare
        n_chars = int(self._visible_chars)
        text_to_show = self.full_text[:n_chars]

        lines = self._wrap_text(text_to_show, inner_w, self.theme.font)
        y = inner_y
        for line in lines:
            ls = self.theme.font.render(line, True, self.theme.color_fg)
            surface.blit(ls, (inner_x, y))
            y += ls.get_height() + 4

# ----------------------------
# UiManager
# ----------------------------
class UiManager:
    """
    - Mantiene lista componenti (e container)
    - Gestisce z-order, focus, hover, pressed
    - Ascolta EventBus: MOUSE_MOVE / DOWN / UP (pos in coord canvas!)
    - Disegna su un surface (tipicamente la tua game_canvas)
    """
    def __init__(self, event_bus, theme: Optional[UITheme] = None):
        self.event_bus = event_bus
        self.theme = theme or UITheme()
        self.components: List[UiComponent] = []  # piatti o container, gestiti tutti
        self._focused: Optional[UiComponent] = None
        self._pointer_capture: Optional[UiComponent] = None  # chi ha catturato il mouse (press in corso)
        self._mouse_pos: Tuple[int, int] = (0, 0)

        # subscribe agli input
        event_bus.subscribe(EventType.MOUSE_MOVE, self._on_mouse_move)
        event_bus.subscribe(EventType.MOUSE_BUTTON_DOWN, self._on_mouse_down)
        event_bus.subscribe(EventType.MOUSE_BUTTON_UP, self._on_mouse_up)

        # facoltativo: supporto wheel
        if hasattr(EventType, "MOUSE_WHEEL"):
            event_bus.subscribe(EventType.MOUSE_WHEEL, self._on_mouse_wheel)

        # floating texts gestiti direttamente dal manager (comodi)
        self._floating: List[FloatingText] = []

    # --- gestione componenti
    def add(self, comp: UiComponent):
        comp.parent = None
        comp.attach(self.theme, self.event_bus)
        self.components.append(comp)
        self.components.sort(key=lambda c: c.z)

    def remove(self, comp: UiComponent):
        if comp in self.components:
            comp.detach()
            self.components.remove(comp)
            if self._focused is comp:
                self._set_focus(None)

    def clear(self):
        for c in self.components:
            c.detach()
        self.components.clear()
        self._focused = None
        self._pointer_capture = None
        self._floating.clear()

    # --- floating text utility
    def add_floating_text(self, pos: Tuple[int, int], text: str, duration_ms: int = 1200, color=(255,255,255)):
        ft = FloatingText(pos, text, duration_ms=duration_ms, color=color)
        ft.attach(self.theme, self.event_bus)
        self._floating.append(ft)

    # --- ciclo
    def update(self, dt: float):
        # update componenti
        for c in self.components:
            c.update(dt)
            if isinstance(c, Container):
                c.update(dt)  # i container aggiornano anche i figli (già chiamato sopra)

        # update e pulizia floating texts
        for ft in self._floating:
            ft.update(dt)
        self._floating = [f for f in self._floating if not f.is_dead()]

    def draw(self, surface: pygame.Surface):
        # draw componenti
        for c in sorted(self.components, key=lambda x: x.z):
            c.draw(surface)
        # draw floating sopra tutto
        for ft in self._floating:
            ft.draw(surface)

    # --- focus
    def _set_focus(self, comp: Optional[UiComponent]):
        if self._focused is comp:
            return
        if self._focused:
            self._focused.on_focus_changed(False)
        self._focused = comp
        if comp:
            comp.on_focus_changed(True)
        # notifica focus change
        self.event_bus.publish(EventType.UI_FOCUS_CHANGED, {"component": comp})

    # --- hit test sul top-most tra manager + container alti
    def _hit_topmost(self, pos: Tuple[int, int]) -> Optional[UiComponent]:
        # cerca dal top (z più alto, lista in reverse)
        for c in reversed(self.components):
            if not c.visible or not c.enabled:
                continue
            # se container, lascia che lui verifichi i figli: ma per cattura e focus
            # vogliamo il componente foglia sotto il cursore.
            target = _hit_in_component_tree(c, pos)
            if target:
                return target
        return None

    # --- handlers EventBus
    def _on_mouse_move(self, event):
        data = _edata(event)
        pos = data.get("pos", self._mouse_pos)
        self._mouse_pos = pos

        # se c'è cattura, inoltra a quello
        if self._pointer_capture and self._pointer_capture.visible and self._pointer_capture.enabled:
            self._pointer_capture.on_mouse_move(pos)
            return

        # gestisci hover enter/leave in modo semplice: il container/manager settano .hovered
        for c in self.components:
            if isinstance(c, Container):
                c.on_mouse_move(pos)
            else:
                inside = c.hit_test(pos) if (c.visible and c.enabled) else False
                c.hovered = inside

    def _on_mouse_down(self, event):
        # print("Mousedown fired")
        data = _edata(event)
        pos = data.get("pos", self._mouse_pos)
        btn = data.get("button", 1)
        self._mouse_pos = pos

        target = self._hit_topmost(pos)
        if target and target.enabled and target.visible:
            self._pointer_capture = target
            self._set_focus(target)
            target.pressed = True
            # passa al ramo gerarchico
            _propagate_mouse_down(target, pos, btn)

    def _on_mouse_up(self, event):
        data = _edata(event)
        pos = data.get("pos", self._mouse_pos)
        btn = data.get("button", 1)
        self._mouse_pos = pos

        # rilascia al catturatore se presente
        if self._pointer_capture:
            target = self._pointer_capture
            _propagate_mouse_up(target, pos, btn)
            target.pressed = False
            self._pointer_capture = None
        else:
            # dispatch “soft” al topmost (raro ma per sicurezza)
            target = self._hit_topmost(pos)
            if target:
                _propagate_mouse_up(target, pos, btn)

    def _on_mouse_wheel(self, event):
        # opzionale: se vuoi gestire scroll globali
        pass

# ----------------------------
# Utility per traversare gerarchia (hit test profondi)
# ----------------------------
def _hit_in_component_tree(comp: UiComponent, pos: Tuple[int, int]) -> Optional[UiComponent]:
    """Ritorna il componente foglia top-most sotto il mouse, se esiste."""
    if not comp.visible or not comp.enabled:
        return None
    if isinstance(comp, Container):
        # prova i figli dal top-most
        for child in reversed(comp.children):
            hit = _hit_in_component_tree(child, pos)
            if hit:
                return hit
    # se nessun figlio ha hit, prova il container stesso / componente foglia
    return comp if comp.hit_test(pos) else None

def _propagate_mouse_down(comp: UiComponent, pos: Tuple[int, int], button: int):
    """Chiama on_mouse_down dal basso verso l'alto (foglia → container), per dare priorità al child."""
    comp.on_mouse_down(pos, button)
    if comp.parent:
        _propagate_mouse_down(comp.parent, pos, button)

def _propagate_mouse_up(comp: UiComponent, pos: Tuple[int, int], button: int):
    comp.on_mouse_up(pos, button)
    if comp.parent:
        _propagate_mouse_up(comp.parent, pos, button)
