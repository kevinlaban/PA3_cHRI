# -*- coding: utf-8 -*-
import sys
import math
import time
import numpy as np
import pygame
import matplotlib.pyplot as plt
import numpy as np
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
#           - g.haptic has several parameters that can be read or updated such as:
#                 - haptic.w and haptic.h: haptic proxy rectangle width and height
#                 - haptic.center: haptic proxy center position
#4: Graphics contains two conversion functions to convert from and to SI units
#     - "g.convert_pos( (x,y) )" converts from the haply's physical coordinates to the graphical coordinates. Remember that the axes may not be aligned the same way!
#     - "g.inv_convert_pos( (x,y) )" converts from the graphical coordinates to the haply's physical coordinates
#     - Both functions can take in a single or multiple point written as a tuple or list with two elements
#           - point = g.convert_pos( (x,y) )
#           - p0,p1 = g.convert_pos( (x0,y0),(x1,y1) )
#     - For simple scale conversion, use the pixels-per-meter value, "g.window_scale"
#5: Other useful parameters of graphics
#     - The framerate of the graphics rendering can be accessed (and changed if you really want) via the "g.FPS" parameter
#     - "g.debug_text" is the debug string that will be drawn in the upper left. This string can be added to for debug purposes
#6: If you want to use pygame's collision detection ( for example, colliderect() ) while also changing the shape of the haptic proxy to represent impedance,
#       consider using the equivalent haptic proxy on the screenHaptic side (g.effort_cursor), as it is the same size as g.haptic and is at the same position.

class PA:
    def __init__(self):
        self.physics = Physics(hardware_version=3) #setup physics class. Returns a boolean indicating if a device is connected
        self.device_connected = self.physics.is_device_connected() #returns True if a connected haply device was found
        self.graphics = Graphics(self.device_connected) #setup class for drawing and graphics.
        #  - Pass along if a device is connected so that the graphics class knows if it needs to simulate the pantograph
        xc,yc = self.graphics.screenVR.get_rect().center
        ##############################################
        #ADD things here that you want to run at the start of the program!
        dx = 0
        dy = 0
        self.prev_xh = np.array([xc, yc])
        self.prev_dx = dx
        self.prev_dy = dy
        self.k = 0.05  # Initial spring stiffness
        self.be = 0  # Initial damping coefficient
        self.mass = 0   # Initial mass
        self.screenwidth = int(600/10)
        self.screenheight = int(400/10)
        self.heightmap = np.zeros((self.screenwidth, self.screenheight))
        #self.create_height_map()
        self.walls = []
        self.generate_random_walls(3)
        

        self.critical_damp = False
        
        ##############################################
    
    def get_height_sine(self, x, y):
        return  math.sin(x) + math.sin(0.5 * y)
    

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

        threshold = 70  # Maximum distance for the force to be active

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
                force_magnitude = max_force * (1 - distance / threshold)  
                force -= force_magnitude * normalized_dir  

        return force
    
    def generate_random_walls(self, num_walls=5):
        """Generates a list of random walls within the screen boundaries."""
        screen_width, screen_height = self.graphics.screenVR.get_size()
        self.walls = []

        for _ in range(num_walls):
            x1, y1 = random.randint(50, screen_width - 50), random.randint(50, screen_height - 50)
            x2, y2 = random.randint(50, screen_width - 50), random.randint(50, screen_height - 50)
            
            self.walls.append(((x1, y1), (x2, y2)))  # Store as (start, end) points

        print(f"Generated {num_walls} random walls.")

    def draw_walls(self):
        """Draws all walls in the Pygame window."""
        wall_color = (255, 255, 255)  # White walls
        wall_thickness = 20  # Adjust thickness

        for wall in self.walls:
            p1, p2 = wall  # Unpack start and end points
            pygame.draw.line(self.graphics.screenVR, wall_color, p1, p2, wall_thickness)

    

    
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
        xc,yc = g.screenVR.get_rect().center
        g.erase_screen()
        self.draw_walls()
        ##############################################
        #ADD things here that run every frame at ~100fps!
        if self.critical_damp == True:
            if self.k > 0 and self.mass > 0:
                self.be = 2 * math.sqrt(self.k * self.mass)
            else:
                self.critical_damp = False

        time = g.FPS
        speed = (xh - self.prev_xh)/time # Calculate the speed of the endpoint
        acceleration = speed/time # Calculate the acceleration of the endpoint
        fe = self.k * (xh - np.array([xc, yc])) - (self.be * speed) + (self.mass * acceleration)
        computed_force = self.compute_wall_force(xh)
        fe += computed_force  # Add wall force
        self.prev_xh = xh

        for key in keyups:
            if key==ord("q"): #q for quit, ord() gets the unicode of the given character
                sys.exit(0) #raises a system exit exception so the "PA.close()" function will still execute
            if key == ord('m'): #Change the visibility of the mouse
                pygame.mouse.set_visible(not pygame.mouse.get_visible())
            if key == ord('r'): #Change the visibility of the linkages
                g.show_linkages = not g.show_linkages
            if key == ord('d'): #Change the visibility of the debug text
                g.show_debug = not g.show_debug
            if key == ord('w'):
                self.k += 0.01  # Increase stiffness
            if key == ord('s'):
                self.k = max(-10, self.k - 0.01)  # Decrease stiffness
            if key == ord('1'):
                self.be += 1  # Increase damping
            if key == ord('2'):
                self.be = max(-100, self.be - 1)  # Decrease damping
            if key == ord('3'):
                self.mass += 10
            if key == ord('4'):
                self.mass = max(0, self.mass - 10) # Decrease mass
            if key == ord('5'):
                if self.critical_damp == True:
                    self.critical_damp = False
                else:
                    self.critical_damp = True
            
        g.debug_text = f"Spring Stiffness (k): {self.k:.2f}\nDamping (be): {self.be:.2f}\nMass: {self.mass:.2f}"
        
        
        ##############################################
        if self.device_connected: #set forces only if the device is connected
            p.update_force(fe)
        else:
            xh = g.sim_forces(xh,fe,xm,mouse_k=0.5,mouse_b=0.8) #simulate forces with mouse haptics
            pos_phys = g.inv_convert_pos(xh)
            pA0,pB0,pA,pB,pE = p.derive_device_pos(pos_phys) #derive the pantograph joint positions given some endpoint position
            pA0,pB0,pA,pB,xh = g.convert_pos(pA0,pB0,pA,pB,pE) #convert the physical positions to screen coordinates
        g.render(pA0,pB0,pA,pB,xh,fe,xm)
        
    def close(self):
        ##############################################
        #ADD things here that you want to run right before the program ends!
        
        ##############################################
        self.graphics.close()
        self.physics.close()

    def create_height_map(self):
        
        for x in range(0, self.screenwidth):
            for y in range(0, self.screenheight):
                self.heightmap[x, y] = self.get_height_sine(x, y)

                self.gradient_x, self.gradient_y = np.gradient(self.heightmap)

        # show hight map in 2d
        plt.figure()
        plt.title('z as 2d heat map')
        p = plt.imshow(self.heightmap)
        plt.colorbar(p)
        plt.show()

if __name__=="__main__":
    pa = PA()
    try:
        while True:
            pa.run()
    finally:
        pa.close()