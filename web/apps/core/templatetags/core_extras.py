from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    if dictionary:
        # Obsługa kluczy string/int
        val = dictionary.get(str(key))
        if val is None:
            val = dictionary.get(int(key) if str(key).isdigit() else key)
        return val
    return None