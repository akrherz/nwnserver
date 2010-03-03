from twisted.application import service, internet
from twisted.internet import reactor, base
reactor.installResolver(base.BlockingResolver())

#from twisted.names import client
#reactor.installResolver(client.createResolver())

import basic

application = service.Application("NWN Server")
serviceCollection = service.IServiceCollection(application)

hubClientFactory = basic.ClientFactory()

hubClient = internet.TCPClient('mesonet', 14998, hubClientFactory)
hubClient.setServiceParent(serviceCollection)


