# hospital/templatetags/form_extras.py
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    """
    Add a CSS class to a form field widget safely.
    Usage: {{ form.field|add_class:"form-control modern-input" }}
    """
    if not field:
        return field

    # Get current classes
    current_classes = field.field.widget.attrs.get('class', '')

    # Add new class if not already present
    classes = current_classes.split()
    if css_class not in classes:
        classes.append(css_class)
        field.field.widget.attrs['class'] = ' '.join(classes)

    return field


@register.filter(name='attr')
def attr(field, attr_string):
    """
    Add any attribute to a form field (placeholder, type, etc.).
    Usage: {{ form.field|attr:"placeholder:Enter name" }}
           {{ form.field|attr:"type:date" }}
    """
    if not field or not attr_string or ':' not in attr_string:
        return field

    attr_name, attr_value = [x.strip() for x in attr_string.split(':', 1)]

    if hasattr(field, 'as_widget'):
        attrs = {attr_name: attr_value}
        return field.as_widget(attrs=attrs)

    # Fallback for non-widget fields
    return field