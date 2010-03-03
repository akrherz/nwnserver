from nwnserver import client
from twisted.internet import reactor

def run(argv):
    if len(argv) > 4:
        print "Connecting to %s:%s" % (argv[1], argv[2])
        reactor.connectTCP(argv[1], int(argv[2]), client.NWNClientProtocolFactory(argv[3], argv[4], 0))
    else:
        print "Connecting to canonical server"
        reactor.connectTCP('12.158.180.10', 14996, client.NWNClientProtocolFactory(argv[1], argv[2], 0))

    reactor.run()
