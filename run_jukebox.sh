#!/bin/bash
export DISPLAY=:0
export XAUTHORITY=/home/jukebox/.Xauthority

# Hide the cursor at OS level so VLC can't bring it back
sleep 2
unclutter -idle 0 -root &

# Set up mirrored displays
sleep 5
xrandr --output HDMI-A-1 --auto --output HDMI-A-2 --auto --same-as HDMI-A-1

# Wait for USB drive to mount
echo "Waiting for USB drive..."
while [ ! -d "/media/jukebox/JUKEBOX/videos" ]; do
    sleep 1
done
echo "USB drive found, starting jukebox..."

source /home/jukebox/jukebox-env/bin/activate
python /home/jukebox//AfterDark2/jukebox.py