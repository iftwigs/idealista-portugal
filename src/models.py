from dataclasses import dataclass
from typing import Optional
from enum import Enum

class PropertyState(Enum):
    GOOD = "bom-estado"
    NEEDS_REMODELING = "para-reformar"
    NEW = "com-novo"

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
    has_furniture: bool = True
    property_state: PropertyState = PropertyState.GOOD
    
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
        """Convert configuration to Idealista URL parameters"""
        params = []
        
        # Add room filters - include all room types from min_rooms up to max_rooms
        room_types = [f"t{i}" for i in range(self.min_rooms, self.max_rooms + 1)]
        params.append(",".join(room_types))
        
        # Add size filter
        params.append(f"tamanho-min_{self.min_size}")
        
        # Add price filter
        params.append(f"preco-max_{self.max_price}")
        
        # Add furniture filter
        if self.has_furniture:
            params.append("equipamento_mobilado")
            
        # Add property state
        params.append(self.property_state.value)
        
        return ",".join(params)
    
    def get_base_url(self) -> str:
        """Get the base URL for Idealista search"""
        if self.custom_polygon:
            return f"https://www.idealista.pt/areas/arrendar-casas/com-{self.to_url_params()}/?shape={self.custom_polygon}&ordem=atualizado-desc"
        else:
            return f"https://www.idealista.pt/arrendar-casas/{self.city}/com-{self.to_url_params()}/?ordem=atualizado-desc" 