import pytest
import sys
import os

# Add src to path
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_path = os.path.join(current_dir, 'src')
sys.path.insert(0, src_path)

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
        assert config.furniture_type == FurnitureType.ANY  # Updated default
        assert config.property_states == [PropertyState.GOOD]
        assert config.city == "lisboa"
        assert config.custom_polygon is None
        assert config.max_pages == 3
    
    def test_furniture_filter_url_generation(self):
        """Test furniture filter URL parameter generation"""
        
        # Test FURNISHED
        config1 = SearchConfig(furniture_type=FurnitureType.FURNISHED)
        url1 = config1.get_base_url()
        assert "equipamento_mobilado" in url1
        
        # Test KITCHEN_FURNITURE
        config2 = SearchConfig(furniture_type=FurnitureType.KITCHEN_FURNITURE)
        url2 = config2.get_base_url()
        assert "equipamento_so-cozinha-equipada" in url2
        
        # Test ANY (no filter) - should NOT add furniture params
        config3 = SearchConfig(furniture_type=FurnitureType.ANY)
        url3 = config3.get_base_url()
        assert "equipamento" not in url3
    
    def test_room_parameter_generation(self):
        """Test room parameter generation following Idealista rules"""
        
        # Test t1, t2, t3 (individual parameters)
        config1 = SearchConfig(min_rooms=1, max_rooms=3)
        url1 = config1.get_base_url()
        assert "t1,t2,t3" in url1
        
        # Test t4-t5 (range parameter)
        config2 = SearchConfig(min_rooms=4, max_rooms=5)
        url2 = config2.get_base_url()
        assert "t4-t5" in url2
        
        # Test mixed: t1,t2,t3,t4-t5
        config3 = SearchConfig(min_rooms=1, max_rooms=5)
        url3 = config3.get_base_url()
        assert "t1,t2,t3,t4-t5" in url3
        
        # Test t0 included
        config4 = SearchConfig(min_rooms=0, max_rooms=2)
        url4 = config4.get_base_url()
        assert "t0,t1,t2" in url4
    
    def test_custom_polygon_url(self):
        """Test custom polygon URL generation"""
        config = SearchConfig()
        config.custom_polygon = "((test_polygon))"
        url = config.get_base_url()
        
        assert "idealista.pt/areas/arrendar-casas/com-" in url
        assert "shape=" in url
        assert "test_polygon" in url
    
    def test_city_based_url(self):
        """Test city-based URL generation"""
        config = SearchConfig(city="porto")
        url = config.get_base_url()
        
        assert "idealista.pt/arrendar-casas/porto/com-" in url
        assert "shape=" not in url