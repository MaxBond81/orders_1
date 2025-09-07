from django.contrib import admin, messages
from django.urls import path, reverse
from django.shortcuts import redirect, render
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from backend.models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken

from backend.tasks import do_import


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Панель управления пользователями
    Attributes:
           model: Модель пользователя
           fieldsets: Группы полей для отображения в форме редактирования
           list_display: Поля для отображения в списке пользователей
           list_filter: Поля для фильтра
           search_fields: Поля для поиска
    """
    model = User

    fieldsets = (
        (None, {'fields': ('email', 'password', 'type')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'last_name')


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """
       Панель управления магазинами
       Attributes:
              list_display: Поля для отображения в списке магазинов
              list_filter: Поля для фильтра
              search_fields: Поля для поиска
    """

    list_display = ('name', 'url', 'user', 'state', 'import_button')
    list_filter = ('state',)
    search_fields = ('name', 'url')

    def import_button(self, obj):
        """ Кнопка 'Импорт товаров' для каждого магазина."""
        return format_html(
            '<a class="button" href="{}">📥 Импорт товаров</a>',
            reverse('admin:run-do-import')  # Указывает маршрут
        )

    import_button.short_description = 'Импорт товаров'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('import/', self.admin_site.admin_view(self.run_do_import), name='run-do-import')
        ]
        return custom_urls + urls

    def run_do_import(self, request):
        if request.method == 'POST':
            url = request.POST.get('url')

            if not url:
                messages.error(request, 'URL не указан')
                return redirect('admin:run-do-import')

            if not request.user.is_authenticated:
                messages.error(request, 'Войдите в аккаунт магазина')
                return redirect('admin:run-do-import')

            if request.user.type != 'shop':
                messages.error(request, 'Только для магазинов')
                return redirect('admin:run-do-import')

            try:
                task = do_import.delay(url=url, user_id=request.user.id)
                messages.success(request, f'Задача импорта запущена. ID задачи: {task.id}')
            except Exception as e:
                messages.error(request, f'Ошибка запуска задачи: {e}')
            return redirect('admin:run-do-import')
        return render(request, 'admin/run_task_form.html', {
            'title': 'Импорт данных магазина',
            'task_name': 'do_import',
            'form_action': 'admin:run-do-import'
        })


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
       Панель управления категориями
       Attributes:
              list_display: Поля для отображения в списке категорий
              filter_horizontal: Поля для горизонтального фильтра
              search_fields: Поля для поиска
    """

    list_display = ('name', )
    filter_horizontal = ('shops',)
    search_fields = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
      Панель управления продуктами
      Attributes:
             list_display: Поля для отображения в списке продуктов
             list_filter: Поля для фильтра
             search_fields: Поля для поиска
    """

    list_display = ('id', 'name', 'category')
    list_filter = ('category', )
    search_fields = ('name', 'category__name' )


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """
      Панель управления информацией о продукте
      Attributes:
             list_display: Поля для отображения в списке информации о продукте
             list_filter: Поля для фильтра
             search_fields: Поля для поиска
             readonly_fields: Поля только для чтения
    """

    list_display = ('model', 'product', 'shop', 'quantity', 'price', 'price_rrc')
    list_filter = ('product', 'shop')
    search_fields = ('model', 'product__name', 'shop__name', 'product__category__name')
    readonly_fields = ('external_id',)


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """
         Панель управления параметрами
         Attributes:
                list_display: Поля для отображения в списке параметров
                search_fields: Поля для поиска
    """

    list_display = ('name', )
    search_fields = ('name', )


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """
        Панель управления параметрами продукта
        Attributes:
            list_display: Поля для отображения в списке параметров продукта
            list_filter: Поля для фильтра
            search_fields: Поля для поиска
    """

    list_display = ('product_info__product__name', 'parameter', 'value')
    list_filter = ('parameter', 'value')
    search_fields = ('product_info__product__name', 'parameter__name',)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
        Панель управления заказами
        Attributes:
            list_display: Поля для отображения в списке заказов
            list_filter: Поля для фильтра
            search_fields: Поля для поиска
    """

    list_display = ('id', 'user', 'dt', 'state', 'contact')
    list_filter = ('user', 'dt', 'state')
    search_fields = ('user__last_name', 'user__email')


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
        Панель управления позициями заказов
        Attributes:
            list_display: Поля для отображения позиций заказов
            list_filter: Поля для фильтра
            search_fields: Поля для поиска
    """

    list_display = ('order', 'product_info__product__name', 'quantity')
    list_filter = ('order__user__email', 'product_info__product__category__name')
    search_fields = ('order__user__email', 'product_info__product__name')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
        Панель управления контактами
        Attributes:
            list_display: Поля для отображения контактов
            list_filter: Поля для фильтра
            search_fields: Поля для поиска
    """

    list_display = ('user', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'phone')
    list_filter = ('city', )
    search_fields = ('user__email', 'city')


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'key', 'created_at',)
