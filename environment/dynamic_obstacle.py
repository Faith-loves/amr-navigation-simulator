from dataclasses import dataclass


@dataclass
class DynamicObstacle:
    x: float
    y: float
    width: int
    height: int
    vx: float
    vy: float
    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def update(self, dt: float) -> None:
        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.x < self.min_x:
            self.x = self.min_x
            self.vx *= -1
        if self.x + self.width > self.max_x:
            self.x = self.max_x - self.width
            self.vx *= -1

        if self.y < self.min_y:
            self.y = self.min_y
            self.vy *= -1
        if self.y + self.height > self.max_y:
            self.y = self.max_y - self.height
            self.vy *= -1

    def touches_point(self, x: float, y: float) -> bool:
        return self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height

    def touches_cell(self, row: int, col: int, cell_size: int) -> bool:
        cell_left = col * cell_size
        cell_right = cell_left + cell_size
        cell_top = row * cell_size
        cell_bottom = cell_top + cell_size

        return not (
            self.x + self.width <= cell_left
            or self.x >= cell_right
            or self.y + self.height <= cell_top
            or self.y >= cell_bottom
        )

    def touches_circle(self, x: float, y: float, radius: int) -> bool:
        closest_x = min(max(x, self.x), self.x + self.width)
        closest_y = min(max(y, self.y), self.y + self.height)

        distance_x = x - closest_x
        distance_y = y - closest_y

        return distance_x * distance_x + distance_y * distance_y <= radius * radius
