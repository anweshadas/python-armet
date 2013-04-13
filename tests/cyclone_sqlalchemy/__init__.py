# -*- coding: utf-8 -*-
from __future__ import print_function, division, unicode_literals
import sys
from .app import application
from ..utils import sqlalchemy


def setup():
    # Initialize the database access layer
    sqlalchemy.initialize()

    # Start the reactor and run the development server
    # Twistedtools spins off the reactor loop into a separate thread
    # so the tests may continue on this thread.
    from nose import twistedtools
    twistedtools.reactor.listenTCP(5000, application, interface='localhost')
    twistedtools.threaded_reactor()


def teardown():
    # Shutdown the reactor thread.
    from nose import twistedtools
    twistedtools.stop_reactor()