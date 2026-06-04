import pickle
import numpy as np
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score

# Load data
data_dict = pickle.load(open('./data.pickle', 'rb'))

# Convert to numpy arrays and ensure uniform shape
data = np.array([np.array(item) for item in data_dict['data']])
labels = np.array(data_dict['labels'])

print(f"Dataset loaded: {len(data)} samples")
print(f"Feature vector size: {data[0].shape[0]} features per sample")
print(f"Unique labels: {np.unique(labels)}")

# Train-test split
x_train, x_test, y_train, y_test = train_test_split(data, labels, test_size=0.2, shuffle=True, stratify=labels)

# Train MLP classifier with two hands (84 features)
# hidden_layer_sizes can be adjusted for better performance
model = MLPClassifier(hidden_layer_sizes=(128, 64), max_iter=500, random_state=42, verbose=True)
model.fit(x_train, y_train)

# Predict and evaluate
y_predict = model.predict(x_test)
score = accuracy_score(y_predict, y_test)
best_accuracy = score * 100  # Convert to percentage

print('\n{}% of samples were classified correctly!'.format(score * 100))
print(f"Best accuracy: {best_accuracy:.2f}%")

# Save model
with open('mlp_model.p', 'wb') as f:
    pickle.dump({'model': model}, f)

print("Model saved as 'mlp_model.p'")












