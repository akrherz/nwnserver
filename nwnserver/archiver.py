# I am the archiving component of the server megaplex :)

from pyIEM import mesonet
from twisted.internet.task import LoopingCall
import re, math

CURRENT_RE = re.compile(r"""
         [A-Z]\s+
         [0-9]{3}\s+
         (?P<hour>[0-2][0-9]):(?P<minute>[0-5][0-9])\s+
         (?P<month>[0-1][0-9])/(?P<day>[0-3][0-9])/(?P<year>[0-9][0-9])\s+
         (?P<drctTxt>[A-Z]{1,3})\s+
         (?P<sped>[0-9]+)MPH\s+
         (?P<srad>[0-9]+)[KF]\s+
         (?P<inside>[0-9]+)F\s+
         (?P<tmpf>[\-0-9]+)F\s+
         (?P<relh>[0-9]+)%\s+
         (?P<pres>[0-9]+\.[0-9]+)(?P<presTend>[RSF"])\s+
         (?P<pDay>[0-9]+\.[0-9]+)"D\s+
         (?P<pMonth>[0-9]+\.[0-9]+)"M\s+
         (?P<pRate>[0-9]+\.[0-9]+)"R
         """, 
         re.VERBOSE)

MAX_RE = re.compile(r"""
         [A-Z]\s+
         [0-9]{3}\s+
         Max\s+
         (?P<month>[0-1][0-9])/(?P<day>[0-3][0-9])/(?P<year>[0-9][0-9])\s+
         (?P<maxDrctTxt>[A-Z]{1,3})\s+
         (?P<maxSped>[0-9]+)MPH\s+
         (?P<maxSrad>[0-9]+)[KF]\s+
         (?P<maxInside>[0-9]+)F\s+
         (?P<maxTmpf>[\-0-9]+)F\s+
         (?P<maxRelh>[0-9]+)%\s+
         (?P<maxPres>[0-9]+\.[0-9]+)(?P<presTend>[RSF"])\s+
         (?P<pDay>[0-9]+\.[0-9]+)"D\s+
         (?P<pMonth>[0-9]+\.[0-9]+)"M\s+
         (?P<pRate>[0-9]+\.[0-9]+)"R
         """, 
         re.VERBOSE)

MIN_RE = re.compile(r"""
         [A-Z]\s+
         [0-9]{3}\s+
         Min\s+
         (?P<month>[0-1][0-9])/(?P<day>[0-3][0-9])/(?P<year>[0-9][0-9])\s+
         (?P<minDrctTxt>[A-Z]{1,3})\s+
         (?P<minSped>[0-9]+)MPH\s+
         (?P<minSrad>[0-9]+)[KF]\s+
         (?P<minInside>[0-9]+)F\s+
         (?P<minTmpf>[\-0-9]+)F\s+
         (?P<minRelh>[0-9]+)%\s+
         (?P<minPres>[0-9]+\.[0-9]+)(?P<presTend>[RSF"])\s+
         (?P<pDay>[0-9]+\.[0-9]+)"D\s+
         (?P<pMonth>[0-9]+\.[0-9]+)"M\s+
         (?P<pRate>[0-9]+\.[0-9]+)"R
         """, 
         re.VERBOSE)

def uv(sped, drct2):
  dirr = drct2 * math.pi / 180.00
  s = math.sin(dirr)
  c = math.cos(dirr)
  u = round(- sped * s, 2)
  v = round(- sped * c, 2)
  return u, v


def dir(u,v):
  if (v == 0):
    v = 0.000000001
  dd = math.atan(u / v)
  ddir = (dd * 180.00) / math.pi

  if (u > 0 and v > 0 ): # First Quad
    ddir = 180 + ddir
  elif (u > 0 and v < 0 ): # Second Quad
    ddir = 360 + ddir
  elif (u < 0 and v < 0 ): # Third Quad
    ddir = ddir
  elif (u < 0 and v > 0 ): # Fourth Quad
    ddir = 180 + ddir

  return int(math.fabs(ddir))


class CurrentOb:
    """
H 170  09:00 03/30/09 WSW 11MPH 000K 460F 041F 061% 29.74S 00.00"D 03.04"M 00.00
"R
M 124  09:53 03/30/09 SE  07KTS 031K 460F 043F 062% 29.85F 00.00"D 03.48"M 00.00"R
    """
    def __init__(self, line):
        m = CURRENT_RE.match( line )
        if m is not None:
            self.ob = m.groupdict()
        else:
            print "Current Parser Fail", line
            self.ob = None

class MaxOb:
    """
G 170   Max  03/30/09 WSW 17MPH 000K 460F 041F 075% 29.83" 00.00"D 03.04"M 00.00"R
    """

    def __init__(self, line):
        m = MAX_RE.match( line )
        if m is not None:
            self.ob = m.groupdict()
        else:
            print "Max Parser Fail", line
            self.ob = None

class MinOb:
    """
F 170   Min  03/30/09 SW  00MPH 000K 460F 036F 061% 29.73" 00.00"D 03.04"M 00.00
"R
    """

    def __init__(self, line):
        m = MIN_RE.match( line )
        if m is not None:
            self.ob = m.groupdict()
        else:
            print "Min Parser Fail", line
            self.ob = None

class SiteData:
    """
    Something to store the necessary data
    """
 
    def __init__(self, id):
        """
        Constructor
        @param id numeric site identifier
        """
        self.id = id
        self.current_obs = []
        self.max_ob = None
        self.min_ob = None

    def parse_line(self, line):
        """
        Parse a line in NWN format
        @param line string line to parse
        """
        tokens = line.split()
        if tokens[2] == "Max":
            self.max_ob = MaxOb(line) 
        elif tokens[2] == "Min":
            self.min_ob = MinOb(line)
        else:
            self.current_obs.append( CurrentOb(line) )

    def average_winds(self):
        """
        Compute the wind speed and direction based on a series of 
        observations
        """
        if len(self.current_obs) == 0:
            return None, None
        asped = []
        ucmp = 0
        vcmp = 0
        for ob in self.current_obs:
            if ob is None:
                continue
            asped.append( float(ob.sped) )
            drct = mesonet.txt2drct[ ob.drctTxt ]
            u, v = uv( float(ob.sped), drct)
            ucmp += u
            vcmp += v
        if len(asped) == 0:
            return None, None
        uavg = ucmp / len(asped)
        vavg = vcmp / len(asped)
        drct = dir(uavg, vavg)
        sped = sum(asped) / len(asped)
        return sped, drct

class Archiver:
    """
    Methodology to do the necessary processing of the data and migration
    to storage
    """

    def __init__(self, dbpool):
        """
        Constructor
        @param dbpool Database pool to do stuff with
        """
        self.dbpool = dbpool
        self.memory = {}

        lc = LoopingCall(self.looper)
        lc.start(60)

    def looper(self):
        """
        Logic for persisting off the datasets we love and care for
        """
        print "Length of memory is ", len( self.memory.keys() )
        for id in self.memory.keys():
            s, d = self.memory[id].average_winds()
            self.memory[id].current_obs = []


    def sendLine(self, line):
        """
        Process a NWN formatted line
        """
        if len(line) < 40:
            return
        id = int( line[2:5] )
        if not self.memory.has_key(id):
            self.memory[ id ] = SiteData(id)
        self.memory[ id ].parse_line( line.strip() )
