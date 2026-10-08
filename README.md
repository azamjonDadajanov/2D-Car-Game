# 🚔 2D Top-Down Police Highway Chase Game

A complete, high-intensity 2D Top-Down Highway Police Chase game built in Python using **Pygame**. Features dynamic vehicle physics, responsive acceleration, police pursuit AI, visual damage stages, continuous distance-based economy, and a garage system with fullscreen support.

---

## 🎮 Game Preview & Features

- **📺 Fullscreen & Responsive Display**: Runs in full screen automatically with dynamic scaling for any resolution. Press `F11` or `F` anytime to toggle between Fullscreen and Windowed mode.
- **🚗 Accurate Sprite Slicing**: Slices transparent sprite sheets (`cars_spritesheet.png`) with two-step bounding-rect snapping to eliminate unwanted borders and car overlap.
- **⚡ Dynamic Driving Physics**:
  - Cruise Speed: `70 km/h`
  - Acceleration / Boost: Hold `UP` / `W` to boost up to `150 km/h` and visually charge forward.
  - Braking: Hold `DOWN` / `S` to brake down to `50 km/h`.
  - Releasing controls smoothly returns to standard cruise speed.
- **💔 Health & Visual Damage Stages**:
  - Start with 5 Lives.
  - Each traffic hit costs 1 Life and provides 2 seconds of invulnerability (visual flicker).
  - Vehicle sprite updates through 5 distinct damage stages.
  - 0 Lives triggers vehicle explosion and Game Over.
- **🚨 Intelligent Police Pursuit (SWAT)**:
  - SWAT cruiser actively chases from behind with flashing sirens.
  - Chases based on speed differences: catches up at normal speed, falls behind when boosted.
  - Outrunning the police past the screen boundary triggers a 15-second respawn timer.
  - Touching the police car results in instant `BUSTED!`.
- **💰 Economy & Garage System**:
  - Earns continuous money based on distance: **$100 for every 1 KM** driven ($10 per 0.1 KM).
  - Total cash persists across runs.
  - Garage vehicle selection:
    - **Red Sports Car**: Free (Unlocked by default).
    - **Yellow Muscle Car**: $500 (Unlockable with earned cash).

---

## 🕹️ Controls

| Key | Action |
| :--- | :--- |
| **`LEFT` / `A`** | Steer Left / Previous Car in Garage |
| **`RIGHT` / `D`** | Steer Right / Next Car in Garage |
| **`UP` / `W`** | Accelerate up to 150 km/h (Boost) |
| **`DOWN` / `S`** | Brake down to 50 km/h |
| **`B`** | Buy selected car in Garage |
| **`ENTER` / `SPACE`** | Start Chase / Confirm |
| **`R`** | Quick Restart after Crash / Busted |
| **`F11` / `F`** | Toggle Fullscreen / Windowed Mode |
| **`ESC`** | Exit to Menu / Quit Game |

---

## 📦 Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/azamjonDadajanov/2D-Car-Game.git
   cd 2D-Car-Game
   ```

2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the game**:
   ```bash
   python main.py
   ```

---

## 🛠️ Project Structure

```
├── assets/
│   ├── cars_spritesheet.png   # Transparent sprite sheet (3 rows x 5 damage stages)
│   └── cars_spritesheet.jpg   # Fallback spritesheet
├── main.py                    # Complete single-file game implementation
├── requirements.txt           # Python dependencies
├── .gitignore                 # Git ignore configuration
└── README.md                  # Project documentation
```

---

## 👤 Author

- **Dadajanov A'zamjon**
- **Email**: keyey678@gmail.com
- **GitHub**: [@azamjonDadajanov](https://github.com/azamjonDadajanov)
