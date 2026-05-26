"""
Сервис для работы с Ozon Seller API.

Документация: https://docs.ozon.ru/api/seller/

⚠️ Интеграция с Ozon Seller API закомментирована.
   Если потребуется вернуть — раскомментируйте файл.
"""

# import requests
# from decimal import Decimal
# from typing import Any
# from django.conf import settings


# class OzonAPIError(Exception):
#     """Ошибка при работе с Ozon API"""
#     pass


# class OzonAPI:
#     """Клиент для работы с Ozon Seller API"""

#     BASE_URL = "https://api-seller.ozon.ru"

#     def __init__(self, client_id: str = None, api_key: str = None):
#         """
#         Инициализация клиента.

#         Args:
#             client_id: Client-ID из настроек Ozon Seller
#             api_key: API-Key из настроек Ozon Seller
#         """
#         self.client_id = client_id or getattr(settings, 'OZON_CLIENT_ID', '')
#         self.api_key = api_key or getattr(settings, 'OZON_API_KEY', '')

#         if not self.client_id or not self.api_key:
#             raise OzonAPIError("Не указаны OZON_CLIENT_ID или OZON_API_KEY в настройках")

#     def _get_headers(self) -> dict:
#         """Заголовки для всех запросов к API"""
#         return {
#             'Client-Id': self.client_id,
#             'Api-Key': self.api_key,
#             'Content-Type': 'application/json',
#         }

#     def _request(self, method: str, endpoint: str, data: dict = None) -> dict:
#         """
#         Базовый метод для выполнения запросов к API.

#         Args:
#             method: HTTP метод (GET, POST)
#             endpoint: путь API (например, /v1/product/import)
#             data: данные для отправки

#         Returns:
#             Ответ API в виде словаря

#         Raises:
#             OzonAPIError: при ошибке запроса
#         """
#         url = f"{self.BASE_URL}{endpoint}"

#         try:
#             response = requests.request(
#                 method=method,
#                 url=url,
#                 headers=self._get_headers(),
#                 json=data,
#                 timeout=30
#             )
#             response.raise_for_status()
#             return response.json()
#         except requests.exceptions.RequestException as e:
#             error_detail = ""
#             if hasattr(e, 'response') and e.response is not None:
#                 try:
#                     error_detail = f" Детали: {e.response.text}"
#                 except:
#                     pass
#             raise OzonAPIError(f"Ошибка запроса к Ozon API: {e}{error_detail}")

#     def get_category_tree(self, category_id: int = None, language: str = "RU") -> dict:
#         """
#         Получить дерево категорий.

#         Args:
#             category_id: ID категории (если None, возвращает корневые категории)
#             language: язык ответа (RU, EN)

#         Returns:
#             Дерево категорий
#         """
#         data = {"language": language}
#         if category_id:
#             data["category_id"] = category_id

#         return self._request("POST", "/v1/description-category/tree", data)

#     def get_category_attributes(self, category_id: int, language: str = "RU") -> dict:
#         """
#         Получить атрибуты категории (шаблон для заполнения).

#         Args:
#             category_id: ID категории Ozon
#             language: язык ответа

#         Returns:
#             Список атрибутов категории
#         """
#         data = {
#             "category_id": [category_id],
#             "language": language
#         }
#         return self._request("POST", "/v1/description-category/attribute", data)

#     def get_product_types(self, category_id: int) -> dict:
#         """
#         Получить типы товаров для категории.

#         Args:
#             category_id: ID категории Ozon

#         Returns:
#             Список типов товаров
#         """
#         data = {"category_id": category_id}
#         return self._request("POST", "/v2/product/type", data)

#     def import_products(self, items: list[dict]) -> dict:
#         """
#         Массовая загрузка товаров.

#         Args:
#             items: список товаров для загрузки

#         Returns:
#             Результат импорта с task_id для проверки статуса
#         """
#         data = {"items": items}
#         return self._request("POST", "/v2/product/import", data)

#     def get_import_info(self, task_id: int) -> dict:
#         """
#         Проверить статус загрузки товаров.

#         Args:
#             task_id: ID задачи импорта

#         Returns:
#             Статус импорта
#         """
#         data = {"task_id": task_id}
#         return self._request("POST", "/v2/product/import/info", data)

#     def update_prices(self, prices: list[dict]) -> dict:
#         """
#         Обновить цены товаров.

#         Args:
#             prices: список с ценами [{offer_id, price, old_price, currency_code}]

#         Returns:
#             Результат обновления
#         """
#         data = {"prices": prices}
#         return self._request("POST", "/v1/product/import/prices", data)

#     def update_stocks(self, stocks: list[dict]) -> dict:
#         """
#         Обновить остатки товаров.

#         Args:
#             stocks: список с остатками [{offer_id, stock}]

#         Returns:
#             Результат обновления
#         """
#         data = {"stocks": stocks}
#         return self._request("POST", "/v1/product/import/stocks", data)

#     def upload_images(self, product_id: int, images: list[str]) -> dict:
#         """
#         Загрузить изображения товара.

#         Args:
#             product_id: ID товара в Ozon
#             images: список URL изображений

#         Returns:
#             Результат загрузки
#         """
#         data = {
#             "product_id": product_id,
#             "images": [{"file_name": url} for url in images]
#         }
#         return self._request("POST", "/v1/product/pictures/import", data)


# def book_to_ozon_item(book) -> dict:
#     """
#     Преобразовать книгу из БД в формат Ozon API.

#     Args:
#         book: объект модели Book

#     Returns:
#         Словарь с данными товара для Ozon API
#     """
#     # Базовые атрибуты товара
#     attributes = [
#         {"complex_id": 0, "id": 85, "values": [{"value": book.title}]},  # Название
#         {"complex_id": 0, "id": 9048, "values": [{"value": book.author}]},  # Автор
#         {"complex_id": 0, "id": 8229, "values": [{"value": book.publisher}]},  # Издательство
#     ]

#     # Добавляем опциональные атрибуты
#     if book.isbn:
#         attributes.append({"complex_id": 0, "id": 9461, "values": [{"value": book.isbn}]})

#     if book.publication_year:
#         attributes.append({"complex_id": 0, "id": 9024, "values": [{"value": str(book.publication_year)}]})

#     if book.pages:
#         attributes.append({"complex_id": 0, "id": 9083, "values": [{"value": str(book.pages)}]})

#     if book.series:
#         attributes.append({"complex_id": 0, "id": 9025, "values": [{"value": book.series}]})

#     # Тип переплёта
#     cover_map = {'hard': 'Твердый переплет', 'soft': 'Мягкая обложка'}
#     if book.cover_type:
#         attributes.append({"complex_id": 0, "id": 9084, "values": [{"value": cover_map.get(book.cover_type, 'Твердый переплет')}]})

#     # Формируем основной объект товара
#     item = {
#         "offer_id": book.sku or f"book_{book.id}",
#         "name": book.title[:500],
#         "category_id": int(book.category.ozon_category_id) if book.category else 0,
#         "price": str(book.price),
#         "old_price": str(book.old_price) if book.old_price else "",
#         "vat": f"0.{book.vat_rate}" if book.vat_rate != '0' else "0",
#         "currency_code": "RUB",
#         "attributes": attributes,
#         "type_id": 0,  # 0 = создать новый товар
#     }

#     # Размеры и вес
#     if book.height:
#         item["height"] = int(book.height * 10)  # см → мм
#     if book.width:
#         item["width"] = int(book.width * 10)
#     if book.length:
#         item["depth"] = int(book.length * 10)
#     if book.weight:
#         item["weight"] = int(book.weight * 1000)  # кг → г

#     # Изображения
#     if book.photos:
#         item["images"] = [{"file_name": photo} for photo in book.photos[:15]]

#     # Описание
#     if book.description:
#         item["description"] = book.description[:5000]

#     return item
