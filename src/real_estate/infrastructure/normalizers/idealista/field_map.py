"""Idealista's raw listing field names -> canonical Property fields.

Data, not code (docs/architecture/05-normalization.md §3): adding/adjusting a
field is a dictionary edit, never a change to :class:`BaseNormalizer`.
"""

from __future__ import annotations

IDEALISTA_FIELD_MAP: dict[str, str] = {
    "precio": "price",
    "superficie": "area",
    "superficie_solar": "plot_area",
    "habitaciones": "rooms",
    "banos": "bathrooms",
    "tipo": "property_type",
    "tipo_suelo": "land_type",
    "operacion": "listing_type",
    "provincia": "province",
    "titulo": "title",
    "descripcion": "description",
    "ascensor": "features.has_lift",
    "terraza": "features.has_terrace",
    "jardin": "features.has_garden",
    "parking": "features.has_parking",
    "piscina": "features.has_pool",
    "obra_nueva": "features.is_new_build",
    "imagenes": "media.images",
    "videos": "media.videos",
}
