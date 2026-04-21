import json
from django import forms
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe


class MultipleImageWidget(forms.Widget):
    """
    Виджет для загрузки нескольких фотографий к книге.
    Отвечает ТОЛЬКО за чтение данных из формы.
    Сохранение файлов на диск — исключительно в BookAdmin.save_model().
    """
    template_name = 'admin_panel/multiple_image_widget.html'

    def __init__(self, attrs=None):
        default_attrs = {'class': 'multiple-image-widget'}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = []
        elif isinstance(value, str):
            try:
                value = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                value = []

        context = {
            'name': name,
            'photos': value,
            'photos_json': json.dumps(value),
            'MEDIA_URL': settings.MEDIA_URL,
            'widget': self,
        }
        return mark_safe(render_to_string(self.template_name, context))

    def value_from_datadict(self, data, files, name):
        """
        Django's JSONField.to_python() вызывает json.loads() на значении,
        которое возвращает виджет. Поэтому возвращаем JSON-СТРОКУ, не список.
        """
        raw = data.get(f'{name}_existing', '[]')

        # Если уже список — сериализуем обратно в строку
        if isinstance(raw, list):
            return json.dumps(raw)

        # Проверяем что это валидный JSON-список, и возвращаем строку как есть
        try:
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                return '[]'
            return raw  # возвращаем строку, не parsed список
        except (json.JSONDecodeError, TypeError):
            return '[]'

    def format_value(self, value):
        if value is None:
            return []
        elif isinstance(value, str):
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return []
        elif isinstance(value, list):
            return value
        return []