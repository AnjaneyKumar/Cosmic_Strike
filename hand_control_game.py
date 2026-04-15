import cv2
import mediapipe as mp
import random
import time
import pygame
import numpy as np

from boss import Boss

# -------------------- INIT --------------------
pygame.mixer.init()

shoot_sound = pygame.mixer.Sound("shoot.wav")
explosion_sound = pygame.mixer.Sound("explosion.wav")

pygame.mixer.music.load("bg_music.mp3")
pygame.mixer.music.play(-1)

# -------------------- IMAGES --------------------
explosion_img = cv2.imread("explosion.png", cv2.IMREAD_UNCHANGED)
explosion_img = cv2.resize(explosion_img, (50, 50))

ship_img = cv2.imread("spaceship.png", cv2.IMREAD_UNCHANGED)
enemy_img = cv2.imread("enemy.png", cv2.IMREAD_UNCHANGED)
bg_img = cv2.imread("background.jpg")

ship_img = cv2.resize(ship_img, (50, 60))
enemy_img = cv2.resize(enemy_img, (30, 30))

life_img = cv2.imread("life.png", cv2.IMREAD_UNCHANGED)
life_img = cv2.resize(life_img, (30, 30))

bullet_img = cv2.imread("bullet.png", cv2.IMREAD_UNCHANGED)
bullet_img = cv2.resize(bullet_img, (8, 18))

boss_img = cv2.imread("boss.png", cv2.IMREAD_UNCHANGED)

# ✅ Rotate first (keep this)
boss_img = cv2.rotate(boss_img, cv2.ROTATE_90_CLOCKWISE)

# ✅ Fix: resize with aspect ratio (NOT square)
h, w = boss_img.shape[:2]

new_w = 80   # you can change this
new_h = int(h * (new_w / w))

boss_img = cv2.resize(boss_img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)

# -------------------- OVERLAY --------------------
def overlay_image(bg, fg, x, y):
    h, w, _ = fg.shape
    for i in range(h):
        for j in range(w):
            if fg[i, j][3] != 0:
                if 0 <= y+i < bg.shape[0] and 0 <= x+j < bg.shape[1]:
                    bg[y + i, x + j] = fg[i, j][:3]
    return bg

# -------------------- MEDIAPIPE --------------------
mp_hands = mp.solutions.hands
hands = mp_hands.Hands()

mp_draw = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0)

screen_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
screen_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

bg_img = cv2.resize(bg_img, (screen_w, screen_h))

cv2.namedWindow("Gesture Space Shooter", cv2.WND_PROP_FULLSCREEN)
cv2.setWindowProperty("Gesture Space Shooter", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# -------------------- HOME SCREEN --------------------
while True:
    home_frame = bg_img.copy()

    cv2.putText(home_frame, "GESTURE COSMIC STRIKE", (50, 200),
                cv2.FONT_HERSHEY_SIMPLEX, 1.25, (255, 255, 255), 3)

    # Blinking effect
    if int(time.time()) % 2 == 0:
        cv2.putText(home_frame, "Press S to Start", (180, 300),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.putText(home_frame, "Press ESC to Exit", (170, 350),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

    cv2.imshow("Gesture Space Shooter", home_frame)

    key = cv2.waitKey(100)

    if key == ord('s') or key == ord('S'):
        break   # start game
    elif key == 27:
        cap.release()
        cv2.destroyAllWindows()
        exit()

# -------------------- GAME LOOP --------------------
while True:

    # RESET VARIABLES
    lives = 3
    bullets = []
    enemies = []
    explosions = []
    powerups = []

    shake_timer = 0
    shake_intensity = 0

    score = 0
    level = 1
    last_shot = 0

    double_shot = False
    double_timer = 0

    laser_mode = False
    laser_timer = 0

    boss = None
    boss_active = False

    angle = 0
    dx, dy = 1, 0

    # ---------------- MAIN LOOP ----------------
    while True:
        ret, cam_frame = cap.read()
        if not ret:
            break

        cam_frame = cv2.flip(cam_frame, 1)
        h, w, _ = cam_frame.shape

        rgb = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        frame = bg_img.copy()

        shoot = False
        ship_x, ship_y = w // 2, h // 2
        # angle = 0
        # dx, dy = 1, 0

        # HAND TRACKING
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:

                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                # Finger tip → position
                x = int(hand_landmarks.landmark[8].x * w)
                y = int(hand_landmarks.landmark[8].y * h)

                ship_x, ship_y = x, y

                # Wrist → direction
                wx = int(hand_landmarks.landmark[0].x * w)
                wy = int(hand_landmarks.landmark[0].y * h)

                new_dx = x - wx
                new_dy = y - wy

                # ✅ ALWAYS update direction if valid
                if abs(new_dx) > 2 or abs(new_dy) > 2:
                    dx, dy = new_dx, new_dy

                # ✅ ALWAYS update angle (NOT dependent on shoot)
                angle = -np.degrees(np.arctan2(dy, dx)) - 90

                # 🔫 ONLY shooting condition
                if hand_landmarks.landmark[8].y > hand_landmarks.landmark[6].y:
                    shoot = True
        # SHOOT

        if shoot:

            #  LASER MODE (highest priority)
            if laser_mode:
                for _ in range(3):   # bullets per frame
                    bullets.append([ship_x, ship_y, dx, dy])

            #  NORMAL / DOUBLE SHOT
            elif time.time() - last_shot > 0.3:

                if double_shot:
                    bullets.append([ship_x - 10, ship_y, dx, dy])
                    bullets.append([ship_x + 10, ship_y, dx, dy])
                else:
                    bullets.append([ship_x, ship_y, dx, dy])

                shoot_sound.play()
                last_shot = time.time()

        # BULLETS
        for bullet in bullets:
            bx, by, bdx, bdy = bullet

            # Normalize direction
            length = max((bdx**2 + bdy**2)**0.5, 1)
            vx = bdx / length
            vy = bdy / length

            # Move bullet
            bullet[0] += int(vx * 15)
            bullet[1] += int(vy * 15)

            # Angle
            angle_bullet = -np.degrees(np.arctan2(bdy, bdx)) - 90

            # -------- SAFE ROTATION --------
            (h_b, w_b) = bullet_img.shape[:2]
            diag = int(np.sqrt(h_b*h_b + w_b*w_b))

            big_img = np.zeros((diag, diag, 4), dtype=np.uint8)

            x_offset = (diag - w_b) // 2
            y_offset = (diag - h_b) // 2
            big_img[y_offset:y_offset+h_b, x_offset:x_offset+w_b] = bullet_img

            center = (diag // 2, diag // 2)
            M = cv2.getRotationMatrix2D(center, angle_bullet, 1.0)

            rotated_bullet = cv2.warpAffine(
                big_img,
                M,
                (diag, diag),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_TRANSPARENT
            )

            # ✅ DRAW INSIDE LOOP
            frame = overlay_image(
                frame,
                rotated_bullet,
                int(bullet[0] - diag//2),
                int(bullet[1] - diag//2)
            )
        # ENEMIES
        if random.randint(1, 20) == 1:
            enemies.append([random.randint(50, w-50), 0])

        for enemy in enemies:
            enemy[1] += 3 + level
            y1 = enemy[1] - 25
            x1 = enemy[0] - 25

            if 0 < y1 < h-50 and 0 < x1 < w-50:
                frame = overlay_image(frame, enemy_img, x1, y1)

        enemies = [e for e in enemies if e[1] < h]

        if boss_active:
            boss.move(w , h)
            boss.shoot(time.time())
            boss.update_bullets(frame, h)

            boss.draw(frame, boss_img)
            boss.hit(bullets)

            # 💥 Boss hits player
            if boss.hit_player(ship_x, ship_y):
                lives -= 1
                shake_timer = 10
                shake_intensity = 10

            # Boss defeated
            if boss.health <= 0:
                explosion_points = []

                # 💥 BIG EXPLOSION EFFECT
                for _ in range(10):   # number of explosions
                    ex = boss.x + random.randint(-60, 60)
                    ey = boss.y + random.randint(-60, 60)
                    explosions.append([ex, ey, 15])   # longer duration

                explosion_sound.play()

                boss_active = False
                score += 30

        # SPAWN POWERUPS
        if random.randint(1, 200) == 1:
            power_type = random.choice(["double", "laser"])
            powerups.append([random.randint(50, w-50), 0, power_type])

        # MOVE POWERUPS
        for p in powerups:
            p[1] += 4

            x, y = p[0], p[1]

            if p[2] == "double":
                color = (255, 0, 255)   # purple

                # ✨ GLOW (outer)
                for r in range(12, 6, -2):
                    cv2.circle(frame, (x, y), r, color, 1)

                # ➕ PLUS SHAPE (inner)
                cv2.line(frame, (x-8, y), (x+8, y), color, 3)
                cv2.line(frame, (x, y-8), (x, y+8), color, 3)

            else:  # laser / rapid fire
                color = (255, 200, 0)   # sky blue (BGR)

                x, y = p[0], p[1]

                # ✨ GLOW
                for r in range(14, 8, -2):
                    cv2.circle(frame, (x, y), r, color, 1)

                # ↑ ARROW SHAFT (vertical)
                cv2.line(frame, (x, y+10), (x, y-5), color, 3)

                # ▲ ARROW HEAD (pointing UP)
                pts = np.array([
                    [x-6, y-5],
                    [x+6, y-5],
                    [x, y-12]
                ])
                cv2.fillPoly(frame, [pts], color)


        # COLLISION
        for bullet in bullets[:]:
            for enemy in enemies[:]:
                if abs(bullet[0] - enemy[0]) < 20 and abs(bullet[1] - enemy[1]) < 20:
                    score += 1
                    explosions.append([enemy[0], enemy[1], 10])
                    explosion_sound.play()
                    bullets.remove(bullet)
                    enemies.remove(enemy)
                    break

        # POWERUP COLLECTION
        for p in powerups[:]:
            if abs(p[0] - ship_x) < 30 and abs(p[1] - ship_y) < 30:

                if p[2] == "double":
                    double_shot = True
                    double_timer = time.time()

                elif p[2] == "laser":
                    laser_mode = True
                    laser_timer = time.time()

                powerups.remove(p)

        # TIMERS
        if double_shot and time.time() - double_timer > 5:
            double_shot = False

        if laser_mode and time.time() - laser_timer > 3:
            laser_mode = False

        # LEVEL
        level = score // 5 + 1

        if level == 5 and not boss_active:
            boss = Boss(w)
            boss_active = True

        # EXPLOSIONS
        for exp in explosions:
            x, y, timer = exp
            frame = overlay_image(frame, explosion_img, x-25, y-25)
            exp[2] -= 1

        explosions = [e for e in explosions if e[2] > 0]

        # PLAYER HIT
        for enemy in enemies[:]:
            if abs(enemy[0] - ship_x) < 25 and abs(enemy[1] - ship_y) < 25:
                lives -= 1
                shake_timer = 10
                shake_intensity = 10
                enemies.remove(enemy)
                break

        lives = max(lives, 0)

        # GAME OVER
        if lives <= 0:
            while True:
                frame = bg_img.copy()

                cv2.putText(frame, "GAME OVER", (120, 250),
                            cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 5)

                cv2.putText(frame, f"Final Score: {score}", (150, 320),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

                cv2.putText(frame, "Press R to Restart or ESC to Exit", (80, 380),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                
                if shake_timer > 0:
                    shake_x = random.randint(-shake_intensity, shake_intensity)
                    shake_y = random.randint(-shake_intensity, shake_intensity)

                    M = np.float32([[1, 0, shake_x], [0, 1, shake_y]])
                    frame = cv2.warpAffine(frame, M, (w, h))

                    shake_timer -= 1

                cv2.imshow("Gesture Space Shooter", frame)

                key = cv2.waitKey(0)

                if key == ord('r') or key == ord('R'):
                    break   # restart outer loop
                elif key == 27:
                    cap.release()
                    cv2.destroyAllWindows()
                    exit()

            break   # exit main game loop → restart

        # DRAW SHIP
        (hs, ws) = ship_img.shape[:2]
        center = (ws // 2, hs // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated_ship = cv2.warpAffine(ship_img, M, (ws, hs), borderMode=cv2.BORDER_TRANSPARENT)

        # 🚨 LOW HEALTH BLINK
        if lives == 1:
            blink = int(time.time() * 10) % 2

            if blink == 0:
                frame = overlay_image(frame, rotated_ship, ship_x-30, ship_y-30)
            else:
                red_ship = rotated_ship.copy()
                red_ship[:, :, 2] = 255   # increase red
                frame = overlay_image(frame, red_ship, ship_x-30, ship_y-30)

        else:
            frame = overlay_image(frame, rotated_ship, ship_x-30, ship_y-30)

        # UI
        cv2.putText(frame, f"Score: {score}", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.putText(frame, f"Level: {level}", (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 255), 2)

        # POWERUP TEXT
        if double_shot:
            cv2.putText(frame, "DOUBLE FIRE!", (200, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 255), 2)

        if laser_mode:
            cv2.putText(frame, "LASER MODE!", (200, 80),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)

        # LIVES
        for i in range(lives):
            x_offset = w - (lives - i) * 35 - 10
            frame = overlay_image(frame, life_img, x_offset, 20)

        # 💥 APPLY SHAKE DURING GAMEPLAY
        if shake_timer > 0:
            shake_x = random.randint(-shake_intensity, shake_intensity)
            shake_y = random.randint(-shake_intensity, shake_intensity)

            frame = np.roll(frame, shake_y, axis=0)
            frame = np.roll(frame, shake_x, axis=1)

            shake_timer -= 1

        cv2.imshow("Gesture Space Shooter", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            cap.release()
            cv2.destroyAllWindows()
            exit()