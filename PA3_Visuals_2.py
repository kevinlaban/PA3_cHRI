# -*- coding: utf-8 -*-
import sys
import math
import time
import numpy as np
import pygame
import random

from Physics import Physics
from Graphics import Graphics

#Hints:
#1: You can create your own persistant variables in the __init__() or run() functions by prefacing them with "self".
#     - For example: "self.prev_xh = xh"
#2: Change the values of "fe" and those forces will be sent to the device or simulated if no device is connected
#     - Note that this occurs AT THE END OF THE RUN FUNCTION
#     - fe is in SI units
#     - The Haply device can only exert a limited amount of force, so at some point setting very high forces will be useless
#3: Graphical components are all encapsulated in self.graphics (variable "g" in the run() function)
#     - These include the screenHaptics and screenVR surfaces which are the right and left display screens respectively
#     - Thus drawing a line on the right screen would be:
#            "pygame.draw.lines(g.screenHaptics, (0,255,0), False,[(0,0),(400,400)],1)"
#     - The orange proxy object is "g.haptic" and has an initial size of 48x48
#4: graphics contains two conversion functions to convert from and to SI units
#     - "g.convert_pos( (x,y) )" converts from the haply's physical coordinates to the graphical coordinates. Remember that the axes may not be aligned the same way!
#     - "g.inv_convert_pos( (x,y) )" converts from the graphical coordinates to the haply's physical coordinates
#     - Both functions can take in a single or multiple point written as a tuple or list with two elements
#           - point = g.convert_pos( (x,y) )
#           - p0,p1 = g.convert_pos( (x0,y0),(x1,y1) )

class PA:
    def __init__(self):
        self.physics = Physics(hardware_version=2) #setup physics class. Returns a boolean indicating if a device is connected
        self.device_connected = self.physics.is_device_connected() #returns True if a connected haply device was found
        self.graphics = Graphics(self.device_connected, window_size=(1500, 1000), pa=self) #setup class for drawing and graphics.
        #  - Pass along if a device is connected so that the graphics class knows if it needs to simulate the pantograph
        xc, yc = self.graphics.window.get_rect().center
        ##############################################
        #ADD things here that you want to run at the start of the program!
        g = self.graphics
        
        """Hide text and linkages"""
        g.show_linkages = False
        g.show_debug = False
        
        # variables for random rotations
        self.next_vibration_time = time.time() + np.random.uniform(0.1, 0.5)
        self.last_vibration_time = 0
        
        # variables for game mode selection
        self.tumor_difficulty = None
        self.use_haptics = None


        # variables for walls
        self.draw_walls_flag = False
        self.walls = []
        self.walls = [
            ((524, 663), (479, 645)),
            ((479, 645), (580, 472)),
            ((580, 472), (650, 440)),
            ((650, 440), (781, 460)),
            #((790, 465), (810, 517)),
            ((850, 530), (942, 591)),
            ((942, 591), (998, 698)),
            ((587, 655), (669, 625)),
            ((669, 625), (903, 664)),
            ((903, 664), (950, 800)),
            ((950, 800), (982, 1000)),
            ((998, 698), (1070,1000)),]

        self.walls.extend([      
            ((850, 530), (900, 430)),
        ])

        self.walls.extend([                # brain tumor walls
            ((798, 445), (694, 391)),
            ((694, 391), (664, 301)),
            ((664, 301), (713, 291)),
            ((713, 291), (744, 357)),
            ((744, 357), (830, 405)),
            ((798, 445), (781, 460)),
            ((830, 405), (900, 430)),
        ])
        self.generate_random_walls(0)

        self.total_wall_force = 0.0  
        self.score = 0.0
        
        self.damage_areas_visible = False
        self.damage_zones_rectangle = [
            pygame.Rect(615, 660, 300, 400),
            pygame.Rect(590, 250, 80, 180),
            pygame.Rect(1080, 630, 250, 400)
        ]
        self.damage_zones_ellipse = [
            ((1075, 200), (780, 500)),
            ((1150, 500), (560, 250)),
            ((1050, 700), (80, 200)),
            ((660, 215), (80, 160))
        ]

        ##############################################

        # functions for walls

    def point_to_segment_distance(self, point, seg_start, seg_end):
        """Returns the closest point on a line segment to a given point and the distance."""
        px, py = point
        ax, ay = seg_start
        bx, by = seg_end

        # Vector AB and AP
        AB = np.array([bx - ax, by - ay])
        AP = np.array([px - ax, py - ay])

        # Project AP onto AB (scalar projection)
        AB_length_sq = np.dot(AB, AB)  # |AB|^2
        if AB_length_sq == 0:
            return seg_start, np.linalg.norm(AP)  # A and B are the same point

        projection_factor = np.dot(AP, AB) / AB_length_sq
        projection_factor = np.clip(projection_factor, 0, 1)  # Clamp between 0 and 1

        # Closest point on segment
        closest_x = ax + projection_factor * AB[0]
        closest_y = ay + projection_factor * AB[1]

        closest_point = (closest_x, closest_y)
        distance = np.linalg.norm(np.array(point) - np.array(closest_point))

        return closest_point, distance
    
    def compute_wall_force(self, xh):
        """Computes the force pushing xh away from the closest wall."""
        force = np.array([0.0, 0.0])  # Initialize force

        threshold = 30  # Maximum distance for the force to be active

        max_force = 10  # Maximum force strength

        for wall in self.walls:
            p1, p2 = wall  # Unpack wall segment
            closest_point, distance = self.point_to_segment_distance(xh, p1, p2)

            if distance < threshold:  # If within the force field
                # Compute perpendicular direction (from wall to mouse)
                direction = np.array(xh) - np.array(closest_point)
                distance = max(distance, 1)  # Avoid division by zero
                normalized_dir = direction / distance  # Normalize

                # Force strength decreases with distance
                force_magnitude = max_force * ((1 - distance / threshold)**3)  
                force -= force_magnitude * normalized_dir  

        return force
    
    def generate_random_walls(self, num_walls=5):
        """Generates a list of random walls within the screen boundaries."""
        screen_width, screen_height = self.graphics.window.get_size()
        print("screenwidth is", screen_width, "screenheight is", screen_height)
        #self.walls = []

        for _ in range(num_walls):
            x1, y1 = random.randint(50, screen_width - 50), random.randint(50, screen_height - 50)
            x2, y2 = random.randint(50, screen_width - 50), random.randint(50, screen_height - 50)
            
            self.walls.append(((x1, y1), (x2, y2)))  # Store as (start, end) points

        print(f"Generated {num_walls} random walls.")

    def draw_walls(self):
        """Draws all walls in the Pygame window."""
        wall_color = (255, 0, 255)  # White walls
        wall_thickness = 20  # Adjust thickness

        for wall in self.walls:
            p1, p2 = wall  # Unpack start and end points
            pygame.draw.line(self.graphics.window, wall_color, p1, p2, wall_thickness)
            
            
    def show_start_menu(self):
        g = self.graphics
        font = pygame.font.Font('freesansbold.ttf', 48)
        small_font = pygame.font.Font('freesansbold.ttf', 28)
        
        selected_difficulty = None
        selected_mode = None
    
        # Button config
        button_w, button_h = 220, 70
        button_color = (57, 62, 70)            # dark gray buttons
        hover_color = (80, 90, 100)            # lighter gray on hover
        click_color = (144, 224, 239)          # unused but you could use it for click flashes
        text_color = (238, 238, 238)           # light text
        selected_border_color = (0, 173, 181)  # teal-cyan highlight
    
        def draw_button(rect, text, is_selected, is_hovered):
            color = hover_color if is_hovered else button_color
            pygame.draw.rect(g.window, color, rect, border_radius=15)
            if is_selected:
                pygame.draw.rect(g.window, selected_border_color, rect, 4, border_radius=15)
            label = small_font.render(text, True, text_color)
            label_rect = label.get_rect(center=rect.center)
            g.window.blit(label, label_rect)
    
        while True:
            g.window.fill((34, 40, 49))
    
            # Title
            title = font.render("Choose Game Settings", True, (238, 238, 238))  # light text
            g.window.blit(title, title.get_rect(center=(g.window_size[0]//2, 100)))
    
            # Button positions
            center_x = g.window_size[0] // 2
    
            easy_rect   = pygame.Rect(center_x - 350, 200, button_w, button_h)
            medium_rect = pygame.Rect(center_x - 110, 200, button_w, button_h)
            hard_rect   = pygame.Rect(center_x + 130, 200, button_w, button_h)
    
            haptics_rect     = pygame.Rect(center_x - button_w - 20, 320, button_w, button_h)
            no_haptics_rect  = pygame.Rect(center_x + 20, 320, button_w, button_h)

    
            mouse_pos = pygame.mouse.get_pos()
            mouse_click = False
    
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_click = True
    
            # Draw difficulty buttons
            for rect, label in [
                (easy_rect, "Easy"),
                (medium_rect, "Medium"),
                (hard_rect, "Hard")
            ]:
                hovered = rect.collidepoint(mouse_pos)
                selected = (label.lower() == selected_difficulty)
                draw_button(rect, label, selected, hovered)
                if hovered and mouse_click:
                    selected_difficulty = label.lower()
    
            # Draw mode buttons
            for rect, label, mode_val in [
                (haptics_rect, "With Haptics", True),
                (no_haptics_rect, "No Haptics", False)
            ]:
                hovered = rect.collidepoint(mouse_pos)
                selected = (mode_val == selected_mode)
                draw_button(rect, label, selected, hovered)
                if hovered and mouse_click:
                    selected_mode = mode_val
    
            # Ready to continue
            if selected_difficulty and selected_mode is not None:
                start_w, start_h = 260, 80
                continue_rect = pygame.Rect(center_x - start_w // 2, 520, start_w, start_h)
                hovered = continue_rect.collidepoint(mouse_pos)
                # Draw start button in bold green style
                pygame.draw.rect(g.window, (40, 160, 100), continue_rect, border_radius=20)
                if hovered:
                    pygame.draw.rect(g.window, (60, 200, 130), continue_rect, border_radius=20)
                label = small_font.render("Start", True, (255, 255, 255))  # light text
                label_rect = label.get_rect(center=continue_rect.center)
                g.window.blit(label, label_rect)
                if hovered and mouse_click:
                    self.tumor_difficulty = selected_difficulty
                    self.use_haptics = selected_mode
                    return
    
            pygame.display.flip()
            g.clock.tick(60)


    def draw_damage_zones(self):
        if not self.damage_areas_visible:
            return
        color = (255, 0, 0)  # Red
        for rect in self.damage_zones_rectangle:
            pygame.draw.rect(self.graphics.window, color, rect, 3)
        for center, size in self.damage_zones_ellipse:
            ellipse_rect = pygame.Rect(0, 0, *size)
            ellipse_rect.center = center
            pygame.draw.ellipse(self.graphics.window, color, ellipse_rect, 3)

    
    def run(self):
        p = self.physics #assign these to shorthand variables for easier use in this function
        g = self.graphics
        #get input events for both keyboard and mouse
        keyups,xm = g.get_events()
        #  - keyups: list of unicode numbers for keys on the keyboard that were released this cycle
        #  - pm: coordinates of the mouse on the graphics screen this cycle (x,y)      
        #get the state of the device, or otherwise simulate it if no device is connected (using the mouse position)
        if self.device_connected:
            pA0,pB0,pA,pB,pE = p.get_device_pos() #positions of the various points of the pantograph
            pA0,pB0,pA,pB,xh = g.convert_pos(pA0,pB0,pA,pB,pE) #convert the physical positions to screen coordinates
        else:
            xh = g.haptic.center
            #set xh to the current haptic position, which is from the last frame.
            #This previous position will be compared to the mouse position to pull the endpoint towards the mouse
        fe = np.array([0.0,0.0]) #fx,fy
        xh = np.array(xh) #make sure fe is a numpy array
        xc, yc = self.graphics.window.get_rect().center
        g.erase_screen()

        # draw walls
        if self.draw_walls_flag == True:
            self.draw_walls()
            
        self.draw_damage_zones()


        ##############################################
        #ADD things here that run every frame at ~100fps!
                
        """Disturbance forces for PA3"""
        # --- Disturbance Forces Only ---
        t = time.time()
        
        # 1. Breathing (slow sinusoidal vertical motion)
        f_breath = np.array([0.0, 0.2 * math.sin(2 * math.pi * 1.0 * t)])  # 1 Hz, 0.2 N
        
        # 2. Patient twitching (random impulses every few seconds)
        if not hasattr(self, 'last_twitch'):
            self.last_twitch = t
            self.twitch_interval = 2.0  # seconds
            self.twitch_force = np.array([0.0, 0.0])
        
        if not hasattr(self, 'next_twitch_time'):
            self.next_twitch_time = t + np.random.uniform(2.0, 4.0)
        
        if t > self.next_twitch_time:
            direction = np.random.randn(2)
            direction /= np.linalg.norm(direction)
            self.twitch_force = direction * np.random.uniform(2.0, 4.0)
            self.next_twitch_time = t + np.random.uniform(2.0, 4.0)
        else:
            self.twitch_force *= 0.8

        # 3. External vibration as small random rotations at random intervals
        now = time.time()
        if not g.delivery_complete and now >= self.next_vibration_time:
            g.rotate_tool(np.random.uniform(-0.05, 0.05))
            self.next_vibration_time = now + np.random.uniform(0.2, 0.5)

        # 4. Wall forces
        wall_force = self.compute_wall_force(xh)
        if self.graphics.start_time_flag:
            self.total_wall_force += wall_force[0]  # Accumulate total force for analysis
            self.score += np.linalg.norm(wall_force) # Accumulate score based on force magnitude

        
        # Damage zones
        in_zone = False
        for rect in self.damage_zones_rectangle:
            if rect.collidepoint(*xh):
                in_zone = True
                break
        
        for center, size in self.damage_zones_ellipse:
            dx = (xh[0] - center[0]) / (size[0] / 2)
            dy = (xh[1] - center[1]) / (size[1] / 2)
            if dx**2 + dy**2 <= 1:
                in_zone = True
                break
        
        if self.graphics.start_time_flag and in_zone:
            self.score += 3
        
            # Trigger blood overlay
            self.graphics.blood_alpha = 255
            current_time = time.time()
            if current_time - self.graphics.last_penalty_time >= 0.1:
                self.graphics.score = max(self.graphics.score - 1, 0)
                self.graphics.last_penalty_time = current_time


        
        # Total force
        if self.use_haptics:
            fe = f_breath + self.twitch_force + wall_force
        else:
            fe = f_breath + self.twitch_force



        """End of disturbance forces code"""
        # Display the score on the screen
        font = pygame.font.Font('freesansbold.ttf', 24)  # Use a readable font size
        score_text = font.render(f"Total damage: {int(self.score)}", True, (0, 5, 0))  # White text
        g.window.blit(score_text, (500, 10))  # Display the score at the top-left corner

        
        for key in keyups:
            if key==ord("q"): #q for quit, ord() gets the unicode of the given character
                sys.exit(0) #raises a system exit exception so the "PA.close()" function will still execute
            if key == ord('m'): #Change the visibility of the mouse
                pygame.mouse.set_visible(not pygame.mouse.get_visible())
            if key == ord('r'): #Change the visibility of the linkages
                g.show_linkages = not g.show_linkages
            if key == ord('d'): #Change the visibility of the debug text
                g.show_debug = not g.show_debug
            if key == ord('f'):  # Rotate counter-clockwise
                g.rotate_tool(-0.25)
            if key == ord('g'):  # Rotate clockwise
                g.rotate_tool(0.25)

            #you can add more if statements to handle additional key characters
            
        
        ##############################################
        if self.device_connected: #set forces only if the device is connected
            p.update_force(fe)
        else:
            xh = g.sim_forces(xh,fe,xm,mouse_k=0.5,mouse_b=1.5) #simulate forces
            pos_phys = g.inv_convert_pos(xh)
            pA0,pB0,pA,pB,pE = p.derive_device_pos(pos_phys) #derive the pantograph joint positions given some endpoint position
            pA0,pB0,pA,pB,xh = g.convert_pos(pA0,pB0,pA,pB,pE) #convert the physical positions to screen coordinates
        g.render(pA0,pB0,pA,pB,xh,fe,xm,wall_force)
        
    def close(self):
        ##############################################
        #ADD things here that you want to run right before the program ends!
        
        ##############################################
        self.graphics.close()
        self.physics.close()

if __name__=="__main__":
    pa = PA()
    pa.show_start_menu()
    pa.graphics.set_tumor_location_from_difficulty()
    try:
        while True:
            pa.run()
    finally:
        pa.close()