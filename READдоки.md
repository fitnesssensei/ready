# в базе данных на сервере 287244 книг

## важно важно важно

меняй код только через python

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

## ХХХ Деплой на сервер

ssh semen@v3144166.hosted-by-vdsina.ru

cd /home/semen/ready

git pull origin main
source venv/bin/activate 
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn

## полный шаблон деплоя:

cd /home/semen/ready
git fetch origin
git checkout production
git cherry-pick <хеш-коммита>
source venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn

1. Подтянуть изменения с GitHub
git fetch origin

2. Переключиться на продовую ветку
git checkout production

3. Перенести нужный коммит из main
git cherry-pick <хеш-коммита>

4. Активировать виртуальное окружение
source venv/bin/activate

5. Применить миграции (если были изменения в моделях БД)
python manage.py migrate --noinput

6. Собрать статику (если менялись CSS/JS/картинки)
python manage.py collectstatic --noinput

7. Перезапустить Gunicorn
sudo systemctl restart gunicorn

## добавление книг АСТ на сервер

(venv) rustamismagilov@MacBook-Pro-Rustam ready % cat /Users/rustamismagilov/Desktop/ready/JSONSS/hudLitClean.json | ssh semen@v3144166.hosted-by-vdsina.ru "cd /home/semen/ready && source venv/bin/activate && python import_ast.py --stdin"

## добавление книг Либекс на сервер

cat /Users/rustamismagilov/Desktop/ready/JSONSS/30000_libex.json | ssh semen@v3144166.hosted-by-vdsina.ru "cd /home/semen/ready && source venv/bin/activate && python import_books.py --stdin"

## миграции

source venv/bin/activate
python manage.py migrate
И перезапусти сервис:
sudo systemctl restart gunicorn

## посмотреть на сервере сколько книг имеют размеры 

sudo -u postgres psql -d shop_admin_db -c "SELECT COUNT(*) FROM admin_panel_book WHERE height IS NOT NULL AND length IS NOT NULL AND width IS NOT NULL;"

## ip servera  

178.20.41.120

## перенести Один конкретный коммит из Гитхаб в продакшн — cherry-pick
-Когда вы в main сделали один фикс и хотите перенести только его:

# Найти хеш коммита в main (локально на Mac)
git log --oneline -10

# На сервере
cd /home/semen/ready
git fetch origin
git checkout production
git cherry-pick <хеш-коммита>
source venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn

## перенос Несколько коммитов подряд — merge
Когда вы в main накопили несколько изменений и хотите перенести их все разом в production:
На сервере:
cd /home/semen/ready
git fetch origin

## Смержить main в production (приедут все новые коммиты из main)
git checkout production
git merge origin/main

## Если возник конфликт — исправить и продолжить
git add .
git merge --continue
source venv/bin/activate
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart gunicorn

## ⚠️ Нюанс: merge притянет все коммиты из main, включая те, которые вы в прошлый раз не захотели деплоить. Если вы их уже откатили в main через git revert — то при merge приедет и реверт, и сами изменения (они скомпенсируют друг друга).