from gpiozero import Button
import time

# White signal wire from receiver connected to GPIO 18
# The sensor output is active-low: HIGH = beam intact, LOW = beam broken
# gpiozero's Button with pull_up=True mirrors this behaviour perfectly
BEAM_PIN = 18

beam = Button(BEAM_PIN, pull_up=True)

print("IR beam test running. Break the beam to test.")
print("Press Ctrl+C to quit.\n")

coin_count = 0

def beam_broken():
    global coin_count
    coin_count += 1
    print(f"Coin detected! (Total: {coin_count})  [{time.strftime('%H:%M:%S')}]")

def beam_restored():
    print("  Beam restored.")

beam.when_pressed = beam_broken    # pin goes LOW = beam broken
beam.when_released = beam_restored # pin goes HIGH = beam restored

try:
    while True:
        time.sleep(0.1)
except KeyboardInterrupt:
    print(f"\nTest ended. Total coins detected: {coin_count}")