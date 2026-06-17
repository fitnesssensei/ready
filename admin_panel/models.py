from email.policy import default
from random import choice
from webbrowser import get
from django.db import models


class OzonTemplate(models.Model):
    """
    Модель для хранения шаблонов Ozon.

    Шаблоны загружаются вручную через админку и используются для экспорта
    товаров в формате, совместимом с Ozon Seller.

    Особенности:
    - Только один шаблон может быть активным одновременно
    - При активации нового шаблона, старые автоматически деактивируются
    - Файлы хранятся в media/ozon_templates/
    """

    # Название шаблона для идентификации (например, "Букинистика май 2026")
    name = models.CharField(max_length=200, verbose_name="Название шаблона")

    # Excel файл шаблона, скачанный из Ozon Seller
    file = models.FileField(upload_to='ozon_templates/', verbose_name="Excel файл")

    # Необязательное описание для дополнительной информации
    description = models.TextField(blank=True, verbose_name="Описание")

    # Флаг активности - только один шаблон может быть активным
    is_active = models.BooleanField(default=True, verbose_name="Активный")

    # Автоматическая дата загрузки шаблона
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Шаблон Ozon"
        verbose_name_plural = "Шаблоны Ozon"
        ordering = ['-uploaded_at']  # Сортировка по дате: новые сверху

    def __str__(self):
        """Строковое представление: название + дата"""
        return f"{self.name} ({self.uploaded_at.strftime('%Y-%m-%d')})"

    def save(self, *args, **kwargs):
        """
        Переопределенный метод сохранения.

        Логика: если текущий шаблон активен, деактивируем все остальные.
        Это гарантирует, что только один шаблон активен в любой момент времени.
        """
        if self.is_active:
            # Деактивировать все остальные шаблоны перед сохранением
            OzonTemplate.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)


class Category(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название категории")
    ozon_category_id = models.CharField(max_length=50, verbose_name="ID категории Озон", unique=True)
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (Ozon ID: {self.ozon_category_id})"

def get_default_category():
    # Возвращаем первую категорию из списка (по алфавиту)
    cat = Category.objects.order_by('name').first()
    return cat.id if cat else None

class Book(models.Model):
    SOURCE_MANUAL = 'manual'
    SOURCE_EKSMO = 'eksmo'

    SOURCE_CHOICES = [
        (SOURCE_MANUAL, 'Админка'),
        (SOURCE_EKSMO, 'Импорт Эксмо'),

    ]

    COVER_TYPES = [
        ('hard', 'Твердый переплет'),
        ('soft', 'Мягкая обложка'),
        ('softSuper', 'Мягкая обложка, суперобложка'),
        ('klapan', 'Обложка с клапанами'),
        ('klapanSuper', 'Обложка с клапанами, суперобложка'),
        ('poluKozha', 'Полукожаный переплет'),
        ('hardSuper', 'Твердый переплет, суперобложка'),
        ('textile', 'Тканевый переплет'),
        ('textileSuper', 'Тканевый переплет, суперобложка'),
        ('block', 'Блок для переплета'),
        ('Bumvinyl', 'Бумвинил'),
        ('integral', 'Интегральный переплет'),
        ('integralSuper', 'Интегральный переплет, суперобложка'),
        ('leather', 'Кожаный переплет'),
        ('sheet', 'Листовое издание'),
        ('copper', 'Медный переплет'),

    ]

    VAT_RATES = [
        ('0', 'Без НДС'),
        ('10', '10%'),
        ('20', '20%'),
    ]
    
    TARGET_AUDIENCE = [
        ('for adults', 'Для взрослых'),
        ('for children', 'Для детей'),

    ]

    AGE_RESTRICTIONS = [
        ('18+', '18+'),
        ('16+', '16+'),
        ('14+', '14+'),
        ('12+', '12+'),
        ('10+', '10+'),
        ('9+', '9+'),
        
    ]

    LANGUAGE_CHOICES = [
        ('russian', 'Русский'),
        ('english', 'Английский'),
        ('french', 'Французский'),
        ('german', 'Немецкий'),

    ]

    CONDITION_CHOICES = [
        ('excellent', 'Отличная'),
        ('good', 'Хорошая'),
        ('veriGood', 'Очень хорошая'),
        ('satisfactorily', 'Удовлетворительная'),
        ('bad', 'Плохая'),

    ]

    BOOK_TYPE = [
        ('printed book', 'Печатная книга'),
        ('second', 'Second-hand книга'),
        ('bookinist', 'Букинистика'),
        ('print_on_demand', 'Печать по требованию'),
    ]


    # строка "тип бумаги"
    PAPER_TYPES = [
        ('offset', 'Офсетная'),
        ('art', 'Художественная'),
        ('newsprint', 'Газетная'),
        ('recycled', 'Макулатурная'),
        ('kremovaya', 'Кремовая'),
        ('design', 'Дизайнерская'),
        ('karton', 'Картон'),
        ('coated', 'Мелованная глянцевая'),
        ('coatedMat', 'Меловання матовая'),
        ('kartograf', 'Картографическая'),
        ('vtorichka', 'Вторичной переработки'),
        ('vlaga', 'Влагостойкая'),
        ('puhlaya', 'Пухлая'),
        ('samokley', 'Самоклеющаяся'),
        ('tipograf', 'Типографская'),
    ]

    title = models.CharField(max_length=200, verbose_name="Название", default="")
    source = models.CharField(
        max_length=10,
        choices=SOURCE_CHOICES,
        default=SOURCE_MANUAL,
        verbose_name="Источник",
        db_index=True,
    )
    
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Артикул")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Категория",
        default=get_default_category
    )

    author = models.CharField(max_length=100, verbose_name="Автор", default="")
    author_oblozh = models.CharField(max_length=100, verbose_name="Автор на обложке", blank=True, null=True)
    genre = models.CharField(max_length=100, verbose_name="Направление", blank=True, null=True)
    target_audience = models.CharField(max_length=100, choices=TARGET_AUDIENCE, verbose_name="Целевая аудитория", default='for adults', blank=True)  # целевая аудитория 
    age_restrictions = models.CharField(max_length=100, choices=AGE_RESTRICTIONS, verbose_name="Возрастные ограничения", default='18+', blank=True)  # возраст огран  
    publisher = models.CharField(max_length=100, verbose_name="Издательство", default="")
    series = models.CharField(max_length=200, verbose_name="Серия", blank=True, null=True)
    publication_year = models.PositiveIntegerField(verbose_name="Год издания", blank=True, null=True)
    language = models.CharField(max_length=50, choices=LANGUAGE_CHOICES, verbose_name="Язык издания", default='russian')  # Язык издания
    condition = models.CharField(
        max_length=20, choices=CONDITION_CHOICES, verbose_name="Сохранность", default='good', blank=True  # состояние 
    )
    cover_type = models.CharField(
        max_length=20, choices=COVER_TYPES, verbose_name="Тип переплёта", default='hard'
    )
    # строка "тип книги
    book_type = models.CharField(
        max_length=20, choices=BOOK_TYPE, verbose_name="Тип книги", default='printed book', blank=True)  # тип книги 

    # строка "тип бумаги"
    paper_type = models.CharField(
    max_length=20, choices=PAPER_TYPES, verbose_name="Тип бумаги", default='offset', blank=True   # "тип бумаги"
    )
    # blank=True - для строк ; обе делают поле не обязательным 
    # null=True больше подходит для числовых 
    hashtags = models.CharField(max_length=200, verbose_name="Хештеги", blank=True, null=True)  # хештеги"
    pages = models.PositiveIntegerField(verbose_name="Количество страниц", blank=True, null=True)
    photos = models.JSONField(default=list, verbose_name="Фотографии", blank=True)
    description = models.TextField(blank=True, verbose_name="Описание", default="")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена", blank=True, null=True)  # цена не обязательно
    old_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Старая цена / цена до скидки",
        blank=True, null=True
    )
    # ✅ FIX: default должен быть кодом из choices ('0'), а не отображаемым текстом ('Без НДС')
    vat_rate = models.CharField(max_length=2, choices=VAT_RATES, verbose_name="Ставка НДС", default='0')
    stock = models.PositiveIntegerField(verbose_name="Остаток на складе", default=1)
    isbn = models.CharField(max_length=20, verbose_name="ISBN", blank=True, null=True, )
    weight = models.DecimalField(
        max_digits=8, decimal_places=4, verbose_name="Вес с упаковкой (г)", blank=True, null=True
    )
    length = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Длина с упаковкой (мм)", blank=True, null=True
    )
    width = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Ширина с упаковкой (мм)", blank=True, null=True
    )
    height = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Высота с упаковкой (мм)", blank=True, null=True
    )
    publication_date = models.DateField(blank=True, null=True, verbose_name="Дата публикации")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Книга"
        verbose_name_plural = "Книги"
        ordering = ['-created_at']
        # 🔇 Дедупликация на уровне БД отключена — она выполняется
        # на уровне приложения (в скриптах импорта).
        # constraints = [
        #     models.UniqueConstraint(
        #         fields=['isbn', 'source'],
        #         condition=models.Q(isbn__isnull=False),
        #         name='unique_isbn_per_source',
        #     ),
        # ]

    def __str__(self):
        return self.title


class ManualBook(Book):
    class Meta:
        proxy = True
        verbose_name = "Книга (админка)"
        verbose_name_plural = "Каталог — админка"


class EksmoBook(Book):
    class Meta:
        proxy = True
        verbose_name = "Книга"
        verbose_name_plural = "База книг"
