from django import template

register = template.Library()


@register.simple_tag
def rate(num, total, mul=100, length=2, suffix='%'):
    if total:
        result = float(num) / float(total) * mul
        return ('{:.%sf}%s' % (length, suffix)).format(result) if result else 0
    else:
        return 'N/A'
