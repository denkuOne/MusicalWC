#Musical Toilet?
#Bryce Martin 2021

import enum
import re
import os
import threading

from gpiozero import Button, LED
from subprocess import Popen, run
from time import time
from signal import pause
from random import choice

#Settings
DOOR_HOLD_TIME_S = 5
AUTO_AUDIO_OFF_S = 600

#Hardware pins
DOOR_PIN = 22
ACTIVE_PIN = 5
IND_PIN = 6
PWR_OFF_PIN = 19
MOTION_SENSOR = 2

#States
class states(enum.Enum):
	inactive = 0
	unarmed = 1
	armed = 2
	playing = 3
	detecting = 4


#	IO handlers
#The functions below are used to handle the IO to the device
def door_closed():
	global current_state

	if current_state == states.unarmed or current_state == states.detecting:
		current_state = states.armed
			
		print(current_state)


def door_open():
	global current_state
	global selected_theme

	if current_state != states.inactive:
		if current_state == states.armed:
			current_state = states.playing
			print(current_state)
			
			#Pick a random theme from the library
			selected_theme = choice(list(library.items()))[0]
			print("Selected path is " + selected_theme)	
			
			#Play open sound associated with selected theme
			if library[selected_theme][0][0] != "None":
				run(['cvlc', '-I', 'dummy', '--play-and-exit', choice(library[selected_theme][0])])
			
			#Start theme playback
			start_playback()

		elif current_state == states.playing:
			current_state = states.detecting
			print(current_state)

			#Stop theme playback
			stop_playback()

			#Play close sound associated with selected theme
			if library[selected_theme][1][0] != "None":
				run(['cvlc', '-I', 'dummy', '--play-and-exit', choice(library[selected_theme][1])])


#Shutoff function tied to power offf button
def power_off():
	run(['sudo', 'shutdown', 'now'])


#PIR sensor released
def room_empty():	
	print("Nobody here!")

	#stop_playback()


#PIR sensor triggered
def room_occupied():
	global current_state
	
	print("Someone here!")
	
	#If someone enters the bathroom due to the door being left open, start playback
	if current_state == states.armed or current_state == states.detecting:
		current_state = states.playing
		print(current_state)

		start_playback()


#This function is called when the switch is flipped to the ON position
#It first mounts the first flash drive plugged into the device
#It discovers the themes on the flash drive and logs associated open and close sounds
#If successful, the corresponding indicator comes on and the process is complete
def switch_active():
	global current_state
	global selected_theme
	global library

	#Mount drive
	run(['sudo', 'mount', '-a'])

	#Search base directory for themes, then find subfolders and look for mp3 files and add
	#the valid folders and the mp3 files contained within to the library
	with os.scandir('/mnt/audioFiles') as entries:
		for entry in entries:
			path = '/mnt/audioFiles/' + entry.name

			items = []

			if os.path.isdir(path + "/entersfx"):
				openeffects = []

				with os.scandir(path + "/entersfx") as files:
					for item in files:
						name = re.match( r'(.*.mp3)', item.name)

						if name:
							openeffects.append(path + "/entersfx/" + name.group())

				if len(openeffects):
					items.append(openeffects)
			else:
				items.append(["None"])

			if os.path.isdir(path + "/exitsfx"):
				closeeffects = []

				with os.scandir(path + "/exitsfx") as files:
					for item in files:
						name = re.match( r'(.*.mp3)', item.name)

						if name:
							closeeffects.append(path + "/exitsfx/" + name.group())

				if len(closeeffects):
					items.append(closeeffects)
			else:
				items.append(["None"])
					
			#Check if there is Music folder, and create a playlist file of items inside
			if os.path.isdir(path + "/music"):
				playlist = open("/home/pi/playlists/" + entry.name + ".m3u", 'w')

				with os.scandir(path + "/music") as files:
					for item in files:
						name = re.match( r'(.*.mp3)', item.name)

						if name:
							playlist.write(path + "/music/" + item.name + '\n')

				library[entry.name] = items
				playlist.close()
				
			#Grab timer duration setting in available
			setting = re.match(r'(timeout.txt)', entry.name)
			
			if setting:
				print("Found a setting file")
				
				contents = open('/mnt/audioFiles/timeout.txt', 'r')
				try:
					AUTO_AUDIO_OFF_S = int(contents.read())
					print("Set timeout duration to {}".format(AUTO_AUDIO_OFF_S))
				except ValueError:
					print("Setting file invalid...")

	print(library.items())

	if len(library):
		active_led.on()
		
		#Select an initial theme
		selected_theme = choice(list(library.items()))[0]

		if door_sw.is_pressed:
			current_state = states.armed
		else:
			current_state = states.unarmed
		print(current_state)
	else:
		print("No valid files found")


#When the switch is off, any playing audio is stopped and the drive is unmounted
#The logged library is also cleared and indicator is turned off
def switch_inactive():
	global current_state
	global library

	current_state = states.inactive
	print(current_state)

	stop_playback()

	#Clear the library
	library = {}

	#Unmount drive
	run(['sudo', 'umount', '/mnt/audioFiles'])

	active_led.off()


#	Audio handlers
def end_of_timer():
	global current_state

	#The timeout timer only reacts if the system is in the 'playing' state
	if current_state == states.playing:
		current_state = states.detecting
		print(current_state)
		
		stop_playback()
		print("Time out!")


#Function that starts audio playback
def start_playback():
	global selected_theme
	global audio
	global timer	
	
	#Cancel any running timer
	try:
		timer.cancel()
		print("Timer cancelled")
	except AttributeError:
		pass
	
	#Start audio playback
	audio = Popen(['cvlc', '-I', 'dummy', '-L', '-Z', "/home/pi/playlists/" + selected_theme + ".m3u"])
	
	#Start auto-off timer
	timer = threading.Timer(AUTO_AUDIO_OFF_S, end_of_timer)
	timer.start()
	print("Timer started")
	

#Function to stop audio playback
def stop_playback():
	global audio

	try:
		audio.terminate()
	except AttributeError:
		pass


#Global Variables
current_state = states.inactive
audio = None
timer = None
library = {}
selected_theme = ""

#Hardware setup
door_sw = Button(DOOR_PIN, bounce_time = 1, pull_up = False)
active_sw = Button(ACTIVE_PIN)
power_btn = Button(PWR_OFF_PIN)
pir_sen = Button(MOTION_SENSOR)
active_led = LED(IND_PIN)

door_sw.when_pressed = door_closed
door_sw.when_released = door_open

active_sw.when_pressed = switch_active
active_sw.when_released = switch_inactive

power_btn.when_pressed = power_off

pir_sen.when_released = room_empty
pir_sen.when_pressed = room_occupied

if active_sw.is_pressed:
	switch_active()

pause()
