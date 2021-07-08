# MusicalWC

A raspberry pi based music jukebox for... bathrooms?

# The Concept:
When the bathroom door (or whatever door the system is monitoring) is opened, a theme is selected and an sound effect is played. The system then plays a shuffled playlist on repeat. Then when the door is closed, the music is stopped and an exit sound effect is played. Themes are created by the user with open sound effects, close sound effects, and music that are loaded into the pi via usb flash memory. Themes are randomly selected to keep the playback interesting.

# The hardware:
The raspberry pi uses an infrared reflective sensor to check the whether the door is open or not and a PIR sensor to detect if the room is occupied or not. The system uses the door sensor to cycle between playback and silence assuming users close the door behind them. In the case 
