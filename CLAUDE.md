# Project

## Rule for Claude
At the start of every session, read this file. At the end of every session, update it with what we finished and what is left.

## Description
"العصي الساقطة / Falling Sticks" — a mobile-first web arcade game based on the Falling Sticks machine: tap the stick whose colour matches the glowing arch before it hits the floor. English by default (device language if supported); also Arabic (RTL), French, Spanish, Portuguese, Turkish, Indonesian.

## Language and tools
- One self-contained `index.html` (HTML + CSS + vanilla JS). Canvas 2D for the game, WebAudio for all sound and music. No libraries, no Three.js.
- Fonts: Lalezar (titles/numbers) + Cairo (text) from Google Fonts, with system fallbacks.
- PWA add-ons next to it: `manifest.webmanifest`, `sw.js`, `icons/` (only used when served over http/https).
- Local preview: `python -m http.server 8765` (config in `.claude/launch.json`). Add `?nosw` to the URL to skip the service worker while developing.
- Phone test on the same Wi-Fi: launch config `game-lan` (port 8766, bound to 0.0.0.0), then open `http://<PC IP>:8766` on the phone.
- Automated tests: `python tests/run_tests.py` (headless Edge/Chrome, own server on a free port, exit code 0 = pass), or open `http://localhost:8765/tests/tests.html` (puts your own save back when done). Run them after every change; add a test for every new mechanic.
- Preview a season: add `?event=ramadan`, `?event=eid` or `?event=none` to the URL.

## Key decisions
- Built on top of the original prototype (`Downloads/falling-sticks.html`): same core rules, arch shape, colours, cfg(n) formula and save key `fs_save` (old saves migrate automatically to save version 2).
- All tuning lives in the `CFG` table at the top of the script (levels, difficulty, chances, coins, combo). Worlds in `WORLDS`, shop items in `SHOP`, achievements in `ACH`, texts in `STR` (ar/en).
- Level count is derived: `MAX_LV = WORLDS.length × 15`. Adding a world = one entry in `WORLDS` + its name in `STR.ar.worlds` / `STR.en.worlds`.
- Static art (city, machine, LED strip, stick sprites) is drawn once into cached offscreen canvases; particles are pooled; one requestAnimationFrame loop drives everything; menus render at ~30 fps.
- State machine `SM` with screens: splash, cinema, menu, map, modes, missions, shop, ach, stats, lb, settings, about, saves, profile, album, intro, countdown, play, pause, end.
- Tap hit test is strict (stick body + small margin, `CFG.hit`); empty taps never cost a heart (user decision 2026-10-28).
- The street cat only helps or reacts — it never gets hurt (user decision).
- Gameplay modules: `Drone` (power-ups), `Cat`, `Boss` (twists from `CFG.boss.twists`), `Missions`, `Glove` (grab feedback + mouse cursor).
- Storage: localStorage only, always inside try/catch. Leaderboard is local; `CFG.leaderboard.url` is the hook for a future server.
- Default language: device language if supported, otherwise English (user decision 2026-10-28). Strings live in `STR.<code>`; `t()` falls back to English.
- Default UI theme: Day (`CFG.defaultTheme`, user decision 2026-10-29 — they disliked Sunset); the other themes stay selectable in Settings. Themes = CSS token sets on `html[data-theme]` + a time of day for the city scene (`THEMES`). Saves still on the untouched old default (sunset) migrate to Day; `settings.themePicked` marks a deliberate choice.
- Save history (`History`): progress log in `save.log` (text built at display time per language) + up to 12 backups in a separate localStorage key `fs_backups`, so a reset can be undone. Auto backup every 15 min of play / after a first boss win, and always before import, reset or restore.
- Rival bots in leaderboards are always labelled 🤖 (never shown as real players) — the user asked for fake members; we chose honest labelled bots.
- First-run intro (`Cinema`, ~16 s) is unskippable the first time only; replay from Settings › Info can be closed.
- Player profile (`Player`): XP from catches, wins, stars, bosses, daily, endless score and missions (`CFG.xp`); level curve `base + (l-1)·step`; titles in `CFG.titles`/`STR.titles`; free reward track `TRACK` (other levels give coins; an owned item becomes 150 coins). Existing players get XP for old progress once (`save.xpInit`).
- Sticker album (`Album`): 5 per world (`STK`), set bonus `CFG.stickerSet`. Free-form save maps (`ach`, `seen`, `stickers`, `fails`, `seenWorld`) must be listed in `mergeSave`.
- Seasons (`Season`) come from the Hijri calendar via `Intl` (no hard-coded dates): Ramadan = lantern sticks (bonus only, never a penalty) + rewards `CFG.ramadan`, crescent and lantern garlands in the city; Eid = daily gift ×2. Event-only shop items have `price: -1`.
- Performance (2.4.1, after the first phone test showed stutter + blur): `QUALITY` dpr 3/2/1.5 (capped by the screen); auto quality steps down only after two slow 3 s windows in a row and ignores a steady ~30 fps battery-saver cap; saves before 2.4.1 restart from high (`settings.perfV`). Fonts used by the canvas (Lalezar 400, Cairo 800) are preloaded and the sprite cache is only cleared between runs (`Cache.refresh`), never mid-play. Full-screen cached canvases are capped at 4 (LRU). The machine layer is blitted in 3 bands (`V.mTop/mBot/mCol`) to skip its empty middle. FPS overlay (Settings) shows fps · worst frame ms · dpr · quality — ask the user for a screenshot of it when debugging phone speed.
- Touch: at most 2 grip hands + 1 empty-air hand on screen; extra fingers (non-primary pointers) never draw hands.
- No text signs in the city backdrop (user decision 2026-10-29: they looked like objects under the sticks). The map still has small side signs.
- World design (`KIT`): every world has its own arch + platform (`ARCH.w0…w9`, `PLAT.w0…w9`, decorations via `deco`). Shop item `world` (default, free) shows it; any bought arch/platform the player equips overrides it (user decision). `kitId(c)` resolves which one is shown.
- Strolling animals (`Pets`): cats, puppies, a duck with ducklings, rabbits walk back and forth on the platform behind the sticks; they hop when a stick lands near them and are never hurt; tapping one shows a heart. Max 2 at once (1 on low quality or while the helper cat is out). Not in the tutorial or the intro.
- Developer mode (`Dev`): tap the version number 7× on About, enter the owner code (given to the user in chat; only its hash is in `Dev.PIN` = `hashStr('fs-dev|' + code)`; to change it, compute a new hash). Then every map level opens, a 🔧 button on the map jumps to any level, and levels beyond the player's progress play as test runs (`Game.test`) that save nothing (`Progress.dry` restores the save; `History.off`). Tap 7× again to turn it off. Stored per device in localStorage `fs_dev`.
- Mechanics 2.4: two-tone sticks from 76 (the tapped half counts; a miss if either half is the target), wind on even levels from 106, rising sticks from 136 (`CFG.floorSticks` extra sticks on the platform). Smart assist (`CFG.assist`, Settings toggle) after 3 fails on a level.

## Done
- v2.0.0 (2026-10-28): full rebuild — 150 generated levels (10 worlds × 15, boss every 15th), mechanics unlocking at 6/10/31/61/91/121, map with stars and auto-scroll, Endless / Daily challenge (date seed) / Practice modes, interactive tutorial, mechanic intro cards, countdown, pause with resume countdown and auto-pause on tab hide, win/lose screens (stars one by one, score count-up, flying coins, 1.4 s button lock), settings (music/SFX volumes, mute, haptics, language, graphics quality + auto FPS detection, difficulty, colour-blind symbols, reduce motion, large text, left-hand mode, export/import/reset), coins + shop (sticks, platforms, arch themes, backdrops), daily reward streak with countdown, 26 achievements, stats, local leaderboard, Bebo the mascot, animated night arcade city per world, generated music per world + boss, PWA files and icons.
- Tested at 390×844: all screens, tutorial, all mechanics on levels 6–150, endless, daily, practice, settings, shop, export/import/reset, save migration. No console errors.
- v2.1.0 (2026-10-28): precise tap hit test + grabbing glove (follows the mouse, grips the stick, closes on air), quick-catch bonus, hit-stop and combo flash, power-up drone (heart / slow / magnet / ×2) with HUD timers, street cat (one save per level, gold → coins, petting), boss robot with HP and per-world twists (rapid, feints, blackout, fast swaps, rage), special levels (survival ⏳, golden rain 💰, lights out 🌑) with map badges, 3 daily missions + bonus, Bebo accessories shop tab, FPS counter, 30 achievements, LAN test config. All tested with bots, no console errors.

- v2.2.0 (2026-10-28): mandatory 16 s first-run intro (scripted demo on the real machine), saga-style level map (winding road bottom→top, world gates, Bebo marker, special-level badges), 6 themes + auto (Sunset default, Day/Sunset city scenes), challenge links (same seed, versus result, reply link, Web Share), labelled rival bots in leaderboards + "rival of the day", player name, English default + device language, 5 new languages (fr, es, pt, tr, id — machine-assisted, need native review).

- v2.3.0 (2026-10-29): Day is the default theme; save history screen (Settings › Data › Save history) with automatic + manual backups, restore (keeps current settings), and a progress timeline; new strings in all 7 languages. Tested: migration, backup/restore, undo reset, all languages, no console errors.

- v2.4.0 (2026-10-29): player profile + XP levels + titles + free reward track, sticker album (50 stickers), two-tone / wind / rising-stick mechanics with intro cards, smart assist, Ramadan lantern event + Eid gift (Hijri calendar), music layers that grow with the combo, faster music when a boss rages, Bebo eyes follow the target stick, squash & breathing, cat breathing, boss rise/sink animation, neon world title card, automated test suite (26 tests in `tests/`). Strings in all 7 languages. All tests pass; screens checked at 390×844 in English and Arabic.

- v2.4.1 (2026-10-29): fixes from the first real-phone test — sharper canvas, smarter auto quality, no mid-play cache rebuilds, lighter machine blit, one hand per touch, FPS overlay with diagnostics.
- v2.5.0 (2026-10-29): city text signs removed, world-specific arch + platform for all 10 worlds, strolling animals, owner developer mode. 29 automated tests pass.

## Remaining
- User said the game is "not very fun" yet (first phone test). Retest on the phone after 2.5.0, then pick game-feel improvements together (ideas offered: fever mode, juicier catches, faster early pacing, pre-level boosts, clutch catches).
- Real art and audio assets are optional upgrades (everything is generated by code now).
- Online leaderboard needs a server (set `CFG.leaderboard.url`).
- Fine-tune difficulty numbers in `CFG` after real players try it on phones (especially `CFG.hit`, drone/cat frequency, boss twists).
- Native-speaker review of fr/es/pt/tr/id strings before publishing (v2.4 strings were written by Claude too).
- Ramadan/Eid art and balance only seen with `?event=` previews; check again when the real season comes.
- Live multiplayer / online leaderboard need a server (Supabase or Firebase) — not started.
- Real-device test still pending (use `game-lan`); GitHub Pages hosting not set up (needs the user's OK — it publishes publicly).
- Git is local only (branch `master`, no remote). First game commit 2026-10-29 (v2.4.0). Commit after each finished version when the user agrees.

Always reply to me in Arabic (Palestinian dialect), but keep code, commands and file names in English.
