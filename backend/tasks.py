import logging

import requests

from celery import shared_task

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import transaction
from django.http import JsonResponse

from requests import RequestException

from backend.models import ProductInfo, Shop, Category, Parameter, ProductParameter, Product, User
import yaml

from backend.utils import validate_url

logger = logging.getLogger(__name__)


@shared_task
def send_email(subject, message, from_email, recipient_list):
    """
    Отправка электронной почты с уведомлением о заказе

    Args:
        subject: Тема письма
        message: Сообщение письма
        from_email: Адрес отправителя
        recipient_list: Список получателей
    """
    msg = EmailMultiAlternatives(subject, message, from_email, recipient_list)
    msg.send()


@shared_task(bind=True, max_retries=3)
def do_import(self, url, user_id=None):
    """
    Импорт данных из YAML-файла

    Args:
        self: Экземпляр задачи Celery
        url: URL-адрес YAML-файла
        user_id: id авторизированного пользователя
    """
    try:
        if not url:
            raise ValueError("URL не указан")

        if not validate_url(url):
            raise ValidationError("Неверный URL")

        if user_id is None:
            raise ValueError('Пользователь не указан')
        try:
            user = User.objects.get(id=user_id, type='shop')
        except ObjectDoesNotExist:
            raise ValueError("Пользователь не найден или не является магазином")

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
        except RequestException as e:
            return JsonResponse({'status': False, 'Ошибка загрузки данных': str(e)})

        data = yaml.safe_load(response.content)

        required_fields = ['shop', 'categories', 'goods']
        for field in required_fields:
            if field not in data:
                raise KeyError(f"Отсутствует обязательное поле: {field}")

        # Создаем/обновляем магазин
        shop, created = Shop.objects.get_or_create(name=data['shop'], defaults={'user': user})
        if not created and shop.user != user:
            raise PermissionError("Этот магазин принадлежит другому пользователю")

        # Обработка категорий
        for category_data in data['categories']:
            Category.objects.get_or_create(
                id=category_data['id'],
                defaults={'name': category_data['name']}
            )

        # Обработка товаров
        with transaction.atomic():
            ProductInfo.objects.filter(shop=shop).delete()

            for item in data['goods']:
                # Проверка обязательных полей
                required_item_fields = ['id', 'category', 'model', 'quantity', 'price', 'price_rrc', 'name']
                for field in required_item_fields:
                    if field not in item:
                        raise KeyError(f"Отсутствует поле в товаре: {field}")

                # Получаем категорию как объект
                category_id = item['category']
                try:
                    category = Category.objects.get(id=category_id)
                except Exception:
                    logger.warning(f"Категория с ID {category_id} не найдена")
                    continue

                # Создаем продукт
                product, _ = Product.objects.get_or_create(
                    name=item['name'],
                    defaults={'category': category}
                )
                if product.category != category:
                    product.category = category
                    product.save()

                # Создаем информацию о товаре
                product_info = ProductInfo.objects.create(
                    product=product,
                    shop=shop,
                    model=item['model'],
                    external_id=item['id'],
                    price=item['price'],
                    price_rrc=item['price_rrc'],
                    quantity=item['quantity']
                )

                # Добавляем параметры
                if 'parameters' in item:
                    for name, value in item['parameters'].items():
                        parameter, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(
                            product_info=product_info,
                            parameter=parameter,
                            value=value
                        )

        return {'Status': True}

    except requests.RequestException as e:
        logger.error(f"Ошибка загрузки файла: {e}")
        if self.request.retries < self.max_retries:
            self.retry(exc=e, countdown=2 ** self.request.retries)
        return {'Status': False, 'Error': f'Не удалось загрузить файл: {str(e)}'}

    except yaml.YAMLError as e:
        logger.error(f"Ошибка парсинга YAML: {e}")
        return {'Status': False, 'Error': 'Файл имеет неверный формат YAML'}

    except Exception as e:
        logger.error(f"Критическая ошибка импорта: {e}", exc_info=True)
        return {'Status': False, 'Error': str(e)}


