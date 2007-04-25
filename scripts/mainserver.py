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

""" Neighborhood Weather Net class definitions needs for the main server."""

from twisted.internet import reactor
from twisted.cred import checkers
from twisted.python import log

from nwnserver import client
from nwnserver import server


class MyClientFactory(client.NWNClientProtocolFactory):
    """I create clients that hand their received data off to a server object"""
    
    def __init__(self, username, password, serverFactory, autoReconnect = 1):
        client.NWNClientProtocolFactory.__init__(self, username, password, autoReconnect)
        self.serverFactory = serverFactory
        
    def processData(self, line):
        # Override base method, send to all connected clients
        self.serverFactory.sendToAllClients(line)
