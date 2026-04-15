import cv2
import random
import time
import numpy as np

class Boss:
    def __init__(self, w):
        self.x = w // 2
        self.y = 80
        self.health = 50
        self.max_health = 50

        self.bullets = []
        self.last_shot = 0

        self.dx = 3
        self.dy = 2
        self.last_dir_change = time.time()

    # ✅ FIXED: now outside __init__
    def move(self, w, h):
        # change direction randomly every 1–2 seconds
        if time.time() - self.last_dir_change > random.uniform(1, 2):
            self.dx = random.randint(-5, 5)
            self.dy = random.randint(-3, 3)
            self.last_dir_change = time.time()

        self.x += self.dx
        self.y += self.dy

        # keep boss inside screen
        if self.x < 80 or self.x > w - 80:
            self.dx *= -1

        if self.y < 50 or self.y > h // 2:
            self.dy *= -1

    def shoot(self, current_time):
        if current_time - self.last_shot > 1:

            angles = [random.randint(-60, 60) for _ in range(3)]   # spread angles

            for angle in angles:
                rad = angle * 3.14 / 180

                dx = int(5 * np.sin(rad))     # small horizontal spread
                dy = int(10 * np.cos(rad))    # strong downward movement


                self.bullets.append([self.x, self.y, dx, dy])

            self.last_shot = current_time

    def update_bullets(self, frame, h):
        for b in self.bullets:
            b[0] += b[2]   # dx
            b[1] += b[3]   # dy

            # Outer glow
            cv2.circle(frame, (b[0], b[1]), 8, (0, 255, 255), -1)   # yellow glow

            # Inner core
            cv2.circle(frame, (b[0], b[1]), 4, (0, 200, 255), -1)   # bright center

        self.bullets = [b for b in self.bullets if 0 < b[0] < frame.shape[1] and 0 < b[1] < frame.shape[0]]

    def draw(self, frame, boss_img):
        frame_h, frame_w = frame.shape[:2]

        h, w = boss_img.shape[:2]

        x1 = int(self.x - w // 2)
        y1 = int(self.y - h // 2)
        
        # Boundary check
        h, w = boss_img.shape[:2]

        for i in range(h):
            for j in range(w):

                if boss_img[i, j][3] != 0:

                    y = y1 + i
                    x = x1 + j

                    # ✅ Only check pixel, not whole image
                    if 0 <= x < frame.shape[1] and 0 <= y < frame.shape[0]:
                        frame[y, x] = boss_img[i, j][:3]

        # Health bar
        bar_w = 200
        health_w = int((self.health / self.max_health) * bar_w)

        cv2.rectangle(frame, (self.x - 100, self.y - 80),
                    (self.x + 100, self.y - 60), (50, 50, 50), -1)

        cv2.rectangle(frame, (self.x - 100, self.y - 80),
                    (self.x - 100 + health_w, self.y - 60), (0, 255, 0), -1)

        bar_w = 200
        health_w = int((self.health / self.max_health) * bar_w)

        cv2.rectangle(frame, (self.x - 100, self.y - 70),
                      (self.x + 100, self.y - 50), (50, 50, 50), -1)

        cv2.rectangle(frame, (self.x - 100, self.y - 70),
                      (self.x - 100 + health_w, self.y - 50), (0, 255, 0), -1)

    def hit(self, bullets):
        for bullet in bullets[:]:
            if abs(bullet[0] - self.x) < 50 and abs(bullet[1] - self.y) < 50:
                self.health -= 1
                bullets.remove(bullet)

    def hit_player(self, ship_x, ship_y):
        for b in self.bullets[:]:
            if abs(b[0] - ship_x) < 30 and abs(b[1] - ship_y) < 30:
                self.bullets.remove(b)
                return True
        return False