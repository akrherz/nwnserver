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

"""
Neighborhood Weather Net Hub local file data source and monitor
"""

import os, sys
import stat, traceback

from twisted.internet import reactor
from twisted.python import log

class FileWatcher:
    """ I am a generic class that watches a list of files and performs a given
    operation when one of them has changed.

    @ivar filenames: A list of filenames, with full paths, to watch
    @ivar delay: Delay between checking for file changes, in seconds.
    """
    
    def __init__(self, filenames, delay=60):
        self.filenames = filenames
        self.timestamps = {}
        self.delay = delay

        # Load data for first time
        self.loadFilesInitially()
        reactor.callLater(self.delay, self.checkFiles)

    def loadFilesInitially(self):
        self.timestamps = self.getTimeStamps()
        
        for myfile in self.filenames:
            self.processFile(myfile)
            
    def getTimeStamps(self):
        timestamps = {}
        
        for myfile in self.filenames:
            try:
                timestamps[myfile] = os.stat(myfile)[stat.ST_MTIME]
            except OSError:
                timestamps[myfile] = ''

        return timestamps


    def checkFiles(self):
        newtimes = self.getTimeStamps()
        
        for myfile in self.filenames:
            if newtimes[myfile] != self.timestamps[myfile]:
                self.processFile(myfile)
                self.timestamps[myfile] = newtimes[myfile]

        reactor.callLater(self.delay, self.checkFiles)


    def processFile(self, filename):
        """Override me to perform a more appropriate operation on the
        changed file.
        """
        lines = open(filename).readlines()

        log.msg("%s has changed!" % filename)
        for line in lines:
            log.msg(line)


from pyIEM import nwnformat
import ConfigParser

class WX32FileWatcher(FileWatcher):
    def __init__(self, path, filespec, ids,
                 serverfactory, delay = 60):
        self.ids = ids
        self.serverfactory = serverfactory
        self.filespec = filespec
        self.pMonthDict = {}
        self.pDayDict = {}
        self.monthDict = {}
        for sid in self.ids:
            self.pDayDict[sid] = 0
            self.pMonthDict[sid] = 0
            self.monthDict[sid] = 0
        self.readPMonth()
       
        if path[-1:] != os.sep:
            path += os.sep
        
        self.filedict = dict([(path + self.filespec % sid, sid) for sid in self.ids])    
        FileWatcher.__init__(self,  [path + self.filespec % sid for sid in self.ids], delay)

    def writePMonth(self):
        out = open("pmonth.log", 'w')
        for sid in self.ids:
            out.write("%s,%s,%s\n" % (sid, self.monthDict[sid], 
                                      self.pMonthDict[sid]) )
        out.close()

    def readPMonth(self):
        import re, string
        lines = open('pmonth.log', 'r').readlines()
        for line in lines:
            tokens = re.split(",", line)
            sid = int(tokens[0])
            self.monthDict[sid] = int(string.strip(tokens[1]) )
            self.pMonthDict[sid] = float(tokens[2])

    def processFile(self, filename):
        id = self.filedict[filename]
        n = nwnformat.nwnformat()
        cf = ConfigParser.ConfigParser()
        
        try:
          cf.read(filename)
        except:
          traceback.print_exc(file=sys.stdout)
          pass

        if (len(cf.sections()) != 3):
          log.msg("%s %s %d" % (id, 'Short read', len(cf.sections())))
          return
        try:
          n.sid = id
          n.setTS( cf.get("Current Values", "Time") )
          n.parseWind( cf.get("Current Values", "Wind") )
          n.setRad( cf.get("Current Values", "Solar") )
          p = cf.get("Current Values", "Temperature")
          if (p != "Missing"):
            n.tmpf = int(float(p))
          p = cf.get("Current Values", "Humidity")
          if (p != "Missing"):
            n.humid = int(float(p))
          p = cf.get("Current Values", "Pressure")
          if (p != "Missing"):
            n.pres = float(p)
          n.presTend = "R"

          """ Ugly precip logic, have to do something tho.... 

          """
          # Get value from the datafile
          n.parsePDay( cf.get("Current Values", "RainForDay") )
          pDay = n.pDay
          lastPDay = self.pDayDict[id]
          yyyymm = int( n.ts.strftime("%Y%m") )
          lastYYYYMM = self.monthDict[id]
          if (lastYYYYMM < yyyymm):   # Reset month dict to zero
            self.pMonthDict[id] = 0   #
            self.monthDict[id] = yyyymm
            self.writePMonth()
          # pDay is smaller, then we should add to month dict
          if (pDay < lastPDay):
            self.pMonthDict[id] += lastPDay
            self.writePMonth()

          pMonth = self.pMonthDict[id] + pDay
          self.pDayDict[id] = pDay

          #n.parsePDay( cf.get("Current Values", "RainForDay") )
          n.setPMonth(pMonth)


          p = cf.get("High Values", "HighTemperature")
          if (p != "Missing"):
            n.xtmpf = int(float(p))
          p = cf.get("Low Values", "LowTemperature")
          if (p != "Missing"):
            n.ntmpf = int(float(p))
          p = cf.get("High Values", "HighWind")
          if (p != "Missing"):
            n.xsped = int(float(p))
          n.sanityCheck()
        except:
          n.error = 1000
          traceback.print_exc(file=sys.stdout)
          pass

        if (n.error > 0):
            print "ERROR %s IS %s" % (id, n.error)
        if n.error == 0:
            self.sendData(n.currentLine())
            reactor.callLater(1, self.sendData, n.maxLine())
            reactor.callLater(2, self.sendData, n.minLine())

    def sendData(self, str):
        self.serverfactory.sendToAllClients(str)


class NWNFileWatcher(FileWatcher):
    def __init__(self, path, filespec, ids,
                 serverfactory, delay = 60):
        self.ids = ids
        self.serverfactory = serverfactory
        self.filespec = filespec
        
        if path[-1:] != os.sep:
            path += os.sep
        
        self.filedict = dict([(path + self.filespec % id, id) for id in self.ids])    
        FileWatcher.__init__(self,  [path + self.filespec % id for id in self.ids], delay)

    def maintainConnections(self):
        self.serverfactory.sendToAllClients("...")
        reactor.callLater(30, self.maintainConnections)

    def processFile(self, filename):
	id = self.filedict[filename]
        lines = None
        try:
          lines = open(filename, 'r').readlines()
        except:
          pass
        if (lines != None and len(lines) == 3):
          reactor.callLater(0.2, self.sendFileData, lines)

    def sendData(self, str):
        self.serverfactory.sendToAllClients(str)

    def sendFileData(self, lines):
        self.sendData(lines[0])
        reactor.callLater(1, self.sendData, lines[1])
        reactor.callLater(2, self.sendData, lines[2])



class ConfigFileWatcher(FileWatcher):
    def __init__(self, filenames, realm, delay=60):
        self.realm = realm

        FileWatcher.__init__(self, filenames, delay)
        
    def processFile(self, filename):
        self.realm.updateConfig(open(filename).readlines())
