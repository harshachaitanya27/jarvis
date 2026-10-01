# Jarvis — iOS

SwiftUI client for the Jarvis backend.

## Generate & run

Needs Xcode 16+ and XcodeGen (`brew install xcodegen`). The Xcode project is
generated from `project.yml`, so generate it first:

```bash
cd ios
xcodegen generate       # creates Jarvis.xcodeproj
open Jarvis.xcodeproj    # then ⌘R to run in the Simulator
```

## Pointing at the backend

Run the backend (`uvicorn app.main:app`). The Simulator reaches it at
`http://localhost:8000` — the default in `Jarvis/App/Config.swift`. For a
physical device, set that to your Mac's LAN IP (e.g. `http://192.168.1.20:8000`).

## Structure

- `App/` — entry point, `AppModel` (auth/onboarding state), root routing
- `Networking/` — `APIClient` + errors
- `Models/` — request/response DTOs
- `Storage/` — Keychain token store
- `Features/Onboarding/` — sign up / log in, API-key setup
- `Features/Library/` — episode library (WIP)
