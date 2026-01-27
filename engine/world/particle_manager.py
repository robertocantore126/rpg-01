from enum import Enum
import pygame
import random

__all__ = [
    "Particle", "ParticleEmitter", "ParticleManager", "ExplosionEmitter",
    "DustEmitter", "SparkEmitter", "SmokeEmitter", "FireEmitter"
    ]

class EmitterType(Enum):
    EXPLOSION = "explosion"
    DUST = "dust"
    SPARK = "spark"
    SMOKE = "smoke"
    FIRE = "fire"
    CUSTOM = "custom"

class Particle:
    def __init__(self, pos, vel, lifetime, color=(255,255,255), radius=3, sprite=None, gravity=0):
        self.x, self.y = pos
        self.vx, self.vy = vel
        self.lifetime = lifetime
        self.age = 0
        self.color = color
        self.radius = radius
        self.sprite = sprite
        self.gravity = gravity

        # Rect utile se vuoi trattarla come "fisica"
        if self.sprite:
            self.rect = self.sprite.get_rect(center=(self.x, self.y))
        else:
            self.rect = pygame.Rect(self.x, self.y, radius*2, radius*2)

    def update(self, dt):
        self.age += dt
        if self.age >= self.lifetime:
            return False  # segnala al manager che è da eliminare

        # movimento
        self.vy += self.gravity * dt
        self.x += self.vx * dt
        self.y += self.vy * dt

        # aggiorna rect
        if self.sprite:
            self.rect.center = (self.x, self.y)
        else:
            self.rect.topleft = (self.x - self.radius, self.y - self.radius)

        return True

    def draw(self, surface):
        if self.sprite:
            surface.blit(self.sprite, self.rect)
        else:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)


class ParticleEmitter:
    def __init__(self, pos, particle_config, burst_count=10):
        """
        particle_config = dict con parametri per Particle
        burst_count = quante particelle generare quando si attiva
        """
        self.pos = pos
        self.particle_config = particle_config
        self.burst_count = burst_count
        self.particles: list[Particle] = []

    def burst(self):
        for _ in range(self.burst_count):
            vel = (
                random.uniform(-100, 100),  # vx
                random.uniform(-100, 100)   # vy
            )
            lifetime = random.uniform(0.5, 1.5)
            config = {**self.particle_config, "vel": vel, "lifetime": lifetime, "pos": self.pos}
            self.particles.append(Particle(**config))

    def update(self, dt, pos):
        self.particles = [p for p in self.particles if p.update(dt)]
        self.pos = pos

    def draw(self, surface):
        for p in self.particles:
            p.draw(surface)

    def get_rects(self):
        return [p.rect for p in self.particles]


class ParticleManager:
    def __init__(self):
        self.emitters: list[ParticleEmitter] = [] 

    def add_emitter(self, emitter: ParticleEmitter):
        self.emitters.append(emitter)

    def update(self, dt, pos):
        for e in self.emitters:
            e.update(dt, pos)

    def draw(self, surface):
        for e in self.emitters:
            e.draw(surface)

    def get_all_rects(self):
        rects = []
        for e in self.emitters:
            rects.extend(e.get_rects())
        return rects
    
    def create_emitter(self, emitter_type: EmitterType, pos, **kwargs) -> ParticleEmitter:
        if emitter_type == EmitterType.EXPLOSION:
            emitter = ExplosionEmitter(pos, kwargs.get("burst_count", 30))
        elif emitter_type == EmitterType.DUST:
            emitter = DustEmitter(pos, kwargs.get("burst_count", 15))
        elif emitter_type == EmitterType.SPARK:
            emitter = SparkEmitter(pos, kwargs.get("burst_count", 10))
        elif emitter_type == EmitterType.SMOKE:
            emitter = SmokeEmitter(pos, kwargs.get("burst_count", 8))
        elif emitter_type == EmitterType.FIRE:
            emitter = FireEmitter(
                pos,
                kwargs.get("burst_count", 5),
                kwargs.get("continuous", False),
                kwargs.get("interval", 0.1),
            )
        elif emitter_type == EmitterType.CUSTOM:
            config = kwargs.get("config", {})
            emitter = ParticleEmitter(pos, config, kwargs.get("burst_count", 10))
        else:
            raise ValueError(f"Unknown emitter type: {emitter_type}")

        self.emitters.append(emitter)
        return emitter


# =======================
# PREDEFINED EMITTERS
# =======================

class ExplosionEmitter(ParticleEmitter):
    def __init__(self, pos, burst_count=30):
        super().__init__(pos, {}, burst_count)

    def burst(self):
        for _ in range(self.burst_count):
            vel = (
                random.uniform(-200, 200),
                random.uniform(-200, 200)
            )
            lifetime = random.uniform(0.4, 1.0)
            config = dict(
                pos=self.pos,
                vel=vel,
                lifetime=lifetime,
                color=(255, random.randint(100,200), 0), # arancio-giallo
                radius=random.randint(2, 4),
                gravity=100
            )
            self.particles.append(Particle(**config)) # type: ignore # type: ignore


class DustEmitter(ParticleEmitter):
    def __init__(self, pos, burst_count=15):
        super().__init__(pos, {}, burst_count)

    def burst(self):
        for _ in range(self.burst_count):
            vel = (
                random.uniform(-50, 50),
                random.uniform(-30, -80)  # verso l’alto ma leggero
            )
            lifetime = random.uniform(0.8, 1.5)
            gray = random.randint(100, 180)
            config = dict(
                pos=self.pos,
                vel=vel,
                lifetime=lifetime,
                color=(gray, gray, gray),
                radius=random.randint(2, 3),
                gravity=200
            )
            self.particles.append(Particle(**config)) # type: ignore


class SparkEmitter(ParticleEmitter):
    def __init__(self, pos, burst_count=10):
        super().__init__(pos, {}, burst_count)

    def burst(self):
        for _ in range(self.burst_count):
            vel = (
                random.uniform(-300, 300),
                random.uniform(-300, 300)
            )
            lifetime = random.uniform(0.2, 0.6)
            config = dict(
                pos=self.pos,
                vel=vel,
                lifetime=lifetime,
                color=(255, 255, random.randint(100, 200)), # giallo-bianco
                radius=2,
                gravity=300
            )
            self.particles.append(Particle(**config)) # type: ignore


class SmokeEmitter(ParticleEmitter):
    def __init__(self, pos, burst_count=8):
        super().__init__(pos, {}, burst_count)

    def burst(self):
        for _ in range(self.burst_count):
            vel = (
                random.uniform(-20, 20),
                random.uniform(-60, -100)  # sempre verso l’alto
            )
            lifetime = random.uniform(1.5, 3.0)
            gray = random.randint(120, 200)
            config = dict(
                pos=self.pos,
                vel=vel,
                lifetime=lifetime,
                color=(gray, gray, gray),
                radius=random.randint(4, 6),
                gravity=-50  # effetto che sale
            )
            self.particles.append(Particle(**config)) # type: ignore


class FireEmitter(ParticleEmitter):
    def __init__(self, pos, burst_count=5, continuous=False, interval=0.1):
        super().__init__(pos, {}, burst_count)
        self.continuous = continuous
        self.interval = interval
        self._time_acc = 0  # accumulatore di tempo per la logica continua

    def burst(self):
        for _ in range(self.burst_count):
            vel = (
                random.uniform(-30, 30),
                random.uniform(-150, -250)  # verso l’alto
            )
            lifetime = random.uniform(0.3, 0.8)
            config = dict(
                pos=self.pos,
                vel=vel,
                lifetime=lifetime,
                color=(255, random.randint(50, 150), 0),  # arancio/rosso
                radius=random.randint(2, 4),
                gravity=-30
            )
            self.particles.append(Particle(**config)) # type: ignore

    def update(self, dt, pos):
        # aggiorna le particelle come sempre
        super().update(dt, pos)

        # se continuo, accumula tempo e fai burst periodici
        if self.continuous:
            self._time_acc += dt
            if self._time_acc >= self.interval:
                self.burst()
                self._time_acc = 0

