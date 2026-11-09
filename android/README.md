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

The version comes from `VERSION` in `index.html` (`2.11.0` → versionCode `21100`), so bump `VERSION` before every
Play release.

### Libraries (`android/libs/`, git-ignored)

The Google Play In-App Review card needs these `.aar` files in `android/libs/` (the build stops without them):
- `review-2.0.2.aar` and `core-common-2.0.4.aar` from https://dl.google.com/android/maven2/com/google/android/play/
- `play-services-tasks-18.2.0.aar` and `play-services-basement-18.9.0.aar` (from the Gradle cache, or the same Google Maven under `com/google/android/gms/`)

`build.py` unpacks them, merges their resources, generates their `R` classes and adds their code to the dex.

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
- Portrait only (`android:appCategory="game"` keeps that on Android 16 tablets too), system bars hidden, screen kept on,
  the camera cut-out is padded natively (and removed from the page's `env(safe-area-inset-*)` so it is not added twice).
- Target SDK 36 (Google Play rule for new apps and updates since 31 Aug 2026). The back button uses `OnBackInvokedCallback`
  on Android 13+ (Android 16 no longer calls `onBackPressed`), `onBackPressed` below that.
- WebView has no `navigator.share`; the shell adds one that opens the Android share sheet (`FSNative.share`).
- Backup: Auto Backup and phone-to-phone transfer keep `app_webview/` (the localStorage save), see `res/xml/`.
- If the WebView renderer is killed (low memory) the activity restarts instead of crashing.
- `window.FSNative.review()` (a JavaScript bridge) asks Google Play for its rating card; `Review` in `index.html` decides when (after a 2+ star win from level 3, then every 10–18 levels, 2+ days apart, at most 5 times). Play shows it only for installs from the Play Store and limits how often.
