from bridge.w3w_lookup import convert_coords_to_words

# Test with a known location, e.g., London Eye
result = convert_coords_to_words(51.503, -0.119)
print(f"what3words result: {result}")