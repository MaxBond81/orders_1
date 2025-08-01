from rest_framework.response import Response
from django.http import JsonResponse
import requests





def validate_url(url):
    try:
        response = requests.head(url, timeout=5)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException:
        raise ValueError("Неверный URL")


def string_to_bool(value: str) -> bool:
    """
    Функция преобразует строку в логическое значение (True или False).
    Применяется при смене статуса поставщика

    Функция чувствительна к следующим значениям:
      - Истина: 'true', '1', 'on' (регистр не важен)
      - Ложь: 'false', '0', 'off' (регистр не важен)

    Args:
        value (str): Входное значение, которое будет преобразовано в bool.

    Returns:
        bool: True — если значение соответствует истине, False — если лжи.

    Raises:
        ValueError: Если входное значение не может быть интерпретировано как логическое значение.
        TypeError: Если передан аргумент не типа str или bool.
    """
    if isinstance(value, bool):
        return value

    if not isinstance(value, str):
        raise TypeError(f"str or bool type is expected, received: {type(value)}")

    value = value.strip().lower()

    if value in ('true', '1', 'on'):
        return True
    elif value in ('false', '0', 'off'):
        return False
    else:
        raise ValueError(f"Invalid value: '{value}'")


class AccessMixin:
    """
    Миксин для проверки доступа к магазину
    """
    @staticmethod
    def check_shop_access(request):
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        return None