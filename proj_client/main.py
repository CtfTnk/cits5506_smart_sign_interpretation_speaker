import cv2
import mediapipe as mp
import numpy as np
import os
import time
import json
from PiicoDev_SSD1306 import *
from picamera2 import Picamera2  # Import picamera2
from gpiozero import Button
from json_req import predict_letter
from gtts_func import text_to_audio
from MQTT_pie import publish_message, start_MQTT_client, stop_MQTT_client


# Initialize MediaPipe Hands and drawing utilities.
mp_hands = mp.solutions.hands
# mp_drawing = mp.solutions.drawing_utils
display = create_PiicoDev_SSD1306()

# Initialize the button
capture_btn = Button(18)
space_btn = Button(23)
backspace_btn = Button(24)
play_btn = Button(25)

# Create a directory to save data if it doesn't exist.
save_dir = os.path.join(os.getcwd(), 'saved_data')
os.makedirs(save_dir, exist_ok=True)

# Global variables to store the latest hand data and image
hand_data = None
hand_image = None

# Global variable to store the content string
content = ''
speech_content = ''

# Initialize picamera2
picam2 = Picamera2()
# Configure the camera for still image capture
picam2.configure(picam2.create_still_configuration(main={"format": "RGB888", "size": (640, 480)}))
picam2.start()

# start AWS IoT core MQTT client
start_MQTT_client()

# Initialize the Hands model once
hands = mp_hands.Hands(
    static_image_mode=True,        # For picture input.
    max_num_hands=1,               # Maximum number of hands to detect.
    min_detection_confidence=0.7, # Minimum confidence for detection.
    min_tracking_confidence=0.5    # Minimum confidence for tracking.
)

def clean_canvas():
    """Clean the display canvas."""
    display.fill(0)
    # display.show()

def update_status(message):
    """Update the text display bar with a given message."""
    clean_canvas()
    if len(message) < 16:
        display_str = message.center(16)
    else:
        display_str = message[:16]
    
    display.text(display_str, 0, 54, 1)
    display.show()
    
def update_content(message):
    """Update the content string with a given message."""
    clean_canvas()
    char_num = len(message)
    if char_num > 48:
        display_str = message[-48:]
    else:
        display_str = message
    display_str = display_str.replace(' ', '_')
    row_num = (len(display_str) - 1) // 16
    for i in range(3):
        if i <= row_num:
            display.text(display_str[i*16:(i+1)*16], 0, i*18, 1)
    display.show()

# find the preset quick speech
def get_speech_content(character):
    # Ensure the input is an uppercase letter
    character = character.upper()

    # Path to speech.json file
    file_path = 'buildin-speech/speech.json'
    
    try:
        # Open and read the JSON file
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Check if the character exists in the JSON file
        if character in data:
            content = data[character]
            if content and content != "":
                return content, True
            else:
                return "Uncertain", False
        else:
            return "Uncertain", False
    except FileNotFoundError:
        return "File not found", False
    except json.JSONDecodeError:
        return "Invalid JSON structure", False

# construct the speech content
def construct_speech_content():
    global content, speech_content
    speech_content = ''
    for char in content:
        tgt_speech, success = get_speech_content(char)
        if success:
            speech_content += tgt_speech + ' '


def take_picture(mode='single'):
    global hand_data, hand_image, content, speech_content

    update_status(f"Capture image")

    # Capture a frame from picamera2
    frame = picam2.capture_array()
    # Flip the frame horizontally for a selfie-view display.
    frame = cv2.flip(frame, 1)
    
    # Convert the image to RGB (already in RGB format, so this step is optional)
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Process the image to find hands.
    results = hands.process(frame)

    # Check if any hands are found.
    if results.multi_hand_landmarks and results.multi_handedness:
        hand_data = []
        for hand_landmarks, hand_handedness in zip(results.multi_hand_landmarks, results.multi_handedness):
            # Collect landmarks data
            landmarks = []
            for lm in hand_landmarks.landmark:
                landmarks.append({'x': lm.x, 'y': lm.y, 'z': lm.z})
            
            # Get handedness (left or right hand)
            handedness_label = hand_handedness.classification[0].label
            handedness_score = hand_handedness.classification[0].score
            
            # Combine landmarks and handedness into one dictionary
            hand_info = {
                'handedness': handedness_label,
                'handedness_score': handedness_score,
                'landmarks': landmarks
            }
            hand_data.append(hand_info)
            
            # Break after processing the first hand.
            break
        
        letter, success = predict_letter(hand_data)
        if success:
            update_status(f"Get: {letter}")
            content += letter
            time.sleep(0.5)
            if mode == 'single':
                update_content(content)
            elif mode == 'speech':
                construct_speech_content()
                update_content(speech_content)
        else:
            update_status("No Result")
            time.sleep(0.5)
            if mode == 'single':
                update_content(content)
            elif mode == 'speech':
                construct_speech_content()
                update_content(speech_content)
            
    else:
        hand_data = None
        update_status("No Result")

def save_data():
    global hand_data
    if hand_data is not None:
        timestamp = int(time.time() * 1000)
        filename = f'hand_{timestamp}.json'
        filepath = os.path.join(save_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(hand_data, f, indent=4)  # Pretty-print JSON data
        update_status(f"Saved hand data: {filepath}")
    else:
        update_status("No hand data to save")

def add_space(mode='single'):
    update_status("Added Space")
    global content, speech_content
    content += ' '
    time.sleep(0.5)
    if mode == 'single':
        update_content(content)
    elif mode == 'speech':
        construct_speech_content()
        update_content(speech_content)
    
def backspace(mode='single'):
    update_status("Deleted Last")
    global content, speech_content
    content = content[:-1]
    time.sleep(0.5)
    if mode == 'single':
        update_content(content)
    elif mode == 'speech':
        construct_speech_content()
        update_content(speech_content)
    
def play_audio(mode='single'):
    update_status("Played Audio")
    global content, speech_content
    if mode == 'single':
        text_to_audio(content, lang='en', save=False)
        publish_message(content)
    elif mode == 'speech':
        text_to_audio(speech_content, lang='en', save=False)
        publish_message(speech_content)
    content = ''
    time.sleep(0.5)
    if mode == 'single':
        update_content(content)
    elif mode == 'speech':
        construct_speech_content()
        update_content(speech_content)


# Execution Logic
def by_alphabet():
    global content
    update_status("a Mode")
    mode_on = True
    while mode_on:
        if capture_btn.is_pressed:
            print('capture button')
            take_picture()
        elif space_btn.is_pressed:
            print('space button')
            add_space()
        elif backspace_btn.is_pressed:
            print('backsp button')
            backspace()
        elif play_btn.is_pressed:
            if len(content) <= 0:
                mode_on = False
                print('quit alphabet mode')
                update_status("Quit a Mode")
            print('audio button')
            play_audio()

def by_speech():
    global content, speech_content
    update_status("s Mode")
    mode_on = True
    while mode_on:
        if capture_btn.is_pressed:
            print('capture button')
            take_picture(mode='speech')
        elif space_btn.is_pressed:
            print('space button')
            # add_space()
            mode_on = False
        elif backspace_btn.is_pressed:
            print('backsp button')
            backspace(mode='speech')
        elif play_btn.is_pressed:
            if len(content) <= 0:
                mode_on = False
                print('quit speech mode')
                update_status("Quit s Mode")
            print('audio button')
            # text_to_audio(speech_content, lang='en', save=False)
            play_audio(mode='speech')
            content = ''
            time.sleep(0.5)
            update_content(content)

# Start the application main loop
try:
    # update_status("Gesture Keyboard")
    # while True:
    #     if capture_btn.is_pressed:
    #         print('capture button')
    #         take_picture()
    #     elif space_btn.is_pressed:
    #         print('space button')
    #         add_space()
    #     elif backspace_btn.is_pressed:
    #         print('backsp button')
    #         backspace()
    #     elif play_btn.is_pressed:
    #         print('audio button')
    #         play_audio()
    while True:
        update_status("SELECT MODE")
        if capture_btn.is_pressed:
            by_alphabet()
        elif space_btn.is_pressed:
            by_speech()

finally:
    # Release resources
    hands.close()
    picam2.close()
    stop_MQTT_client()
