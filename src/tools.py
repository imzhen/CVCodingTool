from collections import Mapping, Iterable

from unidecode import unidecode


def unicode_wrapper(obj):
    if not obj:
        return None
    elif isinstance(obj, str):
        return unidecode(obj)
    elif isinstance(obj, Mapping):
        return dict(map(unicode_wrapper, obj.items()))
    elif isinstance(obj, Iterable):
        return type(obj)(map(unicode_wrapper, obj))
    else:
        return obj
