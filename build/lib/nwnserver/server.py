# Neighborhood Weather Net
# Copyright (C) 2003 Iowa State University
# Written by Travis B. Hartwell
# 
# This module is free software; you can redistribute it and/or
# modify it under the terms of version 2.1 of the GNU Lesser General Public
# License as published by the Free Software Foundation.
# 
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Basic Neighborhood Weather Net server and supporting classes."""

from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.cred import credentials
#from twisted.python.components import Interface
from twisted.internet import reactor
from twisted.python import log

from nwnserver import common
from nwnserver import auth

class NWNServer(LineReceiver):
    # States for state machine
    LOGIN, PASS, AUTH, SUCCESS = range(4)

    def connectionMade(self):
        self.ip = self.transport.getPeer().host
        log.msg("Connection made from: %s" % self.ip)
        if (self.factory.noAuth):
            self._cbAuth(None)
        else:
            self.__state = self.LOGIN
            self.transport.write(common.loginPrompt)
        #self.__state == self.SUCCESS

    def connectionLost(self, reason):
        if self.__state == self.SUCCESS:
            self.factory.clients.remove(self)
        
    def lineReceived(self, line):
        if self.__state == self.LOGIN:
            self.transport.write(common.passwordPrompt)
            self.__state = self.PASS
            self.user = line

        elif self.__state == self.PASS:
            self.__state = self.AUTH
            d = self.factory.portal.login(credentials.UsernamePassword(self.user, line),
                                          None, auth.IDummy)
            d.addCallback(self._cbAuth)
            d.addErrback(self._ebAuth)
            #self._cbAuth(None)

    def _cbAuth(self, dummy):
        """Called when user is successfully authenticated."""
        self.__state = self.SUCCESS
        self.sendLine('')
        self.sendLine(common.successMessage)

        log.msg("Client authenticated from: %s" % self.ip)
        self.factory.clients.append(self)

    def _ebAuth(self, failure):
        """Called when user authentication fails."""
        log.msg("Client failed authentication from: %s" % self.ip)
        self.transport.loseConnection()

    def removeAuth(self):
        log.msg("Removing Authentication")
        self.__state == self.SUCCESS

class NWNServerFactory(Factory):
    protocol = NWNServer

    def __init__(self, portal, noAuth=0):
        """
        @param portal: portal for cred authentication
        """
        self.portal = portal            
        self.clients = []
        self.noAuth = noAuth

    def __getstate__(self):
        """
        This is necessary for persistence, since protocol instances,
        stored in .clients, cannot be pickled. 
        """
        d = self.__dict__.copy()
        d['clients'] = []
        return d
        
    def sendToAllClients(self, line):

        if (line != None and line != ""):
            line = line.strip()
            for client in self.clients:
                client.sendLine(line)
            del line
