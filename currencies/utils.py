# -*- coding: utf-8 -*-

from django.core.cache import cache
from decimal import Decimal as D, ROUND_UP


from .models import Currency as C
from .conf import SESSION_KEY


def get_factor_by_code(code):
    currencies = cache.get("__currencies__")
    if not currencies:
        currencies = {}
        for c in C.active.all():
            currencies[c.code] = c.factor
        cache.set("__currencies__", currencies, timeout=60)
    try:
        return currencies[code]
    except KeyError:
        cache.delete("__currencies__")


def get_default():
    result = cache.get("__default_currency__")
    if not result:
        result = C.active.default()
        cache.set("__default_currency__", result, timeout=60)
    return result


def calculate(price, code, decimals=2):
    to, default = get_factor_by_code(code), get_default().factor

    # First, convert from the default currency to the base currency,
    # then convert from the base to the given currency
    price = (D(price) / default) * to

    return price_rounding(price, decimals=decimals)


def convert(amount, from_code, to_code, decimals=2):
    if from_code == to_code:
        return amount

    from_, to = get_factor_by_code(from_code), get_factor_by_code(to_code)

    amount = D(amount) * (to / from_)
    return price_rounding(amount, decimals=decimals)


def get_currency_code(request):
    for attr in ('session', 'COOKIES'):
        if hasattr(request, attr):
            try:
                return getattr(request, attr)[SESSION_KEY]
            except KeyError:
                continue

    # fallback to default...
    try:
        return get_default().code
    except C.DoesNotExist:
        return None  # shit happens...


def price_rounding(price, decimals=2):
    decimal_format = "0.01"
    # Because of the up-rounding we require at least 2 decimals
    if decimals > 2:
        decimal_format = "0.{}".format('1'.zfill(decimals))
    return price.quantize(D(decimal_format), rounding=ROUND_UP)
