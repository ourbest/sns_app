from django.core.cache import cache

from backend.models import Tag


def reload_cache(clz, key=None):
    cache_key = 'models.%s' % clz.__name__ if not key else 'models.%s.%s' % (clz.__name__, key)
    cache.delete(cache_key)


def get_model_objects(clz, processor=None):
    key = 'models.%s' % clz.__name__
    data = cache.get(key)
    if not data:
        data = list(clz.objects.all()) if not processor else [processor(x) for x in clz.objects.all()]
        cache.set(key, data, 1800)
    return data


def get_model_object_key(clz, key, loader=None):
    cache_key = 'models.%s.%s' % (clz.__name__, key)
    data = cache.get(cache_key)

    if not data:
        if loader:
            data = loader(key)
        else:
            data = clz.objects.filter(pk=key).first()
        cache.set(cache_key, data, 1800)
    return data


def get_tag_names():
    return get_model_objects(Tag, lambda x: x.name)


def get_or_create(key, default_val, ex=1800):
    data = cache.get(key)
    if data is None:
        cache.set(key, default_val, ex)
    return data
