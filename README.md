# FH6 Auction House Sniper

## Automated auction house sniper for Forza Horizon 6

Watches the Auction House for the car you set up, buys it out the instant it appears, collects it, and loops. Set your filters once and leave it running. This tool has about a 10% buyout rate, and generally can snipe a car in under 5 mins.

<img width="1655" height="792" alt="image-3" src="https://github.com/user-attachments/assets/b8047bfe-df94-4e19-bae4-8e2aaf506002" />

---

# Features

- Automatic search and buyout
- Skips past sold listings to find a fresh one
- Auto-collects every car you win
- Tiny always-on-top overlay with live stats
- F8 start/stop, F9 panic stop
- Auto-stops after a set number of cars or minutes
- Smart page awareness to stop accidental misclicks to other pages

---

# Requirements

- Windows 10 or 11
- Forza Horizon 6 on PC
- 1920 x 1080 resolution - Full Screen, uncapped Frame Rate
- Very Low graphics preset
- Keyboard menu navigation (the bot uses keys, not the mouse)
- Wired ethernet strongly recommended

<img width="1386" height="763" alt="image-4" src="https://github.com/user-attachments/assets/3a9b02f4-b3ae-429d-b2d7-563baf3026dc" />
<img width="1386" height="758" alt="image-5" src="https://github.com/user-attachments/assets/433e36b2-0602-4111-8d51-79ef931fb603" />



---

# Download

Grab the latest **FH6-Sniper.zip** from the [Releases page](https://github.com/FrostyIsFake/FH6-Auction-House-Sniper/releases) and extract it anywhere on your PC.

---

# Setup

## Step 1 — Open the Auction House

Launch Forza Horizon 6 and head into the Auction House at the festival site.

<img width="1916" height="971" alt="image-1" src="https://github.com/user-attachments/assets/29f934a8-2aa4-436f-aac7-88c9363ab168" />

---

## Step 2 — Configure your search

Open **Search Auctions** and set your filters:

- **Make** and **Model** for the car you want
- **Max Buyout** as your safety net. The bot buys the first matching car without looking at the price, so this is the most you can spend per car. Set it carefully.

Back out so the screen sits on the **Search config** view. That's where the bot expects to start.

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/7e1cfcca-0ef2-41e6-af02-410117bc2787" />

---

## Step 3 — Run the sniper

Double-click **FH6-Sniper.exe**. A small overlay appears in the top-left of your screen.

Click back into FH6, press **F8** or **Start**, and leave it running.

To stop: **F8** again, **F9** for panic, or click **STOP** on the overlay.

<img width="1902" height="1062" alt="image-2" src="https://github.com/user-attachments/assets/6ae3d516-4339-48a8-a451-7c199fd36f20" />

---

# SmartScreen Warning

Windows SmartScreen will warn you because the exe isn't signed. To run anyway:

1. Click **More info**
2. Click **Run anyway**

---

# Hotkeys

| Key | Action |
|---|---|
| **F8** | Start / stop |
| **F9** | Panic stop |
| **STOP** button | Same as F8 |
| **✕** on overlay | Close and exit |

---

# Settings

The bot is ready to go out of the box. If you want to tweak it, open **config.json** (created next to the exe on first run):

- **max_cars** — auto-stop after this many wins (default: 1)
- **max_minutes** — auto-stop after this many minutes (default: 180)
- **collect_after_buyout** — set to `false` if you'd rather collect cars manually
- **notify_sound** / **notify_toast** — turn the win beep or toast off

---

# Important

> [!WARNING]
> - Auction House automation may violate Forza's Enforcement Guidelines.
> - Results may vary depending on PC/Network setups. 
> - You risk a warning, suspension, or a permanent ban.
> - Use at your own risk.

---

# Notes

- The bot only runs while FH6 is the focused window. The overlay shows **Paused** if you tab out. Click back into the game to resume.
- The overlay is hidden from screen capture, so you can leave it anywhere on screen.
- Drag the overlay by clicking and holding the header.
- You won't win every snipe. The bot is limited by FH6's menu animations and the auction server response, same as any other tool.
- If servers are slow / overloaded it will cause the bot to break (Shall have a fix for it soon)
---

# Troubleshooting

**Overlay says "Paused"** — FH6 isn't focused. Click into the game.

**F8 doesn't do anything** — another app on your PC might be hooking the F8 key. Close it, or change the hotkey in `config.json`.

**Bot misses a screen and just sits there** — restart FH6 and the bot. Make sure your graphics preset is **Very Low** and your resolution is **1920 x 1080**.
