# -*- coding: utf-8 -*-
"""Implements the RESTful resource protocol for django ORM-backed models.
"""
from __future__ import print_function, unicode_literals
from __future__ import absolute_import, division
import six
from . import base
from .. import exceptions, authorization


class BaseModel(base.BaseResource):

    #! The model this resource is bound to; shortcut for declaring a form
    #! for read-only resources.
    model = None

    #! Declares a resource to be the primary provider of the associated model.
    #! There cannot be two resources linked to the same model with
    #! `canonical = True`.
    canonical = True

    #! Class object cache of what is to be prefetched.
    _prefetch_related_paths = {}

    # Authorization.  See base class for more information
    authorization = authorization.Model({
        "create": ("add",),
        "update": ("change",),
        "delete": ("delete",),
        "read":   ("read",)
    })

    def authorize_queryset(self, queryset, operation):
        return self.authorization.filter(self.request, operation, queryset)

    @classmethod
    def _build_prefetch_related_paths(cls, queryset, prefix=None, skip=None):
        # Initialize the store
        prefetched = []

        # Get sorted list of visibile path elements
        field_paths = []
        for field in six.itervalues(cls._fields):
            if field.visible:
                field_paths.append(field.path)

        field_paths.sort(reverse=True)

        # Cache of what to prefetch has not been built; build it.
        # First iterate and store all field names
        for field_path in field_paths:
            if field_path is None:
                # No field path; nothing to check.
                continue

            for index in range(len(field_path), 0, -1):
                try:
                    # Attempt to prefetch
                    path = '__'.join(field_path[:index])
                    if prefix:
                        path = '{}__{}'.format(prefix, path)

                    queryset.prefetch_related(path)[0]

                except (ValueError, AttributeError):
                    # Not able to prefetch; move along
                    pass

                else:
                    # Worked somehow; store it and get out
                    prefetched.append(path)
                    break

        if skip is None:
            # Initialize skip list if we need to.
            skip = []

        for name, field in six.iteritems(cls._fields):
            relation = field.relation
            if relation and issubclass(relation.resource, BaseModel):
                # Do we need to skip this?
                if relation in skip:
                    continue

                # Nope; add to skip list
                skip.append(relation)

                # Attempt to apply a test prefetch related
                paths = relation.resource._build_prefetch_related_paths(
                    queryset, prefix=field.path, skip=skip)

                # Append these to our list as well
                prefetched.extend(paths)

        # Ensure cache is unique and sorted properly
        return sorted(set(prefetched), reverse=True)

    @classmethod
    def prefetch_related(cls, queryset, prefix=None):
        """Performs a `prefetch_related` on all possible fields."""
        prefetch = cls._build_prefetch_related_paths
        cache = cls._prefetch_related_paths
        if id(cls) not in cache and len(queryset) >= 1:
            # Initialize the store
            cache[id(cls)] = prefetch(queryset, prefix)

        if id(cls) in cache:
            # Actually apply the prefetched prefetching
            return queryset.prefetch_related(*cache[id(cls)])

        # Apply nothing.
        return queryset

    @classmethod
    def make_slug(cls, obj):
        return str(obj.pk)

    def read(self):
        # Build the queryset
        queryset = self.model.objects.all()

        # Filter the queryset based on permissions you can have
        # queryset = self.authorize_queryset(queryset, 'read')

        try:
            # # Prefetch all related fields and return the queryset.
            # queryset = self.prefetch_related(queryset)

            if self.slug is not None:
                # Model resources by default have the slug as the identifier.
                # TODO: Support non-pk slugs easier by allowing a
                #   hook or something.
                chance = queryset.filter(pk=self.slug)
                if not chance.exists() and self.path:
                    try:
                        # Attempt to perform array access; and just return it.
                        return queryset[int(self.slug)]

                    except IndexError:
                        # Not an array; oh well.
                        pass

        except ValueError:
            # Something went wront when applying the slug filtering.
            raise exceptions.NotFound()

        # Build filter string for parents
        parent, path = self.parent, []
        while parent is not None:
            slug = parent.resource.slug
            path.append(parent.related_name)
            queryset = queryset.filter(**{'__'.join(path): slug})
            parent = parent.resource.parent

        if self.slug is not None:
            try:
                # Attempt to get what we have.
                queryset = chance.get()

            except self.model.DoesNotExist:
                # Didn't find it.
                raise exceptions.NotFound()

        # Return the queryset if we still have it.
        return queryset
