#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Silly listener/sender for Zhorn Software Stickies
    (http://www.zhornsoftware.co.uk/stickies/)


    license: GNU General Public License (GPL) 2.0
    (http://www.gnu.org/licenses/gpl-2.0.html)
"""
__file_name__ = "ete_pystickies.py"
__author__ = "Luca Zaccaria <luca.vs800@hotmail.it>"
__version__ = "1.1.3"
__date__ = "2012-06-13"


# some python3 hacks
try:
    unicode = unicode
except NameError:
    ISP3 = True
    # 'unicode' is undefined, must be Python 3
    # str = str
    # unicode = str
    # bytes = bytes
    basestring = (str, bytes)
else:
    ISP3 = False
    # 'unicode' exists, must be Python 2
    # str = str
    # unicode = unicode
    # bytes = str
    basestring = basestring

import os
import sys
from os.path import join
import socket
import binascii
import re
import struct
# from tempfile import NamedTemporaryFile
import threading
import signal
from subprocess import call
import daemon
import subprocess
import shlex
import yaml
from datetime import datetime
from optparse import OptionParser

STD_PORT = 52673
REC = re.compile(r'^(\w+)=(.*)', re.MULTILINE)
RE_GETIP = '^(?P<id1>\d)\|(?P<id2>0)\|(?P<name>{})=' \
    '(?P<ip>.*)\|(?P<port>\d*)\|$'
RE_GETNAME = r'^(?P<id1>\d)\|(?P<id2>0)\|(?P<name>.*)=' \
    r'(?P<ip>{})\|(?P<port>\d*)\|$'
RE_RTF_STRIP = r'\{\*?\\[^{}]+}|[{}]|\\\n?[A-Za-z]+\n?(?:-?\d+)?[ ]?'


def get_name(address, filename):
    """
    Retrieve info by address.
    """
    if not os.path.isfile(filename):
        print ("Missing friends file {}".format(filename))
        sys.exit(1)
    rawstr = RE_GETNAME.format(address)
    if ISP3:
        rawstr = bytes(rawstr, 'utf-8')
    match_obj = re.search(rawstr, open(filename, "rb").read(), re.MULTILINE)
    if match_obj:
        try:
            print (match_obj.group('name'), match_obj.group('ip'))
            return [match_obj.group('name'),
                    match_obj.group('ip'), match_obj.group('port')]
        except Exception as error:
            print (error)
            return None
    else:
        try:
            return [socket.gethostbyaddr(address), address, None]
        except Exception as error:
            print (error)
            return None


def get_ip(nome, filename):
    """
    Retrieve info by name
    """
    if not os.path.isfile(filename):
        print ("Missing friends file {}".format(filename))
        sys.exit(1)
    rawstr = RE_GETIP.format(nome)
    if ISP3:
        rawstr = bytes(rawstr, 'utf-8')
    match_obj = re.search(rawstr, open(filename, "rb").read(), re.MULTILINE)
    if match_obj:
        try:
            print (match_obj.group('name'), match_obj.group('ip'))
            return [socket.gethostbyname(match_obj.group('ip')),
                    match_obj.group('name'), match_obj.group('port')]
        except Exception as error:
            print (error)
            return None
    else:
        try:
            return [socket.gethostbyname(nome), nome, None]
        except Exception as error:
            print (error)
            return None

#: custom exception to handle SIGTERM when needed


class StickyCloseError(Exception):
    pass

class StickyNoEditorError(Exception):
    pass


def check_output(command):
    """
        A silly version of check_output that works with python 2.6
    """
    if isinstance(command, basestring):
        command = shlex.split(command)
    p = subprocess.Popen(command, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    out, err = p.communicate()
    return out


class EteDumbObj(dict):
    """ Dumb class to use a dictionary as an object.  """

    def __init__(self, *args, **kwargs):
        dict.__init__(self, *args, **kwargs)

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        else:
            return self.get(name, None)

    def __setattr__(self, name, value):
        if name in self.__dict__:
            self.__dict__[name] = value
        else:
            self[name] = value

    def __delattr__(self, name):
        del self[name]

    def __dir__(self):
        return self.keys() + self.__dict__.keys()

    def __getstate__(self):
        return dict(self.items())


class Config(EteDumbObj):
    """
        Silly configuration from yaml
    """

    def __init__(self, *args, **kwargs):
        self.__dict__['_filename'] = None
        if len(args) == 1 and isinstance(args[0], basestring):
            filename = args[0]
            if not os.path.exists(filename):
                in_file = open(filename, "wb")
                in_file.close()
            self._filename = filename
            with open(self._filename, "rb") as f:
                EteDumbObj.__init__(self, yaml.load(f.read()))
        else:
            EteDumbObj.__init__(self, *args, **kwargs)

    def __getattr__(self, name):
        if name in self.__dict__:
            return self.__dict__[name]
        else:
            return self.get(name, self.get(name.upper(), None))

    def __setattr__(self, name, value):
        if name in ['save', 'optset']:
            raise KeyError("%s cannot be used as a key")
        elif name in self.__dict__:
            self.__dict__[name] = value
        elif name.upper() in self.keys():
            self[name.upper()] = value
        else:
            self[name] = value

    def save(self, filename=None):
        """
        Save the config
        """
        filename = filename or self._filename
        with open(filename, 'wb') as fobj:
            fobj.write(yaml.dump(dict(self.items()), default_flow_style=False))

    def optset(self, options, force=False):
        """
        Set config according to the options dictionary.
        If *force* is True overwrites the value, else takes the most
        significant.
        """
        for key, value in options.items():
            if not force:
                value = value or getattr(self, key, None)
            setattr(self, key, value)


class Sticky(object):
    """
       The Stickie handler.
    """

    def __init__(self, parent, connection, address, cfg):
        self.parent = parent
        self.conn = connection
        self.addr = address
        self.cfg = cfg
        self.data = ''
        self.closed = False
        self.sticky = EteDumbObj()
        self.sequenza = ['W', 'COL', 'TEXT', 'RTF', 'TO', 'PORT', 'HEIGHT']
        if self.conn is not None:
            self.receive()

    def receive(self):
        """
        Starts to receiving data...
        """
        while True:
            data = self.conn.recv(1024)
            if not data:
                break
            self.data += data
            if self.cfg.debug:
                self.cfg.logfile.write(data)
        """
        Gets some information.
        """
        self.length, self.command, self.data = re.split(
            r'#(\w+)\s', self.data, maxsplit=1)
        # Retreive more informations.
        self.data_from_command()
        self.sticky.PORT = self.sticky.PORT or STD_PORT
        name = get_name(self.addr[0], self.cfg.friendsfile)
        if name is None:
            name = self.addr[0]
        else:
            name = name[0]
        self.cfg.dest_name = name
        # Let's try to advise the user via notify-send.
        try:
            call(["notify-send", "-u", "normal",
                  "EtePyStickies: message from %s\n" % name,
                  self.sticky.TEXT.replace('\r', '')[:50]])
        except:
            pass
        # And call the action if there is one.
        if self.action:
            self.action()

    def data_from_command(self):
        """
        Process data depending on the command.
        """
        self.action = None
        if self.command == 'sticky':
            # It's a Sticky, let's take all the properties and then open
            # the Sticky.
            lst = REC.findall(self.data)
            self.sequenza = [l[0] for l in lst]
            self.sticky = EteDumbObj(lst)
            self.action = self.open
        elif self.command == 'send':
            # TODO: i have to implement this.
            pass
        elif self.command == '3friends':
            # Seems someone is sending a Friends list. let's save it.
            with open(self.cfg.friendsfile, 'wb') as f:
                f.write(self.data)

    def send(self, filename):
        """
        Sends the Sticky.
        """
        with open(filename) as f:
            # let's make some conversion... but i'm still confused.
            s = f.read()
            if self.cfg.signit:
                # Signature if is needed.
                s += "\n%s." % self.cfg.myname
            if self.cfg.rtf:
                self.sticky.RTF = f.read().replace('\n', '\r')
                self.sticky.TEXT = self.sticky.RTF
            else:
                text = []
                for ttt in s.splitlines():
                    if '\\' in ttt:
                        ttt = ttt.encode('string-escape')
                    text.append(ttt)
                self.sticky.RTF = '{\\rtf1\\ansi\\ansicpg1252\\deff0\\deflang1040 %s}\r' % (
                    '\\par\r'.join(text))
                self.sticky.TEXT = "\r".join(text)
        data = ''
        # ok we will take the port where to send.
        port = int(self.sticky.PORT)
        # And set the port where to send back.
        self.sticky.PORT = self.cfg.port
        # Ok fill the data string with rights thing according with the original
        # sequence.
        for key in self.sequenza:
            data += "%s=%s\n" % (key, self.sticky[key])
        data = '#sticky ' + data
        # Add data length to the beginning.
        if ISP3:
            data = b"\xff" + struct.pack('H', len(data)) + bytes(data, 'utf-8')
        else:
            data = "\xff" + struct.pack('H', len(data)) + data

        if self.cfg.debug:
            self.cfg.logfile.write(data)
        # Ok and now is time to send.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self.addr[0], port))
            sock.send(data)
            sock.close()
        except Exception as error:
            print ("I can't send the message: %s" % error.args[1])

    def ask_for_friends(self):
        """
        Ask to the defined server for a friends list.
        """
        data = "#send 3friends:%s" % self.cfg.port
        data = "\xff" + struct.pack('H', len(data)) + data
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            # serverip = get_ip(self.cfg.serverip, self.cfg.friendsfile)
            s.connect((self.cfg.serverip, self.cfg.serverport))
            s.send(data)
            s.close()
        except Exception as error:
            print ("Cannot connect to the serever. %s" % str(error))

    def new(self, msg=None):
        """
        Prepare for the new message.
        """
        self.sticky.W = self.cfg.witdh or 250
        self.sticky.RTF = msg
        self.sticky.TEXT = msg
        self.sticky.TO = self.addr[1]
        self.sticky.HEIGHT = self.cfg.height or 200
        self.sticky.COL = self.cfg.col or "255,255,180"
        self.sticky.PORT = self.addr[2] or self.cfg.port
        fname = self.get_filename()
        if msg:
            filename = self.get_msgfile(content=msg)
            self.send(filename)
        else:
            self.open()

    def get_msgfile(self, content=''):
        filename = self.get_filename()
        with open(filename, 'wb') as fobj:
            if ISP3:
                fobj.write(bytes(content, "utf-8"))
            else:
                fobj.write(content)
        return filename

    def get_filename(self):
        date = datetime.now()
        if isinstance(self.cfg.dest_name, basestring):
            dname = self.cfg.dest_name
        else:
            dname = self.cfg.dest_name[0]
        filename = "{:%Y%m%d-%H%M%S}-{}.txt".format(date, dname.replace(' ', '-'))
        filename = os.path.join(self.cfg.home, filename)
        return filename

    def open(self):
        """
        Open the temporary file and send it if there are some changes.
        """
        if self.cfg.rtf:
            content = self.sticky.RTF
        else:
            content = self.sticky.TEXT
        # I'm not so sure if is this the right replacment.
        content = content.replace(r'^M', os.linesep)
        filename = self.get_msgfile(content=content)
        mdate = os.path.getmtime(filename)
        check_output("%s %s" % (self.cfg.cmd, filename))
        if mdate != os.path.getmtime(filename):
            self.send(filename)
        if self.conn:
            self.conn.close()
        self.closed = True


class StickiesListener(object):
    """
    Listener
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.socket.bind((self.cfg.host, self.cfg.port))
        self.socket.listen(1)
        signal.signal(signal.SIGTERM, self.close)
        self.listen()

    def close(self, sig, frame=None):
        """
        Avoid the closing of the listener if there are some ope threads.
        """
        count = threading.active_count()
        if count > 1:
            call(["notify-send", "-u", "critical", "Ete PyStickies",
                  "Non posso uscire ci sono ancora %s messaggi aperti." %
                  (count - 1)])
            raise StickyCloseError

    def listen(self):
        """
        Starts to listen.
        """
        lista = []
        while True:
            try:
                conn, addr = self.socket.accept()
                print ("Connectino from %s" % str(addr))
                self.cfg.logfile.flush()
                thread = threading.Thread(
                    target=Sticky, args=(self, conn, addr, self.cfg))
                lista.append(thread)
                thread.start()
            except KeyboardInterrupt:
                print ("Closing by CTRL+C...")
                break
            except StickyCloseError:
                pass
            except socket.error as error:
                if error.args[0] == 4:
                    print ("Closing by SIGTERM...")
                    break
                else:
                    raise
        for thread in lista:
            try:
                thread.conn.close()
            except:
                pass
            del thread
        del lista


if __name__ == "__main__":
    parser = OptionParser(
        version="%prog " + __version__,
        usage="usage: %prog [options] [friend|pcname|address] [message]")
    ehome = join(os.path.expanduser('~'), '.ete_pystickies')
    parser.description = (
        "Silly program to receive and send Zhorn Software Stickies."
        "\n%prog supports completion for friend's names, where avaible "
        "(remember to use double quotes).")
    parser.add_option(
        '-l',
        '--listen',
        dest='listen',
        action='store_true',
        default=False,
        help="Starts in listening mode to accept incoming "
        "Stickies.")
    parser.add_option(
        '-p', '--port', type=int,
        help="listen to PORT instead of the port specified in the rc file")
    parser.add_option(
        '-d',
        '--daemon',
        dest='daemon',
        action='store_true',
        default=False,
        help="Used with -listen starts %prog as daemon.")
    parser.add_option('-f', '--friends', dest='friends', action='store_true',
                      default=False, help="Ask for friends.")
    parser.add_option(
        '-F', '--fserver', dest='ipfriends', metavar="IP",
        help="Ask for friends to server.")
    parser.add_option('-g', '--debug', dest='debug', action="store_true",
                      default=False, help="Writes some info to the log")
    options, args = parser.parse_args()
    cfg = Config(join(ehome, 'ete_pystickiesrc'))
    if not cfg.cmd:
        print("You must setup your editor (cmd: option in your config file "
            "{})".format(join(ehome, 'ete_pystickiesrc')))
        sys.exit(1)
    cfg.logfile = open(join(ehome, 'ete_pystickies.log'), "w+")
    cfg.friendsfile = join(ehome, "friends")
    cfg.home = ehome
    cfg.cwd = os.getcwd()
    cfg.optset(vars(options))
    if options.listen:
        os.sys.path.append(cfg.cwd)
        if 'In' not in locals() and options.daemon:
            dm_ = daemon.DaemonContext(
                working_directory=str(cfg.cwd), stdout=cfg.logfile,
                stderr=cfg.logfile)
            dm_.open()
        if options.port:
            cfg.port = options.port
        StickiesListener(cfg)
        print ("Closed.")
    elif options.friends:
        sticky = Sticky(None, None, None, cfg)
        sticky.ask_for_friends()
        del sticky
    elif options.ipfriends:
        cfg.serverip = options.ipfriends
        sticky = Sticky(None, None, None, cfg)
        sticky.ask_for_friends()
        del sticky
    else:
        if len(args):
            ipadd = get_ip(args[0], cfg.friendsfile)

            if ipadd:
                cfg.dest_name = args[0]
                sticky = Sticky(None, None, ipadd, cfg)
                sticky.new(" ".join(args[1:]))
            else:
                print ("it seems there no one are connected for", args[0])
        else:
            print ("Needs a friend or in ip address")
    cfg.logfile.close()
    sys.exit(0)
