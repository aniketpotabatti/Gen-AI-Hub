import torch
from torch.utils.data import Dataset
import random

class DummyCaptionDataset(Dataset):
    """A dummy dataset that returns random images and captions for quick testing."""
    
    def __init__(self, size=100, image_size=224, vocab_size=50257, max_caption_len=20):
        self.size = size
        self.image_size = image_size
        self.vocab_size = vocab_size
        self.max_caption_len = max_caption_len
        
    def __len__(self):
        return self.size
    
    def __getitem__(self, idx):
        # Random image tensor (C, H, W)
        image = torch.randn(3, self.image_size, self.image_size)
        # Random caption token ids (including BOS/EOS? we just use random length)
        caption_len = random.randint(5, self.max_caption_len)
        caption = torch.randint(0, self.vocab_size, (caption_len,))
        return image, caption

def collate_fn(batch):
    """Collate function to pad captions to the same length."""
    images, captions = zip(*batch)
    images = torch.stack(images, dim=0)
    
    # Pad captions
    max_len = max(len(c) for c in captions)
    padded_captions = torch.full((len(captions), max_len), 0, dtype=torch.long)  # pad with 0
    for i, cap in enumerate(captions):
        padded_captions[i, :len(cap)] = cap
    return images, padded_captions