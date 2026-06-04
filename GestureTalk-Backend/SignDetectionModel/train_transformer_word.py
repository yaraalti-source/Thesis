"""
Train Transformer-MLP for WORD detection (2 hands = 84 features)

Usage:
1. Collect word images: python collect_word_imgs.py
2. Create dataset: python create_word_dataset.py  
3. Train model: python train_transformer_word.py
"""

import pickle
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler

# ==================== CONFIGURATION ====================
BATCH_SIZE = 32
EPOCHS = 100
LEARNING_RATE = 0.001
HIDDEN_DIM = 64
NUM_HEADS = 4
NUM_LAYERS = 2
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

print(f"Using device: {DEVICE}", flush=True)


# ==================== MODEL DEFINITION ====================
class TransformerMLPWord(nn.Module):
    """Transformer-MLP for two hands (84 features) - WORD detection"""
    def __init__(self, input_dim=84, num_classes=10, hidden_dim=64, num_heads=4, num_layers=2):
        super(TransformerMLPWord, self).__init__()
        
        self.num_landmarks = 21
        self.features_per_landmark = 4  # x,y for left + x,y for right per landmark
        
        self.input_linear = nn.Linear(self.features_per_landmark, hidden_dim)
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=128,
            dropout=0.1,
            activation='relu',
            batch_first=True
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        
        self.mlp = nn.Sequential(
            nn.Linear(self.num_landmarks * hidden_dim, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes)
        )
    
    def forward(self, x):
        batch_size = x.shape[0]
        # Reshape: (batch, 84) -> (batch, 21, 4)
        # Each landmark has 4 features: left_x, left_y, right_x, right_y
        x = x.view(batch_size, self.num_landmarks, self.features_per_landmark)
        x = self.input_linear(x)
        x = self.transformer(x)
        x = x.view(batch_size, -1)
        x = self.mlp(x)
        return x


# ==================== DATA LOADING ====================
print("Loading WORD dataset...", flush=True)

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

# Train-test split
x_train, x_test, y_train, y_test = train_test_split(
    data_scaled, labels_encoded, test_size=0.2, shuffle=True, stratify=labels_encoded, random_state=42
)

print(f"Training samples: {len(x_train)}", flush=True)
print(f"Test samples: {len(x_test)}", flush=True)

# Create DataLoaders
train_dataset = TensorDataset(torch.FloatTensor(x_train), torch.LongTensor(y_train))
test_dataset = TensorDataset(torch.FloatTensor(x_test), torch.LongTensor(y_test))

train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)


# ==================== MODEL TRAINING ====================
print("\nInitializing Transformer-MLP WORD model...", flush=True)
model = TransformerMLPWord(
    input_dim=data.shape[1],
    num_classes=num_classes,
    hidden_dim=HIDDEN_DIM,
    num_heads=NUM_HEADS,
    num_layers=NUM_LAYERS
).to(DEVICE)

print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}", flush=True)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=0.01)
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

print(f"\nTraining for {EPOCHS} epochs...", flush=True)
print("=" * 60, flush=True)

best_accuracy = 0.0

for epoch in range(EPOCHS):
    # Training
    model.train()
    train_loss = 0.0
    train_correct = 0
    
    for batch_x, batch_y in train_loader:
        batch_x, batch_y = batch_x.to(DEVICE), batch_y.to(DEVICE)
        
        optimizer.zero_grad()
        outputs = model(batch_x)
        loss = criterion(outputs, batch_y)
        loss.backward()
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
    scheduler.step()
    
    # Save best model
    if test_acc > best_accuracy:
        best_accuracy = test_acc
        torch.save(model.state_dict(), 'transformer_mlp_word_model.pth')
        
        # Save preprocessing
        with open('preprocessing_word.pkl', 'wb') as f:
            pickle.dump({'scaler': scaler, 'encoder': label_encoder}, f)
        
        # Print when new best accuracy is achieved
        print(f"★ NEW BEST! Test Accuracy: {best_accuracy:.2f}% (Model saved)", flush=True)
    
    if (epoch + 1) % 10 == 0 or epoch == 0:
        print(f"Epoch [{epoch+1:3d}/{EPOCHS}] | Train Acc: {train_acc:.2f}% | Test Acc: {test_acc:.2f}% | Best: {best_accuracy:.2f}%", flush=True)

print("=" * 60, flush=True)
print(f"\nTraining completed!", flush=True)
print(f"Best accuracy: {best_accuracy:.2f}%", flush=True)
print(f"Model saved as 'transformer_mlp_word_model.pth'", flush=True)
print(f"Preprocessing saved as 'preprocessing_word.pkl'", flush=True)










