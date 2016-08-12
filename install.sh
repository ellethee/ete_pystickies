#!/bin/bash
#
# Filename:     install.sh
# Author:       luca
# Version:      1.0.0
# Date:         2012-09-14
#
BASE_DIR=$(dirname "$(readlink -f "$0")")
CONFIG_DIR="$HOME/.ete_pystickies"
EXE_DIR="/opt/ete_pystickies"
BIN_PATH="/usr/local/bin/ete_pystickies"
CONFIG_FILE="$CONFIG_DIR/ete_pystickiesrc"
if [ -z "$EDITOR" ]; then
    if [ -e "$(which editor)" ]; then
        EDITOR=$(which editor)
    fi
fi
# root part
[ ! -e "$EXE_DIR" ] && sudo mkdir -p "$EXE_DIR"
sudo cp "$BASE_DIR/ete_pystickies.py" "$EXE_DIR/"
sudo chmod +x "$EXE_DIR/ete_pystickies.py"
sudo ln -s "$EXE_DIR/ete_pystickies.py" "$BIN_PATH"
sudo cp "$BASE_DIR/ete_pystickies.completion" "/etc/bash_completion.d/ete_pystickies"
# user part
[ ! -e "$CONFIG_DIR" ] && mkdir -p "$CONFIG_DIR"
if [ ! -e $CONFIG_FILE ]; then
    envsubst < "$BASE_DIR/ete_pystickiesrc.sample" > "$CONFIG_FILE"
    touch "$CONFIG_DIR/friends"
cat << FINE
    ####
    # Remember to edit your config $CONFIG_FILE and your friends $CONFIG_DIR/friends.
    # Or try to creaete it by configuring the serverip option in your config 
    # and launching ete_pystickies -f
    ###
FINE
    echo -e 
    if [ ! -z $EDITOR ]; then
        $EDITOR "$CONFIG_FILE"
    fi
fi
