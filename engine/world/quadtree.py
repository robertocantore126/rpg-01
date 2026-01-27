# ===============================
# QuadTree per spatial partitioning
# ===============================
from typing import List, Tuple
import pygame


class QuadTree:
    def __init__(self, bounds: pygame.Rect, capacity=4, depth=0, max_depth=6):
        self.bounds = bounds
        self.capacity = capacity
        self.depth = depth
        self.max_depth = max_depth
        self.entities: List[Tuple[int, pygame.Rect]] = []
        self.divided = False
        self.children = []

    def subdivide(self):
        x, y, w, h = self.bounds
        hw, hh = w // 2, h // 2
        self.children = [
            QuadTree(pygame.Rect(x, y, hw, hh), self.capacity, self.depth+1, self.max_depth),
            QuadTree(pygame.Rect(x+hw, y, hw, hh), self.capacity, self.depth+1, self.max_depth),
            QuadTree(pygame.Rect(x, y+hh, hw, hh), self.capacity, self.depth+1, self.max_depth),
            QuadTree(pygame.Rect(x+hw, y+hh, hw, hh), self.capacity, self.depth+1, self.max_depth),
        ]
        self.divided = True

    def insert(self, entity_id: int, rect: pygame.Rect):
        if not self.bounds.colliderect(rect):
            return False
        if len(self.entities) < self.capacity or self.depth >= self.max_depth:
            self.entities.append((entity_id, rect))
            return True
        if not self.divided:
            self.subdivide()
        for child in self.children:
            if child.insert(entity_id, rect):
                return True
        return False

    def remove(self, entity_id: int) -> bool:
        """Remove an entity_id from this quadtree node (recursively). Returns True if removed."""
        for i, (eid, rect) in enumerate(self.entities):
            if eid == entity_id:
                self.entities.pop(i)
                return True
        if self.divided:
            for child in self.children:
                if child.remove(entity_id):
                    return True
        return False

    def update(self, entity_id: int, rect: pygame.Rect):
        """Update an entity's rect by removing and reinserting it."""
        # naive approach: remove then insert
        self.remove(entity_id)
        return self.insert(entity_id, rect)

    def query(self, area: pygame.Rect, found=None):
        if found is None:
            found = []
        if not self.bounds.colliderect(area):
            return found
        for entity_id, rect in self.entities:
            if area.colliderect(rect):
                found.append(entity_id)
        if self.divided:
            for child in self.children:
                child.query(area, found)
        return found