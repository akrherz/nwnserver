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

""" NWN Hub Poller server service """

from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.cred import credentials, portal
#from twisted.python.components import Interface
from zope.interface import Interface, implements
from twisted.internet import reactor
from twisted.python import log

from nwnserver import common
from nwnserver import filewatcher

class IPollerDataFormatter(Interface):

    def updateConfig(self, replacements):
        """ Update the replacement configuration for this station """

    def logout(self):
        """ Clean up resources for this avatar """

    def formatLine(self, line):
        """ Format the line """
        

class PollerDataFormatter:
    #__implements__ = (IPollerDataFormatter, )
    implements(IPollerDataFormatter)

    CURRENT, MIN, MAX = range(3)
    obTypes = ['C', 'N', 'X']
    obTypeNames = [None, 'Min', 'Max']

    OBTYPE = 0
    COLUMN, VALUE = range(2)

    BOGUS_LINE_LIMIT = 10
        
    def __init__(self, realm, stationID):
        self.replacements = {}
        self.realm = realm
        self.stationID = int(stationID)
        self.bogusLineCount = 0
        self.server = None

    def setPollerServer(self, server):
        self.server = server
        
    def updateConfig(self, replacements):
        self.replacements = {}
        
        for r in replacements:
            obType, column, value = r
            column = int(column)

            self.replacements.setdefault(obType, []).append((column, value))

    def logout(self):
        self.realm.removePoller(self.stationID)
        log.msg("Poller station %s disconnecting" % self.stationID)

    def formatLine(self, line):
        line = line.strip()

        if line in ['', '...NO DATA...']:
            return ''

        data = line.split()
        
        leadingElement = "A"

        obType = data[self.OBTYPE]

        if obType[0].isdigit():
            obType = self.obTypes[self.CURRENT]
        else:
            try:
                obType = self.obTypes[self.obTypeNames.index(obType)]
            except ValueError:
                # Gets thrown when an invalid obType is passed
                self.bogusLineCount += 1

                if self.bogusLineCount >= self.BOGUS_LINE_LIMIT:
                    try:
                        self.server.loseConnection()
                    except AttributeError:
                        log.msg("Station %s doesn't have reference to \
                                 its protocol instance.  Can't disconnect" % self.stationID)

                    return ''

        if obType in self.replacements:
            for replacement in self.replacements[obType]:
                # A change is going to be made, so indicate it with "R"
                leadingElement = "R"
                data[replacement[self.COLUMN]] = replacement[self.VALUE]

        # Prepend the line with the the dummy leading element and the stationID
        data.insert(0, self.stationID)
        data.insert(0, leadingElement)
        #return ' '.join([str(i) for i in data])
        if len(data) != 14:
            log.msg("Unparsable line received |%s|" % (line,))
            return ' '.join([str(i) for i in data])
        return "%s %03i  %5s %8s %3s %5s %4s %4s %4s %4s %6s %7s %7s %7s" % (
            data[0], data[1], data[2], data[3], data[4], data[5], data[6],
            data[7], data[8], data[9], data[10], data[11], data[12], data[13])



class PollerRealm:
    #__implements__ = portal.IRealm
    implements(portal.IRealm)

    def __init__(self, replacementConfigFilePath, reloadInterval=60):
        self.replacementConfig = {}
        self.avatars = {}

        # Load the replacement configuration and watch for changes
        self.fileWatcher = filewatcher.ConfigFileWatcher([replacementConfigFilePath],
                                                         self, reloadInterval)
        
    def updateConfig(self, configLines):
        # Recreate the config from scratch
        self.replacementConfig = {}
        
        for line in [line.strip() for line in configLines]:
            log.msg(self.replacementConfig)
            if line != "" and line[0] != '#':
                try:
                    stationID, obType, column, value = line.split(",")
                except ValueError:
                    # ValueError thrown when there is an "unpack list of wrong size"
                    log.msg("Error in poller config file\n\tLine: %s" % line)
                else:
                    if stationID in self.replacementConfig:
                        self.replacementConfig[stationID].append((obType, column, value))
                    else:
                        self.replacementConfig[stationID] = [(obType, column, value)]

        # Update the configuration on the stations
        self.updateStationConfigs()

    def updateStationConfigs(self):
        for stationId, replacements in self.replacementConfig.iteritems():
            if stationId in self.avatars:
                self.avatars[stationId].updateConfig(replacements)
                            
    def removePoller(self, stationID):
        """ remove a stationID from the avatars dict """
        self.avatars.pop( str(stationID), None )
        
    def requestAvatar(self, avatarId, mind, *interfaces):
        if IPollerDataFormatter in interfaces:
            stationID = avatarId[4:]
            poller = PollerDataFormatter(self, stationID)
            self.avatars[stationID] = poller
            self.updateStationConfigs()

            log.msg("Poller station %s connected" % stationID)
            
            return IPollerDataFormatter, poller, poller.logout


class PollerServer(LineReceiver):
    # States for state machine
    LOGIN, PASS, TIME, AUTH, SUCCESS = range(5)

    def logPrefix(self):
        """ Override the logPrefix so that the twisted python logging
        includes the username connected """
        return "%s,%s" % (getattr(self, 'user', '-'), 
                          getattr(self, 'ip', '-'))

    def loseConnection(self):
        self.transport.loseConnection()
        
    def connectionMade(self):
        self.ip = self.transport.getPeer().host

        self.__state = self.LOGIN
        self.transport.write(common.loginPrompt.upper())
        log.msg("New connection established")

    def connectionLost(self, reason):
        if self.__state == self.SUCCESS:
            self.factory.clients.remove(self)
            self.avatar.logout()

        log.msg("Connection lost from: %s because of: %s" % (self.ip, reason))
        
    def lineReceived(self, line):
        if self.__state == self.LOGIN:
            self.transport.write(common.passwordPrompt.upper())
            self.__state = self.PASS
            self.user = line
            self.transport.logstr = '%s,%s,%s' % (self.user, 
                                                  self.transport.sessionno,
                                                  self.ip)
            
        elif self.__state == self.PASS:
            self.passwd = line
            self.__state = self.TIME

        elif self.__state == self.TIME:
            # We don't care about the time info sent right now, so line is ignored here
            self.__state = self.AUTH

            d = self.factory.portal.login(credentials.UsernamePassword(self.user, self.passwd),
                                          None, IPollerDataFormatter)
            d.addCallback(self._cbAuth)
            d.addErrback(self._ebAuth)

        elif self.__state == self.SUCCESS:
            #print line
            self.factory.lineReceived(self.avatar.formatLine(line))

    def _cbAuth(self, (interface, avatar, logout)):
        """Called when user is successfully authenticated."""
        assert interface is IPollerDataFormatter

        self.avatar = avatar
        self.logout = logout
        
        self.__state = self.SUCCESS
        self.sendLine('')
        self.sendLine(common.successMessage)

        self.factory.clients.append(self)
        self.avatar.setPollerServer(self)

        log.msg("Client authenticated from: %s" % self.ip)

    def _ebAuth(self, reason):
        """Called when user authentication fails."""
        self.loseConnection()

        log.msg("Client failed authentication from: %s" % self.ip)



class PollerServerFactory(Factory):
    protocol = PollerServer

    def __init__(self, portal, hubFactory):
        """
        @param portal: portal for cred authentication
        @param hubFactory: factory for hub server
        """
        self.portal = portal
        self.hubFactory = hubFactory
        self.clients = []
        reactor.callLater(300, self.keepalive)

    def __getstate__(self):
        """
        This is necessary for persistence, since protocol instances,
        stored in .clients, cannot be pickled. 
        """
        d = self.__dict__.copy()
        d['clients'] = []
        return d

    def lineReceived(self, line):
        self.hubFactory.sendToAllClients(line)

    def keepalive(self):
        """
        Send something to keep the NWN clients happy
        """
        for client in self.clients:
            client.sendLine("...")
        log.msg("Sent keepalive to %s clients" % (len(self.clients),))
        reactor.callLater(300, self.keepalive)