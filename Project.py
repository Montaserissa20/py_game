import cv2
import mediapipe as mp
import time
import pygame
import sys
import math

# some code to init mediapipe hands model 
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2, min_detection_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# some code to init our pygame model
pygame.init()
screen = pygame.display.set_mode((800, 400))
pygame.display.set_caption(" Jump Up Game")

# some colors for the game
WHITE = (255, 255, 255)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
BLACK = (0, 0, 0)

# games variables   
character = pygame.Rect(100, 300, 50, 50)  # character represented by a rectangle
gravity = 0
jumping = False
jump_start_time = 0  # Track jump start time
jump_duration = 1.5  # Duration of the jump (increased for further jump)
score = 0
font = pygame.font.Font(None, 36)
# empty list to put the obstacles in 
obstacles = []
obstacle_speed = 5
spawn_obstacle_event = pygame.USEREVENT + 1
pygame.time.set_timer(spawn_obstacle_event, 2000)
waiting_to_jump_over = False

# Virtual button position (middle of the screen as a black box)
virtual_button_x = 550 # X axis of the virtual button
virtual_button_y = 250 # Y axis of the virtual button
virtual_button_width = 60
virtual_button_height = 60

# Start video capture
cap = cv2.VideoCapture(0)

# Start screen
start_screen = True
while start_screen:
    screen.fill(WHITE)
    start_text = font.render("Press START to play", True, BLACK)
    start_button = pygame.Rect(350, 200, 100, 50)
    pygame.draw.rect(screen, BLUE, start_button)
    screen.blit(start_text, (275, 150))
    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            start_screen = False
            running = False
            cap.release()
            cv2.destroyAllWindows()
            pygame.quit(); sys.exit()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if start_button.collidepoint(event.pos):
                start_screen = False
                running = True

# Game loop
last_jump_time = 0
virtual_key_touched = False

while running:
    # taking frame from webcam
    ret, frame = cap.read()
    if not ret:
        break

    # Flip the frame horizontally for a natural interaction
    frame = cv2.flip(frame, 1)

    # Convert the frame to RGB because mediapipe only works with RGB
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Process the frame with MediaPipe Hands
    results = hands.process(rgb_frame)

    # Detect virtual button touch
    virtual_key_touched = False
    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            # Get index finger tip coordinates
            index_tip = hand_landmarks.landmark[mp_hands.HandLandmark.INDEX_FINGER_TIP]
            h, w, _ = frame.shape  # Frame dimensions
            index_x, index_y = int(index_tip.x * w), int(index_tip.y * h)

            # Draw the index finger tip
            cv2.circle(frame, (index_x, index_y), 10, (0, 255, 0), -1)

            # Check if index finger touches the virtual button located middle of the screen
            if (virtual_button_x <= index_x <= virtual_button_x + virtual_button_width) and \
               (virtual_button_y <= index_y <= virtual_button_y + virtual_button_height):
                virtual_key_touched = True

            # Draw hand landmarks
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)

    # Draw the virtual button on the camera feed located middle of the screen
    cv2.rectangle(frame, (virtual_button_x, virtual_button_y),
                  (virtual_button_x + virtual_button_width, virtual_button_y + virtual_button_height),
                  (0, 0, 0), -1)

    # Add a title inside the virtual button
    text_size = cv2.getTextSize("Jump", cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
    text_x = virtual_button_x + (virtual_button_width - text_size[0]) // 2
    text_y = virtual_button_y + (virtual_button_height + text_size[1]) // 2
    cv2.putText(frame, "Jump", (text_x, text_y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Pygame event handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == spawn_obstacle_event:
            if len(obstacles) == 0 or obstacles[-1].x < 500:  # Ensure logical distance between obstacles
                obstacles.append(pygame.Rect(800, 300, 20, 50))  # Add a new obstacle

    # Jump if virtual button is touched and enough time has passed since the last jump
    current_time = time.time()
    if virtual_key_touched and not jumping and (current_time - last_jump_time > 1):
        jump_start_time = current_time  # Start the jump
        jumping = True
        waiting_to_jump_over = True  # Start waiting to jump over an obstacle
        last_jump_time = current_time

    # Apply a sine curve motion for the jump
    if jumping:
        # the time the square been in the air 
        elapsed_time = time.time() - jump_start_time
        # so we can make it jump in a curvy way
        if elapsed_time <= jump_duration:
            character.y = 300 - int(120 * math.sin(math.pi * elapsed_time / jump_duration))  # Higher jump amplitude
        else:
            jumping = False
            character.y = 300  # Reset position

    # Move obstacles and check for collisions
    for obstacle in obstacles:
        obstacle.x -= obstacle_speed
        if character.colliderect(obstacle):
            # Lose screen
            lose_screen = True
            while lose_screen:
                screen.fill(WHITE)
                lose_text = font.render("You Lost!", True, BLACK)
                play_again_text = font.render("Press R to Restart or Q to Quit", True, BLACK)
                screen.blit(lose_text, (325, 150))
                screen.blit(play_again_text, (200, 200))
                pygame.display.flip()

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        lose_screen = False
                        pygame.quit()
                        cap.release()
                        cv2.destroyAllWindows()
                        sys.exit()
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_r:
                            obstacles.clear()
                            score = 0
                            obstacle_speed = 5
                            lose_screen = False
                        elif event.key == pygame.K_q:
                            running = False
                            lose_screen = False
                            pygame.quit()
                            cap.release()
                            cv2.destroyAllWindows()
                            sys.exit()

        # Increase score if the character jumps over the obstacle
        if obstacle.x + obstacle.width < character.x and waiting_to_jump_over:
            score += 1
            waiting_to_jump_over = False

    # Remove obstacles that are off-screen
    obstacles = [obstacle for obstacle in obstacles if obstacle.x > -20]

    # Increase speed every 10 points
    if score > 0 and score % 10 == 0:
        obstacle_speed += 0.1

    # Draw everything
    screen.fill(WHITE)  # White background
    pygame.draw.rect(screen, BLUE, character)  # Draw the character as a blue rectangle
    for obstacle in obstacles:
        pygame.draw.rect(screen, RED, obstacle)  # Draw obstacles as red rectangles
    score_text = font.render(f"Score: {score}", True, BLACK)  # Display score
    screen.blit(score_text, (10, 10))
    pygame.display.flip()

    # Show the webcam frame (with virtual button)
    cv2.imshow('Virtual Button', frame)

    # Exit condition
    if cv2.waitKey(1) & 0xFF == ord('q'):
        running = False

# Release resources
cap.release()
cv2.destroyAllWindows()
pygame.quit()
