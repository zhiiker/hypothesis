from h.schemas.base import validate_query_params
from h.schemas.annotation import SearchAnnotationsSchema

from webob.multidict import MultiDict

# Input query params. This would usually come from `request.params`.
params = MultiDict()

# Enum-valued field. Should be validated against the set of legal values.
params.add("order", "asc")

# Field with a string value, should be returned as an int.
params.add("limit", "5")

# Field with a boolean value, should be converted to `True` or `False`.
params.add("_separate_replies", "true")

# Scalar field specified multiple times. Only the last value should be kept
params.add("offset", "10")
params.add("offset", "20")

# List field specified multiple times. This should be converted into a list.
params.add("quote", "foo")
params.add("quote", "bar")

# An unknown field. This should not appear in the parsed result.
params.add("ignore_me", "whatever")

validated_params = validate_query_params(SearchAnnotationsSchema(), params)

assert validated_params == {"order": "asc",
                            "limit": 5,
                            "_separate_replies": True,
                            "offset": 20,
                            "quote": ["foo", "bar"]}
