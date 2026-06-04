"""
Train Temporal Transformer for WORD detection (2 hands = 84 features, 30 frames)

This script trains the Temporal Transformer model that processes sequences of 30 frames
to capture temporal dynamics in sign language.

Usage:
1. Collect word images: python collect_word_imgs.py
2. Create dataset: python create_word_dataset.py or create_word_dataset_wlasl.py
3. Train temporal model: python train_temporal_transformer.py
"""

import pickle
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from collections import deque

# ==================== CONFIGURATION ====================
BATCH_SIZE = 32  # Increased batch size for better gradient estimates
EPOCHS = 150  # Increased epochs for better convergence
LEARNING_RATE = 0.0005  # Higher learning rate for faster convergence
HIDDEN_DIM = 256  # Temporal transformer uses 256 dim
NUM_HEADS = 8  # 8 attention heads
NUM_LAYERS = 6  # 6 transformer layers
NUM_FRAMES = 30  # Sequence length
DROPOUT = 0.3  # Reduced dropout for better capacity utilization
LABEL_SMOOTHING = 0.1  # Label smoothing to prevent overconfidence
GRADIENT_CLIP = 1.0  # Gradient clipping threshold
EARLY_STOPPING_PATIENCE = 25  # Early stopping patience
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print(f"Using device: {DEVICE}", flush=True)
print(f"Temporal Transformer Configuration:", flush=True)
print(f"  Hidden Dim: {HIDDEN_DIM}", flush=True)
print(f"  Attention Heads: {NUM_HEADS}", flush=True)
print(f"  Transformer Layers: {NUM_LAYERS}", flush=True)
print(f"  Sequence Length: {NUM_FRAMES} frames", flush=True)
print(f"  Dropout: {DROPOUT}", flush=True)
print(f"  Label Smoothing: {LABEL_SMOOTHING}", flush=True)
print(f"  Learning Rate: {LEARNING_RATE}", flush=True)
print(f"  Batch Size: {BATCH_SIZE}", flush=True)


# ==================== TEMPORAL TRANSFORMER MODEL ====================
class TemporalTransformer(nn.Module):
    """Temporal Transformer for sequence-based word recognition"""
    def __init__(self, input_dim=84, num_classes=300, hidden_dim=256,
                 num_heads=8, num_layers=6, dropout=0.4, num_frames=30):
        super().__init__()
        self.expects_sequence = True
        self.num_frames = num_frames
        self.hidden_dim = hidden_dim
        
        # Spatial encoder for each frame
        self.spatial_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout * 0.5)
        )
        
        # Frame positional encoding
        self.pos_encoding = nn.Parameter(torch.randn(1, num_frames, hidden_dim) * 0.02)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            activation='gelu',
            batch_first=True
        )
        self.temporal_transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        # Classifier head
        self.classifier = nn.Sequential(
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, num_classes)
        )
    
    def forward(self, x):
        # x: (batch, frames, 84)
        x = self.spatial_encoder(x)
        # Use only as many positional slots as frames provided
        x = x + self.pos_encoding[:, :x.shape[1], :]
        x = self.temporal_transformer(x)
        x = x.mean(dim=1)  # Mean pooling across frames
        return self.classifier(x)


# ==================== DATA LOADING ====================
print("\n" + "="*60, flush=True)
print("Loading WORD dataset...", flush=True)
print("="*60, flush=True)

try:
    data_dict = pickle.load(open('./data_word.pickle', 'rb'))
except FileNotFoundError:
    print("\nERROR: data_word.pickle not found!", flush=True)
    print("\nTo create word training data:", flush=True)
    print("1. Create folders in ./data_word/ for each word (e.g., 'hello', 'thanks', 'please')", flush=True)
    print("2. Collect images showing both hands for each word", flush=True)
    print("3. Run create_word_dataset.py to extract features", flush=True)
    exit(1)

if len(data_dict['data']) == 0:
    print("ERROR: Dataset is empty!", flush=True)
    exit(1)

data = np.array([np.array(item) for item in data_dict['data']], dtype=np.float32)
labels = np.array(data_dict['labels'])

print(f"Dataset loaded: {len(data)} samples", flush=True)
print(f"Feature vector size: {data.shape[1]} features (expected 84 for 2 hands)", flush=True)
print(f"Unique labels: {np.unique(labels)}", flush=True)

# Encode labels
label_encoder = LabelEncoder()
labels_encoded = label_encoder.fit_transform(labels)
num_classes = len(label_encoder.classes_)

print(f"Number of word classes: {num_classes}", flush=True)
print(f"Words: {list(label_encoder.classes_)}", flush=True)

# Scale features
scaler = StandardScaler()
data_scaled = scaler.fit_transform(data)

# ==================== CREATE SEQUENCES ====================
print("\n" + "="*60, flush=True)
print("Creating temporal sequences (30 frames per sample)...", flush=True)
print("="*60, flush=True)

def create_sequences(data, labels, sequence_length=30):
    """
    Create sequences by repeating each sample to form a sequence.
    In real application, these would be consecutive frames from video.
    For training, we create sequences by repeating the same frame.
    """
    sequences = []
    sequence_labels = []
    
    for i, (sample, label) in enumerate(zip(data, labels)):
        # Repeat the same frame to create a sequence
        # In production, these would be 30 consecutive frames from video
        sequence = np.tile(sample, (sequence_length, 1))  # (30, 84)
        sequences.append(sequence)
        sequence_labels.append(label)
    
    return np.array(sequences, dtype=np.float32), np.array(sequence_labels)

# Create sequences
sequences, sequence_labels = create_sequences(data_scaled, labels_encoded, NUM_FRAMES)
print(f"Created {len(sequences)} sequences", flush=True)
print(f"Sequence shape: {sequences.shape} (samples, {NUM_FRAMES} frames, 84 features)", flush=True)

# Train-test split
x_train, x_test, y_train, y_test = train_test_split(
    sequences, sequence_labels, test_size=0.2, shuffle=True, stratify=sequence_labels, random_state=42
)

print(f"Training samples: {len(x_train)}", flush=True)
print(f"Test samples: {len(x_test)}", flush=True)

# Create DataLoaders
train_dataset = TensorDataset(torch.FloatTensor(x_train), torch.LongTensor(y_train))
test_dataset = TensorDataset(torch.FloatTensor(x_test), torch.LongTensor(y_test))

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)


# ==================== MODEL TRAINING ====================
print("\n" + "="*60, flush=True)
print("Initializing Temporal Transformer model...", flush=True)
print("="*60, flush=True)

model = TemporalTransformer(
    input_dim=84,
    num_classes=num_classes,
    hidden_dim=HIDDEN_DIM,
    num_heads=NUM_HEADS,
    num_layers=NUM_LAYERS,
    dropout=DROPOUT,
    num_frames=NUM_FRAMES
).to(DEVICE)

print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}", flush=True)

# CrossEntropyLoss with label smoothing for better generalization
criterion = nn.CrossEntropyLoss(label_smoothing=LABEL_SMOOTHING)
optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)

# Use ReduceLROnPlateau for adaptive learning rate scheduling
scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
    optimizer, mode='max', factor=0.5, patience=10, min_lr=1e-6
)

print(f"\nTraining for {EPOCHS} epochs...", flush=True)
print("=" * 60, flush=True)

best_accuracy = 0.0
patience_counter = 0
best_epoch = 0

for epoch in range(EPOCHS):
    # Training
    model.train()
    train_loss = 0.0
    train_correct = 0
    
    for batch_x, batch_y in train_loader:
        batch_x, batch_y = batch_x.to(DEVICE), batch_y.to(DEVICE)
        
        optimizer.zero_grad()
        outputs = model(batch_x)  # (batch, 30, 84) -> (batch, num_classes)
        loss = criterion(outputs, batch_y)
        loss.backward()
        
        # Gradient clipping to prevent exploding gradients
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=GRADIENT_CLIP)
        
        optimizer.step()
        
        train_loss += loss.item()
        _, predicted = torch.max(outputs, 1)
        train_correct += (predicted == batch_y).sum().item()
    
    train_acc = 100 * train_correct / len(x_train)
    
    # Evaluation
    model.eval()
    test_correct = 0
    
    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            batch_x, batch_y = batch_x.to(DEVICE), batch_y.to(DEVICE)
            outputs = model(batch_x)
            _, predicted = torch.max(outputs, 1)
            test_correct += (predicted == batch_y).sum().item()
    
    test_acc = 100 * test_correct / len(x_test)
    
    # Update learning rate scheduler based on validation accuracy
    old_lr = optimizer.param_groups[0]['lr']
    scheduler.step(test_acc)
    new_lr = optimizer.param_groups[0]['lr']
    
    # Print if learning rate was reduced
    if new_lr < old_lr:
        print(f"📉 Learning rate reduced: {old_lr:.6f} → {new_lr:.6f}", flush=True)
    
    # Save best model and early stopping logic
    if test_acc > best_accuracy:
        best_accuracy = test_acc
        patience_counter = 0
        best_epoch = epoch
        torch.save(model.state_dict(), 'temporal_transformer_model.pth')
        
        # Save preprocessing with num_frames info
        with open('preprocessing_word.pkl', 'wb') as f:
            pickle.dump({
                'scaler': scaler,
                'encoder': label_encoder,
                'label_encoder': label_encoder,  # Alias for compatibility
                'num_frames': NUM_FRAMES
            }, f)
        
        # Print when new best accuracy is achieved
        print(f"★ NEW BEST! Test Accuracy: {best_accuracy:.2f}% (Model saved)", flush=True)
    else:
        patience_counter += 1
        if patience_counter >= EARLY_STOPPING_PATIENCE:
            print(f"\n{'='*60}", flush=True)
            print(f"Early stopping triggered at epoch {epoch+1}", flush=True)
            print(f"Best accuracy: {best_accuracy:.2f}% achieved at epoch {best_epoch+1}", flush=True)
            print(f"{'='*60}\n", flush=True)
            break
    
    if (epoch + 1) % 10 == 0 or epoch == 0:
        current_lr = optimizer.param_groups[0]['lr']
        print(f"Epoch [{epoch+1:3d}/{EPOCHS}] | Train Acc: {train_acc:.2f}% | Test Acc: {test_acc:.2f}% | Best: {best_accuracy:.2f}% | LR: {current_lr:.6f}", flush=True)

print("=" * 60, flush=True)
print(f"\nTraining completed!", flush=True)
print(f"Best accuracy: {best_accuracy:.2f}%", flush=True)
print(f"Model saved as 'temporal_transformer_model.pth'", flush=True)
print(f"Preprocessing saved as 'preprocessing_word.pkl' (with num_frames={NUM_FRAMES})", flush=True)
print(f"\nModel Architecture:", flush=True)
print(f"  - Temporal Transformer (256/8/6)", flush=True)
print(f"  - Sequence Length: {NUM_FRAMES} frames", flush=True)
print(f"  - Input: (batch, {NUM_FRAMES}, 84)", flush=True)
print(f"  - Output: (batch, {num_classes})", flush=True)

