"""
Balloon Popping Game (Tkinter, standard library only)

How to play:
  - Balloons float up from the bottom. Click them to pop and score.
  - Faster balloons are worth more points.
  - You lose a life for every balloon that escapes off the top.
  - Game ends at 0 lives. Press R to restart, P to pause.
"""

import random
import tkinter as tk

WIDTH, HEIGHT = 600, 700
COLORS = ["red", "blue", "green", "orange", "purple", "hotpink", "gold", "cyan"]
FRAME_MS = 30          # ~33 FPS
START_LIVES = 5


class Balloon:
    """One balloon = an oval + a string line + a highlight on the canvas."""

    def __init__(self, canvas, level):
        self.canvas = canvas
        self.r = random.randint(22, 38)                      # radius
        self.x = random.randint(self.r + 5, WIDTH - self.r - 5)
        self.y = HEIGHT + self.r
        # speed grows with level, with some randomness per balloon
        self.speed = random.uniform(1.5, 3.0) + level * 0.35
        self.sway = random.uniform(-0.6, 0.6)                # horizontal drift
        color = random.choice(COLORS)

        self.body = canvas.create_oval(
            self.x - self.r, self.y - self.r * 1.2,
            self.x + self.r, self.y + self.r * 1.2,
            fill=color, outline="black", width=1, tags="balloon")
        self.shine = canvas.create_oval(
            self.x - self.r * 0.5, self.y - self.r * 0.9,
            self.x - self.r * 0.1, self.y - self.r * 0.5,
            fill="white", outline="", tags="balloon")
        self.string = canvas.create_line(
            self.x, self.y + self.r * 1.2,
            self.x, self.y + self.r * 2.2,
            fill="gray30", tags="balloon")

        # points: smaller + faster balloons are worth more
        self.points = max(1, int(self.speed * 2 + (40 - self.r) / 5))

    def move(self):
        self.y -= self.speed
        self.x += self.sway
        # bounce off side walls
        if self.x < self.r or self.x > WIDTH - self.r:
            self.sway *= -1
        for item in (self.body, self.shine, self.string):
            self.canvas.move(item, self.sway, -self.speed)

    def contains(self, px, py):
        """Ellipse hit-test: ((dx/a)^2 + (dy/b)^2) <= 1"""
        a, b = self.r, self.r * 1.2
        return ((px - self.x) / a) ** 2 + ((py - self.y) / b) ** 2 <= 1

    def escaped(self):
        return self.y + self.r * 2.2 < 0

    def delete(self):
        for item in (self.body, self.shine, self.string):
            self.canvas.delete(item)


class BalloonGame:
    def __init__(self, root):
        self.root = root
        root.title("Balloon Pop")
        root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#87ceeb")
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)
        root.bind("<r>", lambda e: self.reset())
        root.bind("<R>", lambda e: self.reset())
        root.bind("<p>", lambda e: self.toggle_pause())
        root.bind("<P>", lambda e: self.toggle_pause())

        self.hud = self.canvas.create_text(
            10, 10, anchor="nw", font=("Arial", 16, "bold"), fill="black")
        self.reset()

    # ---------- game state ----------
    def reset(self):
        self.canvas.delete("balloon")
        self.canvas.delete("overlay")
        self.balloons = []
        self.score = 0
        self.lives = START_LIVES
        self.level = 0
        self.spawn_timer = 0
        self.spawn_gap = 40          # frames between spawns
        self.paused = False
        self.game_over = False
        self.update_hud()
        # cancel any old loop so restarting doesn't double the speed
        if getattr(self, "loop_id", None):
            self.root.after_cancel(self.loop_id)
        self.loop()

    def toggle_pause(self):
        if self.game_over:
            return
        self.paused = not self.paused
        self.canvas.delete("overlay")
        if self.paused:
            self.canvas.create_text(
                WIDTH // 2, HEIGHT // 2, text="PAUSED", tags="overlay",
                font=("Arial", 36, "bold"), fill="white")

    def update_hud(self):
        self.canvas.itemconfig(
            self.hud,
            text=f"Score: {self.score}   Lives: {'♥' * self.lives}   Level: {self.level + 1}")
        self.canvas.tag_raise(self.hud)

    # ---------- input ----------
    def on_click(self, event):
        if self.paused or self.game_over:
            return
        # iterate top-most (newest) first so overlapping balloons pop correctly
        for b in reversed(self.balloons):
            if b.contains(event.x, event.y):
                self.pop(b, event.x, event.y)
                break

    def pop(self, balloon, x, y):
        self.score += balloon.points
        self.balloons.remove(balloon)
        balloon.delete()
        self.spawn_burst(x, y, balloon.points)
        # level up every 50 points
        new_level = self.score // 50
        if new_level > self.level:
            self.level = new_level
            self.spawn_gap = max(12, 40 - self.level * 4)
        self.update_hud()

    def spawn_burst(self, x, y, points):
        """Small '+N' popup that floats up and fades away."""
        text = self.canvas.create_text(
            x, y, text=f"+{points}", font=("Arial", 18, "bold"),
            fill="white", tags="balloon")

        def rise(step=0):
            if step >= 15:
                self.canvas.delete(text)
                return
            self.canvas.move(text, 0, -2)
            self.root.after(30, rise, step + 1)
        rise()

    # ---------- main loop ----------
    def loop(self):
        if not self.paused and not self.game_over:
            self.spawn_timer += 1
            if self.spawn_timer >= self.spawn_gap:
                self.spawn_timer = 0
                self.balloons.append(Balloon(self.canvas, self.level))

            # iterate over a copy because we remove items while looping
            for b in self.balloons[:]:
                b.move()
                if b.escaped():
                    self.balloons.remove(b)
                    b.delete()
                    self.lives -= 1
                    self.update_hud()
                    if self.lives <= 0:
                        self.end_game()
                        return

        self.loop_id = self.root.after(FRAME_MS, self.loop)

    def end_game(self):
        self.game_over = True
        self.canvas.create_rectangle(
            0, HEIGHT // 2 - 80, WIDTH, HEIGHT // 2 + 80,
            fill="black", stipple="gray50", tags="overlay")
        self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 - 25, text="GAME OVER", tags="overlay",
            font=("Arial", 36, "bold"), fill="white")
        self.canvas.create_text(
            WIDTH // 2, HEIGHT // 2 + 25,
            text=f"Final score: {self.score}   |   Press R to restart",
            tags="overlay", font=("Arial", 16), fill="white")


if __name__ == "__main__":
    root = tk.Tk()
    BalloonGame(root)
    root.mainloop()
