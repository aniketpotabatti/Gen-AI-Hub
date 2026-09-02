import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from src.utils.model_loader import get_model
from src.utils.dataset import DummyCaptionDataset, collate_fn
from src.utils.image_utils import load_and_preprocess_image
import argparse
import os

def train(args):
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Model
    model = get_model(device=device)
    model.train()
    
    # Optimizer & loss
    optimizer = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    criterion = nn.CrossEntropyLoss(ignore_index=0)  # ignore padding token
    
    # Dataset & DataLoader
    train_dataset = DummyCaptionDataset(
        size=args.dataset_size,
        image_size=args.image_size,
        vocab_size=50257,  # GPT-2 vocab size
        max_caption_len=args.max_caption_len
    )
    train_loader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=args.num_workers,
        collate_fn=collate_fn,
        pin_memory=True
    )
    
    # Training loop
    for epoch in range(args.epochs):
        epoch_loss = 0.0
        for batch_idx, (images, captions) in enumerate(train_loader):
            images = images.to(device)
            captions = captions.to(device)
            
            # Forward pass
            optimizer.zero_grad()
            attention_mask = (captions != 0).long()
            logits = model(images, captions, attention_mask)  # (B, seq_len, vocab_size)
            shift_logits = logits[:, :-1, :].contiguous()
            shift_labels = captions[:, 1:].contiguous()
            loss = criterion(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
            
            # Backward pass
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            
            if batch_idx % args.log_interval == 0:
                print(f"Epoch [{epoch+1}/{args.epochs}] Batch [{batch_idx}/{len(train_loader)}] "
                      f"Loss: {loss.item():.4f}")
        
        avg_loss = epoch_loss / len(train_loader)
        print(f"Epoch [{epoch+1}/{args.epochs}] Average Loss: {avg_loss:.4f}")
        
        # Save checkpoint
        if (epoch + 1) % args.save_interval == 0:
            ckpt_path = os.path.join(args.checkpoint_dir, f"model_epoch_{epoch+1}.pt")
            torch.save({
                'epoch': epoch + 1,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'loss': avg_loss,
            }, ckpt_path)
            print(f"Checkpoint saved to {ckpt_path}")

def main():
    parser = argparse.ArgumentParser(description="Train Image Caption Generator (dummy data)")
    parser.add_argument('--epochs', type=int, default=5, help='Number of training epochs')
    parser.add_argument('--batch_size', type=int, default=8, help='Batch size')
    parser.add_argument('--lr', type=float, default=1e-4, help='Learning rate')
    parser.add_argument('--weight_decay', type=float, default=0.01, help='Weight decay')
    parser.add_argument('--dataset_size', type=int, default=200, help='Size of dummy dataset')
    parser.add_argument('--image_size', type=int, default=224, help='Image size')
    parser.add_argument('--max_caption_len', type=int, default=30, help='Maximum caption length')
    parser.add_argument('--num_workers', type=int, default=2, help='Number of DataLoader workers')
    parser.add_argument('--log_interval', type=int, default=10, help='Log every N batches')
    parser.add_argument('--save_interval', type=int, default=2, help='Save checkpoint every N epochs')
    parser.add_argument('--checkpoint_dir', type=str, default='checkpoints', help='Directory to save checkpoints')
    args = parser.parse_args()
    
    os.makedirs(args.checkpoint_dir, exist_ok=True)
    train(args)

if __name__ == "__main__":
    main()