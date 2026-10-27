from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def active(context, *names):
    """Returns 'active' when the current page is one of the given url names (used by the sidebar)."""
    match = context["request"].resolver_match
    return "active" if match and match.view_name in names else ""


@register.filter
def initials(name):
    parts = str(name).split()
    return "".join(part[0] for part in parts[:2]).upper() or "?"


@register.filter
def stars(rating):
    """4 -> '★★★★☆'"""
    rating = int(rating or 0)
    return "★" * rating + "☆" * (5 - rating)
