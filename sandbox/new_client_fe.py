# 
from twisted.application import service, internet
from twisted.cred import checkers, portal

from nwnserver import server, auth
from nwnserver.scripts import rainwise
from nwnserver import filewatcher

import receiver

application = service.Application("KIMT NWN Server")
serviceCollection = service.IServiceCollection(application)

userPassFile = "./passwords.txt"
myPortal = portal.Portal(auth.NWNRealm())
myPortal.registerChecker(checkers.FilePasswordDB(userPassFile))

nwn_factory = server.NWNServerFactory(myPortal)
rw_factory = server.NWNServerFactory(myPortal)

r = receiver.ReceiverFactory(nwn_factory, rw_factory)
receiverPort = 15000

d = internet.TCPServer(receiverPort, r)
d.setServiceParent(serviceCollection)
