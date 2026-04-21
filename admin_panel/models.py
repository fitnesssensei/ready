from django.db import models


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


class Book(models.Model):
    COVER_TYPES = [
        ('hard', 'Твердый'),
        ('soft', 'Мягкий'),
    ]

    VAT_RATES = [
        ('0', 'Без НДС'),
        ('10', '10%'),
        ('20', '20%'),
    ]

    CONDITION_CHOICES = [
        ('excellent', 'Отличная'),
        ('good', 'Хорошая'),
    ]

    title = models.CharField(max_length=200, verbose_name="Название", default="")
    sku = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="Артикул")
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Категория"
    )
    author = models.CharField(max_length=100, verbose_name="Автор", default="")
    author_oblozh = models.CharField(max_length=100, verbose_name="Автор на обложке", default="")
    genre = models.CharField(max_length=100, verbose_name="Жанр", default="")
    publisher = models.CharField(max_length=100, verbose_name="Издательство", default="")
    series = models.CharField(max_length=200, verbose_name="Серия", blank=True, null=True)
    publication_year = models.PositiveIntegerField(verbose_name="Год издания", blank=True, null=True)
    language = models.CharField(max_length=50, verbose_name="Язык издания", default="")
    condition = models.CharField(
        max_length=20, choices=CONDITION_CHOICES, verbose_name="Сохранность", blank=True, null=True
    )
    cover_type = models.CharField(
        max_length=10, choices=COVER_TYPES, verbose_name="Тип переплёта", default='hard'
    )
    pages = models.PositiveIntegerField(verbose_name="Количество страниц", blank=True, null=True)
    photos = models.JSONField(default=list, verbose_name="Фотографии", blank=True)
    description = models.TextField(blank=True, verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена", default=0)
    old_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Старая цена / цена до скидки",
        blank=True, null=True
    )
    # ✅ FIX: default должен быть кодом из choices ('0'), а не отображаемым текстом ('Без НДС')
    vat_rate = models.CharField(max_length=2, choices=VAT_RATES, verbose_name="Ставка НДС", default='0')
    stock = models.PositiveIntegerField(verbose_name="Остаток на складе", default=1)
    isbn = models.CharField(max_length=13, unique=True, blank=True, null=True, verbose_name="ISBN")
    weight = models.DecimalField(
        max_digits=6, decimal_places=3, verbose_name="Вес с упаковкой (кг)", blank=True, null=True
    )
    length = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Длина с упаковкой (см)", blank=True, null=True
    )
    width = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Ширина с упаковкой (см)", blank=True, null=True
    )
    height = models.DecimalField(
        max_digits=6, decimal_places=2, verbose_name="Высота с упаковкой (см)", blank=True, null=True
    )
    publication_date = models.DateField(blank=True, null=True, verbose_name="Дата публикации")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Книга"
        verbose_name_plural = "Книги"
        ordering = ['-created_at']

    def __str__(self):
        return self.title
