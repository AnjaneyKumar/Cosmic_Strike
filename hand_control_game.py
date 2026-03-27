import cv2
import mediapipe as mp
import random
import time
import pygame

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

ship_img = cv2.resize(ship_img, (80, 80))
enemy_img = cv2.resize(enemy_img, (50, 50))
bg_img = cv2.resize(bg_img, (640, 480))

life_img = cv2.imread("life.png", cv2.IMREAD_UNCHANGED)
life_img = cv2.resize(life_img, (30, 30))

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

# -------------------- GAME LOOP (RESTARTABLE) --------------------
while True:

    # RESET GAME VARIABLES
    lives = 3
    bullets = []
    enemies = []
    explosions = []
    score = 0
    last_shot = 0
    level = 1

    # ---------------- MAIN GAME LOOP ----------------
    while True:
        ret, cam_frame = cap.read()
        if not ret:
            break

        cam_frame = cv2.flip(cam_frame, 1)
        h, w, c = cam_frame.shape

        rgb = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb)

        frame = bg_img.copy()

        shoot = False
        ship_x, ship_y = w // 2, h // 2

        # HAND TRACKING
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

                x = int(hand_landmarks.landmark[8].x * w)
                y = int(hand_landmarks.landmark[8].y * h)

                ship_x, ship_y = x, y

                if hand_landmarks.landmark[8].y > hand_landmarks.landmark[6].y:
                    shoot = True

        # SHOOT
        if shoot and time.time() - last_shot > 0.3:
            bullets.append([ship_x, ship_y])
            shoot_sound.play()
            last_shot = time.time()

        # BULLETS
        for bullet in bullets:
            bullet[1] -= 15
            cv2.rectangle(frame, (bullet[0]-2, bullet[1]-10),
                          (bullet[0]+2, bullet[1]+10), (0, 255, 255), -1)

        bullets = [b for b in bullets if b[1] > 0]

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

        # UPDATE LEVEL
        level = score // 5 + 1

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
                enemies.remove(enemy)
                break

        lives = max(lives, 0)

        # GAME OVER SCREEN
        if lives <= 0:
            frame = bg_img.copy()
            cv2.putText(frame, "GAME OVER", (120, 250),
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 5)
            cv2.putText(frame, f"Final Score: {score}", (150, 320),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
            cv2.putText(frame, "Press R to Restart", (120, 380),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            cv2.imshow("Gesture Space Shooter", frame)

            key = cv2.waitKey(0)

            if key == ord('r') or key == ord('R'):
                break  # restart game
            else:
                cap.release()
                cv2.destroyAllWindows()
                exit()

        # DRAW SHIP
        if 30 < ship_x < w-30 and 30 < ship_y < h-30:
            frame = overlay_image(frame, ship_img, ship_x-30, ship_y-30)

        # UI
        cv2.putText(frame, f"Score: {score}", (10, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

        cv2.putText(frame, f"Level: {level}", (10, 80),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 255), 2)

        # DRAW LIVES ON RIGHT SIDE
        for i in range(lives):
            x_offset = w - (lives - i) * 35 - 10   # align to right
            y_offset = 20
            frame = overlay_image(frame, life_img, x_offset, y_offset)
        
        # cv2.putText(frame, f"Level: {level}", (10, 120),
        #     cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 200, 255), 2)

        cv2.imshow("Gesture Space Shooter", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            cap.release()
            cv2.destroyAllWindows()
            exit()