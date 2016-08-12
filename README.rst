=============
EtePyStickies
=============

.. sectnum::

.. contents:: table of contents

What is it?
___________
EtePyStickies it's a silly program that permit to receive and send
Zhorn Software Stickies (http://www.zhornsoftware.co.uk/stickies/) through
the LAN using Linux.


System requirements
___________________
Actually i have tested this thing only with Python 2.7 on Ubuntu 12.04, 14.04, 16.04
and Mint 18.

So i don't know if there are problems. 
let me know.


Dependencies
____________
As i remember only the python-daemon (http://pypi.python.org/pypi/python-daemon/)
is needed all other modules should be in the standard library


Files
_____
**ete_pystickies.py**
  The program.

  Should be symlinked into /usr/local/bin/ as ete_pystickies (without extension)

**ete_pystickies.completion**
  The completion file. It should be symlinked into /etc/bash_completion.d/ 

  It helps to find friends name when you start a new message.

**ete_pystickiesrc.sample**
  The sample configuration file.

**friends**
  The file that contains the friends list.

**ete_pystickiesd.log**
  The log file that contains some information, but not too much.


Configuration
_____________
**myname**
    Just to say what is your name.

**host**
    The host where the program is listening should be an empty string ('').

**port**
    The port where the program is listening (default is 52673).

**serverip**
    The IP of the machine where to retrieve the friends list.

**serverport**
    The port for the above machine (default is 52673).

**cmd**
    The program you want to use to edit messages (ex. gedit).

**rtf True|False**
    Indicates that the program that you're using is capable to read rtf format.

**width**
    The Sticky window's width (sent message).

**height**
    The Sticky window's height (sent message).

**col**
    The Sticky window's colors (sent message).


Options & Arguments
___________________
**-l or --listen**
    Starts the program in listening mode, waiting for incoming messages.

**-d or --daemon**
    Starts the program in daemon mode when is used with **--listen**.

**-f or --friends**
    Retrieve the friends list from the server (config: *serverip*, *serverport*)

**-g or --debug**
    Write messages into the log too.

**Arguments**
    As Argument accepts only the recipient it can be a name from the friends 
    list, a computer name in the LAN or an IP address.
    
    *Remember to use double quotes(") for firend's names thats contains spaces*.


Installation
____________
The installation script *install.sh* will try to create the folder $HOME/.ete_pystickies 
where will take place the files *friends*, *ete_pystickies.log*, 
*ete_pystickiesrc* and *backup messages files*.
It will copy *ete_pystickies.py* in /opt/ete_pystickies/ and will try to copy 
*ete_pystickies.completion* in /etc/bash_completion/


Usage
_____
**ete_pystickies --listen** 
    to start the program as stand alone listener.

**ete_pystickies "Friend Name"**
    to send a message.

You can put *ete_pystickies --listen* in your **Startup  Applications** so 
it will start automatically.
