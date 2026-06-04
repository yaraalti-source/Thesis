# GestureTalk

Bidirectional American Sign Language (ASL) translation system for a thesis project.

- **GestureTalk-Front** — Flutter mobile app (live camera, media upload, voice-to-sign, history)
- **GestureTalk-Backend** — Laravel API (auth, persistence, TTS) and Python ML services (sign detection)

## Repository layout

```
Thesis/
├── GestureTalk-Front/     # Flutter app
├── GestureTalk-Backend/   # Laravel API + SignDetectionModel/
└── assets/                # Shared assets
```

## Large files (not in this repo)

These are excluded from Git because of GitHub size limits (~5 GB total). Keep them on your machine or use Git LFS / cloud storage if you need to share them:

- `SignDetectionModel/wordset/videos/` — WLASL training videos
- `SignDetectionModel/data/` and `data_word/` — collected training images
- Model weights (`*.pth`, `mlp_model.p`) and pickles (`*.pkl`, `data*.pickle`)

The Flutter app’s small sign clips under `GestureTalk-Front/assets/signs/words/` **are** included so the app runs out of the box.

## Getting started

1. Copy environment templates and fill in your values:
   - `GestureTalk-Backend/.env.example` → `GestureTalk-Backend/.env`
   - `GestureTalk-Front/.env.example` → `GestureTalk-Front/.env`
2. See component docs:
   - Backend ML: `GestureTalk-Backend/SignDetectionModel/COMPLETE_SYSTEM_DOCUMENTATION.md`
   - Front vocabulary: `GestureTalk-Front/VOCABULARY_AND_SIGNS_GUIDE.md`

## Tech stack

| Layer | Technologies |
|-------|----------------|
| Mobile | Flutter, Dart |
| API | Laravel, MySQL, JWT |
| ML | Python, MediaPipe, PyTorch, scikit-learn |
| TTS | ElevenLabs |

## License

Add your license here if you plan to make the repository public.
