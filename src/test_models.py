import pytest
from models import SearchConfig, PropertyState, FurnitureType


class TestSearchConfig:
    """Test SearchConfig model and URL generation"""
    
    def test_default_config(self):
        """Test default configuration values"""
        config = SearchConfig()
        
        assert config.min_rooms == 1
        assert config.max_rooms == 10
        assert config.min_size == 30
        assert config.max_size == 200
        assert config.max_price == 2000
        assert config.furniture_types == [FurnitureType.FURNISHED]
        assert config.property_states == [PropertyState.GOOD]
        assert config.city == "lisboa"
        assert config.custom_polygon is None
        assert config.update_frequency == 5
    
    def test_room_filter_generation(self):
        """Test room filter URL parameter generation"""
        # Test default rooms (1-5)
        config = SearchConfig()
        config.min_rooms = 1
        config.max_rooms = 5
        params = config.to_url_params()
        assert "t1,t2,t3,t4-t5" in params
        
        # Test single room
        config.min_rooms = 2
        config.max_rooms = 2
        params = config.to_url_params()
        assert "t2" in params
        
        # Test two consecutive rooms
        config.min_rooms = 3
        config.max_rooms = 4
        params = config.to_url_params()
        assert "t3,t4" in params
        
        # Test T0 (studio) support
        config.min_rooms = 0
        config.max_rooms = 2
        params = config.to_url_params()
        assert "t0,t1,t2" in params
    
    def test_price_filter_generation(self):
        """Test price filter URL parameter generation"""
        config = SearchConfig()
        config.max_price = 1500
        params = config.to_url_params()
        assert "preco-max_1500" in params
        
        # Test default price
        config.max_price = None
        params = config.to_url_params()
        assert "preco-max_2000" in params
    
    def test_size_filter_generation(self):
        """Test size filter URL parameter generation"""
        config = SearchConfig()
        config.min_size = 60
        params = config.to_url_params()
        assert "tamanho-min_60" in params
        
        # Test default size
        config.min_size = None
        params = config.to_url_params()
        assert "tamanho-min_20" in params or "tamanho-min_30" in params
    
    def test_furniture_filter_generation(self):
        """Test furniture filter URL parameter generation"""
        # Test furnished only
        config = SearchConfig()
        config.furniture_types = [FurnitureType.FURNISHED]
        params = config.to_url_params()
        assert "equipamento_mobilado" in params
        
        # Test kitchen furniture only
        config.furniture_types = [FurnitureType.KITCHEN_FURNITURE]
        params = config.to_url_params()
        assert "equipamento_so-cozinha-equipada" in params
        
        # Test unfurnished only (should not add furniture parameter)
        config.furniture_types = [FurnitureType.UNFURNISHED]
        params = config.to_url_params()
        assert "equipamento_mobilado" not in params
        assert "equipamento_so-cozinha-equipada" not in params
        
        # Test multiple furniture types
        config.furniture_types = [FurnitureType.FURNISHED, FurnitureType.KITCHEN_FURNITURE]
        params = config.to_url_params()
        assert "equipamento_mobilado" in params
        assert "equipamento_so-cozinha-equipada" in params
    
    def test_property_state_filter_generation(self):
        """Test property state filter URL parameter generation"""
        # Test single state
        config = SearchConfig()
        config.property_states = [PropertyState.GOOD]
        params = config.to_url_params()
        assert "bom-estado" in params
        
        # Test new state
        config.property_states = [PropertyState.NEW]
        params = config.to_url_params()
        assert "novo" in params
        
        # Test remodeling state
        config.property_states = [PropertyState.NEEDS_REMODELING]
        params = config.to_url_params()
        assert "para-reformar" in params
        
        # Test multiple states
        config.property_states = [PropertyState.GOOD, PropertyState.NEW]
        params = config.to_url_params()
        assert "bom-estado" in params
        assert "novo" in params
    
    def test_complete_url_generation(self):
        """Test complete URL generation with all parameters"""
        config = SearchConfig()
        config.max_price = 1100
        config.min_size = 60
        config.min_rooms = 1
        config.max_rooms = 5
        config.furniture_types = [FurnitureType.FURNISHED]
        config.property_states = [PropertyState.NEW, PropertyState.GOOD]
        config.city = "lisboa"
        
        url = config.get_base_url()
        expected_parts = [
            "https://www.idealista.pt/arrendar-casas/lisboa/com-",
            "preco-max_1100",
            "tamanho-min_60", 
            "t1,t2,t3,t4-t5",
            "equipamento_mobilado",
            "novo",
            "bom-estado",
            "arrendamento-longa-duracao"
        ]
        
        for part in expected_parts:
            assert part in url
    
    def test_custom_polygon_url(self):
        """Test URL generation with custom polygon"""
        config = SearchConfig()
        config.custom_polygon = "test_polygon_data"
        
        url = config.get_base_url()
        assert "areas/arrendar-casas" in url
        assert "shape=test_polygon_data" in url
    
    def test_parameter_order(self):
        """Test that URL parameters are in the correct order"""
        config = SearchConfig()
        config.max_price = 1000
        config.min_size = 50
        config.min_rooms = 2
        config.max_rooms = 4
        config.furniture_types = [FurnitureType.FURNISHED]
        config.property_states = [PropertyState.GOOD]
        
        params = config.to_url_params()
        parts = params.split(",")
        
        # Price should be first
        assert parts[0].startswith("preco-max_")
        # Size should be second
        assert parts[1].startswith("tamanho-min_")
        # Rooms should be third
        assert any("t" in part for part in parts[2:5])
        # Should end with long-term rental
        assert parts[-1] == "arrendamento-longa-duracao"


class TestFurnitureType:
    """Test FurnitureType enum"""
    
    def test_furniture_values(self):
        """Test furniture type enum values"""
        assert FurnitureType.FURNISHED.value == "mobilado"
        assert FurnitureType.KITCHEN_FURNITURE.value == "mobilado-cozinha"
        assert FurnitureType.UNFURNISHED.value == "sem-mobilia"


class TestPropertyState:
    """Test PropertyState enum"""
    
    def test_property_state_values(self):
        """Test property state enum values"""
        assert PropertyState.GOOD.value == "bom-estado"
        assert PropertyState.NEW.value == "com-novo"
        assert PropertyState.NEEDS_REMODELING.value == "para-reformar"