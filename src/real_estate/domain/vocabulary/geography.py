"""Spanish geography vocabulary keyed by official INE codes.

Using INE codes as canonical keys makes municipality/province references stable
and unambiguous across portals that spell names differently ("A Coruña" /
"La Coruña" / "Coruña"). See docs/architecture/02-domain-model.md §3.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Province(Enum):
    """The 52 Spanish provinces, keyed by their 2-digit INE province code.

    ``UNKNOWN`` (code ``"00"``) is the never-drop fallback for a province we
    could not resolve; it always comes with a logged normalization issue.
    """

    UNKNOWN = ("00", "Unknown")
    ARABA = ("01", "Araba/Álava")
    ALBACETE = ("02", "Albacete")
    ALICANTE = ("03", "Alicante/Alacant")
    ALMERIA = ("04", "Almería")
    AVILA = ("05", "Ávila")
    BADAJOZ = ("06", "Badajoz")
    ILLES_BALEARS = ("07", "Illes Balears")
    BARCELONA = ("08", "Barcelona")
    BURGOS = ("09", "Burgos")
    CACERES = ("10", "Cáceres")
    CADIZ = ("11", "Cádiz")
    CASTELLON = ("12", "Castellón/Castelló")
    CIUDAD_REAL = ("13", "Ciudad Real")
    CORDOBA = ("14", "Córdoba")
    A_CORUNA = ("15", "A Coruña")
    CUENCA = ("16", "Cuenca")
    GIRONA = ("17", "Girona")
    GRANADA = ("18", "Granada")
    GUADALAJARA = ("19", "Guadalajara")
    GIPUZKOA = ("20", "Gipuzkoa")
    HUELVA = ("21", "Huelva")
    HUESCA = ("22", "Huesca")
    JAEN = ("23", "Jaén")
    LEON = ("24", "León")
    LLEIDA = ("25", "Lleida")
    LA_RIOJA = ("26", "La Rioja")
    LUGO = ("27", "Lugo")
    MADRID = ("28", "Madrid")
    MALAGA = ("29", "Málaga")
    MURCIA = ("30", "Murcia")
    NAVARRA = ("31", "Navarra")
    OURENSE = ("32", "Ourense")
    ASTURIAS = ("33", "Asturias")
    PALENCIA = ("34", "Palencia")
    LAS_PALMAS = ("35", "Las Palmas")
    PONTEVEDRA = ("36", "Pontevedra")
    SALAMANCA = ("37", "Salamanca")
    SANTA_CRUZ_DE_TENERIFE = ("38", "Santa Cruz de Tenerife")
    CANTABRIA = ("39", "Cantabria")
    SEGOVIA = ("40", "Segovia")
    SEVILLA = ("41", "Sevilla")
    SORIA = ("42", "Soria")
    TARRAGONA = ("43", "Tarragona")
    TERUEL = ("44", "Teruel")
    TOLEDO = ("45", "Toledo")
    VALENCIA = ("46", "Valencia/València")
    VALLADOLID = ("47", "Valladolid")
    BIZKAIA = ("48", "Bizkaia")
    ZAMORA = ("49", "Zamora")
    ZARAGOZA = ("50", "Zaragoza")
    CEUTA = ("51", "Ceuta")
    MELILLA = ("52", "Melilla")

    def __init__(self, code: str, display_name: str) -> None:
        self._code = code
        self._display_name = display_name

    @property
    def code(self) -> str:
        """The 2-digit INE province code (e.g. ``"36"``)."""
        return self._code

    @property
    def display_name(self) -> str:
        """The human-readable province name."""
        return self._display_name

    @classmethod
    def from_code(cls, code: str) -> Province:
        """Resolve a province by its INE code, or ``UNKNOWN`` if unrecognized."""
        for province in cls:
            if province.code == code:
                return province
        return cls.UNKNOWN


@dataclass(frozen=True, slots=True)
class Municipality:
    """A Spanish municipality identified by its 5-digit INE code.

    The first two digits of the code are the province code, so a municipality
    belongs to exactly one province — validated at construction.
    """

    ine_code: str
    name: str

    def __post_init__(self) -> None:
        if len(self.ine_code) != 5 or not self.ine_code.isdigit():
            raise ValueError(f"Municipality INE code must be 5 digits, got {self.ine_code!r}")
        if Province.from_code(self.ine_code[:2]) is Province.UNKNOWN:
            raise ValueError(f"Municipality code {self.ine_code!r} has no valid province prefix")
        if not self.name.strip():
            raise ValueError("Municipality name must not be empty")

    @property
    def province(self) -> Province:
        """The province this municipality belongs to (from the code prefix)."""
        return Province.from_code(self.ine_code[:2])
