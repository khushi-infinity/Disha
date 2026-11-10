# gNani AI

gNani is a mobile-first, voice-led navigation companion designed for older adults. It uses real OpenStreetMap search/routing data and keeps all provider keys on the FastAPI server.

## What is implemented

- Friendly, large-touch-target React interface for Android browsers
- Browser GPS permission + `watchPosition` movement updates and retry states
- Live PCM microphone relay to Gnani Prisma realtime STT (`/ws/stt`)
- Gnani Timbre v2.5 server-side speech synthesis, with browser speech fallback only when it is not configured/unavailable
- OpenRouter conversation layer, kept server-side, with a safe deterministic fallback
- Real Nominatim destination lookup and OSRM pedestrian routes; no made-up turns, distance, or ETA
- Safety wording that does not assume a crossing is safe
- Route cards and an end-journey control

## Setup

Prerequisites: Python 3.10+ and Node 18+.

```bash
cp .env.example .env
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
npm install
```

Add your actual server credentials in `.env` (do not use a `VITE_` prefix):

```dotenv
GNANI_API_KEY=...
OPENROUTER_API_KEY=...
# optional; defaults to OpenRouter's free router
OPENROUTER_MODEL=openrouter/free
```

Run these in separate terminals from the project root:

```bash
. .venv/bin/activate
uvicorn backend.main:app --reload --port 8000
```

```bash
npm run dev
```

Open `http://localhost:5173`. For a phone, use an HTTPS deployment (or a trusted local HTTPS tunnel); microphone and geolocation are restricted to secure contexts by browsers.

## Provider implementation notes

The Gnani integration follows the current official API documentation:

- Prisma v3 realtime: `wss://api.vachana.ai/stt/v3/stream`, header `x-api-key-id`, 16-bit mono 16 kHz PCM frames, `indic-auto` language detection.
- Timbre v2.5 REST: `POST /api/v1/tts/inference`, header `X-API-Key-ID`, with WAV output.

The browser never receives provider credentials. The app returns a useful configuration error if the server has no Gnani key; it does not pretend speech recognition is operating.

## Routing and data limits

Nominatim and the public OSRM demo service have usage limits and availability constraints. This project identifies those failures explicitly rather than replacing them with invented routes. Public BMTC data is not integrated yet because an authorized, stable live source and verified fare feed must be selected before presenting transit information; the app deliberately does not fabricate arrivals or fares.

## Test checklist

1. Grant location access and verify the green location indicator.
2. Add a valid `GNANI_API_KEY`, tap the microphone, say a destination, and check the transcript.
3. Say a destination, confirm the offered place, then verify the returned route card against its map source.
4. Tap the speaker button and verify Timbre audio; disconnect the service to verify browser fallback.

