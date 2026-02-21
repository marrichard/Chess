"""Lightweight particle system for visual effects."""

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass, field

import tcod.console


@dataclass
class Particle:
    """A single visual particle."""
    x: float
    y: float
    dx: float
    dy: float
    char: str
    color: tuple[int, int, int]
    lifetime: float
    elapsed: float = 0.0

    @property
    def alive(self) -> bool:
        return self.elapsed < self.lifetime

    @property
    def alpha(self) -> float:
        if self.lifetime <= 0:
            return 0.0
        return max(0.0, 1.0 - self.elapsed / self.lifetime)


class ParticleSystem:
    """Manages spawning, updating, and drawing particles."""

    def __init__(self) -> None:
        self.particles: list[Particle] = []
        self._last_time: float = time.time()

    def spawn(self, effect: str, x: float, y: float,
              color: tuple[int, int, int] = (255, 255, 100)) -> None:
        """Spawn particles for a named effect at console position (x, y)."""
        if effect == "capture_burst":
            # 8 radiating particles
            for angle_idx in range(8):
                angle = angle_idx * (math.pi / 4)
                speed = 3.0 + random.random() * 2.0
                self.particles.append(Particle(
                    x=x, y=y,
                    dx=math.cos(angle) * speed,
                    dy=math.sin(angle) * speed * 0.5,  # half vertical speed (char aspect)
                    char=random.choice(["*", "+", ".", "o"]),
                    color=color,
                    lifetime=0.4 + random.random() * 0.3,
                ))
        elif effect == "sparkle":
            # 4 random stars drifting upward
            for _ in range(4):
                self.particles.append(Particle(
                    x=x + random.uniform(-1, 1),
                    y=y + random.uniform(-1, 1),
                    dx=random.uniform(-0.5, 0.5),
                    dy=-random.uniform(0.5, 1.5),
                    char=random.choice(["*", ".", "'"]),
                    color=color,
                    lifetime=0.5 + random.random() * 0.3,
                ))
        elif effect == "trail":
            # Single fading dot
            self.particles.append(Particle(
                x=x, y=y,
                dx=0, dy=0,
                char=".",
                color=color,
                lifetime=0.6,
            ))

    def update(self) -> None:
        """Advance all particles by elapsed time."""
        now = time.time()
        dt = now - self._last_time
        self._last_time = now

        for p in self.particles:
            p.elapsed += dt
            p.x += p.dx * dt
            p.y += p.dy * dt

        # Remove dead particles
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, console: tcod.console.Console) -> None:
        """Render all alive particles onto the console."""
        for p in self.particles:
            ix, iy = int(round(p.x)), int(round(p.y))
            if 0 <= ix < console.width and 0 <= iy < console.height:
                alpha = p.alpha
                r = int(p.color[0] * alpha)
                g = int(p.color[1] * alpha)
                b = int(p.color[2] * alpha)
                console.print(ix, iy, p.char, fg=(r, g, b))

    @property
    def active(self) -> bool:
        return len(self.particles) > 0
