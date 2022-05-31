import pygame
import random
import math
import pygame
import conf
import numpy as np
from destination import *
from aircraft import *
from obstacle import *
from aircraftspawnevent import *
from utility import *
from pgu import gui
from flightstrippane import *

class AIGame:

    SCREEN_W = 0               
    SCREEN_H = 0                

    AERIALPANE_W = 0           
    AERIALPANE_H = 0           

    FSPANE_LEFT = 0            
    FSPANE_TOP = 200            
    FS_W = 0
    FS_H = 0

    RADAR_CIRC_COLOR = (0, 0x44, 0)
    RADAR_RADIUS = 0

    COLOR_SCORETIME = (0,0,255)    #score

    POTENTIAL_COLLISION_THRESHOLD = 150

    def __init__(self, screen, demomode):                     #Screen vars
        AIGame.SCREEN_W = screen.get_size()[0]
        AIGame.SCREEN_H = screen.get_size()[1]
        AIGame.AERIALPANE_W = AIGame.SCREEN_H
        AIGame.AERIALPANE_H = AIGame.SCREEN_H
        AIGame.FSPANE_LEFT = AIGame.AERIALPANE_W + 3
        AIGame.FSPANE_H = AIGame.SCREEN_H - AIGame.FSPANE_TOP
        AIGame.FS_W = AIGame.SCREEN_W - AIGame.FSPANE_LEFT
        AIGame.FS_H = 60
        AIGame.RADAR_RADIUS = (AIGame.AERIALPANE_H - 50) / 2

        self.font = pygame.font.Font(None, 30)
        self.screen = screen

                                                             #Aircraft and destination state vars
        self.demomode = demomode
        self.gameEndCode = 0
        self.ms_elapsed = 0
        self.score = 0
        self.aircraft = []
        self.obstacles = []
        self.destinations = []
        self.aircraftspawntimes = []
        self.aircraftspawns = []

        self.ac_selected = None
        self.way_clicked = None

        self.last_click_time = None

        self.__generateDestinations()
        self.__generateObstacles()
        self.__generateAircraftSpawnEvents()
        self.sound_warning = pygame.mixer.Sound("data/sounds/warning.ogg")
        self.sound_collision = pygame.mixer.Sound("data/sounds/boom.wav")
        self.channel_warning = pygame.mixer.Channel(0)
        self.channel_collision = pygame.mixer.Channel(1)

        self.app = gui.App()
        self.cnt_main = gui.Container(align=-1,valign=-1)
        self.delaytimer = 0

        if not self.demomode:
            self.btn_game_end = gui.Button(value="End Game", width=AIGame.FS_W-3, height=60)
            self.btn_game_end.connect(gui.CLICK, self.__callback_User_End)
            self.cnt_main.add(self.btn_game_end, AIGame.FSPANE_LEFT, AIGame.FSPANE_TOP - 65)
        else:
            pygame.mouse.set_visible(False)
            self.delaytimer = pygame.time.get_ticks()

        self.cnt_fspane = FlightStripPane(left=AIGame.FSPANE_LEFT, top=AIGame.FSPANE_TOP, width=AIGame.FS_W, align=-1, valign=-1)
        self.cnt_main.add(self.cnt_fspane, AIGame.FSPANE_LEFT, AIGame.FSPANE_TOP)

        self.app.init(self.cnt_main, self.screen)

        self.clock = None

    def start(self):
        self.clock = pygame.time.Clock()
        nextDemoEventTime = 6000 # demo for  6 second 
        randAC = None
        ds = 3
        pygame.draw.rect(self.screen, (0, 0, 0), self.screen.get_rect())


    def step(self):
        destination_airplanes = []
        if self.gameEndCode == 0:
            timepassed = self.clock.tick(conf.get()['game']['framerate'])
            self.screen.set_clip(pygame.Rect(0,0,AIGame.FSPANE_LEFT,AIGame.SCREEN_H))
            #Handle any UI stuff
            self.__handleUserInteraction()
            #Draw background
            pygame.draw.rect(self.screen, (0, 0, 0), self.screen.get_rect())

            #Draw obstacles
            for x in self.obstacles:
                x.draw(self.screen)

            #Draw radar circles
            pygame.draw.circle(self.screen, AIGame.RADAR_CIRC_COLOR, (int(AIGame.AERIALPANE_W / 2), int(AIGame.AERIALPANE_H / 2)), int(AIGame.RADAR_RADIUS * 1/3), 1)
            pygame.draw.circle(self.screen, AIGame.RADAR_CIRC_COLOR, (int(AIGame.AERIALPANE_W / 2), int(AIGame.AERIALPANE_H / 2)), int(AIGame.RADAR_RADIUS * 2/3), 1)
            pygame.draw.circle(self.screen, AIGame.RADAR_CIRC_COLOR, (int(AIGame.AERIALPANE_W / 2), int(AIGame.AERIALPANE_H / 2)), int(AIGame.RADAR_RADIUS), 1)

            #Draw destinations
            for x in self.destinations:
                x.draw(self.screen)

            #Move/redraw/collide aircraft
            # get airplanes that get destination reward
            destination_airplanes = self.__update()
            self.__handleAircraftObstacleCollisions()

            self.screen.set_clip(None)
            pygame.draw.line(self.screen, (255, 255, 255), (AIGame.AERIALPANE_W + 1, 0), (AIGame.AERIALPANE_W + 1, AIGame.SCREEN_H), 3)
            pygame.draw.line(self.screen, (255, 255, 255), (AIGame.FSPANE_LEFT, AIGame.FSPANE_TOP - 2), (AIGame.SCREEN_W, AIGame.FSPANE_TOP - 2), 3)
            if self.score <= 0:
                self.score = 0
            sf_score = self.font.render("Score: " + str(self.score), True, AIGame.COLOR_SCORETIME)    ## time score 
            self.screen.fill((0,0,0),sf_score.get_rect().move(AIGame.FSPANE_LEFT + 30, 10))
            self.screen.blit(sf_score, (AIGame.FSPANE_LEFT + 30, 10))
            self.ms_elapsed = self.ms_elapsed + timepassed
            self.app.update(self.screen)
            pygame.display.flip()
        aircraft = self.getPlaneDict()
        collidingAircraft, collisionSet = self.getCollidingAircraft()
        rewards = self.getRewards(destination_airplanes, collisionSet)
        if len(self.aircraftspawns) == 0:
            self.gameEndCode = conf.get()['codes']['ac_collide']

        return (aircraft, rewards, collidingAircraft, self.gameEndCode, self.score)

    #Request a new selected aircraft
    def requestSelected(self, ac):
        self.ac_selected = ac
        # Deselect all aircraft first
        for a in self.aircraft:
            if(a != self.ac_selected):
                a.setSelected(False)
        # Then reselect the active aircraft
        if(self.ac_selected != None):
            self.ac_selected.setSelected(True)

    def __update(self):
        ac_removal = []                                    #Update the positions of all existing aircraft
                                                           #Check if any aircraft have collided with an obstacle
                                                          #Check if any aircraft have reached a destination
        completed_aircraft = []

        for n in range(0, len(self.aircraft)):
            a = self.aircraft[n]

            #Update positions and redraw
            reachdest = a.update()
            if(reachdest == True):
                #Schedule aircraft for removal
                ac_removal.append(a)
                self.score += conf.get()['scoring']['reach_dest']
            else:
                a.draw(self.screen)

            #Check collisions
            self.__highlightImpendingCollision(a)
            for ac_t in self.aircraft:
                if(ac_t != a):
                    self.__handleAircraftCollision(ac_t, a)

        for a in ac_removal:
            if(self.ac_selected == a):
                self.requestSelected(None)
            completed_aircraft.append(a.getIdent())
            self.aircraft.remove(a)
            self.cnt_fspane.remove(a.getFS())
            self.cnt_fspane.repaint()

        #4: Spawn new aircraft due for spawning (or if in demo, regenerate list if none left)
        if(len(self.aircraftspawntimes) != 0 and len(self.aircraftspawns) != 0):
            if self.ms_elapsed >= self.aircraftspawntimes[0]:  # If game time has exceeded normal aircraft spawn time
                sp = self.aircraftspawns[0]
                while (self.__isSpawnPointTooCloseToAircraft(sp)):  # While we get close spawn points we strip those points
                    #print("Trying while again")
                    if (len(self.aircraftspawns) > 1):  # Quick fix; I can increase number of spawn points for improving this
                        self.aircraftspawns.remove(sp)
                        sp = self.aircraftspawns[0]
                    # Do we still have to take care of times????
                if(len(self.aircraft) < math.floor(AIGame.FSPANE_H / 60)):
                    ac = Aircraft(self, sp.getSpawnPoint(), conf.get()['aircraft']['speed_default'], sp.getDestination(), "BA" + str(random.randint(1, 100000000)))
                    self.aircraft.append(ac)
                    self.cnt_fspane.addNewFlightStrip(ac)
                self.aircraftspawns.remove(sp)      # Removes the previous spawn point
                self.aircraftspawntimes.remove(self.aircraftspawntimes[0])


        return completed_aircraft

    def __handleUserInteraction(self):

        for event in pygame.event.get():

            self.app.event(event)

            if self.demomode:
                if (pygame.time.get_ticks() - self.delaytimer) >= 1000:
                    if event.type == pygame.MOUSEMOTION or event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
                        self.gameEndCode = conf.get()['codes']['user_end']
                        pygame.mouse.set_visible(True)
                        return
            else:
                if(event.type == pygame.MOUSEBUTTONDOWN and event.button == 1):
                    if (self.last_click_time and pygame.time.get_ticks() -  self.last_click_time < 400):
                        dbl_click = True
                    else:
                        dbl_click = False
                    self.last_click_time = pygame.time.get_ticks()

                    clickedac = self.__getACClickedOn(event.pos)
                    if(clickedac != None):
                       
                        self.requestSelected(clickedac)
                    else:
                        if(self.ac_selected != None):
                         
                            wclick = False
                            for x in range(0, len(self.ac_selected.getWaypoints()) - 1):
                                w = self.ac_selected.getWaypoints()[x]
                                if(w.clickedOn(event.pos) == True):
                                    if (dbl_click):
                                        # Use del list[index] instead?
                                        self.ac_selected.waypoints.remove(w)
                                        wclick = True
                                        break
                                    else:
                                        self.way_clicked = w
                                        wclick = True
                            if wclick == False:
                         
                                way_added = False
                    
                                ac = self.ac_selected
                                listy = [ac.getLocation()]
                                listy = listy + list(map(Waypoint.getLocation,ac.getWaypoints()))
                                for x in range(0, len(listy)-1):
                                    currP = listy[x]
                                    nextP = listy[x+1]
                                    (intersect, dist) = Utility.getPointLineIntersect(currP, nextP, event.pos)
                                    if((intersect != None) and (dist <= 40)):
                                        newway = Waypoint(event.pos)
                                        self.ac_selected.addWaypoint(newway, x)
                                        self.way_clicked = newway
                                        way_added = True
                                        break
                           
                                if (way_added == False and 0 < event.pos[0] < AIGame.AERIALPANE_W ):
                                    self.requestSelected(None)

                elif(event.type == pygame.MOUSEBUTTONUP and event.button == 1):

                    if(self.way_clicked != None):
                        self.way_clicked = None

                elif(event.type == pygame.MOUSEMOTION):
   

                    if(self.way_clicked != None):
                        if(event.pos[0] >= AIGame.AERIALPANE_W - 3):
                            self.way_clicked.setLocation((AIGame.AERIALPANE_W - 3, event.pos[1]))
                        else:
                            self.way_clicked.setLocation(event.pos)

                elif(event.type == pygame.KEYDOWN):

                    if(event.key == pygame.K_ESCAPE):
                        self.gameEndCode = conf.get()['codes']['user_end']

    def __callback_User_End(self):
        self.gameEndCode = conf.get()['codes']['user_end']

    def __handleAircraftObstacleCollisions(self):
        for o in self.obstacles:
            newCollides = o.collideAircraft(self.aircraft)
            self.score += (newCollides * conf.get()['scoring']['obs_collide'])

    def __handleAircraftCollision(self, ac1, ac2):
        if( Utility.locDistSq(ac1.getLocation(), ac2.getLocation()) < (conf.get()['aircraft']['collision_radius'] ** 2) ):
            if not self.demomode:
                self.gameEndCode = conf.get()['codes']['ac_collide']
            self.score += conf.get()['scoring']['ac_collide']
            # Highlight the collided aircraft
            ac1.image = Aircraft.AC_IMAGE_NEAR # later set to Aircraft.AC_IMAGE_COLLIDED
            ac2.image = Aircraft.AC_IMAGE_NEAR


    def __highlightImpendingCollision(self, a):
        for at in self.aircraft:
            if ((at != a) and (not a.selected)):
                if (Utility.locDistSq(a.getLocation(), at.getLocation()) < ((3 * conf.get()['aircraft']['collision_radius']) ** 2) ):
                    #a.state = Aircraft.AC_STATE_NEAR
                    a.image = Aircraft.AC_IMAGE_NEAR
                    break
                else:
                    if (a.selected):
                        a.image = Aircraft.AC_IMAGE_SELECTED
                    else:
                        a.image = Aircraft.AC_IMAGE_NORMAL

    def __getACClickedOn(self, clickpos):
        foundac = None
        mindistsq = 100
        for i in range(0, len(self.aircraft)):
            ac = self.aircraft[i]
            distsq = ac.getClickDistanceSq(clickpos)
            if( distsq < mindistsq ):
                foundac = ac
                mindistsq = distsq
        return foundac

    def __generateAircraftSpawnEvents(self):
        (self.aircraftspawntimes, self.aircraftspawns) = AircraftSpawnEvent.generateGameSpawnEvents(AIGame.AERIALPANE_W, AIGame.AERIALPANE_H, self.destinations)
        while self.__areSpawnEventsTooClose(self.aircraftspawntimes, self.aircraftspawns) == True: # If spawn events are too close try to fix it
            (self.aircraftspawntimes, self.aircraftspawns) = AircraftSpawnEvent.generateGameSpawnEvents(AIGame.AERIALPANE_W, AIGame.AERIALPANE_H, self.destinations)

    def __isSpawnPointTooCloseToAircraft(self,spawn):
        ret = False
        for i in self.aircraft:
            dist = Utility.locDistSq(spawn.getSpawnPoint(), i.getLocation())
            if (dist < 10000):                              # This distance can be manipulated for spawn point check
                ret = True;
        return ret


    def __areSpawnEventsTooClose(self, times, spawns):  # This should fix the problem
        ret = False
        if len(times) == len(spawns):
            x = 0
            y = 0
            brk = False
            while x < len(spawns) and (brk == False):
                while y < len(spawns) and (brk == False):
                    if(x != y):
                        dist = Utility.locDistSq(spawns[x].getSpawnPoint(), spawns[y].getSpawnPoint())
                        dt = math.fabs(times[x] - times[y])
                        if ((dist < 25 ** 2) and (dt < 6000)):
                            ret = True
                            brk = True
                    y += 1
                x += 1
        else:
            ret = True
        return ret


    def __generateDestinations(self):
        self.destinations = Destination.generateGameDestinations(AIGame.AERIALPANE_W, AIGame.AERIALPANE_H)

    def __generateObstacles(self):
        self.obstacles = Obstacle.generateGameObstacles(AIGame.AERIALPANE_W, AIGame.AERIALPANE_H, self.destinations)

    def __displayPostGameDialog(self):
        if(self.gameEndCode != conf.get()['codes']['user_end'] and self.gameEndCode != conf.get()['codes']['kill']):
            l = gui.Label("Game Over!")
            b = gui.Button("OK")
            bob = [False]
            def okcb(b):
                b[0] = True

            b.connect(gui.CLICK,okcb,bob)
            c = gui.Container()


            if(self.gameEndCode == conf.get()['codes']['ac_collide']):
                c.add(gui.Label("COLLISION!!!!"), 0, 0)
            elif(self.gameEndCode == conf.get()['codes']['time_up']):
                c.add(gui.Label("Time up!"), 0, 0)

            c.add(b,0,30)

            d = gui.Dialog(l, c)
            d.open()
            self.app.update(self.screen)
            pygame.display.flip()
            #pygame.time.delay(3000)
            clock = pygame.time.Clock()
            while(not bob[0]):
                timepassed = clock.tick(conf.get()['game']['framerate'])
                for e in pygame.event.get():
                    self.app.event(e)
                self.app.repaint()
                self.app.update(self.screen)
                pygame.display.flip()


    def getPlaneDict(self):
        planeDict = {}
        for plane in self.aircraft:
            id = plane.getIdent()
            planeDict[id] = plane
        
        return planeDict


    def getCollidingAircraft(self):
        potentialCollisions = set()
        collisionPlanes = set()
        for i,plane1 in enumerate(self.aircraft):
            for j,plane2 in enumerate(self.aircraft):
                if (i == j):
                    continue
                loc1 = plane1.getLocation()
                planeId1 = plane1.getIdent()
                loc2 = plane2.getLocation()
                planeId2 = plane2.getIdent()
                distance = np.linalg.norm(loc1 - loc2)

                if (distance < AIGame.POTENTIAL_COLLISION_THRESHOLD and (planeId2,planeId1) not in potentialCollisions):
                    potentialCollisions.add((planeId1,planeId2))
                    if planeId1 not in collisionPlanes:
                        collisionPlanes.add(planeId1)
                    if planeId2 not in collisionPlanes:
                        collisionPlanes.add(planeId2)

        return list(potentialCollisions), collisionPlanes


    def getRewards(self, destination_airplanes, collision_set):
        rewards = {}
        planes = self.getPlaneDict()
        for plane in self.aircraft:
            id = plane.getIdent()

            reward = 0

            loc = np.array(plane.getLocation())
            closest_distance = np.inf
            if id in collision_set:
                # get closest plane
                for plane2id in collision_set:
                    plane2 = planes[plane2id]
                    if plane is plane2:
                        continue
                    loc2 = np.array(plane2.getLocation())
                    dist = np.linalg.norm(loc2-loc)
                    if dist < closest_distance:
                        closest_distance = dist

                radius = AIGame.POTENTIAL_COLLISION_THRESHOLD
                dist_rew = -(radius**2 - closest_distance**2)/(radius**2/500)
                reward += dist_rew

            reward += 100 - plane.getDistanceToGo()

            rewards[id] = reward
        for id in destination_airplanes:
            rewards[id] = 1000

        return rewards
