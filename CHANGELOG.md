# Changelog

Newest changes first. Each section header is the release date.

## v1.1.1 - 2026-05-27

### Sold-listing detection fix
The bot was occasionally still trying to buy listings that had just sold - it would land on the View Seller / View Highest Bidder menu before backing out, wasting a cycle. Root cause: with moving background on, the bright FH6 menu scene showing through empty slots was being mistaken for a card. Detection now looks for the pure-white card UI body specifically, which the game's background scene never produces. The bot will correctly skip sold listings instead of stumbling into the wrong menu.

## v1.1.0 - 2026-05-26

### Settings panel
New **Settings** tab in the overlay. Edit match sensitivity, loop speed, auto-stop limits, notifications, hotkeys, HDR mode, moving background, and overlay visibility in screenshots / recordings. Saves and applies live.

### Resolution & monitor support
- 1080p, 1440p, 4K: all work.
- Ultrawide / 16:10 / 4:3: run FH6 windowed at 1920×1080. Black bars get cropped automatically.

### HDR
HDR was shifting FH6's lime UI toward yellow and breaking color detection. Fixed. Extra **HDR mode** toggle in Settings for displays that shift even more.

### Slow-load fix
Was reporting "no cars" when the Auction House just hadn't finished loading yet. Now recognizes the loading screen and waits.

### Polish
- Tabbed Status / Settings layout
- Collapsible Settings sections, scrolls if your screen is short
- Faster captures at high resolutions

### Logs
Cleaner state names, including the new loading state.
