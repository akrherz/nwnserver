
from twisted.internet import reactor
from twisted.cred import checkers
from twisted.python import log

from nwnserver import client
from nwnserver import server

from pyIEM import mesonet
import re, mx.DateTime, string

_CURRENT_RE = "[A-Z] ([0-9][0-9][0-9])  ([0-2][0-9]:[0-9][0-9]) ([0-1][0-9]/[0-3][0-9]/[0-9][0-9]) (...) ([0-9][0-9])MPH ([0-9][0-9][0-9])K ...F (...)F ([0-9][0-9][0-9])% ([0-9][0-9].[0-9][0-9])([\"RFS]) ([0-9][0-9].[0-9][0-9])\"D ([0-9][0-9].[0-9][0-9])\"M"


class MyClientFactory(client.NWNClientProtocolFactory):
    """I create clients that hand their received data off to a server object"""
    
    def __init__(self, username, password, serverFactory, autoReconnect = 1):
        client.NWNClientProtocolFactory.__init__(self, username, password, autoReconnect)
        self.serverFactory = serverFactory
        
    def processData(self, line):
        # Override base method, send to all connected clients
        tokens = re.findall(_CURRENT_RE, line)
        if (len(tokens) == 0):
            return
        stationID = int(tokens[0][0])
        #if (not mesonet.snetConv.has_key(stationID)):
        #    return
        #nwsli = mesonet.snetConv[stationID]
        now  = mx.DateTime.now()
        drct = mesonet.txt2drct[string.strip(tokens[0][3])]
        sped = int(tokens[0][4])
        if (tokens[0][6][:2] == "0-"):
            tmpf = int(tokens[0][6][1:])
        else:
            tmpf = int(tokens[0][6])
        relh = int(tokens[0][7])
        alti = float(tokens[0][8])
        pDay = float(tokens[0][10])
# D,9xxx,02/12,23:42:24, 34, 94,29.80,112,  3, 19, 0.00, 6.66,  31,!005
        line = "D,%s,%s,%3s,%3s,%5s,%3s,%3s,  0,%5s, 9.99,%4s,!000" % \
  (now.strftime('%m/%d,%H:%M:%S'), 9000 + stationID, tmpf, relh, alti, drct, sped, \
   pDay, 0)
        self.serverFactory.sendToAllClients(line)
