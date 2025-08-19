#!/usr/bin/env python3
import argparse
import sys
import time
from dataclasses import dataclass
from typing import Generator, Iterable, List, Optional, Tuple


Coordinate = Tuple[int, int]


@dataclass
class GridField:
    """Represents a rectangular field subdivided into cells.

    The field uses zero-based coordinates with origin at the top-left corner.
    """

    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Field dimensions must be positive integers")
        self._harvested: List[List[bool]] = [
            [False for _ in range(self.width)] for _ in range(self.height)
        ]

    def is_within_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def mark_harvested(self, x: int, y: int) -> None:
        if not self.is_within_bounds(x, y):
            raise IndexError("Attempted to harvest out-of-bounds cell")
        self._harvested[y][x] = True

    def is_harvested(self, x: int, y: int) -> bool:
        if not self.is_within_bounds(x, y):
            raise IndexError("Attempted to query out-of-bounds cell")
        return self._harvested[y][x]

    def all_harvested(self) -> bool:
        for row in self._harvested:
            for cell in row:
                if not cell:
                    return False
        return True

    def __str__(self) -> str:
        return f"GridField(width={self.width}, height={self.height})"


@dataclass
class Combine:
    """A simple combine that moves cell-by-cell and harvests the current cell."""

    field: GridField
    position: Coordinate
    harvested_cells: int = 0

    def __post_init__(self) -> None:
        x, y = self.position
        if not self.field.is_within_bounds(x, y):
            raise ValueError("Initial position is out of field bounds")
        self._harvest_current()

    def move_to(self, x: int, y: int) -> None:
        if not self.field.is_within_bounds(x, y):
            raise ValueError("Move target out of bounds")
        self.position = (x, y)
        self._harvest_current()

    def _harvest_current(self) -> None:
        x, y = self.position
        if not self.field.is_harvested(x, y):
            self.field.mark_harvested(x, y)
            self.harvested_cells += 1


def plan_boustrophedon_path(
    field: GridField,
    start: Coordinate = (0, 0),
    left_to_right_first_row: bool = True,
) -> List[Coordinate]:
    """Generate a full-coverage boustrophedon (serpentine) path.

    The path covers each cell exactly once. Start coordinate will be placed at the
    beginning of the planned path; if it does not align with the serpentine order,
    the path will be rotated so that it begins at `start`.
    """
    # Build the canonical serpentine order
    canonical: List[Coordinate] = []
    for row in range(field.height):
        is_left_to_right = (row % 2 == 0) == left_to_right_first_row
        xs = range(field.width) if is_left_to_right else range(field.width - 1, -1, -1)
        for x in xs:
            canonical.append((x, row))

    # Rotate path so that it starts at the requested start if possible
    if start in canonical:
        start_index = canonical.index(start)
        rotated = canonical[start_index:] + canonical[:start_index]
        return rotated
    else:
        # Fallback: if start is outside, just return canonical; caller will error on move
        return canonical


def animate(
    field: GridField,
    combine: Combine,
    path: Iterable[Coordinate],
    delay_seconds: float = 0.05,
    harvested_char: str = "·",
    unharvested_char: str = "░",
    combine_char: str = "C",
) -> None:
    """Render an ASCII animation of the combine moving and harvesting the field."""
    for target in path:
        combine.move_to(*target)
        render(field, combine, harvested_char, unharvested_char, combine_char)
        time.sleep(delay_seconds)


def render(
    field: GridField,
    combine: Combine,
    harvested_char: str = "·",
    unharvested_char: str = "░",
    combine_char: str = "C",
) -> None:
    # Clear screen (ANSI escape). Works in most terminals.
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

    combine_x, combine_y = combine.position
    lines: List[str] = []
    for y in range(field.height):
        row_chars: List[str] = []
        for x in range(field.width):
            if x == combine_x and y == combine_y:
                row_chars.append(combine_char)
            else:
                row_chars.append(harvested_char if field.is_harvested(x, y) else unharvested_char)
        lines.append("".join(row_chars))

    border = "#" * (field.width + 2)
    print(border)
    for line in lines:
        print(f"#{line}#")
    print(border)
    print(
        f"Position: {combine.position} | Harvested: {combine.harvested_cells}/{field.width * field.height}"
    )


def run_simulation(
    width: int,
    height: int,
    start_x: int,
    start_y: int,
    left_to_right_first_row: bool,
    animate_enabled: bool,
    delay_seconds: float,
) -> None:
    field = GridField(width=width, height=height)
    combine = Combine(field=field, position=(start_x, start_y))
    path = plan_boustrophedon_path(
        field=field,
        start=(start_x, start_y),
        left_to_right_first_row=left_to_right_first_row,
    )

    # Skip the first step if it is the starting cell which is already harvested on init
    steps: List[Coordinate] = path[1:]

    if animate_enabled:
        animate(field, combine, steps, delay_seconds=delay_seconds)
    else:
        for step in steps:
            combine.move_to(*step)

        # Final static render
        render(field, combine)


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Simulate a combine harvesting a field using a boustrophedon path.",
    )
    parser.add_argument("--width", type=int, default=20, help="Field width in cells")
    parser.add_argument("--height", type=int, default=10, help="Field height in cells")
    parser.add_argument("--start-x", type=int, default=0, help="Starting X coordinate (0-based)")
    parser.add_argument("--start-y", type=int, default=0, help="Starting Y coordinate (0-based)")
    parser.add_argument(
        "--right-first",
        action="store_true",
        help="If set, the first row goes left-to-right; otherwise right-to-left",
    )
    parser.add_argument(
        "--animate",
        action="store_true",
        help="Enable ASCII animation instead of static result",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.05,
        help="Animation delay between steps in seconds",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> None:
    args = parse_args(argv)
    run_simulation(
        width=args.width,
        height=args.height,
        start_x=args.start_x,
        start_y=args.start_y,
        left_to_right_first_row=args.right_first,
        animate_enabled=args.animate,
        delay_seconds=args.delay,
    )


if __name__ == "__main__":
    main()

