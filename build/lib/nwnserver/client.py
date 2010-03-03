# -*- test-case-name: nwnserver.test.test_client -*-

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

""" Neighborhood Weather Net client implementation
"""
from twisted.internet import protocol
from twisted.protocols import policies, basic
from twisted.python import log

from nwnserver import common

class NWNClientProtocol(basic.LineReceiver, policies.TimeoutMixin):
    delimiter = "\r\n"
    # If haven't received data for a minute, reconnect
    timeOut = 60
    
    def __init__(self):
        self.buffer = ""
        
        # Raw mode until authenticated
        self.setRawMode()

    def connectionMade(self):
        self.setTimeout(self.timeOut)

    def connectionLost(self, reason):
        self.setTimeout(None)

    def timeoutConnection(self):
        log.msg("Timing out...")
        policies.TimeoutMixin.timeoutConnection(self)
        
    def rawDataReceived(self, data):
        self.resetTimeout()
        self.buffer += data

        promptEndingLocation = self.buffer.find(common.promptEnding)
        successMsgLocation = self.buffer.find(common.successMessage)
        
        if  promptEndingLocation > 0:
            if self.buffer[promptEndingLocation - common.loginPromptLen + common.promptEndingLen:
                           promptEndingLocation + common.promptEndingLen] == common.loginPrompt:
                self.transport.write(self.factory.username + self.delimiter)
                self.buffer = self.buffer[promptEndingLocation + common.promptEndingLen:]
                
            elif self.buffer[promptEndingLocation - common.passwordPromptLen + common.promptEndingLen:
                             promptEndingLocation + common.promptEndingLen] == common.passwordPrompt:
                self.transport.write(self.factory.password + self.delimiter)
                self.buffer = self.buffer[promptEndingLocation + common.promptEndingLen:]

        elif successMsgLocation >= 0:
             self.setLineMode(self.buffer[successMsgLocation + common.successMessageLen:])
             self.buffer = ""
            
    def lineReceived(self, line):
        self.resetTimeout()
        # Only called after client authenticates
        self.factory.processData(line)


class NWNClientProtocolFactory(protocol.ReconnectingClientFactory):
    protocol = NWNClientProtocol
    maxDelay = 60.0
    factor = 1.0
    initialDelay = 60.0

    def __init__(self, username, password, autoReconnect = 1):
        self.username = username
        self.password = password
        self.continueTrying = autoReconnect
    
    def buildProtocol(self, addr):
        self.resetDelay()
        return protocol.ReconnectingClientFactory.buildProtocol(self, addr)

    def processData(self, data):
        """ Do something with the data the client received.  Override to
        do more than the default print.
        """
        data = data.strip()

        if data != "":
            print data
