[app]

# Dead Drift — Android Play Store slice (flight + delivery tunnels).
title = Dead Drift
package.name = deaddrift
package.domain = org.chrisdewitt
source.dir = .
source.include_exts = py,png,jpg,json,ttf,txt,md
source.include_patterns = assets/fonts/*,assets/android/*
source.exclude_dirs = tests,docs,dist,build,.git,.pytest_cache,.buildozer,bin,assets/nltk_data,assets/audio
source.exclude_patterns = **/*.pyc,**/__pycache__/**,tools/bundle_nltk.py
version = 0.9.0

# No NLTK — terminals are not in the mobile slice.
requirements = python3,pygame-ce,numpy

orientation = landscape
fullscreen = 1
android.manifest.orientation = sensorLandscape

# App entry is main.py (p4a default).
# presplash.filename = assets/android/icon.png
icon.filename = assets/android/icon.png

android.permissions = VIBRATE
android.api = 34
android.minapi = 24
android.ndk = 25b
android.accept_sdk_license = True
android.archs = arm64-v8a,armeabi-v7a
android.presplash_color = #040408
android.logcat_filters = *:S python:D
android.allow_backup = True
android.block_network = True

# Keep the APK lean — skip desktop-only packaging.
android.skip_update = False
p4a.branch = master

[buildozer]
log_level = 2
warn_on_root = 1
