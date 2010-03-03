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

""" NWN Hub Proxy server service """

from twisted.cred import credentials, portal
#from twisted.python.components import Interface
from zope.interface import Interface, implements
from twisted.internet import reactor
from twisted.python import log


class IHubProxyClient(Interface):

    def updateConfig(self, sites):
        """ Update the sites wanted configuration for this station """

    def logout(self):
        """ Clean up resources for this avatar """

    def wantThisLine(self, line):
        """ Do I want this line """
        

class HubProxyClient:
    implements(IHubProxyClient)
    
    def __init__(self, realm, station):
        self.sites = []
        self.station = station
        
    def updateConfig(self, sites):
        self.sites = sites
        
    def logout(self):
        self.realm.removeHubProxy(self.station)

        log.msg("Station %s logging out" % self.station)

    def wantThisLine(self, line):
        site = int(line[2:5])

        if site in self.sites:
            return True
        else:
            return False


from nwnserver import filewatcher

class HubProxyRealm:
    __implements__ = portal.IRealm

    def __init__(self, siteListPath, reloadInterval=60):
        self.avatars = {}
        self.siteListConfig = {}

        self.fileWatcher = filewatcher.ConfigFileWatcher([siteListPath],
                                                         self, reloadInterval)


    def updateConfig(self, configLines):
        # Recreate the config from scratch
        self.siteListConfig = {}
        
        for line in [line.strip() for line in configLines]:
            if line != "" and line[0] != '#':
                data = line.split(",")

                site = data[0]

                for station in data[1:]:
                    self.siteListConfig.setdefault(station.upper(), []).append(int(site))

        # Send updated configuration to all stations
        self.updateStationConfigs()

    def updateStationConfigs(self):
        for station, sites in self.siteListConfig.iteritems():
            if station in self.avatars:
                self.avatars[station].updateConfig(sites)

    def removeHubProxy(self, station):
        self.avatars.pop(station)
        
    def requestAvatar(self, avatarId, mind, *interfaces):
        if IHubProxyClient in interfaces:
            station = avatarId[:4].upper()
            
            proxyClient = HubProxyClient(self, station)
            self.avatars[station] = proxyClient

            self.updateStationConfigs()

            log.msg("Client %s connected" % str(proxyClient))
            return IHubProxyClient, proxyClient, proxyClient.logout



from nwnserver import hubserver

class ProxyHubServer(hubserver.HubServer):
    def wantThisLine(self, line):
        return self.avatar.wantThisLine(line)

class ProxyHubServerFactory(hubserver.HubServerFactory):
    protocol = ProxyHubServer

    def sendToAllClients(self, line):
        line = line.strip()

        if line != "":
            for client in self.clients:
                if client.wantThisLine(line) == True:
                    client.sendLine(line)
