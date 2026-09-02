import torch
from torchvision import transforms
from PIL import Image

def load_and_preprocess_image(image_path, image_size=224):
    """Load an image from disk and apply preprocessing transforms.
    
    Args:
        image_path (str): Path to the image file.
        image_size (int): Desired size for the shorter edge after resizing.
        
    Returns:
        torch.Tensor: Preprocessed image tensor of shape (C, H, W).
    """
    # Define preprocessing transforms (same as used in BLIP training)
    transform = transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], 
                             std=[0.229, 0.224, 0.225])
    ])
    
    image = Image.open(image_path).convert('RGB')
    return transform(image).unsqueeze(0)  # Add batch dimension

def denormalize_image(tensor):
    """Convert a normalized tensor back to a PIL image for visualization.
    
    Args:
        tensor (torch.Tensor): Normalized image tensor of shape (C, H, W) or (1, C, H, W).
        
    Returns:
        PIL.Image: Denormalized image.
    """
    if tensor.dim() == 4:
        tensor = tensor.squeeze(0)
    
    # Denormalize
    mean = torch.tensor([0.485, 0.456, 0.406]).view(3, 1, 1)
    std = torch.tensor([0.229, 0.224, 0.225]).view(3, 1, 1)
    tensor = tensor * std + mean
    
    # Clamp to [0, 1] and convert to PIL
    tensor = torch.clamp(tensor, 0, 1)
    return transforms.ToPILImage()(tensor)