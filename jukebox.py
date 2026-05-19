import os
import subprocess
import pygame
from gpiozero import Button
import time

# -----------------------------
# CONFIG
# -----------------------------
VIDEO_DIR = "videos"
VALID_LETTERS = set("ABCDEFGHJKLMNQRSTUV")
VALID_NUMBERS = set("0123456789")
GPIO_STOP_PIN = 17  # GPIO pin connected to your stop button
# -----------------------------

current_letter = None
current_process = None  # mpv process

# Initialize GPIO button
stop_button = Button(GPIO_STOP_PIN)

def stop_video():
    """Stop the current video."""
    global current_process
    if current_process:
        print(f"Stopping video (PID {current_process.pid})")
        if current_process.poll() is None:
            current_process.kill()
        current_process = None
    else:
        print("No video playing.")

# Link button press to stop_video
stop_button.when_pressed = stop_video

# Initialize pygame for letter/number selection
pygame.init()
screen = pygame.display.set_mode((400, 300))
pygame.display.set_caption("Pi Jukebox")

def play_video(filename):
    """Play a video fullscreen, stop previous if any."""
    global current_process
    path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(path):
        print(f"File not found: {filename}")
        return

    stop_video()  # stop any previous video

    print(f"Playing: {filename}")
    current_process = subprocess.Popen([
        "mpv",
        "--no-terminal",
        "--fullscreen",          # fullscreen video
        "--force-window=yes",    # ensures Python can still detect GPIO
        path
    ])

# -----------------------------
# MAIN LOOP
# -----------------------------
print("Press a LETTER then a NUMBER to play a video")
print(f"Press the GPIO button (GPIO {GPIO_STOP_PIN}) to stop the current video")
print("Press ESC to quit")

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            stop_video()
            break
        elif event.type == pygame.KEYDOWN:
            key_name = pygame.key.name(event.key).upper()
            if key_name == "ESCAPE":
                running = False
                stop_video()
                break
            # Letter pressed
            if key_name in VALID_LETTERS:
                current_letter = key_name
                print(f"Letter selected: {current_letter}")
            # Number pressed after letter
            elif key_name in VALID_NUMBERS and current_letter:
                filename = f"{current_letter}{key_name}.mp4"
                play_video(filename)
                current_letter = None

pygame.quit()
