from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class PropertyState(Enum):
    GOOD = "bom-estado"
    NEEDS_REMODELING = "para-reformar"
    NEW = "com-novo"


class FurnitureType(Enum):
    INDIFFERENT = "indifferent"  # No URL parameter - show all apartments
    FURNISHED = "equipamento_mobilado"  # Fully furnished
    KITCHEN_FURNITURE = "equipamento_so-cozinha-equipada"  # Kitchen only


class SizeRange(Enum):
    """Size ranges in square meters (minimum size)"""

    SIZE_30_PLUS = 30
    SIZE_40_PLUS = 40
    SIZE_50_PLUS = 50
    SIZE_60_PLUS = 60
    SIZE_70_PLUS = 70
    SIZE_80_PLUS = 80
    SIZE_90_PLUS = 90
    SIZE_100_PLUS = 100
    SIZE_110_PLUS = 110
    SIZE_120_PLUS = 120
    SIZE_130_PLUS = 130
    SIZE_140_PLUS = 140
    SIZE_150_PLUS = 150

    def __init__(self, min_size: int):
        self.min_size = min_size
        self.max_size = 200  # Set a high maximum to include all sizes above minimum


@dataclass
class SearchConfig:
    # Basic filters
    min_rooms: int = 1  # Minimum number of rooms (will show this number and above)
    max_rooms: int = (
        10  # Maximum number of rooms (set high to include all above minimum)
    )
    min_size: int = 30
    max_size: int = 200
    max_price: int = 2000
    furniture_type: FurnitureType = FurnitureType.INDIFFERENT
    property_states: List[PropertyState] = None

    def __post_init__(self):
        if self.property_states is None:
            self.property_states = [PropertyState.GOOD]

    # Location
    city: str = "lisboa"
    custom_polygon: Optional[str] = None

    # Update frequency in minutes
    update_frequency: int = 5

    # Pagination settings
    max_pages: int = (
        3  # Maximum pages to scrape (1-5, higher values increase blocking risk)
    )

    # Rate limiting
    requests_per_minute: int = 2

    @classmethod
    def from_size_range(cls, size_range: SizeRange, **kwargs):
        """Create a SearchConfig with the given minimum size"""
        return cls(min_size=size_range.min_size, max_size=size_range.max_size, **kwargs)

    def to_url_params(self) -> str:
        """Convert configuration to Idealista URL parameters in the correct order"""
        params = []

        # 1. Price filter (always include, default 2000)
        price = self.max_price if self.max_price else 2000
        params.append(f"preco-max_{price}")

        # 2. Size filter (always include, default 20)
        min_size = self.min_size if self.min_size else 20
        params.append(f"tamanho-min_{min_size}")

        # 3. Room filters (default t0,t1,t2,t3,t4,t5 if not specified)
        if self.min_rooms == 0:
            room_types = [
                f"t{i}" for i in range(0, min(self.max_rooms + 1, 6))
            ]  # t0-t5 max
        else:
            room_types = [
                f"t{i}" for i in range(self.min_rooms, min(self.max_rooms + 1, 6))
            ]

        # Add room types following Idealista rules: t1, t2, t3, t4-t5 as separate parameters
        room_numbers = [int(rt[1:]) for rt in room_types]

        # Always add individual room parameters first (t0, t1, t2, t3)
        individual_rooms = []
        for room_num in room_numbers:
            if room_num <= 3:
                individual_rooms.append(f"t{room_num}")

        # Add individual room parameters
        if individual_rooms:
            params.extend(individual_rooms)

        # Add t4-t5 range as a separate parameter if needed
        has_t4_or_t5 = any(room_num >= 4 for room_num in room_numbers)
        if has_t4_or_t5:
            # Find the range of rooms >= 4
            high_rooms = [room_num for room_num in room_numbers if room_num >= 4]
            if high_rooms:
                min_high = min(high_rooms)
                max_high = min(max(high_rooms), 5)  # Cap at t5
                if min_high == max_high:
                    # Single room (e.g., just t4)
                    params.append(f"t{min_high}")
                else:
                    # Range (e.g., t4-t5)
                    params.append(f"t{min_high}-t{max_high}")

        # 4. Furniture filter (single choice)
        if self.furniture_type != FurnitureType.INDIFFERENT:
            params.append(self.furniture_type.value)

        # 5. Property states (only if any are specified)
        if self.property_states:
            state_values = []
            for state in self.property_states:
                if state == PropertyState.NEW:
                    state_values.append("novo")
                elif state == PropertyState.GOOD:
                    state_values.append("bom-estado")
                elif state == PropertyState.NEEDS_REMODELING:
                    state_values.append("para-reformar")

            if state_values:
                params.extend(
                    state_values
                )  # Add as separate parameters, not comma-separated

        # 6. Always add long-term rental filter
        params.append("arrendamento-longa-duracao")

        return ",".join(params)

    def get_base_url(self) -> str:
        """Get the base URL for Idealista search"""
        if self.custom_polygon:
            # For custom polygons, use the path-based filter format with /areas/ endpoint
            # Format: https://www.idealista.pt/areas/arrendar-casas/com-FILTERS/?shape=POLYGON
            import urllib.parse

            params = self.to_url_params()
            # URL-encode the polygon parameter to ensure special characters are properly encoded
            encoded_polygon = urllib.parse.quote(self.custom_polygon, safe="")
            return f"https://www.idealista.pt/areas/arrendar-casas/com-{params}/?shape={encoded_polygon}"
        else:
            # Build URL in the exact Idealista format for city-based searches
            params = self.to_url_params()
            return f"https://www.idealista.pt/arrendar-casas/{self.city}/com-{params}/"
