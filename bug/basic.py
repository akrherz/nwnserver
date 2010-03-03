
from twisted.internet import protocol
from twisted.protocols import basic

class PrintProtocol(basic.LineReceiver):

    def connectionMade(self):
        self.factory.resetDelay()

    def lineReceived(self, line):
        print line

class ClientFactory(protocol.ReconnectingClientFactory):
    protocol = PrintProtocol

    def bogus(self):
        print "Bogus!"
