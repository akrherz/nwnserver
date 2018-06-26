# Neighborhood Weather Net Hub
# Copyright (C) 2003-2004 Iowa State University
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

""" Neighborhood Weather Net Hub client implementation
"""
from twisted.internet import protocol
from twisted.protocols import policies, basic
from twisted.python import log

from nwnserver import common

class HubClientProtocol(basic.LineReceiver, policies.TimeoutMixin):
    delimiter = b"\r\n"
    # If haven't received data for a minute, reconnect
    timeOut = 60
    
    def __init__(self):
        self.buffer = ""
        
        # Raw mode until authenticated
        self.setRawMode()

    def connectionMade(self):
        self.ip = self.transport.getPeer().host
        self.setTimeout(self.timeOut)

        log.msg("Connection made to: %s" % self.ip)

    def connectionLost(self, reason):
        self.setTimeout(None)

        log.msg("Connection logged out from server: %s" % self.ip)

    def timeoutConnection(self):
        policies.TimeoutMixin.timeoutConnection(self)

        log.msg("Connection timed out to: %s" % self.ip)

        
    def rawDataReceived(self, data):
        self.resetTimeout()
        self.buffer += data.decode('utf-8', 'ignore')
        promptEndingLocation = self.buffer.find(common.promptEnding)
        successMsgLocation = self.buffer.find(common.successMessage)
        
        if promptEndingLocation > 0:
            if self.buffer[promptEndingLocation - common.loginPromptLen + common.promptEndingLen:
                           promptEndingLocation + common.promptEndingLen] == common.loginPrompt:
                self.transport.write(self.factory.username.encode('utf-8') + self.delimiter)
                self.buffer = self.buffer[promptEndingLocation + common.promptEndingLen:]
                
            elif self.buffer[promptEndingLocation - common.passwordPromptLen + common.promptEndingLen:
                             promptEndingLocation + common.promptEndingLen] == common.passwordPrompt:
                self.transport.write(self.factory.password.encode('utf-8') + self.delimiter)
                self.buffer = self.buffer[promptEndingLocation + common.promptEndingLen:]

        elif successMsgLocation >= 0:
             self.setLineMode((self.buffer[successMsgLocation + common.successMessageLen:]).encode('utf-8'))
             self.buffer = ""
            
    def lineReceived(self, line):
        self.resetTimeout()
        # Only called after client authenticates
        # send back str instead of bytes
        self.factory.processData(line.decode('utf-8', 'ignore'))


class HubClientProtocolBaseFactory(protocol.ReconnectingClientFactory):
    protocol = HubClientProtocol
    maxDelay = 60

    def __init__(self, username, password, autoReconnect=1):
        self.username = username
        self.password = password
        self.continueTrying = autoReconnect
        
    def processData(self, data):
        """ Do something with the data the client received.  Override to
        do more than the default print.
        """
        data = data.strip()

        if data != "":
            print(data)

class HubClientProtocolFactory(HubClientProtocolBaseFactory):
    """I create clients that hand their received data off to a hub object"""
    
    def __init__(self, username, password, hubFactory, autoReconnect = 1):
        HubClientProtocolBaseFactory.__init__(self, username, password, autoReconnect)
        self.hubFactory = hubFactory
        
    def processData(self, line):
        # Override base method, send to all connected clients

        line = line.strip()
        
        # Baron server sends "..." or something similar, ignore it
        if line != "" and line[0] != '.':
                self.hubFactory.sendToAllClients(line)
        del line
