#!/usr/bin/env python3
"""
Model Detection Script
Checks which models are loaded and their properties
"""

import pickle
import torch
import os

print("="*60)
print("MODEL DETECTION ANALYSIS")
print("="*60)

# Check Letter Model
print("\n1. LETTER MODEL (mlp_model.p):")
if os.path.exists('mlp_model.p'):
    try:
        with open('mlp_model.p', 'rb') as f:
            letter_data = pickle.load(f)
        print(f"   ✅ File exists")
        print(f"   Type: {type(letter_data)}")
        if isinstance(letter_data, dict):
            print(f"   Keys: {list(letter_data.keys())}")
            if 'model' in letter_data:
                model = letter_data['model']
                print(f"   Model type: {type(model)}")
                if hasattr(model, 'n_features_in_'):
                    print(f"   Features: {model.n_features_in_}")
                if hasattr(model, 'n_classes_'):
                    print(f"   Classes: {model.n_classes_}")
        else:
            print(f"   Data type: {type(letter_data)}")
    except Exception as e:
        print(f"   ❌ Error loading: {e}")
else:
    print("   ❌ File not found!")

# Check Word Preprocessing
print("\n2. WORD PREPROCESSING (preprocessing_word.pkl):")
if os.path.exists('preprocessing_word.pkl'):
    try:
        with open('preprocessing_word.pkl', 'rb') as f:
            prep = pickle.load(f)
        print(f"   ✅ File exists")
        print(f"   Type: {type(prep)}")
        if isinstance(prep, dict):
            print(f"   Keys: {list(prep.keys())}")
            if 'num_frames' in prep:
                print(f"   Num frames: {prep['num_frames']}")
            encoder = prep.get('label_encoder') or prep.get('encoder')
            if encoder:
                print(f"   Classes: {len(encoder.classes_)}")
                print(f"   Sample classes: {list(encoder.classes_)[:10]}")
        else:
            print(f"   Data type: {type(prep)}")
    except Exception as e:
        print(f"   ❌ Error loading: {e}")
else:
    print("   ❌ File not found!")

# Check Word Model
print("\n3. WORD MODEL (transformer_mlp_word_model.pth):")
if os.path.exists('transformer_mlp_word_model.pth'):
    try:
        state = torch.load('transformer_mlp_word_model.pth', map_location='cpu', weights_only=False)
        print(f"   ✅ File exists")
        print(f"   Type: {type(state)}")
        if isinstance(state, dict):
            keys = list(state.keys())
            print(f"   Total keys: {len(keys)}")
            print(f"   First 10 keys: {keys[:10]}")
            has_spatial = any(k.startswith("spatial_encoder") for k in keys)
            print(f"   Has 'spatial_encoder': {has_spatial}")
            if has_spatial:
                print(f"   → Architecture: Temporal Transformer (256/8/6, 30 frames)")
            else:
                print(f"   → Architecture: Single-frame Transformer-MLP (128/4/4, 1 frame)")
        else:
            print(f"   Data type: {type(state)}")
    except Exception as e:
        print(f"   ❌ Error loading: {e}")
else:
    print("   ❌ File not found!")

# Check Alternative Word Model
print("\n4. ALTERNATIVE WORD MODEL (temporal_transformer_model.pth):")
if os.path.exists('temporal_transformer_model.pth'):
    print(f"   ⚠️  File exists but NOT used by websocket_final_classifier.py")
    print(f"   (The code only loads transformer_mlp_word_model.pth)")
else:
    print("   ℹ️  File not found (this is OK, not used)")

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print("\nModels used by websocket_final_classifier.py:")
print("  1. Letter: mlp_model.p (sklearn MLP)")
print("  2. Word: transformer_mlp_word_model.pth (PyTorch Transformer)")
print("  3. Preprocessing: preprocessing_word.pkl")
print("\n" + "="*60)







