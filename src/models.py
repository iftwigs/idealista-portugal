from dataclasses import dataclass
from typing import Optional, List
from enum import Enum

class PropertyState(Enum):
    GOOD = "bom-estado"
    NEEDS_REMODELING = "para-reformar"
    NEW = "com-novo"

class FurnitureType(Enum):
    FURNISHED = "mobilado"
    KITCHEN_FURNITURE = "mobilado-cozinha"
    UNFURNISHED = "sem-mobilia"

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
    max_rooms: int = 10  # Maximum number of rooms (set high to include all above minimum)
    min_size: int = 30
    max_size: int = 200
    max_price: int = 2000
    furniture_types: List[FurnitureType] = None
    property_states: List[PropertyState] = None
    
    def __post_init__(self):
        if self.property_states is None:
            self.property_states = [PropertyState.GOOD]
        if self.furniture_types is None:
            self.furniture_types = [FurnitureType.FURNISHED]
    
    # Location
    city: str = "lisboa"
    custom_polygon: Optional[str] = None
    
    # Update frequency in minutes
    update_frequency: int = 5
    
    # Rate limiting
    requests_per_minute: int = 2

    @classmethod
    def from_size_range(cls, size_range: SizeRange, **kwargs):
        """Create a SearchConfig with the given minimum size"""
        return cls(
            min_size=size_range.min_size,
            max_size=size_range.max_size,
            **kwargs
        )
    
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
            room_types = [f"t{i}" for i in range(0, min(self.max_rooms + 1, 6))]  # t0-t5 max
        else:
            room_types = [f"t{i}" for i in range(self.min_rooms, min(self.max_rooms + 1, 6))]
        
        # Add room types in Idealista format: t1,t2,t3,t4-t5 style
        room_numbers = [int(rt[1:]) for rt in room_types]
        
        if len(room_numbers) <= 3:
            # For 3 or fewer rooms, list them all individually
            params.append(",".join(room_types))
        else:
            # For more than 3 rooms, use specific Idealista formatting
            # Always compress the last two into a range when we have 4+ rooms
            if len(room_numbers) == 4:
                # Special case: t2,t3,t4-t5 format
                individual_rooms = [f"t{i}" for i in room_numbers[:2]]  # First 2
                range_part = f"t{room_numbers[2]}-t{room_numbers[3]}"   # Last 2 as range
                all_parts = individual_rooms + [range_part]
                params.append(",".join(all_parts))
            else:
                # For 5+ rooms, list first 2 individually, then compress the rest
                individual_rooms = [f"t{i}" for i in room_numbers[:2]]
                remaining_rooms = room_numbers[2:]
                range_part = f"t{remaining_rooms[0]}-t{remaining_rooms[-1]}"
                all_parts = individual_rooms + [range_part]
                params.append(",".join(all_parts))
        
        # 4. Furniture filter (only if specified and not UNFURNISHED only)
        if self.furniture_types and FurnitureType.UNFURNISHED not in self.furniture_types:
            furniture_params = []
            if FurnitureType.FURNISHED in self.furniture_types:
                furniture_params.append("equipamento_mobilado")
            if FurnitureType.KITCHEN_FURNITURE in self.furniture_types:
                furniture_params.append("equipamento_so-cozinha-equipada")
            
            # Add furniture parameters
            params.extend(furniture_params)
        
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
                params.extend(state_values)  # Add as separate parameters, not comma-separated
        
        # 6. Always add long-term rental filter
        params.append("arrendamento-longa-duracao")
        
        return ",".join(params)
    
    def get_base_url(self) -> str:
        """Get the base URL for Idealista search"""
        if self.custom_polygon:
            return f"https://www.idealista.pt/areas/arrendar-casas/com-{self.to_url_params()}/?shape={self.custom_polygon}"
        else:
            # Build URL in the exact Idealista format
            params = self.to_url_params()
            return f"https://www.idealista.pt/arrendar-casas/{self.city}/com-{params}/" 