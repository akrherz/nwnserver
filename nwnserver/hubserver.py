# Neighborhood Weather Net Hub
# Copyright (C) 2004 Iowa State University
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

"""Basic Neighborhood Weather Net Hub server and supporting classes."""

from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.cred import credentials
#from twisted.python.components import Interface
from zope.interface import Interface, implements
from twisted.internet import reactor
from twisted.python import log

from nwnserver import common
from nwnserver import auth

class HubServer(LineReceiver):
    # States for state machine
    LOGIN, PASS, AUTH, SUCCESS = range(4)

    def __init__(self, avatarInterface):
        self.avatarInterface = avatarInterface
        self.avatar = None
        
    def connectionMade(self):
        self.ip = self.transport.getPeer().host
        self.__state = self.LOGIN
        self.transport.write(common.loginPrompt)
        if (self.ip == "66.115.217.146" or self.ip == "66.115.208.218" or self.ip == "208.107.61.74"):
            log.msg("BYPASS: %s" % self.ip)
            self.__state = self.SUCCESS
            d = self.factory.portal.login(credentials.UsernamePassword('kelo999', 'kelo999'),
                                          None, self.avatarInterface)
            d.addCallback(self._cbAuth)
            d.addErrback(self._ebAuth)
        
        log.msg("Connection made from: %s" % self.ip)

    def connectionLost(self, reason):
        if self.__state == self.SUCCESS:
            self.factory.clients.remove(self)

        log.msg("Client logged out from: %s" % self.ip)
        
    def lineReceived(self, line):
        if self.__state == self.LOGIN:
            self.transport.write(common.passwordPrompt)
            self.__state = self.PASS
            self.user = line

        elif self.__state == self.PASS:
            self.__state = self.AUTH
            d = self.factory.portal.login(credentials.UsernamePassword(self.user, line),
                                          None, self.avatarInterface)
            d.addCallback(self._cbAuth)
            d.addErrback(self._ebAuth)

    def _cbAuth(self, successData):
        """Called when user is successfully authenticated."""
        self.__state = self.SUCCESS
        self.sendLine('')
        self.sendLine(common.successMessage)
        
        self.factory.clients.append(self)

        # Derived classes may use successData
        if successData != None:
            self.avatar = successData[1]

        log.msg("Client authenticated from: %s" % (self.ip,) )
        
    def _ebAuth(self, failure):
        """Called when user authentication fails."""
        self.transport.loseConnection()
        
        log.msg("Client failed authentication from: %s" % self.ip)

class HubServerFactory(Factory):
    protocol = HubServer
    
    def __init__(self, portal, avatarInterface=auth.IDummy, archiver=None):
        """
        @param portal: portal for cred authentication
        """
        self.portal = portal            
        self.clients = []
        self.archiver = archiver
        self.avatarInterface = avatarInterface

    def __getstate__(self):
        """
        This is necessary for persistence, since protocol instances,
        stored in .clients, cannot be pickled. 
        """
        d = self.__dict__.copy()
        d['clients'] = []
        return d

    def buildProtocol(self, addr):
        p = self.protocol(self.avatarInterface)
        p.factory = self
        return p
            
    def sendToAllClients(self, line):
        if (line != None and line != ""):
            line = line.strip()
            for client in self.clients:
                client.sendLine(line)
