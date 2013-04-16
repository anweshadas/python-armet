# -*- coding: utf-8 -*-
from __future__ import print_function, unicode_literals, division
from __future__ import absolute_import
from flask import Flask
from ..sqlalchemy import models
import armet
from armet import resources
from armet.resources import attributes


# Instantiate the flask application.
application = Flask(__name__)


class Meta:
    connectors = {
        'http': 'flask',
        'model': 'sqlalchemy'
    }


@armet.route('/api/', application)
class SimpleResource(resources.ManagedResource):

    class Meta(Meta):
        pass

    def read(self):
        return None


@armet.route('/api/', application)
class PollResource(resources.ModelResource):

    class Meta(Meta):
        model = models.Poll
        engine = models.engine

    id = attributes.Attribute('id')
    question = attributes.Attribute('question')


@armet.route('/api/', application)
class HttpWholeForbiddenResource(resources.ManagedResource):

    class Meta(Meta):
        http_allowed_methods = ('GET', 'DELETE',)


@armet.route('/api/', application)
class HttpForbiddenResource(resources.ManagedResource):

    class Meta(Meta):
        http_list_allowed_methods = ('DELETE',)
        http_detail_allowed_methods = ('GET',)


@armet.route('/api/', application)
class WholeForbiddenResource(resources.ManagedResource):

    class Meta(Meta):
        allowed_operations = ('read', 'destroy',)


@armet.route('/api/', application)
class ForbiddenResource(resources.ManagedResource):

    class Meta(Meta):
        list_allowed_operations = ('destroy',)
        detail_allowed_operations = ('read',)
