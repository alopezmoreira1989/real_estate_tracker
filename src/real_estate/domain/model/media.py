"""Media value object: images and videos attached to a listing."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Media:
    """Immutable collections of image and video URLs.

    Tuples keep the value object hashable and immutable. URLs must be absolute
    http(s) links; anything else is rejected at construction.
    """

    images: tuple[str, ...] = field(default_factory=tuple)
    videos: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for url in (*self.images, *self.videos):
            if not url.startswith(("http://", "https://")):
                raise ValueError(f"media URL must be absolute http(s), got {url!r}")
