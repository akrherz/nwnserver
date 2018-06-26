# This is it, all schoolnet processing under one roof!

""" 
This application does a lot of things.
1. Creates a server (nwn format) that clients can connect to...
2. Ingests data...
   a. Connects to Baron to get its data
   b. Watches for wx32 files from KELO (provided by LDM)
   c. Connects to IEM service for KIMT data
   d. Listens for TWI poller connections
3. Processes these observations, sending to the database
"""

from twisted.application import service, internet
from twisted.cred import checkers, portal
from twisted.enterprise import adbapi


# Hack around 2.0 problem
#from twisted.internet import reactor, base
#reactor.installResolver(base.BlockingResolver())

# Import nwnserver stuff!
from nwnserver import server, auth, hubclient, proxyserver
from nwnserver import pollerserv, filewatcher, archiver
from nwnserver.scripts import mainserver

# Create the Python Hub application
application = service.Application("PythonHub")
serviceCollection = service.IServiceCollection(application)

#_________________________________________________________________________
# 3. Archiver
dbpool = adbapi.ConnectionPool("psycopg2",  database="iem")
archiver = archiver.Archiver(dbpool)

#______________________________________________________________________
# 1. Setup hub server!
#  Accepts connects on port 14998
hubServerPasswdFile = './passwords.txt'
proxySiteListPath = './sitelist.csv'
hubServerPort = 14998

# set up Portal
hubServerPortal = portal.Portal(proxyserver.HubProxyRealm(proxySiteListPath))
hubServerPortal.registerChecker(checkers.FilePasswordDB(hubServerPasswdFile))

# Set up Hub server service
hubServerFactory = proxyserver.ProxyHubServerFactory(hubServerPortal,
                  proxyserver.IHubProxyClient, archiver)
hubServer = internet.TCPServer(hubServerPort, hubServerFactory)
hubServer.setServiceParent(serviceCollection)

#______________________________________________________________________
# 2a.  Connect to Baron to get their data
remoteServerIP = 'nwnhub.baronservices.com'
#remoteServerIP = '74.51.117.181'
remoteServerPort = 14996
remoteServerUser = 'darryl'
remoteServerPass = 'darryl'

hubClientFactory = hubclient.HubClientProtocolFactory(remoteServerUser,
                                                      remoteServerPass,
                                                      hubServerFactory)
hubClient = internet.TCPClient(remoteServerIP, 
                               remoteServerPort, 
                               hubClientFactory)
hubClient.setServiceParent(serviceCollection)


#______________________________________________________________________
# 2b.  Watches local wx32 files for changes...
wxpath = '/home/ldm/data/kelo/incoming/'
wxfilespec = 'nwn_%03i.txt'
wxids = [0, 1, 3, 4, 5, 6, 7, 8, 9, 11, 13, 15, 25,
         49] + list(range(500, 520)) + list(range(900, 950))
wx32 = filewatcher.WX32FileWatcher(wxpath, wxfilespec, wxids, hubServerFactory)


#______________________________________________________________________
# 2c.  Connect to iem for KIMT data
kimtServerIP = 'data2.stormnetlive.com'
kimtServerPort = 15002
kimtServerUser = 'kimtfeed'
kimtServerPass = 'kimtfeed'
kimtClientFactory = hubclient.HubClientProtocolFactory(kimtServerUser,
                                                        kimtServerPass,
                                                        hubServerFactory)
kimtClient = internet.TCPClient(kimtServerIP, kimtServerPort,
                                 kimtClientFactory)
kimtClient.setServiceParent(serviceCollection)

#______________________________________________________________________
# 2d.  Listen for TWI poller clients
pollerServerPasswdFile = './pollerpasswd.txt'
pollerServerConfigFile = './replacements.csv'
pollerServerPort = 27001
# set up Portal
pollerServerPortal = portal.Portal(pollerserv.PollerRealm(pollerServerConfigFile))
pollerServerPortal.registerChecker(checkers.FilePasswordDB(pollerServerPasswdFile))

# set up factory and listen
pollerServerFactory = pollerserv.PollerServerFactory(pollerServerPortal, hubServerFactory)
pollerServer = internet.TCPServer(pollerServerPort, pollerServerFactory)
pollerServer.setServiceParent(serviceCollection)


