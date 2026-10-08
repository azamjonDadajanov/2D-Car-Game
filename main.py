"""
==============================================================================
   2D TOP-DOWN POLICE CHASE GAME - COMPLETE WITH SOUND (WINDOWED MODE)
==============================================================================
Features:
1. Windowed Display:
   - Fixed clean 800x700 windowed mode.
2. Audio System (sounds/):
   - 'game-start.mp3': Plays on game start / chase launch.
   - 'in-game-sound.mp3': High-energy looped background music during chase.
   - 'game-over.mp3': Dramatic sound effect on crash or police bust.
3. Sprite Slicing & Snap-to-Car (Transparent PNG):
   - Two-step cropping with get_bounding_rect() eliminates car overlaps/borders.
   - Scaled to (80, 160) pixels.
4. Physics & Driving Mechanics:
   - Base speed: 70 km/h.
   - Hold [UP] / [W]: Boost up to 150 km/h and move forward.
   - Release: Return to 70 km/h.
   - Hold [DOWN] / [S]: Brake down to 50 km/h.
5. Health & Visual Damage Stages:
   - 5 Lives mapped to damage frames (Col 0 = 100% health, Col 4 = 1 Life).
   - Collision = -1 Life & 2s invulnerability (flicker).
   - 0 Lives = Explosion & Game Over.
6. Police Pursuit AI:
   - SWAT car chases from behind with flashing sirens.
   - Catches up if player is slow, falls behind when boosted.
   - 15-second respawn timer if outrun.
7. Economy & Garage System:
   - Earns $100 per 1 KM driven (calculated continuously).
   - Garage: Red Car (Free), Yellow Car ($500).
==============================================================================
"""

import pygame
import random
import math
import os
import sys

# ---------------------------------------------------------------------------
# INITIAL PYGAME & DISPLAY SETUP (WINDOWED MODE: 800x700)
# ---------------------------------------------------------------------------
pygame.init()
pygame.mixer.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 700
FPS = 60

# Road geometry
LANE_COUNT = 3
CAR_WIDTH = 80
CAR_HEIGHT = 160
ROAD_WIDTH = 330
LANE_WIDTH = ROAD_WIDTH // LANE_COUNT  # 110 px
ROAD_LEFT = (SCREEN_WIDTH - ROAD_WIDTH) // 2
ROAD_RIGHT = ROAD_LEFT + ROAD_WIDTH

# Speeds (km/h)
SPEED_MIN = 50.0
SPEED_DEFAULT = 70.0
SPEED_MAX = 150.0
ACCEL_RATE = 85.0
DECEL_RATE = 65.0

TRAFFIC_SPEED_KMH = 50.0
POLICE_SPEED_KMH = 75.0
SPEED_PIXEL_SCALE = 0.13

# Colors
COLOR_GRASS = (34, 139, 34)
COLOR_GRASS_DARK = (26, 110, 26)
COLOR_ROAD = (42, 45, 52)
COLOR_ROAD_SHOULDER = (75, 75, 80)
COLOR_KERB_RED = (215, 45, 45)
COLOR_KERB_WHITE = (245, 245, 245)
COLOR_LINE_WHITE = (250, 250, 250)
COLOR_LINE_YELLOW = (255, 204, 0)
COLOR_UI_BG = (15, 20, 30, 235)
COLOR_TEXT = (245, 245, 250)
COLOR_GOLD = (255, 215, 0)
COLOR_GREEN = (46, 204, 113)
COLOR_RED = (231, 76, 60)
COLOR_BLUE = (52, 152, 219)
COLOR_DARK_OVERLAY = (0, 0, 0, 195)


# ---------------------------------------------------------------------------
# AUDIO MANAGER
# ---------------------------------------------------------------------------
class SoundManager:
    def __init__(self):
        self.sound_start = self._load_sound(["sounds/game-start.mp3", "game-start.mp3"])
        self.sound_game_over = self._load_sound(["sounds/game-over.mp3", "game-over.mp3"])
        self.music_path = self._find_path(["sounds/in-game-sound.mp3", "in-game-sound.mp3"])

    def _find_path(self, candidates):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        for p in candidates:
            full_p = os.path.join(base_dir, p)
            if os.path.exists(full_p):
                return full_p
            if os.path.exists(p):
                return p
        return None

    def _load_sound(self, candidates):
        path = self._find_path(candidates)
        if path:
            try:
                snd = pygame.mixer.Sound(path)
                snd.set_volume(0.8)
                print(f"[SOUND] Loaded sound: {path}")
                return snd
            except Exception as e:
                print(f"[SOUND] Error loading sound {path}: {e}")
        return None

    def play_start(self):
        if self.sound_start:
            self.sound_start.play()

    def play_game_over(self):
        self.stop_music()
        if self.sound_game_over:
            self.sound_game_over.play()

    def play_music(self):
        if self.music_path:
            try:
                pygame.mixer.music.load(self.music_path)
                pygame.mixer.music.set_volume(0.55)
                pygame.mixer.music.play(-1)
            except Exception as e:
                print(f"[SOUND] Music playback error: {e}")

    def stop_music(self):
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# SPRITE SHEET LOADER & ACCURATE BOUNDING RECT CROPPING
# ---------------------------------------------------------------------------
def load_car_sprites():
    candidate_paths = [
        "cars_spritesheet.png",
        os.path.join("assets", "cars_spritesheet.png"),
        "cars_spritesheet.jpg",
        os.path.join("assets", "cars_spritesheet.jpg"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "cars_spritesheet.png"),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "cars_spritesheet.png"),
    ]
    
    sheet_img = None
    for p in candidate_paths:
        if os.path.exists(p):
            try:
                sheet_img = pygame.image.load(p)
                if pygame.display.get_surface() is not None:
                    sheet_img = sheet_img.convert_alpha()
                print(f"[SPRITES] Loaded transparent sprite sheet: {p} (size: {sheet_img.get_size()})")
                break
            except Exception as e:
                print(f"[SPRITES] Error loading {p}: {e}")

    sprites = {"red": [], "police": [], "yellow": []}
    row_keys = ["red", "police", "yellow"]

    if sheet_img is not None:
        img_w, img_h = sheet_img.get_size()
        row_ratios = [
            (0.095, 0.360),  # Row 0: Red
            (0.370, 0.695),  # Row 1: Police SWAT
            (0.710, 0.965),  # Row 2: Yellow Muscle
        ]
        col_center_ratios = [0.185, 0.347, 0.508, 0.670, 0.831]
        cell_w = int(img_w * 0.13)

        for row_idx, key in enumerate(row_keys):
            y_min_ratio, y_max_ratio = row_ratios[row_idx]
            top_y = max(0, int(img_h * y_min_ratio))
            bot_y = min(img_h, int(img_h * y_max_ratio))
            cell_h = max(10, bot_y - top_y)

            for col_idx in range(5):
                cx = int(img_w * col_center_ratios[col_idx])
                bx = max(0, min(img_w - cell_w, cx - cell_w // 2))
                
                safe_rect = pygame.Rect(bx, top_y, cell_w, min(cell_h, img_h - top_y))
                cell = sheet_img.subsurface(safe_rect).copy()
                
                bbox = cell.get_bounding_rect()
                if bbox.width > 0 and bbox.height > 0:
                    snapped_cell = cell.subsurface(bbox)
                else:
                    snapped_cell = cell
                
                scaled_frame = pygame.transform.smoothscale(snapped_cell, (CAR_WIDTH, CAR_HEIGHT))
                sprites[key].append(scaled_frame)
    else:
        print("[SPRITES] Warning: Sprite sheet not found. Generating procedural fallback sprites.")
        palette = {
            "red": [(220, 40, 40), (200, 70, 70), (170, 80, 80), (130, 80, 80), (70, 70, 70)],
            "police": [(30, 40, 70), (40, 50, 80), (50, 60, 80), (60, 60, 80), (50, 50, 50)],
            "yellow": [(240, 195, 20), (210, 175, 40), (180, 150, 50), (140, 120, 50), (60, 60, 60)]
        }
        for key in row_keys:
            for stage in range(5):
                surf = pygame.Surface((CAR_WIDTH, CAR_HEIGHT), pygame.SRCALPHA)
                base_c = palette[key][stage]
                pygame.draw.rect(surf, base_c, (6, 6, CAR_WIDTH - 12, CAR_HEIGHT - 12), border_radius=10)
                pygame.draw.rect(surf, (150, 200, 240, 220), (14, 38, CAR_WIDTH - 28, 26), border_radius=4)
                pygame.draw.rect(surf, (150, 200, 240, 220), (14, CAR_HEIGHT - 54, CAR_WIDTH - 28, 20), border_radius=4)
                pygame.draw.rect(surf, (255, 255, 200), (12, 8, 12, 6), border_radius=2)
                pygame.draw.rect(surf, (255, 255, 200), (CAR_WIDTH - 24, 8, 12, 6), border_radius=2)
                if key == "police":
                    pygame.draw.rect(surf, (255, 255, 255), (18, 70, CAR_WIDTH - 36, 14))
                if stage > 0:
                    for _ in range(stage * 4):
                        rx1, ry1 = random.randint(10, CAR_WIDTH - 10), random.randint(15, CAR_HEIGHT - 15)
                        pygame.draw.line(surf, (30, 30, 30), (rx1, ry1), (rx1 + 8, ry1 + 8), 2)
                sprites[key].append(surf)

    return sprites


# ---------------------------------------------------------------------------
# PARTICLE EFFECTS
# ---------------------------------------------------------------------------
class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit_spark(self, x, y, count=15):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 7)
            self.particles.append({
                'x': x, 'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'life': random.randint(15, 30),
                'max_life': 30,
                'color': random.choice([(255, 220, 50), (255, 120, 20), (255, 50, 50)]),
                'size': random.randint(3, 6)
            })

    def emit_smoke(self, x, y, count=4):
        for _ in range(count):
            self.particles.append({
                'x': x + random.uniform(-10, 10),
                'y': y + random.uniform(-10, 10),
                'vx': random.uniform(-0.8, 0.8),
                'vy': random.uniform(1.0, 3.0),
                'life': random.randint(25, 45),
                'max_life': 45,
                'color': random.choice([(100, 100, 100), (140, 140, 140), (70, 70, 70)]),
                'size': random.randint(5, 12)
            })

    def emit_explosion(self, x, y, count=50):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(2, 10)
            self.particles.append({
                'x': x, 'y': y,
                'vx': math.cos(angle) * speed,
                'vy': math.sin(angle) * speed,
                'life': random.randint(20, 55),
                'max_life': 55,
                'color': random.choice([(255, 240, 100), (255, 140, 0), (220, 30, 10), (80, 80, 80)]),
                'size': random.randint(5, 14)
            })

    def update(self):
        for p in self.particles[:]:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['life'] -= 1
            if p['life'] <= 0:
                self.particles.remove(p)

    def draw(self, surface):
        for p in self.particles:
            alpha_ratio = p['life'] / p['max_life']
            radius = max(1, int(p['size'] * alpha_ratio))
            pygame.draw.circle(surface, p['color'], (int(p['x']), int(p['y'])), radius)


# ---------------------------------------------------------------------------
# SPRITE CLASSES
# ---------------------------------------------------------------------------
class Player(pygame.sprite.Sprite):
    def __init__(self, sprite_frames):
        super().__init__()
        self.frames = sprite_frames
        self.lives = 5
        self.image = self.frames[0]
        self.rect = self.image.get_rect()
        
        self.rect.centerx = ROAD_LEFT + ROAD_WIDTH // 2
        self.base_y = SCREEN_HEIGHT - CAR_HEIGHT - 40
        self.target_y = self.base_y
        self.rect.y = self.base_y

        self.speed_kmh = SPEED_DEFAULT
        self.steer_speed = 7.0
        self.invulnerable_timer = 0.0

    def take_damage(self):
        if self.invulnerable_timer <= 0:
            self.lives -= 1
            self.invulnerable_timer = 2.0
            self.speed_kmh = SPEED_MIN
            self.update_frame()
            return True
        return False

    def update_frame(self):
        stage = max(0, min(4, 5 - self.lives))
        self.image = self.frames[stage]

    def update(self, dt_seconds):
        if self.invulnerable_timer > 0:
            self.invulnerable_timer = max(0.0, self.invulnerable_timer - dt_seconds)

        keys = pygame.key.get_pressed()

        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.speed_kmh = min(SPEED_MAX, self.speed_kmh + ACCEL_RATE * dt_seconds)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.speed_kmh = max(SPEED_MIN, self.speed_kmh - DECEL_RATE * dt_seconds)
        else:
            if self.speed_kmh > SPEED_DEFAULT:
                self.speed_kmh = max(SPEED_DEFAULT, self.speed_kmh - DECEL_RATE * 0.7 * dt_seconds)
            elif self.speed_kmh < SPEED_DEFAULT:
                self.speed_kmh = min(SPEED_DEFAULT, self.speed_kmh + ACCEL_RATE * 0.7 * dt_seconds)

        speed_factor = (self.speed_kmh - SPEED_MIN) / (SPEED_MAX - SPEED_MIN)
        max_forward_y = SCREEN_HEIGHT * 0.38
        self.target_y = self.base_y - speed_factor * (self.base_y - max_forward_y)
        self.rect.y += (self.target_y - self.rect.y) * 0.1

        dx = 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= self.steer_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += self.steer_speed

        self.rect.x += int(dx)

        min_x = ROAD_LEFT + 6
        max_x = ROAD_RIGHT - CAR_WIDTH - 6
        if self.rect.left < min_x:
            self.rect.left = min_x
        if self.rect.right > ROAD_RIGHT - 6:
            self.rect.right = ROAD_RIGHT - 6

    def draw(self, surface):
        if self.invulnerable_timer > 0:
            if int(self.invulnerable_timer * 10) % 2 == 0:
                return
        surface.blit(self.image, self.rect)


class EnemyTraffic(pygame.sprite.Sprite):
    def __init__(self, sprite_frames, lane_center_x, start_y):
        super().__init__()
        self.image = random.choice(sprite_frames[:2])
        self.rect = self.image.get_rect()
        self.rect.centerx = lane_center_x
        self.rect.bottom = start_y
        self.speed_kmh = TRAFFIC_SPEED_KMH

    def update(self, player_speed_kmh):
        relative_speed_kmh = player_speed_kmh - self.speed_kmh
        dy = relative_speed_kmh * SPEED_PIXEL_SCALE
        self.rect.y += dy

        if self.rect.top > SCREEN_HEIGHT + 180 or self.rect.bottom < -250:
            self.kill()


class Police(pygame.sprite.Sprite):
    def __init__(self, sprite_frames):
        super().__init__()
        self.frames = sprite_frames
        self.image = self.frames[0]
        self.rect = self.image.get_rect()
        
        self.rect.centerx = ROAD_LEFT + ROAD_WIDTH // 2
        self.rect.top = SCREEN_HEIGHT - 30
        self.speed_kmh = POLICE_SPEED_KMH
        self.siren_timer = 0.0

    def update(self, player_speed_kmh, player_center_x, dt_seconds):
        self.siren_timer += dt_seconds

        relative_speed_kmh = player_speed_kmh - self.speed_kmh
        dy = relative_speed_kmh * SPEED_PIXEL_SCALE
        self.rect.y += dy

        target_x = player_center_x
        diff_x = target_x - self.rect.centerx
        max_steer = 3.6
        if abs(diff_x) > 2:
            self.rect.centerx += int(math.copysign(min(abs(diff_x), max_steer), diff_x))

        if self.rect.left < ROAD_LEFT + 6:
            self.rect.left = ROAD_LEFT + 6
        if self.rect.right > ROAD_RIGHT - 6:
            self.rect.right = ROAD_RIGHT - 6

    def draw(self, surface):
        surface.blit(self.image, self.rect)
        
        siren_phase = int(self.siren_timer * 8) % 2
        light_y = self.rect.top + 72
        left_light_x = self.rect.left + 20
        right_light_x = self.rect.right - 20
        
        c1, c2 = (COLOR_RED, COLOR_BLUE) if siren_phase == 0 else (COLOR_BLUE, COLOR_RED)

        pygame.draw.circle(surface, c1, (left_light_x, light_y), 8)
        pygame.draw.circle(surface, (255, 255, 255), (left_light_x, light_y), 4)
        pygame.draw.circle(surface, c2, (right_light_x, light_y), 8)
        pygame.draw.circle(surface, (255, 255, 255), (right_light_x, light_y), 4)


# ---------------------------------------------------------------------------
# ROAD & ENVIRONMENT RENDERER
# ---------------------------------------------------------------------------
class Road:
    def __init__(self):
        self.scroll_y = 0.0

    def update(self, player_speed_kmh):
        dy = player_speed_kmh * SPEED_PIXEL_SCALE
        self.scroll_y = (self.scroll_y + dy) % 80

    def draw(self, surface):
        surface.fill(COLOR_GRASS)
        stripe_height = 80
        offset = int(self.scroll_y) % stripe_height
        for y in range(-stripe_height, SCREEN_HEIGHT + stripe_height, stripe_height):
            pygame.draw.rect(surface, COLOR_GRASS_DARK, (0, y + offset, SCREEN_WIDTH, stripe_height // 2))

        kerb_w = 18
        pygame.draw.rect(surface, COLOR_ROAD_SHOULDER, (ROAD_LEFT - kerb_w - 4, 0, ROAD_WIDTH + (kerb_w + 4) * 2, SCREEN_HEIGHT))
        
        for y in range(-stripe_height, SCREEN_HEIGHT + stripe_height, 40):
            k_color = COLOR_KERB_RED if (int((y + offset) // 40) % 2 == 0) else COLOR_KERB_WHITE
            pygame.draw.rect(surface, k_color, (ROAD_LEFT - kerb_w, y + offset, kerb_w, 40))
            pygame.draw.rect(surface, k_color, (ROAD_RIGHT, y + offset, kerb_w, 40))

        pygame.draw.rect(surface, COLOR_ROAD, (ROAD_LEFT, 0, ROAD_WIDTH, SCREEN_HEIGHT))
        pygame.draw.line(surface, COLOR_LINE_WHITE, (ROAD_LEFT + 4, 0), (ROAD_LEFT + 4, SCREEN_HEIGHT), 4)
        pygame.draw.line(surface, COLOR_LINE_WHITE, (ROAD_RIGHT - 4, 0), (ROAD_RIGHT - 4, SCREEN_HEIGHT), 4)

        dash_len = 36
        dash_gap = 26
        total_dash = dash_len + dash_gap
        dash_offset = int(self.scroll_y) % total_dash

        for lane_idx in range(1, LANE_COUNT):
            lane_x = ROAD_LEFT + lane_idx * LANE_WIDTH
            for y in range(-total_dash, SCREEN_HEIGHT + total_dash, total_dash):
                pygame.draw.line(surface, COLOR_LINE_YELLOW, (lane_x, y + dash_offset), (lane_x, y + dash_offset + dash_len), 4)


# ---------------------------------------------------------------------------
# MAIN GAME CLASS & STATE MANAGER
# ---------------------------------------------------------------------------
class Game:
    def __init__(self):
        pygame.display.set_caption("Police Pursuit - 2D Highway Chase")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()

        # Audio Manager
        self.audio = SoundManager()

        # Fonts
        self.font_huge = pygame.font.SysFont("impact", 54)
        self.font_large = pygame.font.SysFont("arial", 28, bold=True)
        self.font_medium = pygame.font.SysFont("arial", 20, bold=True)
        self.font_small = pygame.font.SysFont("consolas", 15, bold=True)

        self.sprites = load_car_sprites()

        self.total_cash = 0.0
        self.unlocked_cars = {"red": True, "yellow": False}
        self.car_prices = {"red": 0, "yellow": 500}
        self.selected_car_index = 0
        self.available_car_keys = ["red", "yellow"]

        self.state = "MENU"
        self.game_over_reason = ""

        self.road = Road()
        self.particles = ParticleSystem()
        self.player = None
        self.police = None
        self.traffic_group = pygame.sprite.Group()
        self.distance_km = 0.0
        self.cash_earned_this_run = 0.0
        self.traffic_spawn_timer = 0.0
        self.police_respawn_timer = 0.0
        self.police_active = False

    def get_selected_car_key(self):
        return self.available_car_keys[self.selected_car_index]

    def reset_game(self):
        selected_key = self.get_selected_car_key()
        self.player = Player(self.sprites[selected_key])
        self.police = Police(self.sprites["police"])
        self.police_active = True
        self.police_respawn_timer = 0.0
        self.traffic_group.empty()
        self.particles = ParticleSystem()
        self.distance_km = 0.0
        self.cash_earned_this_run = 0.0
        self.traffic_spawn_timer = 0.0
        self.game_over_reason = ""

        self.audio.play_start()
        self.audio.play_music()

    def spawn_traffic_vehicle(self):
        lane_idx = random.randint(0, LANE_COUNT - 1)
        lane_center_x = ROAD_LEFT + lane_idx * LANE_WIDTH + LANE_WIDTH // 2
        car_type = random.choice(["yellow", "red"])
        traffic_car = EnemyTraffic(self.sprites[car_type], lane_center_x, start_y=-60)
        
        for existing in self.traffic_group:
            if abs(existing.rect.centerx - lane_center_x) < 30 and existing.rect.top < 180:
                return
                
        self.traffic_group.add(traffic_car)

    def trigger_game_over(self, reason):
        self.game_over_reason = reason
        self.state = "GAME_OVER"
        self.audio.play_game_over()

    def run(self):
        running = True
        while running:
            dt_ms = self.clock.tick(FPS)
            dt_sec = dt_ms / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(event)

            self.update(dt_sec)
            self.draw()
            pygame.display.flip()

        pygame.quit()
        sys.exit()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if self.state == "MENU":
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    self.selected_car_index = (self.selected_car_index - 1) % len(self.available_car_keys)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    self.selected_car_index = (self.selected_car_index + 1) % len(self.available_car_keys)
                elif event.key == pygame.K_b:
                    car_key = self.get_selected_car_key()
                    price = self.car_prices[car_key]
                    if not self.unlocked_cars[car_key] and self.total_cash >= price:
                        self.total_cash -= price
                        self.unlocked_cars[car_key] = True
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    car_key = self.get_selected_car_key()
                    if self.unlocked_cars[car_key]:
                        self.reset_game()
                        self.state = "PLAYING"
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

            elif self.state == "GAME_OVER":
                if event.key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE):
                    self.state = "MENU"
                    self.audio.stop_music()
                elif event.key == pygame.K_r:
                    car_key = self.get_selected_car_key()
                    if self.unlocked_cars[car_key]:
                        self.reset_game()
                        self.state = "PLAYING"

    def update(self, dt_sec):
        if self.state == "PLAYING":
            self.road.update(self.player.speed_kmh)
            self.player.update(dt_sec)

            distance_delta = (self.player.speed_kmh / 3600.0) * dt_sec
            self.distance_km += distance_delta
            
            cash_gain = distance_delta * 100.0
            self.cash_earned_this_run += cash_gain
            self.total_cash += cash_gain

            self.traffic_spawn_timer += dt_sec
            spawn_delay = max(0.9, 1.8 - (self.player.speed_kmh / 150.0) * 0.8)
            if self.traffic_spawn_timer >= spawn_delay:
                self.traffic_spawn_timer = 0.0
                self.spawn_traffic_vehicle()

            self.traffic_group.update(self.player.speed_kmh)

            for traffic_car in list(self.traffic_group):
                if pygame.sprite.collide_rect(self.player, traffic_car):
                    if self.player.take_damage():
                        self.particles.emit_spark(self.player.rect.centerx, self.player.rect.top + 20, 25)
                        self.particles.emit_smoke(self.player.rect.centerx, self.player.rect.centery, 12)
                        traffic_car.kill()
                        
                        if self.player.lives <= 0:
                            self.particles.emit_explosion(self.player.rect.centerx, self.player.rect.centery, 60)
                            self.trigger_game_over("VEHICLE DESTROYED! (0 LIVES LEFT)")
                            return

            if self.police_active and self.police is not None:
                self.police.update(self.player.speed_kmh, self.player.rect.centerx, dt_sec)
                
                if self.police.rect.top > SCREEN_HEIGHT + 70:
                    self.police_active = False
                    self.police = None
                    self.police_respawn_timer = 15.0

                elif self.police is not None and pygame.sprite.collide_rect(self.player, self.police):
                    self.particles.emit_spark(self.player.rect.centerx, self.player.rect.bottom, 30)
                    self.trigger_game_over("BUSTED BY POLICE!")
                    return
            else:
                if self.police_respawn_timer > 0:
                    self.police_respawn_timer -= dt_sec
                    if self.police_respawn_timer <= 0:
                        self.police = Police(self.sprites["police"])
                        self.police_active = True

            self.particles.update()

        elif self.state == "GAME_OVER":
            self.particles.update()

    def draw(self):
        if self.state == "MENU":
            self.draw_menu()
        elif self.state == "PLAYING":
            self.draw_gameplay()
        elif self.state == "GAME_OVER":
            self.draw_gameplay()
            self.draw_game_over()

    def draw_gameplay(self):
        self.road.draw(self.screen)

        for traffic in self.traffic_group:
            self.screen.blit(traffic.image, traffic.rect)

        if self.police_active and self.police is not None:
            self.police.draw(self.screen)

        if self.player is not None and self.player.lives > 0:
            self.player.draw(self.screen)

        self.particles.draw(self.screen)
        self.draw_hud()

    def draw_hud(self):
        hud_h = 65
        hud_surface = pygame.Surface((SCREEN_WIDTH, hud_h), pygame.SRCALPHA)
        hud_surface.fill(COLOR_UI_BG)
        self.screen.blit(hud_surface, (0, 0))
        pygame.draw.line(self.screen, COLOR_BLUE, (0, hud_h), (SCREEN_WIDTH, hud_h), 2)

        # 1. Speedometer
        speed_color = COLOR_GOLD if self.player.speed_kmh > 100 else COLOR_TEXT
        speed_txt = self.font_medium.render(f"SPEED: {int(self.player.speed_kmh)} KM/H", True, speed_color)
        self.screen.blit(speed_txt, (15, 10))
        if self.player.invulnerable_timer > 0:
            inv_txt = self.font_small.render(f"SHIELD: {self.player.invulnerable_timer:.1f}s", True, COLOR_RED)
            self.screen.blit(inv_txt, (15, 38))
        else:
            hint_txt = self.font_small.render("[UP] BOOST  [DOWN] BRAKE", True, (170, 180, 200))
            self.screen.blit(hint_txt, (15, 38))

        # 2. Lives Bar
        lives_label = self.font_medium.render("LIVES:", True, COLOR_TEXT)
        self.screen.blit(lives_label, (215, 10))
        for i in range(5):
            heart_rect = pygame.Rect(280 + i * 22, 12, 18, 18)
            if i < self.player.lives:
                pygame.draw.rect(self.screen, COLOR_RED, heart_rect, border_radius=4)
                pygame.draw.rect(self.screen, (255, 255, 255), heart_rect, 1, border_radius=4)
            else:
                pygame.draw.rect(self.screen, (60, 60, 60), heart_rect, border_radius=4)

        # 3. Distance & Continuous Cash
        dist_txt = self.font_medium.render(f"DIST: {self.distance_km:.2f} KM", True, COLOR_GOLD)
        self.screen.blit(dist_txt, (410, 10))
        cash_txt = self.font_small.render(f"+${self.cash_earned_this_run:.1f}  (Bank: ${self.total_cash:.0f})", True, COLOR_GREEN)
        self.screen.blit(cash_txt, (410, 38))

        # 4. Police Pursuit Status
        if self.police_active and self.police is not None:
            pol_dist_px = self.police.rect.top - self.player.rect.bottom
            pol_txt = self.font_medium.render("PURSUIT ACTIVE!", True, COLOR_RED)
            self.screen.blit(pol_txt, (615, 10))
            dist_desc = f"Gap: {max(0, pol_dist_px)} px"
            gap_txt = self.font_small.render(dist_desc, True, COLOR_TEXT)
            self.screen.blit(gap_txt, (615, 38))
        else:
            status_txt = self.font_medium.render("POLICE OUTRUN!", True, COLOR_GREEN)
            self.screen.blit(status_txt, (615, 10))
            timer_txt = self.font_small.render(f"Next in: {self.police_respawn_timer:.1f}s", True, COLOR_GOLD)
            self.screen.blit(timer_txt, (615, 38))

    def draw_menu(self):
        self.road.draw(self.screen)

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 15, 25, 215))
        self.screen.blit(overlay, (0, 0))

        title = self.font_huge.render("POLICE HIGHWAY CHASE", True, COLOR_GOLD)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 35))

        subtitle = self.font_medium.render("OUTRUN THE SWAT PURSUIT & SURVIVE THE HIGHWAY", True, COLOR_TEXT)
        self.screen.blit(subtitle, (SCREEN_WIDTH // 2 - subtitle.get_width() // 2, 95))

        # Bank Cash Display
        bank_box = pygame.Rect(SCREEN_WIDTH // 2 - 160, 135, 320, 45)
        pygame.draw.rect(self.screen, (20, 30, 45), bank_box, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_GREEN, bank_box, 2, border_radius=8)
        cash_txt = self.font_large.render(f"BANK: ${self.total_cash:.0f}", True, COLOR_GREEN)
        self.screen.blit(cash_txt, (bank_box.centerx - cash_txt.get_width() // 2, bank_box.centery - cash_txt.get_height() // 2))

        # Garage Container
        garage_rect = pygame.Rect(SCREEN_WIDTH // 2 - 320, 195, 640, 350)
        pygame.draw.rect(self.screen, (25, 35, 50, 230), garage_rect, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_BLUE, garage_rect, 2, border_radius=12)

        garage_title = self.font_large.render("GARAGE / SELECT VEHICLE", True, COLOR_TEXT)
        self.screen.blit(garage_title, (garage_rect.centerx - garage_title.get_width() // 2, garage_rect.top + 15))

        card_w, card_h = 240, 260
        car_configs = [
            {"key": "red", "name": "Red Sports Car", "x": garage_rect.left + 50},
            {"key": "yellow", "name": "Yellow Muscle Car", "x": garage_rect.left + 350}
        ]

        for idx, cfg in enumerate(car_configs):
            key = cfg["key"]
            is_selected = (self.selected_car_index == idx)
            is_unlocked = self.unlocked_cars[key]
            price = self.car_prices[key]

            card_rect = pygame.Rect(cfg["x"], garage_rect.top + 55, card_w, card_h)
            bg_c = (35, 48, 70) if is_selected else (20, 28, 40)
            border_c = COLOR_GOLD if is_selected else (60, 75, 100)
            pygame.draw.rect(self.screen, bg_c, card_rect, border_radius=8)
            pygame.draw.rect(self.screen, border_c, card_rect, 3 if is_selected else 1, border_radius=8)

            c_name = self.font_medium.render(cfg["name"], True, COLOR_TEXT)
            self.screen.blit(c_name, (card_rect.centerx - c_name.get_width() // 2, card_rect.top + 10))

            car_sprite = self.sprites[key][0]
            self.screen.blit(car_sprite, (card_rect.centerx - CAR_WIDTH // 2, card_rect.top + 38))

            if is_unlocked:
                status_txt = self.font_medium.render("UNLOCKED", True, COLOR_GREEN)
            else:
                status_txt = self.font_medium.render(f"LOCKED - ${price}", True, COLOR_RED)
            self.screen.blit(status_txt, (card_rect.centerx - status_txt.get_width() // 2, card_rect.bottom - 42))

            if is_selected:
                sel_tag = self.font_small.render("[SELECTED]", True, COLOR_GOLD)
                self.screen.blit(sel_tag, (card_rect.centerx - sel_tag.get_width() // 2, card_rect.bottom - 18))

        sel_key = self.get_selected_car_key()
        if not self.unlocked_cars[sel_key]:
            price = self.car_prices[sel_key]
            can_afford = self.total_cash >= price
            buy_col = COLOR_GOLD if can_afford else (150, 150, 150)
            action_prompt = self.font_large.render(f"Press 'B' to Buy for ${price}" if can_afford else f"Need ${int(price - self.total_cash)} more to Unlock", True, buy_col)
        else:
            action_prompt = self.font_large.render("Press 'ENTER' or 'SPACE' to START CHASE", True, COLOR_GREEN)
        
        self.screen.blit(action_prompt, (SCREEN_WIDTH // 2 - action_prompt.get_width() // 2, 560))

        controls_txt = self.font_small.render("Controls: [LEFT / RIGHT] Steer | [UP] Accelerate (150 km/h) | Earn $100 per 1 KM", True, (200, 200, 210))
        self.screen.blit(controls_txt, (SCREEN_WIDTH // 2 - controls_txt.get_width() // 2, 650))

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill(COLOR_DARK_OVERLAY)
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(SCREEN_WIDTH // 2 - 280, SCREEN_HEIGHT // 2 - 190, 560, 380)
        pygame.draw.rect(self.screen, (20, 25, 38), panel, border_radius=12)
        pygame.draw.rect(self.screen, COLOR_RED, panel, 3, border_radius=12)

        is_busted = "BUSTED" in self.game_over_reason
        title_text = "BUSTED!" if is_busted else "WRECKED!"
        t_color = COLOR_BLUE if is_busted else COLOR_RED
        title = self.font_huge.render(title_text, True, t_color)
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.top + 20))

        reason = self.font_medium.render(self.game_over_reason, True, COLOR_TEXT)
        self.screen.blit(reason, (panel.centerx - reason.get_width() // 2, panel.top + 85))

        dist_info = self.font_large.render(f"Distance Survived: {self.distance_km:.2f} KM", True, COLOR_GOLD)
        self.screen.blit(dist_info, (panel.centerx - dist_info.get_width() // 2, panel.top + 135))

        cash_info = self.font_large.render(f"Earned: +${self.cash_earned_this_run:.1f}   |   Bank: ${self.total_cash:.0f}", True, COLOR_GREEN)
        self.screen.blit(cash_info, (panel.centerx - cash_info.get_width() // 2, panel.top + 185))

        prompt1 = self.font_medium.render("Press 'R' to Retry Chase", True, COLOR_TEXT)
        self.screen.blit(prompt1, (panel.centerx - prompt1.get_width() // 2, panel.top + 255))

        prompt2 = self.font_medium.render("Press 'ENTER' or 'ESC' for Garage / Menu", True, (180, 180, 190))
        self.screen.blit(prompt2, (panel.centerx - prompt2.get_width() // 2, panel.top + 295))


# ---------------------------------------------------------------------------
# ENTRY POINT
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    game = Game()
    game.run()
