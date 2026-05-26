 [![Consider Supporting me by donating to my ko-fi (100% optional, please dont feel pressured to do so) ](https://img.shields.io/badge/Support_on-Ko--fi-FF5E5B?logo=ko-fi&logoColor=white)](https://ko-fi.com/frostyisbored)
# FH6 Auction House Sniper

## Automated auction house sniper for Forza Horizon 6

Watches the Auction House for the car you set up, buys it out the instant it appears, collects it, and loops. Set your filters once and leave it running. This tool has about a 10% buyout rate, and generally can snipe a car in under 5 mins.



<img width="1655" height="792" alt="image-3" src="https://github.com/user-attachments/assets/61b58048-c3e6-4156-9510-0c2600aa7e9f" />
<img width="340" height="488" alt="image" src="https://github.com/user-attachments/assets/d594b885-9e5d-4519-bbea-182a3d99999b" />


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
- Moving background turned **ON** (Or set to false in config file)
- Game Language set to English
- Keyboard menu navigation (the bot uses keys, not the mouse)
- Wired ethernet strongly recommended

<img width="1386" height="763" alt="image-4" src="https://github.com/user-attachments/assets/fd2bf173-259f-4458-938b-2267144ce3ab" />
<img width="1386" height="758" alt="image-5" src="https://github.com/user-attachments/assets/34f3fe88-9575-4ec5-aa6c-0c9e04a9964c" />



---

# Download

Grab the latest **FH6-Sniper.zip** from the [Releases page](https://github.com/FrostyIsBored/FH6-Auction-House-Sniper/releases) and extract it anywhere on your PC.

---

# Setup

## Step 1 - Open the Auction House

Launch Forza Horizon 6 and head into the Auction House at the festival site.

<img width="1916" height="971" alt="image-1" src="https://github.com/user-attachments/assets/2e4c412e-974e-4bf4-9d4d-bbc31fcd2432" />

---

## Step 2 - Configure your search

Open **Search Auctions** and set your filters:

- **Make** and **Model** for the car you want
- **Max Buyout** as your safety net. The bot buys the first matching car without looking at the price, so this is the most you can spend per car. Set it carefully.

Back out so the screen sits on the **Search config** view. That's where the bot expects to start.

<img width="1919" height="1079" alt="image" src="https://github.com/user-attachments/assets/7fac68c0-f89d-45ee-a10a-5133b02da681" />

---

## Step 3 - Run the sniper

Double-click **FH6-Sniper.exe**. A small overlay appears in the top-left of your screen.

Click back into FH6, press **F8** or **Start**, and leave it running.

To stop: **F8** again, **F9** for panic, or click **STOP** on the overlay.

<img width="1902" height="1062" alt="image-2" src="https://github.com/user-attachments/assets/ccdfba46-4c90-42de-bb79-fe26658bb262" />

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

- **max_cars** - auto-stop after this many wins (default: 1)
- **max_minutes** - auto-stop after this many minutes (default: 180)
- **collect_after_buyout** - set to `false` if you'd rather collect cars manually
- **notify_sound** / **notify_toast** - turn the win beep or toast off
- **buyout_select_delay_ms** - extra ms between selecting Buy Out and pressing Enter. Bump to `200` if the bot occasionally opens the Place Bid dialog instead of Buy Out (default: 0)
- **moving_background** - set to `false` if you have FH6's moving background video setting turned **off** (default: true)

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

**Overlay says "Paused"** - FH6 isn't focused. Click into the game.

**F8 doesn't do anything** - another app on your PC might be hooking the F8 key. Close it, or change the hotkey in `config.json`.

**Bot misses a screen and just sits there** - restart FH6 and the bot. Make sure your graphics preset is **Very Low** and your resolution is **1920 x 1080**.

**When posting issues relating to the bot** - Please include your Sniper.log so that I can look into it.

  **The sniper opens the Buy Out dialog but won't click Yes.**
  <img width="1513" height="840" alt="image" src="https://github.com/user-attachments/assets/61472f11-389c-47f9-90e3-197530331486" />


  Almost always a mismatch between FH6's **Moving Background** video setting and the sniper's. If you've turned moving backgrounds off in-game, open the **Settings** tab in  the overlay and untick **Moving background mode** so the sniper loads the right templates for your setup.

  <img width="331" height="472" alt="image" src="https://github.com/user-attachments/assets/049c4dab-a718-4cab-882e-d45782f5391c" />


  **The sniper says "Stopped: could not recover" right after Start.**

  Two common causes:

  - **Game language is not English.** The sniper's templates only match the English UI.
  Switch FH6 to English under Settings > Language Select.
  - **Capturable overlay sitting over the menus.** If you've enabled **Show overlay in screenshots & recordings**, the overlay can land on top of the area the sniper is reading. Drag it to the top-right or bottom-right corner so it doesn't overlap the game UI.

  If neither helps, [open an issue](https://github.com/FrostyIsBored/FH6-Auction-House-Sniper/issues) or message me on Discord.
