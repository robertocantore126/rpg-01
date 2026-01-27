from __future__ import annotations
import pygame


class Physics:
    """Physics component providing velocity/acceleration and force integration.

    This component is intentionally self-contained and can be attached to an Entity
    via Entity.add_component('physics', Physics(...)). It uses semi-implicit Euler
    integration and separates X/Y resolution helpers for collision systems.
    """
    def __init__(self, mass: float = 1.0, gravity: float = 0.0) -> None:
        self.mass = mass
        self.gravity = gravity
        self.pos = pygame.Vector2(0, 0)
        self.vel = pygame.Vector2(0, 0)
        self.acc = pygame.Vector2(0, 0)
        # accumulator for external forces this frame
        self._force_acc = pygame.Vector2(0, 0)

    # --- external API ---
    def apply_force(self, fx: float, fy: float) -> None:
        """Apply a continuous force (Newtons) that will affect acceleration.

        Multiple forces accumulate every frame; they are cleared after integration.
        """
        self._force_acc.x += fx
        self._force_acc.y += fy

    def apply_impulse(self, ix: float, iy: float) -> None:
        """Apply an instantaneous change in velocity (impulse = delta momentum / mass).

        This modifies velocity immediately.
        """
        self.vel.x += ix / self.mass
        self.vel.y += iy / self.mass

    def apply_friction(self, coefficient: float) -> None:
        """Apply a simple kinetic friction model reducing velocity.

        This is applied as a force opposite to the velocity direction.
        """
        if self.vel.length_squared() == 0:
            return
        friction_dir = -self.vel.normalize()
        # friction magnitude = coefficient * normal (assume normal = mass*1)
        friction_mag = coefficient * self.mass
        self.apply_force(friction_dir.x * friction_mag, friction_dir.y * friction_mag)

    # --- integration ---
    def integrate(self, dt: float) -> None:
        """Integrate forces and velocities over dt using semi-implicit Euler.

        Steps:
         1. compute total acceleration = forces/mass + gravity
         2. update velocity (v += a * dt)
         3. update position (p += v * dt)
         4. clear force accumulator
        """
        # total acceleration from forces
        self.acc.x = self._force_acc.x / self.mass
        self.acc.y = (self._force_acc.y / self.mass) + self.gravity

        # semi-implicit Euler: update velocity then position
        self.vel.x += self.acc.x * dt
        self.vel.y += self.acc.y * dt

        self.pos.x += self.vel.x * dt
        self.pos.y += self.vel.y * dt

        # clear forces
        self._force_acc.update(0, 0)

    # --- helpers for axis-separated movement ---
    def integrate_axis_x(self, dt: float) -> None:
        """Integrate only X axis (useful for separated collision resolution)."""
        ax = self._force_acc.x / self.mass
        self.vel.x += ax * dt
        self.pos.x += self.vel.x * dt

    def integrate_axis_y(self, dt: float) -> None:
        """Integrate only Y axis (useful for separated collision resolution). Gravity is included."""
        ay = (self._force_acc.y / self.mass) + self.gravity
        self.vel.y += ay * dt
        self.pos.y += self.vel.y * dt
