from django import template
from cart.models import Cart


register = template.Library()


@register.simple_tag(takes_context=True)
def get_cart_count(context):
    request = context["request"]
    if not request.session.session_key:  # во избежания ошибок 
        return 0
    
    try:
        cart = Cart.objects.get(session_key=request.session.session_key)
        return cart.total_items
    except Cart.DoesNotExist:
        return 0
    

@register.filter
def multiply(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
    
# Весь файл объяснить надо и для чего он нужен вообще 
# Шаблон к нему: 
# {% load cart_tags %}  # Что это 
# <button class="relative group">
#     <span class="text-sm font-medium text-gray-900 group-hover:text-gray-700">
#         CART ({% get_cart_count %})
#     </span>
#     {% if cart_total_items > 0 %}
#     <span class="absolute -top-2 -right-2 h-4 w-4 bg-black text-white text-xs rounded-full flex items-center justify-center">
#         {{ cart_total_items }}
#     </span>
#     {% endif %}
# </button>
