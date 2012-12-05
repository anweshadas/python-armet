# -*- coding: utf-8 -*-
"""Implements the RESTful resource protocol for django ORM-backed models.
"""
from __future__ import print_function, unicode_literals
from __future__ import absolute_import, division
import six
from . import base
from .. import exceptions


class BaseModel(base.BaseResource):

    #! The model this resource is bound to; shortcut for declaring a form
    #! for read-only resources.
    model = None

    #! Class object cache of what is to be prefetched.
    _prefetch_related_paths = None

    @classmethod
    def prefetch_related(cls, queryset, prefix=None):
        """Performs a `prefetch_related` on all possible fields."""
        if cls._prefetch_related_paths is None:
            # First call; initialize the cache.
            cls._prefetch_related_paths = []

        if not cls._prefetch_related_paths and len(queryset) >= 1:
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
                        cls._prefetch_related_paths.append(path)
                        break

            for name, field in six.iteritems(cls._fields):
                if field.relation and issubclass(field.relation[0], BaseModel):
                    # Attempt to apply a test prefetch related
                    field.relation[0].prefetch_related(queryset,
                        prefix=field.path)

                    # Append these to our list as well
                    cls._prefetch_related_paths.extend(
                        field.relation[0]._prefetch_related_paths)

            # Ensure cache is unique and sorted properly
            cls._prefetch_related_paths = sorted(
                set(cls._prefetch_related_paths), reverse=True)

        # Actually apply the prefetched prefetching
        return queryset.prefetch_related(*cls._prefetch_related_paths)

    @classmethod
    def make_slug(cls, obj):
        return str(obj.pk)

    def read(self):
        # Build the queryset
        queryset = self.model.objects

        try:
            # Apply transveral first.
            # Build filter string for parents
            parent = self.parent
            path = []
            while parent is not None:
                path.append(parent.related_name)
                queryset = queryset.filter(**{'__'.join(path): parent.slug})
                parent = parent.resource.parent

            if self.slug is not None:
                # Model resources by default have the slug as the identifier.
                # TODO: Support non-pk slugs easier by allowing a
                #   hook or something.
                queryset = queryset.filter(pk=self.slug)

        except ValueError:
            # Something went wront when applying the slug filtering.
            raise exceptions.NotFound()

        else:
            # No slug; start with all the models.
            queryset = queryset.all()

        # Prefetch all related fields and return the queryset.
        return self.prefetch_related(queryset)
