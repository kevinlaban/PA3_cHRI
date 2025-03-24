# -*- coding: utf-8 -*-

import pygame
import numpy as np
import math
#import matplotlib.pyplot as plt
#from HaplyHAPI import Board, Device, Mechanisms, Pantograph
#import sys, serial, glob
#from serial.tools import list_ports
import time
import random

class Graphics:
    def __init__(self,device_connected,window_size=(1080, 1200)):
        self.device_connected = device_connected
        
        #initialize pygame window
        self.window_size = window_size #default (600,400)
        pygame.init()
        self.window = pygame.display.set_mode(self.window_size)
        pygame.display.set_caption('Virtual Haptic Device')

        self.mainSurface = pygame.Surface(self.window_size)

        ##add nice icon from https://www.flaticon.com/authors/vectors-market
        self.icon = pygame.image.load('robot.png')
        pygame.display.set_icon(self.icon)

        ##add text on top to debugToggle the timing and forces
        self.font = pygame.font.Font('freesansbold.ttf', 18)

        pygame.mouse.set_visible(True)     ##Hide cursor by default. 'm' toggles it
         
        ##set up the on-screen debugToggle
        self.text = self.font.render('Virtual Haptic Device', True, (0, 0, 0),(255, 255, 255))
        self.textRect = self.text.get_rect()
        self.textRect.topleft = (10, 10)

        #xc,yc = screenVR.get_rect().center ##center of the screen

        ##initialize "real-time" clock
        self.clock = pygame.time.Clock()
        self.FPS = 100   #in Hertz

        ##define some colors
        self.cWhite = (255,255,255)
        self.cDarkblue = (36,90,190)
        self.cLightblue = (0,176,240)
        self.cRed = (255,0,0)
        self.cOrange = (255,100,0)
        self.cYellow = (255,255,0)
        
        self.hhandle = pygame.image.load('handle.png')
        
        """ Modifications for PA3 """
        
        """Jasper Code"""
        self.haptic_width = 64
        self.haptic_height = 128
        self.snake_mode = True
        self.frame_count = 0
        self.tumor_visible = True
        """End of Jasper Code"""
        
        
        self.tumor_positions = [
            (672, 456),
            (723, 460),
            (783, 476),
            (819, 507),
            (884, 550),
        ]
        self.tumor_location = random.choice(self.tumor_positions)
        
        # new background
        try:
            self.background = pygame.image.load('sagital2.jpg')
            self.background = pygame.transform.scale(self.background, self.window_size)
        except:
            print("Warning: background image not found.")
            self.background = None
            
        self.nose_overlay = pygame.image.load('sagital_overlay.png').convert_alpha()  # keep alpha!
        self.nose_overlay = pygame.transform.scale(self.nose_overlay, self.window_size)
        
        self.blood_overlay = pygame.image.load("blood_overlay.png").convert_alpha()
        self.blood_overlay = pygame.transform.scale(self.blood_overlay, self.window_size)
        self.blood_alpha = 0  # 0 = invisible

        self.stick_angle = -0.7  # radians (0 = right)
        
        self.window_scale = 9000 #6000 #2500 #pixels per meter
        self.device_origin = (self.window_size[0] // 2, 0) #self.window_size[1] // 3)
        
        self.delivery_zone = pygame.Rect(120, 770, 100, 100)  # x, y, width, height
        
        self.delivery_complete = False
        
        self.wall_collision = False
        
        self.start_time = time.time()
        self.score = 100
        
        self.end_time = None
        
        self.last_penalty_time = time.time()
        
        self.hover_start_time = None
        self.hover_duration_required = 5.0  # seconds
        """ End of modifications for PA3 """
        

        self.haptic = pygame.Rect(*self.window.get_rect().center, 0, 0).inflate(self.haptic_width, self.haptic_height)
        self.effort_cursor = pygame.Rect(*self.haptic.center, 0, 0).inflate(self.haptic_width, self.haptic_height)
        self.colorHaptic = self.cOrange ##color of the wall

        ####Pseudo-haptics dynamic parameters, k/b needs to be <1
        self.sim_k = 0.5 #0.1#0.5       ##Stiffness between cursor and haptic display
        self.sim_b = 0.8 #1.5#0.8       ##Viscous of the pseudohaptic display
        
        
        self.show_linkages = True
        self.show_debug = True
        
    def brain_tumor(self):
        """ Draws the brain tumor unless it's removed by the gripper """
        if not getattr(self, "tumor_visible", True): 
            return  

        self.tumor_width = 48
        self.tumor_height = 48

        #self.tumor_location = self.window.get_rect().center
        self.tumor_rect = pygame.Rect(*self.tumor_location, 0, 0).inflate(self.tumor_width, self.tumor_height)

        self.tumor_image = pygame.image.load('brain-tumor2.png')
        self.tumor_image = pygame.transform.scale(self.tumor_image, (self.tumor_width, self.tumor_height))

        self.window.blit(self.tumor_image, self.tumor_rect.topleft)

        keys = pygame.key.get_pressed()
        hovering = keys[pygame.K_SPACE] and self.haptic.colliderect(self.tumor_rect)
    
        if hovering:
            if self.hover_start_time is None:
                self.hover_start_time = time.time()
            elapsed_hover = time.time() - self.hover_start_time
            if elapsed_hover >= self.hover_duration_required:
                self.snake_mode = False
                self.tumor_visible = False
                self.hover_start_time = None  # reset
        else:
            self.hover_start_time = None  # reset if not hovering
            
    
    def check_delivery(self):
        keys = pygame.key.get_pressed()
        if not self.delivery_complete and not self.snake_mode and keys[pygame.K_SPACE] and self.delivery_zone.colliderect(self.haptic):
            self.delivery_complete = True
            self.end_time = time.time()




    def snake_gripper(self):
        """Snake like gripper animation and movement"""
        "Dont forget to call this function in render loop"
        self.haptic_width = 64
        self.haptic_height = 128

        if not hasattr(self, "snake_mode"):
            self.snake_mode = True

        if not hasattr(self, "frame_count"):
            self.frame_count = 0
        self.frame_count += 1

        self.brain_tumor()
        if (self.frame_count // 20 )% 2 == 0:
            image_path = 'snake-gripper.png' if self.snake_mode else 'snake-gripper-brain-tumor.png'
        else:
            image_path = 'snake-gripper-mirrored.png' if self.snake_mode else 'snake-gripper-brain-tumor-mirrored.png'
        self.snake_image = pygame.image.load(image_path)
        
        '''Allow rotation of the snake'''
        scaled_img = pygame.transform.scale(self.snake_image, (self.haptic_width, self.haptic_height))
        angle_deg = math.degrees(self.stick_angle)  # negative because pygame rotates CCW
        rotated_img = pygame.transform.rotate(scaled_img, angle_deg)
        rotated_rect = rotated_img.get_rect(center=self.haptic.center)
        self.window.blit(rotated_img, rotated_rect.topleft)
        
        
    def rotate_tool(self, delta_angle):
        self.stick_angle += delta_angle

    '''Dummy fucntion for wall collision'''
    def check_wall_collision(self, f):
        if np.linalg.norm(f) > 5.0:
            self.wall_collision = True
        else:
            self.wall_collision = False

            

    def convert_pos(self,*positions):
        #invert x because of screen axes
        # 0---> +X
        # |
        # |
        # v +Y
        converted_positions = []
        for physics_pos in positions:
            x = self.device_origin[0]-physics_pos[0]*self.window_scale
            y = self.device_origin[1]+physics_pos[1]*self.window_scale
            converted_positions.append([x,y])
        if len(converted_positions)<=0:
            return None
        elif len(converted_positions)==1:
            return converted_positions[0]
        else:
            return converted_positions
        return [x,y]
    def inv_convert_pos(self,*positions):
        #convert screen positions back into physical positions
        converted_positions = []
        for screen_pos in positions:
            x = (self.device_origin[0]-screen_pos[0])/self.window_scale
            y = (screen_pos[1]-self.device_origin[1])/self.window_scale
            converted_positions.append([x,y])
        if len(converted_positions)<=0:
            return None
        elif len(converted_positions)==1:
            return converted_positions[0]
        else:
            return converted_positions
        return [x,y]
        
    def get_events(self):
        #########Process events  (Mouse, Keyboard etc...)#########
        events = pygame.event.get()
        keyups = []
        for event in events:
            if event.type == pygame.QUIT: #close window button was pressed
                sys.exit(0) #raises a system exit exception so any Finally will actually execute
            elif event.type == pygame.KEYUP:
                keyups.append(event.key)
        
        mouse_pos = pygame.mouse.get_pos()
        return keyups, mouse_pos

    def sim_forces(self,pE,f,pM,mouse_k=None,mouse_b=None):
        #simulated device calculations
        if mouse_k is not None:
            self.sim_k = mouse_k
        if mouse_b is not None:
            self.sim_b = mouse_b
        if not self.device_connected:
            pP = self.haptic.center
            #pM is where the mouse is
            #pE is where the position is pulled towards with the spring and damping factors
            #pP is where the actual haptic position ends up as
            diff = np.array(( pM[0]-pE[0],pM[1]-pE[1]) )
            #diff = np.array(( pM[0]-pP[0],pM[1]-pP[1]) )
            
            scale = self.window_scale/1e3
            scaled_vel_from_force = np.array(f)*scale/self.sim_b
            vel_from_mouse_spring = (self.sim_k/self.sim_b)*diff
            dpE = vel_from_mouse_spring - scaled_vel_from_force
            #dpE = -dpE
            #if diff[0]!=0:
            #    if (diff[0]+dpE[0])/diff[0]<0:
            #        #adding dpE has changed the sign (meaning the distance that will be moved is greater than the original displacement
            #        #prevent the instantaneous velocity from exceeding the original displacement (doesn't make physical sense)
            #        #basically if the force given is so high that in a single "tick" it would cause the endpoint to move back past it's original position...
            #        #whatever thing is exerting the force should basically be considered a rigid object
            #        dpE[0] = -diff[0]
            #if diff[1]!=1:
            #    if (diff[1]+dpE[1])/diff[1]<0:
            #        dpE[1] = -diff[1]
            if abs(dpE[0])<1:
                dpE[0] = 0
            if abs(dpE[1])<1:
                dpE[1] = 0
            pE = np.round(pE+dpE) #update new positon of the end effector
            
            #Change color based on effort
            cg = 255-np.clip(np.linalg.norm(self.sim_k*diff/self.window_scale)*255*20,0,255)
            cb = 255-np.clip(np.linalg.norm(self.sim_k*diff/self.window_scale)*255*20,0,255)
            self.effort_color = (255,cg,cb)
        return pE

    def erase_screen(self):
        if self.background:
            self.window.blit(self.background, (0, 0))
        else:
            self.window.fill(self.cLightblue)


    
    def render(self, pA0, pB0, pA, pB, pE, f, pM):
        self.haptic.center = pE
        
        """ Changes for PA3 """
        if not self.delivery_complete:
            self.brain_tumor()
            self.check_delivery()
            self.snake_gripper()
            
            
            '''Check for collision and reduce score for colliding'''
            self.check_wall_collision(f)
            if self.wall_collision:
                self.blood_alpha = 255
                current_time = time.time()
                if current_time - self.last_penalty_time >= 0.1:
                    self.score = max(self.score - 1, 0)
                    self.last_penalty_time = current_time

                
            elapsed_time = round(time.time() - self.start_time, 1)

        else:
            self.snake_mode = True
            self.snake_gripper()
            elapsed_time = round(self.end_time - self.start_time, 1)
            
            # Show tumor at drop zone
            tumor_image = pygame.image.load('brain-tumor2.png')
            tumor_image = pygame.transform.scale(tumor_image, (self.tumor_width, self.tumor_height))
            tumor_rect = tumor_image.get_rect(center=self.delivery_zone.center)
            self.window.blit(tumor_image, tumor_rect)

        
            # Final message background box
            box_width = 800
            box_height = 140
            box_surface = pygame.Surface((box_width, box_height), pygame.SRCALPHA)
            box_surface.fill((255, 255, 255, 220))  # White with alpha
            
            box_rect = box_surface.get_rect(center=(self.window_size[0] // 2, 120))
            self.window.blit(box_surface, box_rect)
            
            # Text
            big_font = pygame.font.Font('freesansbold.ttf', 48)
            delivered_text = big_font.render("Tumor Successfully Removed!", True, (0, 200, 0))
            text_rect = delivered_text.get_rect(center=(self.window_size[0]//2, 100))
            self.window.blit(delivered_text, text_rect)
            
            time_score_text = self.font.render(f"Time: {elapsed_time}s     Final Score: {self.score}", True, (0, 0, 0))
            score_rect = time_score_text.get_rect(center=(self.window_size[0]//2, 150))
            self.window.blit(time_score_text, score_rect)

        
        # Pretty side-by-side time + score
        info_text = self.font.render(f"Time: {elapsed_time}s     Score: {self.score}", True, (0, 0, 0))
        info_bg = pygame.Surface((info_text.get_width() + 20, info_text.get_height() + 10))
        info_bg.fill((255, 255, 255))
        info_bg_rect = info_bg.get_rect(topleft=(20, 20))
        self.window.blit(info_bg, info_bg_rect)
        self.window.blit(info_text, (info_bg_rect.x + 10, info_bg_rect.y + 5))


        
        # Always draw delivery zone
        pygame.draw.rect(self.window, (0, 255, 0), self.delivery_zone, 4)
        zone_label = self.font.render("DROP ZONE", True, (0, 100, 0))
        self.window.blit(zone_label, (self.delivery_zone.x, self.delivery_zone.y - 25))
        
        # draw nose overlay on top to hide device behind nose
        self.window.blit(self.nose_overlay, (0, 0))  # this masks over the tool
        
        # Draw red damage overlay if needed
        if self.blood_alpha > 0:
            blood = self.blood_overlay.copy()
            blood.set_alpha(self.blood_alpha)
            self.window.blit(blood, (0, 0))
            self.blood_alpha = max(self.blood_alpha - 10, 0)  # fade out slowly

        """ End of changes """
        
        if self.device_connected:
            self.effort_color = (255,255,255)
    
        if self.show_linkages:
            pantographColor = (150,150,150)
            pygame.draw.lines(self.window, pantographColor, False, [pA0,pA],15)
            pygame.draw.lines(self.window, pantographColor, False, [pB0,pB],15)
            pygame.draw.lines(self.window, pantographColor, False, [pA,pE],15)
            pygame.draw.lines(self.window, pantographColor, False, [pB,pE],15)
            
            for p in (pA0,pB0,pA,pB,pE):
                pygame.draw.circle(self.window, (0, 0, 0),p, 15)
                pygame.draw.circle(self.window, (200, 200, 200),p, 6)

    
        if self.show_debug:    
            debug_text = f"FPS = {round(self.clock.get_fps())} fe: [{np.round(f[0],1)},{np.round(f[1],1)}] xh: [{np.round(pE[0],1)},{np.round(pE[1],1)}]"
            self.text = self.font.render(debug_text, True, (0, 0, 0), (255, 255, 255))
            self.window.blit(self.text, self.textRect)
    
        pygame.display.flip()
        self.clock.tick(self.FPS)


    def close(self):
        pygame.display.quit()
        pygame.quit()

