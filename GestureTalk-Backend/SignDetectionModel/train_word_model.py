"""
Train WORD model using sklearn MLP (same as letter model)
Uses 84 features (2 hands × 42 features each)
"""

import pickle
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from collections import Counter

# ==================== LOAD DATA ====================
print("Loading word dataset...")

try:
    data_dict = pickle.load(open('./data_word.pickle', 'rb'))
except FileNotFoundError:
    print("\n✗ ERROR: data_word.pickle not found!")
    print("  Run 'python create_word_dataset_wlasl.py' first")
    exit(1)

data = np.array([np.array(item) for item in data_dict['data']])
labels = np.array(data_dict['labels'])

print(f"Dataset loaded: {len(data)} samples")
print(f"Features per sample: {data.shape[1]}")
print(f"Unique words: {len(set(labels))}")

# Show class distribution
print("\nClass distribution:")
label_counts = Counter(labels)
for word, count in sorted(label_counts.items(), key=lambda x: -x[1])[:15]:
    print(f"  {word}: {count} samples")
if len(label_counts) > 15:
    print(f"  ... and {len(label_counts) - 15} more words")

# ==================== PREPARE DATA ====================
# Create label mapping
unique_labels = sorted(set(labels))
label_to_idx = {label: idx for idx, label in enumerate(unique_labels)}
idx_to_label = {idx: label for label, idx in label_to_idx.items()}

labels_encoded = np.array([label_to_idx[l] for l in labels])

print(f"\nLabel mapping created: {len(unique_labels)} classes")

# Train-test split
x_train, x_test, y_train, y_test = train_test_split(
    data, labels_encoded, test_size=0.2, shuffle=True, stratify=labels_encoded, random_state=42
)

print(f"Training samples: {len(x_train)}")
print(f"Test samples: {len(x_test)}")

# ==================== TRAIN MODEL ====================
print("\n" + "="*60)
print("Training MLP Word Classifier...")
print("="*60)

model = MLPClassifier(
    hidden_layer_sizes=(256, 128, 64),  # Larger network for more classes
    max_iter=500,
    random_state=42,
    verbose=True,
    early_stopping=True,
    validation_fraction=0.1
)

model.fit(x_train, y_train)

# ==================== EVALUATE ====================
print("\n" + "="*60)
print("Evaluation Results:")
print("="*60)

y_pred_train = model.predict(x_train)
y_pred_test = model.predict(x_test)

train_acc = accuracy_score(y_train, y_pred_train)
test_acc = accuracy_score(y_test, y_pred_test)

print(f"\nTraining Accuracy: {train_acc * 100:.2f}%")
print(f"Test Accuracy: {test_acc * 100:.2f}%")

# Per-class accuracy for top 10 classes
print("\nPer-word accuracy (top 10):")
for idx in range(min(10, len(unique_labels))):
    mask = y_test == idx
    if mask.sum() > 0:
        word_acc = (y_pred_test[mask] == y_test[mask]).mean()
        print(f"  {idx_to_label[idx]}: {word_acc * 100:.1f}%")

# ==================== SAVE MODEL ====================
print("\n" + "="*60)
print("Saving model...")

with open('word_model.p', 'wb') as f:
    pickle.dump({
        'model': model,
        'labels': idx_to_label,
        'label_to_idx': label_to_idx
    }, f)

print(f"✓ Model saved as 'word_model.p'")
print(f"✓ {len(unique_labels)} words trained")
print(f"\nNext step: Run 'python unified_classifier.py' to use the model")

















