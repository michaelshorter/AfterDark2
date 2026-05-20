import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
import vlc
import pygame
import threading
import time
from gpiozero import Button

# -----------------------------
# CONFIG
# -----------------------------
VIDEO_DIR     = "/media/jukebox/JUKEBOX/videos"
VALID_LETTERS = set("ABCDEFGHJKLMNQRSTUV")
VALID_NUMBERS = set("0123456789")
BEAM_PIN      = 18
GPIO_STOP_PIN = 17
FADE_DURATION = 3
FADE_STEPS    = 100
WINDOW_WIDTH  = 1920
WINDOW_HEIGHT = 1080
TOKEN_IMAGE   = "/media/jukebox/JUKEBOX/insert_token.png"
IDLE_IMAGE    = "/media/jukebox/JUKEBOX/make_selection.png"
# -----------------------------

current_letter  = None
player          = None
fade_lock       = threading.Lock()
show_token_flag = threading.Event()
show_idle_flag  = threading.Event()

# States
STATE_TOKEN   = "token"    # waiting for token
STATE_IDLE    = "idle"     # waiting for selection
STATE_PLAYING = "playing"  # video playing
state         = STATE_TOKEN

vlc_instance = vlc.Instance("--quiet", "--codec=avcodec,none", "--mouse-hide-timeout=0")
beam_sensor  = Button(BEAM_PIN, pull_up=True)

# -----------------------------
# PYGAME SETUP
# -----------------------------
pygame.init()
pygame.mouse.set_visible(False)
os.environ['SDL_VIDEO_CENTERED'] = '1'
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.FULLSCREEN)
pygame.display.set_caption("AfterDark Jukebox")

def load_surface(path):
    if os.path.exists(path):
        return pygame.transform.scale(
            pygame.image.load(path), (WINDOW_WIDTH, WINDOW_HEIGHT)
        )
    else:
        surf = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT))
        surf.fill((0, 0, 0))
        return surf

token_surface = load_surface(TOKEN_IMAGE)
idle_surface  = load_surface(IDLE_IMAGE)

def show_token():
    """Show insert token screen. Call only from main thread."""
    screen.blit(token_surface, (0, 0))
    pygame.display.flip()

def show_idle():
    """Show make your selection screen. Call only from main thread."""
    screen.blit(idle_surface, (0, 0))
    pygame.display.flip()

# Start on token screen
pygame.mouse.set_visible(False)
pygame.event.pump()
show_token()
pygame.display.flip()

# -----------------------------
# FADE HELPER
# -----------------------------
def _set_video_level(p, frac):
    p.video_set_adjust_float(vlc.VideoAdjustOption.Brightness, frac)
    p.video_set_adjust_float(vlc.VideoAdjustOption.Contrast,   frac)
    p.video_set_adjust_float(vlc.VideoAdjustOption.Saturation, frac)
    p.audio_set_volume(int(frac * 100))

# -----------------------------
# FADE
# -----------------------------
def _fade(p, direction="out", block=False):
    def _run():
        with fade_lock:
            if not p:
                return
            delay = FADE_DURATION / FADE_STEPS
            rng = range(FADE_STEPS, -1, -1) if direction == "out" else range(FADE_STEPS + 1)
            for i in rng:
                if not p.is_playing() and direction == "out":
                    break
                _set_video_level(p, i / FADE_STEPS)
                time.sleep(delay)
            if direction == "out":
                p.stop()
                show_idle_flag.set()  # token was inserted so go to selection screen
                print("Fade out complete, video stopped.")

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    if block:
        t.join()

# -----------------------------
# VIDEO CONTROL
# -----------------------------
def play_video(filename):
    global player, state

    path = os.path.join(VIDEO_DIR, filename)
    if not os.path.exists(path):
        print(f"File not found: {filename}")
        return

    if player and player.is_playing():
        print("Video already playing, selection ignored.")
        return

    print(f"Playing: {filename}")
    state  = STATE_PLAYING
    media  = vlc_instance.media_new(path)
    player = vlc_instance.media_player_new()
    player.set_media(media)

    wm_info = pygame.display.get_wm_info()
    player.set_xwindow(wm_info["window"])

    player.video_set_adjust_int(vlc.VideoAdjustOption.Enable, 1)
    _set_video_level(player, 1.0)
    player.play()

def stop_video():
    global player, state
    if player:
        player.stop()
        player = None
    state = STATE_TOKEN
    show_token()

# -----------------------------
# IR BEAM
# -----------------------------
def on_beam_broken():
    global state
    if state == STATE_PLAYING:
        # Token during video — fade out then go to selection screen
        p = player
        threading.Thread(target=_fade, kwargs={"p": p, "direction": "out"}, daemon=True).start()
    elif state == STATE_TOKEN:
        # Token inserted at token screen — go to selection screen
        state = STATE_IDLE
        show_idle_flag.set()
        print("Token inserted, showing selection screen.")
    else:
        print("Already on selection screen.")

beam_sensor.when_pressed = on_beam_broken

# -----------------------------
# MAIN LOOP
# -----------------------------
print("Waiting for token insertion...")
print("Press ESC to quit")

running = True
while running:
    pygame.mouse.set_visible(False)

    # Handle screen transitions requested by background threads
    if show_idle_flag.is_set():
        show_idle()
        show_idle_flag.clear()
        state = STATE_IDLE

    if show_token_flag.is_set():
        show_token()
        show_token_flag.clear()
        state = STATE_TOKEN

    # Clean up player if video ended naturally
    if player and player.get_state() == vlc.State.Ended:
        player.stop()
        player = None
        state = STATE_TOKEN
        show_token()
        print("Video ended, waiting for token.")

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
            if state == STATE_IDLE:
                if key_name in VALID_LETTERS:
                    current_letter = key_name
                    print(f"Letter selected: {current_letter}")
                elif key_name in VALID_NUMBERS and current_letter:
                    filename = f"{current_letter}{key_name}.mp4"
                    threading.Thread(target=play_video, args=(filename,), daemon=True).start()
                    current_letter = None

    time.sleep(0.1)

pygame.quit()
