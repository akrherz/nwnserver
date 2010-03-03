from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor
from twisted.protocols import policies, basic

import mx.DateTime, os, pickle, csv
from pyIEM import mesonet

# Load datastore from file, if possible
sites = {}
config = csv.DictReader( open('sites.txt') )
for row in config:
    sites[ int(row['id']) ] = row
    ld = row['lastd'][:10]
    sites[ int(row['id']) ]['lastd'] = mx.DateTime.strptime(ld, "%Y-%m-%d")
    lm = row['lastm'][:10]
    sites[ int(row['id']) ]['lastm'] = mx.DateTime.strptime(lm, "%Y-%m-%d")

def save_sites():
    print 'Saving sites.txt'
    w = csv.DictWriter( open('sites.txt','w'), config.fieldnames)
    w.writerow(dict(zip(config.fieldnames, config.fieldnames)))
    for key in sites.keys():
        w.writerow( sites[key] )

    del(w)

reactor.callLater(15*60, save_sites)

class ReceiverProtocol(basic.LineReceiver):
    def __init__(self):
        self.ip = None
        self.id = None
        self.lastm = None
        self.lastd = None
        self.counter = 0
        self.year = None
        self.last = mx.DateTime.now()
        self.ob = {
          'tmpf': None, 'relh': None, 'sped': None, 'drct': None, 'alti': None,
          'pday': None, 'pmonth': None,
        }

    def writeln(self,s):
        print "SEND[%s] (%s)" % (self.id, s)
        self.transport.write("%s\r\n" % (s,) )

    def set_clock(self):
        self.cmdStopAuto()
        #self.cmdStopAuto()
        # Lets set the clock
        tzoff = int( sites[self.id]['tzoff'] )
        now = mx.DateTime.now() + mx.DateTime.RelativeDateTime(hours=tzoff) + mx.DateTime.RelativeDateTime(seconds=6)
        currentTime = now.strftime("%m%d%H%M%S")
        print "set_clock() id=%s currentTime=%s" % (self.id, currentTime)
        reactor.callLater(6, self.writeln, ":K%s" % (currentTime,) )
        reactor.callLater(10, self.cmdStartAuto)

    def cmdZeroMonthRainfall(self):
        self.writeln(":S")

    def cmdZeroYearRainfall(self):
        self.writeln(":T")

    def cmdZeroPeakWind(self):
        self.writeln(":W")

    def cmdSetBarometer(self, val):
        self.writeln(":B%s" % (val,) )

    def cmdStopAuto(self):
        self.writeln(":")

    def cmdStartAuto(self):
        self.writeln(":A")

    def sendMax(self):
        #self.cmdStopAuto()
        self.writeln(":M")

    def sendRain(self):
        #self.cmdStopAuto()
        self.writeln(":R")


    def lineReceived(self, data):
        """As soon as any data is received, write it back."""
        #log.flush()
        print "|||"+data +"|||"
        if (len(data) < 3):
            print 'TRUNCATED', data
            return
        if (data[0] == "D"):
            tokens = data.split(",")
            if not self.id:
               self.id = int(tokens[3])
               self.lastm = sites[self.id]['lastm']
               self.lastd = sites[self.id]['lastd']
               self.year = self.lastm.year
               self.set_clock()
               return
            if ( len(tokens) != 14):
               return
            self.ob['tmpf'] = int( tokens[4] )
            self.ob['relh'] = int( tokens[5] )
            self.ob['alti'] = float( tokens[6] )
            self.ob['drct'] = int( tokens[7] )
            self.ob['sped'] = int( tokens[8] )

            self.last = mx.DateTime.strptime("%s %s %s" % \
                  (self.year, tokens[1], tokens[2]), "%Y %m/%d %H:%M:%S")
            # if new day, reset stuff 
            if (self.last.day != self.lastd.day):
               print "Daily reset %s" % (self.id,)
               self.cmdZeroPeakWind()
               reactor.callLater(10, self.cmdStartAuto)

               # Check to see if its a new year?
               if (self.lastm.month - self.last.month > 0):
                   self.last += mx.DateTime.RelativeDateTime(years=1)

               # Also check for new month
               if (self.last.month != self.lastm.month):
                   print "Monthly reset %s" % (self.id,)
                   self.cmdZeroMonthRainfall()
                   reactor.callLater(10, self.cmdStartAuto)
                   self.lastm = self.last
                   sites[self.id]['lastm'] = self.lastm
               # Also check for new year
               if (self.last.year != self.lastd.year):
                   print "Yearly reset %s" % (self.id,)
                   self.cmdZeroYearRainfall()
                   reactor.callLater(10, self.cmdStartAuto)
               self.lastd = self.last
               sites[self.id]['lastd'] = self.lastd
               return

            self.factory.processData( data )
            self.counter += 1
            if (self.counter > 30*5):  # Every 5 minutes
               self.sendMax()
               self.counter = 0
            return
        data = data.replace(">","")
        if data == "OK":
            return
        if (data[0] == "M"):
            self.factory.processData( data )
            self.sendRain()
        if (data[0] == "R"):
            self.factory.processData( data )
            self.cmdStartAuto()

    def serviceGuard(self):
        print "Checking Connection Status"
        if int(mx.DateTime.now() - self.last) > 120:
            print "Closing connection..."
            self.transport.loseConnection()
            return
        reactor.callLater(180, self.serviceGuard)

    def connectionMade(self):
        self.ip = self.transport.getPeer().host
        #log.write("Connection made from: %s\n" % self.ip)
        self.cmdStartAuto()

        reactor.callLater(60, self.serviceGuard)
        #reactor.callLater(11, self.sendRain)
        #self.__state == self.SUCCESS

class ReceiverFactory(Factory):
    protocol = ReceiverProtocol

    def __init__(self, nwn_serverfactory, rw_serverfactory):
        self.rw_serverfactory = rw_serverfactory
        self.nwn_serverfactory = nwn_serverfactory
        self.pmonth = {}
        self.pday = {}
        self.loadPmonth()

    def loadPmonth(self):
        o = open('kimt_pmonth.txt', 'r').readlines()
        for line in o:
            tokens = line.split(",")
            self.pmonth[ int(tokens[0]) ] = float(tokens[1])
            self.pday[ int(tokens[0]) ] = float(tokens[2])
       

    def writePmonth(self):
        o = open('kimt_pmonth.txt', 'w')
        now = mx.DateTime.now()
        for key in self.pmonth.keys():
            if (now.day == 1): # Reset for first....
                self.pmonth[key] = 0
            o.write("%s,%s,%s\n" % (key, self.pmonth[key], self.pday[key]) )
        o.close()

    def processData(self, data):
        # Send the RW formated data to the RW clients
        self.rw_serverfactory.sendToAllClients(data)


    def bogus(self, data):
        tokens = data.split(",")
        if (len(tokens) == 14):
            drctTxt = mesonet.drct2dirTxt( tokens[7] )
            pday = float(tokens[10])
            nwnid = 600 + int(tokens[3])
            if (not self.pday.has_key(nwnid)):
                self.pday[nwnid] = 0
                self.pmonth[nwnid] = 0
            # If pday has reset
            if (pday < self.pday[nwnid]):
                print "PDay reset %s, old pmonth %s, old pday %s, new pmonth %s, new pday %s" \
   % (nwnid, self.pmonth[nwnid], self.pday[nwnid], \
      self.pmonth[nwnid] + self.pday[nwnid], pday)
                self.pmonth[nwnid] += self.pday[nwnid]
                self.pday[nwnid] = pday
                self.writePmonth()
            self.pday[nwnid] = pday
                      
            ts = mx.DateTime.strptime("%s %s" % (tokens[1], tokens[2]), "%m/%d %H:%M:%S")
            nstr = "%s %03i  %5s %6s%02i %-3s %02iMPH %03iK %03iF %03iF %03i%s %05.2f%s %05.2f\"D %05.2f\"M %05.2f\"R\015\012" % ("A", nwnid, ts.strftime("%H:%M"), \
        ts.strftime("%m/%d/"), mx.DateTime.now().year - 2000, drctTxt, int(tokens[8]), 0, \
        460, int(tokens[4]), int(tokens[5]), "%", float(tokens[6]), '"', \
        pday, self.pmonth[nwnid] + pday, 0)
            # Send the NWN formated data to the NWN clients
            self.nwn_serverfactory.sendToAllClients(nstr)
