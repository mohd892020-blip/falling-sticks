# Falling Sticks for Android (offline app)

The app is a small native shell (`MainActivity.java`, a full-screen WebView) with the game files inside the APK
(`assets/www`). It serves them from `https://appassets.androidplatform.net/`, so it needs no internet and no website.

## Build

```
python android/build.py
```

Output in `android/out/`:
- `FallingSticks-<version>.apk` — install directly on a phone (sideload).
- `FallingSticks-<version>.aab` — upload to Google Play.

The version comes from `VERSION` in `index.html` (`2.10.0` → versionCode `21000`), so bump `VERSION` before every
Play release.

Tools come from the Unity 6 install on this PC (Android SDK, OpenJDK 17, bundletool). Override with the environment
variables `ANDROID_SDK`, `JAVA_HOME`, `BUNDLETOOL`. No Gradle is needed.

## Signing

`android/signing.properties` (git-ignored, never commit it):

```
storeFile=C:/Users/<you>/Documents/Falling Sticks signing key/fallingsticks-upload.jks
keyAlias=fallingsticks
storePassword=...
keyPassword=...
```

The keystore and its passwords live in `Documents/Falling Sticks signing key/`. Back that folder up. Google Play
uses this key as the upload key (Play App Signing keeps the real signing key).

## Behaviour inside the app

- `IN_APP` in `index.html` is true there: no service worker, challenge links point at the public website.
- The Android back button calls `window.appBack()`: it closes a dialog, pauses, steps back, and leaves only from the main menu.
- Portrait only, system bars hidden, screen kept on, the camera cut-out is padded.
