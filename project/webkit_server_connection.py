"""
Python bindings for the `webkit-server <https://github.com/niklasb/webkit-server/>`_
"""
import subprocess
from threading import Thread
import re
import socket
import atexit
import time
from webkit_server import SERVER_EXEC, NoX11Error, InvalidResponseError, EndOfStreamError,NoResponseError

import logging
logger = logging.getLogger(__name__)

class Server(object):
    """ Manages a Webkit server process. If `binary` is given, the specified
    ``webkit_server`` binary is used instead of the included one. """

    def _watch(self):
        while not self._exiting:
            if self._server.poll() is not None:
                logger.error('Server process found dead.')
                self._child()
            time.sleep(0.5)

    def _child(self):
        logger.debug('Spawning server process.')
        self._server = subprocess.Popen([self._binary, '--ignore-ssl-errors'],
            stdin  = subprocess.PIPE,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE)
        output = self._server.stdout.readline()
        try:
            self._port = int(re.search("port: (\d+)", output).group(1))
            logger.debug('Server is listening on port %d.'%self._port)
        except AttributeError:
            raise NoX11Error, "Cannot connect to X. You can try running with xvfb-run."

    def __init__(self, binary = None):
        self._binary = binary or SERVER_EXEC
        self._exiting = False
        self._child()
        self._watchdog = Thread(target=self._watch)
        self._watchdog.daemon = True
        self._watchdog.start()
        # on program termination, kill the server instance
        atexit.register(self.__del__)

    def __del__(self):
        self._exiting = True
        self.kill()

    def kill(self):
        """ Kill the process. """
        try:
            logger.warn('killing the server')
            self._server.kill()
            self._server.wait()
        except OSError as e:
            logger.exception(e)

    def connect(self):
        """ Returns a new socket connection to this server. """
        for i in range(3):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect(("127.0.0.1", self._port))
                return sock
            except:
                self.kill()
                raise Exception('cannot create socket..')

class ServerConnection(object):
    """ A connection to a Webkit server.

    `server` is a server instance or `None` if a singleton server should be connected
    to (will be started if necessary). """

    @classmethod
    def get_server(cls):
        if not hasattr(cls, '_server') or not hasattr(cls, '_count'):
            cls._server = Server()
            cls._count = 0
        cls._count += 1
        logger.debug('connections %d' % cls._count)
        return cls._server

    @classmethod
    def del_server(cls):
        if hasattr(cls, '_server') and hasattr(cls, '_count'):
            cls._count -= 1
            logger.debug('connections %d' % cls._count)
            if cls._count <= 0:
                pass #cls._server.kill()

    def __init__(self, server = None):
        super(ServerConnection, self).__init__()
        self._sock = (server or self.get_server()).connect()

    def __del__(self):
        logger.debug('closing connection')
        self._sock.close()
        self.del_server()

    def issue_command(self, cmd, *args):
        """ Sends and receives a message to/from the server """
        self._writeline(cmd)
        self._writeline(str(len(args)))
        for arg in args:
            arg = str(arg)
            self._writeline(str(len(arg)))
            self._sock.send(arg)

        return self._read_response()

    def _read_response(self):
        """ Reads a complete response packet from the server """
        result = self._readline()
        if not result:
            raise NoResponseError, "No response received from server."

        if result != "ok":
            raise InvalidResponseError, self._read_message()

        return self._read_message()

    def _read_message(self):
        """ Reads a single size-annotated message from the server """
        size = int(self._readline())
        if size == 0:
            return ""
        else:
            return self._recvall(size)

    def _recvall(self, size):
        """ Receive until the given number of bytes is fetched or until EOF (in which
        case ``EndOfStreamError`` is raised). """
        result = []
        while size > 0:
            data = self._sock.recv(min(8192, size))
            if not data:
                raise EndOfStreamError, "Unexpected end of stream."
            result.append(data)
            size -= len(data)
        return ''.join(result)

    def _readline(self):
        """ Cheap implementation of a readline function that operates on our underlying
        socket. """
        res = []
        while True:
            c = self._sock.recv(1,)
            if c == "\n":
                return "".join(res)
            res.append(c)

    def _writeline(self, line):
        """ Writes a line to the underlying socket. """
        self._sock.send(line + "\n")
