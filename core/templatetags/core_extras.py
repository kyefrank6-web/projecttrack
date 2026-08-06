from django import template

register = template.Library()


@register.filter
def get_item(d, key):
    if d is None:
        return ""
    return d.get(key, "")


@register.filter
def format_competency_score(score_map, competency_id):
    """Show — when competency not yet scored; otherwise percentage."""
    if not score_map:
        return "—"
    val = score_map.get(competency_id)
    if val is None or val == "":
        return "—"
    return f"{val}%"

