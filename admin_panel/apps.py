from django.apps import AppConfig


class AdminPanelConfig(AppConfig):
    name = 'admin_panel'

    def ready(self):
        # Яндекс Маркет: экшен «Экспортировать выбранные в шаблон Яндекс Маркета»
        # подключается к BookAdmin через monkey-patch (admin.py не изменяется).
        from . import yandex_admin  # noqa: F401

        yandex_admin.register_yandex_admin_actions()

