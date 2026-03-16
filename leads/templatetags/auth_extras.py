from django import template

register = template.Library()


@register.filter
def is_manager(user):
    """Check if user is a manager"""
    if user.is_superuser:
        return True
    return user.groups.filter(name='Manager').exists()
