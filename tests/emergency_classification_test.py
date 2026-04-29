
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from bridge.emergency_classifier import is_emergency, parse_sos

class TestEmergencyClassifier(unittest.TestCase):
    def test_valid_sos(self):
        """Test valid SOS message detection"""
        self.assertTrue(is_emergency('SOS|VER:1|ID:test|LAT:51.5|LON:-0.1'))
    
    def test_invalid_prefix(self):
        """Test non-SOS message is rejected"""
        self.assertFalse(is_emergency('LOC|VER:1|ID:test|LAT:51.5'))
    
    def test_old_timestamp(self):
        """Test old SOS (TS older than 5 min) is rejected"""
        import time
        old_ts = int(time.time()) - 301  # 5 minutes + 1 second
        self.assertFalse(is_emergency(f'SOS|TS:{old_ts}'))
    
    def test_parse_sos_extracts_data(self):
        """Test lat/lon/bat extraction"""
        result = parse_sos('SOS|VER:1|ID:abc123|LAT:51.509|LON:-0.118|BAT:3920')
        self.assertEqual(result['lat'], 51.509)
        self.assertEqual(result['lon'], -0.118)
        self.assertEqual(result['bat'], 3920)
        self.assertEqual(result['id'], 'abc123')

if __name__ == '__main__':
    unittest.main()