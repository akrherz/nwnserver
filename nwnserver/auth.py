# Neighborhood Weather Net
# Copyright (C) 2003 Iowa State University
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

"""Basic Neighborhood Weather Net cred authentication support."""

from twisted.cred import credentials, portal
#from twisted.python.components import Interface
from zope.interface import Interface, implements

class IDummy(Interface):
    """I am a dummy interface for the cred Mind to attach to."""
    pass


class NWNRealm:
    """I am a dummy realm for cred.  All I need to do is know whether or
    not the user authenticated and continue to use the protocol object."""
    #__implements__ = (portal.IRealm,)
    implements(portal.IRealm)

    def requestAvatar(self, avatarId, mind, *interfaces):
        pass

