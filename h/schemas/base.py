# -*- coding: utf-8 -*-

"""Shared functionality for schemas."""

from __future__ import unicode_literals

import copy

import colander
import deform
import jsonschema
from pyramid.session import check_csrf_token


@colander.deferred
def deferred_csrf_token(node, kw):
    request = kw.get('request')
    return request.session.get_csrf_token()


class ValidationError(Exception):
    pass


class CSRFSchema(colander.Schema):
    """
    A CSRFSchema backward-compatible with the one from the hem module.

    Unlike hem, this doesn't require that the csrf_token appear in the
    serialized appstruct.
    """

    csrf_token = colander.SchemaNode(colander.String(),
                                     widget=deform.widget.HiddenWidget(),
                                     default=deferred_csrf_token,
                                     missing=None)

    def validator(self, form, value):
        request = form.bindings['request']
        check_csrf_token(request)


class JSONSchema(object):
    """
    Validate data according to a Draft 4 JSON Schema.

    Inherit from this class and override the `schema` class property with a
    valid JSON schema.
    """

    schema = {}

    def __init__(self):
        format_checker = jsonschema.FormatChecker()
        self.validator = jsonschema.Draft4Validator(self.schema,
                                                    format_checker=format_checker)

    def validate(self, data):
        """
        Validate `data` according to the current schema.

        :param data: The data to be validated
        :returns: valid data
        :raises ~h.schemas.ValidationError: if the data is invalid
        """
        # Take a copy to ensure we don't modify what we were passed.
        appstruct = copy.deepcopy(data)

        errors = list(self.validator.iter_errors(appstruct))
        if errors:
            msg = ', '.join([_format_jsonschema_error(e) for e in errors])
            raise ValidationError(msg)
        return appstruct


def remove_unknown_properties(data, schema):
    """
    Remove unknown properties from the data.

    Remove all "properties" in the data that aren't in the schema.
    It does not perform any validation of property values; meaning if
    a property's value is the incorrect type, it is left as-is in the
    data.

    :param data: The data to be validated
    :param schema: The jsonschema schema to validate against
    """

    def remove_props(data, properties):
        for prop in properties:
            del data[prop]

    data_properties = [(data, schema["properties"])]
    # While there are still properties to be checked.
    while data_properties:
        data_d, schema_d = data_properties.pop()

        extra_props = set(data_d.keys()) - set(schema_d.keys())
        remove_props(data_d, extra_props)

        for prop, value in data_d.items():
            # Value must be a dict-like object.
            if isinstance(value, dict):
                # If a prop exists and doesn't have nested props in the
                # schema but it does have nested props in the data, it has
                # an invalid value so just ignore it.
                if "properties" in schema_d[prop]:
                    data_properties.append((value, schema_d[prop]["properties"]))


def enum_type(enum_cls):
    """
    Return a `colander.Type` implementation for a field with a given enum type.

    :param enum_cls: The enum class
    :type enum_cls: enum.Enum
    """
    class EnumType(colander.SchemaType):
        def deserialize(self, node, cstruct):
            if cstruct == colander.null:
                return None

            try:
                return enum_cls[cstruct]
            except KeyError:
                msg = '"{}" is not a known value'.format(cstruct)
                raise colander.Invalid(node, msg)

        def serialize(self, node, appstruct):
            if not appstruct:
                return ''
            return appstruct.name

    return EnumType


def combine_repeated_fields(schema, data):
    """
    Convert a `MultiDict` into a dict.

    Repeated fields are either dropped, except for the last entry, or combined
    into a list, depending on the type of the corresponding schema node.

    This is useful for preparing a query string multidict for processing with
    a colander schema.

    :type schema: colander.SchemaNode
    :type data: webob.multidict.MultiDict
    :rtype: Dict[str,Any]
    """
    result = data.dict_of_lists()
    for key, values in result.items():
        node = schema.get(key)

        if not node or not isinstance(node.typ, colander.Sequence):
            # Not a list-valued field, keep only the last entry.
            result[key] = values[-1]

    return result


def _colander_exception_msg(exc):
    """
    Combine error messages from a `colander.Invalid` exception.

    :type exc: colander.Invalid
    :rtype str:
    """
    msg_dict = exc.asdict()
    for child in exc.children:
        msg_dict.update(child.asdict())
    msg_list = ["{}: {}".format(field, err) for field, err in msg_dict.items()]
    return "\n".join(msg_list)


def validate_query_params(schema, params):
    """
    Validate query parameters using a colander schema.

    :type schema: colander.Schema
    :param params: Query parameter dict, usually `request.params`.
    :type params: webob.multidict.MultiDict
    :raises ValidationError:
    """
    try:
        combined_params = combine_repeated_fields(schema, params)
        return schema.deserialize(combined_params)
    except colander.Invalid as exc:
        raise ValidationError(_colander_exception_msg(exc))


def _format_jsonschema_error(error):
    """Format a :py:class:`jsonschema.ValidationError` as a string."""
    if error.path:
        dotted_path = '.'.join([str(c) for c in error.path])
        return '{path}: {message}'.format(path=dotted_path,
                                          message=error.message)
    return error.message
