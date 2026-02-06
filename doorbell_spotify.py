#!/usr/bin/env python3

import os
import time
import random
from gpiozero import Button
import pygame
import queue
import subprocess
import requests

# ---------------- DISPLAY ENV ----------------
os.environ["DISPLAY"] = ":0"
os.environ["SDL_VIDEODRIVER"] = "x11"

# ---------------- CONFIG ----------------
BUTTON_PIN = 17
HOME = os.path.expanduser("~")
CACHE_DIR = os.path.join(HOME, "doorbell_cache")
PLAY_SECONDS = 15
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")

if not SLACK_WEBHOOK_URL:
    raise ValueError("SLACK_WEBHOOK_URL environment variable not set")


# ---------------- INIT ----------------
os.makedirs(CACHE_DIR, exist_ok=True)

button = Button(BUTTON_PIN, pull_up=True)

pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# Fullscreen display
info = pygame.display.Info()
screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
pygame.mouse.set_visible(False)
WIDTH, HEIGHT = screen.get_size()

# ---------------- FONT ----------------
try:
    font = pygame.font.SysFont("Arial", 70, bold=True)
except:
    font = pygame.font.Font(None, 70)

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# ---------------- UI ----------------
def show_text(msg):
    """Draw text centered on the screen"""
    screen.fill(BLACK)
    txt = font.render(msg, True, WHITE)
    rect = txt.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(txt, rect)
    pygame.display.update()

# ---------------- LOAD AUDIO ----------------
sounds = []

def load_sounds():
    global sounds
    sounds.clear()
    print("Loading audio clips...")
    for file in os.listdir(CACHE_DIR):
        if file.lower().endswith(".wav"):
            path = os.path.join(CACHE_DIR, file)
            try:
                s = pygame.mixer.Sound(path)
                sounds.append(s)
                print("Loaded:", file)
            except Exception as e:
                print("Failed to load:", file, e)
    print("Total sounds loaded:", len(sounds))

# ---------------- NOTIFY FUNCTION ----------------
def send_notification():
    """Send a Slack notification when the doorbell is pressed"""
    payload = {
        "text": "🔔 *Doorbell Pressed*\nSomeone is at the door."
    }

    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json=payload,
            timeout=5
        )
        response.raise_for_status()
        print("Slack notification sent.")
    except requests.exceptions.RequestException as e:
        print(f"Failed to send Slack notification: {e}")


# ---------------- BUTTON HANDLER ----------------
event_queue = queue.Queue()
song_playing = False
notification_sent = False  # Flag to track if notification was sent

def handle_button():
    """Handle single button press, ignore if already playing or notification sent"""
    global song_playing, notification_sent
    if not song_playing and not notification_sent:
        song_playing = True
        event_queue.put("BUTTON_PRESSED")
        # Wait for button release to avoid multiple triggers
        #button.wait_for_release()

button.when_pressed = handle_button

# ---------------- MAIN ----------------
show_text("PRESS DOORBELL FOR SERVICE")  # Initial message
print("System Ready")

load_sounds()

while True:
    pygame.event.pump()
    try:
        event = event_queue.get_nowait()
        if event == "BUTTON_PRESSED":
            print("Button Pressed")

            # Send notification (only once)
            if not notification_sent:
                send_notification()
                notification_sent = True  # Set flag to prevent further notifications

            # Change screen to "SOMEONE WILL BE RIGHT WITH YOU"
            show_text("SOMEONE WILL BE RIGHT WITH YOU")

            # Play random sound
            if sounds:
                sound = random.choice(sounds)
                sound.play(maxtime=PLAY_SECONDS * 1000)  # Play for 15 seconds
                time.sleep(PLAY_SECONDS)  # Wait for the sound to finish
                sound.stop()  # Ensure sound stops after 15 seconds

            # Revert back to default message
            show_text("PRESS DOORBELL FOR SERVICE")

            # Reset the notification flag after the message is played
            notification_sent = False

            # Allow next button press
            song_playing = False

    except queue.Empty:
        pass

    time.sleep(0.05)
