# в базе данных на сервере 37111 книг с размерами

## база ЭКСМО заняла 55 часов

## zapusk neyrosety

cline
                                                            # or
                                                            cline "your task"

## объединение всех JSON в один

python merge_json.py --input JSON --output merged_books.json

## ssh semen@v3144166.hosted-by-vdsina.ru

### keyGitHub - ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIDB9zQW/iaf6p+Uvx11CZaCYE4UH7qgGOejy750Lz1bE semen@v3144166-ready-deploy

### Всего книг в базе : 12825

Рекомендации для продакшена

### 🚀 Команды для пуша и деплоя

## Важно: перед git push убедись, что большие файлы (JSON > 100 MB) не попадают в коммит — они уже в .gitignore под путями

vBaze/12825_libex.json

### Локально — закоммитить и запушить на GitHub

## Добавить изменения

git add .

## Закоммитить

git commit -m "описание изменений"

## Запушить на GitHub

git push origin main

## На сервере — задеплоить

## Зайти на сервер

## ssh semen@v3144166.hosted-by-vdsina.ru

## Перейти в папку проекта и обновить код

cd /home/semen/ready
git pull origin main

## Активировать venv и применить миграции (если есть изменения в БД)

source venv/bin/activate
python manage.py migrate --noinput

## Собрать статику (если были изменения)

python manage.py collectstatic --noinput

## Перезапустить Gunicorn

sudo systemctl restart gunicorn

## Всё одной строкой (с локальной машины)

## Пуш на GitHub

git add .
git commit -m "update"
git push origin main

## Деплой на сервер

ssh semen@v3144166.hosted-by-vdsina.ru

cd /home/semen/ready

git pull origin main
source venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn

## миграции

source venv/bin/activate
python manage.py migrate
И перезапусти сервис:
sudo systemctl restart gunicorn

## посмотреть на сервере сколько книг имеют размеры 

sudo -u postgres psql -d shop_admin_db -c "SELECT COUNT(*) FROM admin_panel_book WHERE height IS NOT NULL AND length IS NOT NULL AND width IS NOT NULL;"
