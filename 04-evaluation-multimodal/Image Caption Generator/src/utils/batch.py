# Batch processing utilities
def process_batch(image_paths, model, batch_size=8):
    # Placeholder
    results = []
    for i in range(0, len(image_paths), batch_size):
        batch = image_paths[i:i+batch_size]
        # process...
        for img in batch:
            results.append("caption")
    return results