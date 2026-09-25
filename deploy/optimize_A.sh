#!/usr/bin/env bash
# =============================================================================
# Вариант A — быстрые победы без изменения логики приложения.
#
# Что делает:
#   1. DEBUG=False в .env           — включает кэш шаблонов, убирает запись всех
#                                     SQL в память и закрывает утечку настроек
#   2. Тюнинг PostgreSQL            — ALTER SYSTEM + перезапуск
#   3. gunicorn sync -> gthread     — медленный запрос больше не блокирует всех
#   4. Составной индекс под фильтр издательств — без него фильтры варианта B
#                                     работают ХУЖЕ исходного списка (см. раздел 4)
#   5. Гасит мёртвый деплой /var/www/ready (4 воркера, 96 дней аптайма)
#
# Свойства:
#   * идемпотентен — можно запускать повторно;
#   * все изменяемые файлы бэкапятся в /home/semen/ready/backups/optimize-A-<ts>/;
#   * НЕ трогает код приложения — его деплоят отдельно (git pull + restart).
#
# Использование:
#   bash deploy/optimize_A.sh --dry-run      # показать план, ничего не менять
#   bash deploy/optimize_A.sh                # применить, спросив подтверждение
#   bash deploy/optimize_A.sh --yes           # применить без вопросов
#   bash deploy/optimize_A.sh --yes --skip-indexes   # без индексов
#
# Откат: восстановить файлы из каталога бэкапа, затем
#   sudo systemctl daemon-reload && sudo systemctl restart gunicorn postgresql
#   ALTER SYSTEM RESET <параметр>;   -- для настроек PostgreSQL
# =============================================================================

set -euo pipefail

# ----------------------------- настройки -------------------------------------
APP_DIR="/home/semen/ready"
DB_NAME="shop_admin_db"
SERVICE="gunicorn"
STAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${APP_DIR}/backups/optimize-A-${STAMP}"

DRY_RUN=0
ASSUME_YES=0
SKIP_INDEXES=0

for arg in "$@"; do
    case "$arg" in
        --dry-run)      DRY_RUN=1 ;;
        --yes|-y)       ASSUME_YES=1 ;;
        --skip-indexes) SKIP_INDEXES=1 ;;
        -h|--help)      sed -n '2,28p' "$0"; exit 0 ;;
        *) echo "Неизвестный аргумент: $arg" >&2; exit 2 ;;
    esac
done

# ----------------------------- утилиты ---------------------------------------
log()  { printf '\n\033[1m==> %s\033[0m\n' "$*"; }
info() { printf '    %s\n' "$*"; }
warn() { printf '\033[33m    ! %s\033[0m\n' "$*"; }
die()  { printf '\033[31mОШИБКА: %s\033[0m\n' "$*" >&2; exit 1; }

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '    [dry-run] %s\n' "$*"
    else
        "$@"
    fi
}

psql_db() { sudo -n -u postgres psql -d "$DB_NAME" -X -q -v ON_ERROR_STOP=1 "$@"; }

confirm() {
    [ "$ASSUME_YES" -eq 1 ] && return 0
    [ "$DRY_RUN" -eq 1 ] && return 0
    read -r -p "    Продолжить? [y/N] " answer
    [[ "$answer" =~ ^[Yy]$ ]] || { echo "    Отменено."; exit 0; }
}

# ----------------------------- проверки --------------------------------------
log "Проверка окружения"
[ -d "$APP_DIR" ]                        || die "нет каталога $APP_DIR"
[ -f "${APP_DIR}/.env" ]                 || die "нет ${APP_DIR}/.env"
[ -x "${APP_DIR}/venv/bin/gunicorn" ]    || die "нет venv/bin/gunicorn"
systemctl cat "$SERVICE" >/dev/null 2>&1 || die "нет systemd-юнита $SERVICE"
sudo -n true 2>/dev/null                 || die "нужен sudo без пароля"
info "каталог: $APP_DIR"
info "память: $(free -m | awk '/^Mem:/{print $3" МБ занято из "$2" МБ"}'), swap: $(free -m | awk '/^Swap:/{print $3" МБ из "$2" МБ"}')"

if [ "$DRY_RUN" -eq 0 ]; then
    mkdir -p "$BACKUP_DIR"
    cp -a "${APP_DIR}/.env"    "${BACKUP_DIR}/env.bak"
    systemctl cat "$SERVICE" > "${BACKUP_DIR}/gunicorn.service.bak"
    sudo -n -u postgres psql -d "$DB_NAME" -X -q -c \
        "SELECT name, setting, unit FROM pg_settings WHERE name IN \
        ('shared_buffers','effective_cache_size','work_mem','maintenance_work_mem','track_io_timing');" \
        > "${BACKUP_DIR}/pg_settings_before.txt" 2>/dev/null || true
    info "бэкап: $BACKUP_DIR"
fi

# -----------------------------------------------------------------------------
log "1/5. DEBUG=False"
if grep -qE '^DEBUG=True' "${APP_DIR}/.env"; then
    info "DEBUG=True -> False"
    run sed -i 's/^DEBUG=True/DEBUG=False/' "${APP_DIR}/.env"
elif grep -qE '^DEBUG=False' "${APP_DIR}/.env"; then
    info "DEBUG уже False — пропускаем"
else
    warn "строка DEBUG= в .env не найдена, добавьте вручную: DEBUG=False"
fi
info "ALLOWED_HOSTS:        $(grep -E '^ALLOWED_HOSTS' "${APP_DIR}/.env" | cut -d= -f2-)"
info "CSRF_TRUSTED_ORIGINS: $(grep -E '^CSRF_TRUSTED_ORIGINS' "${APP_DIR}/.env" | cut -d= -f2-)"

# -----------------------------------------------------------------------------
log "2/5. Тюнинг PostgreSQL"
info "shared_buffers       128MB -> 192MB  (таблица 937 МБ, cache hit ~60 %)"
info "effective_cache_size 485MB -> 640MB  (подсказка планировщику, RAM не занимает)"
info "work_mem               4MB -> 16MB   (сейчас сортировки уходят на диск)"
info "maintenance_work_mem  64MB -> 128MB"
info "track_io_timing         off -> on"
warn "shared_buffers НЕ поднят до 256MB сознательно: всего 961 МБ RAM, swap уже занят."
warn "max_parallel_workers_per_gather НЕ трогаем: замерено, что 0 делает COUNT(*)"
warn "  МЕДЛЕННЕЕ (5.5 с против 4.7 с) — на 1 vCPU параллельный скан всё равно выигрывает."
warn "random_page_cost НЕ трогаем: замерено, что 1.1 не меняет план и не ускоряет."
confirm

if [ "$DRY_RUN" -eq 0 ]; then
    psql_db <<'SQL'
ALTER SYSTEM SET shared_buffers = '192MB';
ALTER SYSTEM SET effective_cache_size = '640MB';
ALTER SYSTEM SET work_mem = '16MB';
ALTER SYSTEM SET maintenance_work_mem = '128MB';
ALTER SYSTEM SET track_io_timing = on;
SQL
    info "настройки записаны, перезапускаю PostgreSQL (shared_buffers требует restart)"
    sudo -n systemctl restart postgresql
    sudo -n systemctl is-active --quiet postgresql || die "PostgreSQL не поднялся"
    psql_db -c "SELECT name, setting, unit FROM pg_settings WHERE name IN \
        ('shared_buffers','effective_cache_size','work_mem','maintenance_work_mem','track_io_timing') ORDER BY name;"
fi

# -----------------------------------------------------------------------------
log "3/5. gunicorn: sync 2 воркера -> gthread 2x4"
info "сейчас 2 sync-воркера: два медленных запроса блокируют весь сайт"
info "и timeout 30 с — из-за этого в логе уже 283 таймаута"
confirm

if [ "$DRY_RUN" -eq 0 ]; then
    sudo -n tee /etc/systemd/system/gunicorn.service >/dev/null <<EOF
[Unit]
Description=Горы Книг — Gunicorn daemon
After=network.target postgresql.service

[Service]
User=semen
Group=semen
WorkingDirectory=/home/semen/ready
EnvironmentFile=/home/semen/ready/.env
ExecStart=/home/semen/ready/venv/bin/gunicorn \\
    --workers 2 \\
    --threads 4 \\
    --worker-class gthread \\
    --timeout 120 \\
    --graceful-timeout 30 \\
    --bind unix:/home/semen/ready/ready.sock \\
    --log-level=info \\
    --access-logfile /home/semen/ready/logs/gunicorn_access.log \\
    --error-logfile /home/semen/ready/logs/gunicorn_error.log \\
    shop_admin.wsgi:application

[Install]
WantedBy=multi-user.target
EOF
    sudo -n systemctl daemon-reload
    sudo -n systemctl restart "$SERVICE"
    info "gunicorn перезапущен"
fi

# -----------------------------------------------------------------------------
log "4/5. Составной индекс под фильтр издательств"
cat <<'NOTE'
    Зачем именно он.

    Админка сортирует список по created_at DESC с LIMIT 100. Когда применён
    фильтр по издательству, планировщик идёт по индексу created_at назад и
    отбрасывает всё, что не подходит. Замерено на проде:

        WHERE publisher = 'Издательство АСТ'   -> Rows Removed by Filter: 457 067
        WHERE publisher = 'Издательство "Эксмо"' -> страница открывалась 101 с

    Книги в таблице не сгруппированы по издательству (АСТ импортирован раньше,
    последние строки — почти целиком Эксмо), поэтому «свежий» индекс приходится
    просматривать почти насквозь.

    Индекс (publisher, created_at DESC) превращает это в чтение ровно 100 строк
    индекса. Без него фильтры варианта B медленнее, чем исходный список.

    ВАЖНО: CREATE INDEX CONCURRENTLY на 726 237 строк и одном ядре занимает
    минуты и заметно грузит диск — лучше запускать ночью.
NOTE
warn "Индекс (publication_year, created_at DESC) НЕ создаём: замерено, что периоды"
warn "  и так работают за 0.4-1100 мс — worst case 'до 1950' = 1.1 с. Не нужен."

if [ "$SKIP_INDEXES" -eq 0 ]; then
    confirm
    if [ "$DRY_RUN" -eq 0 ]; then
        INDEX_NAME="book_publisher_created_idx"
        if psql_db -tAc "SELECT 1 FROM pg_class WHERE relname='${INDEX_NAME}'" | grep -q 1; then
            info "индекс ${INDEX_NAME} уже есть — пропускаем"
        else
            info "создаю ${INDEX_NAME} (может занять несколько минут)..."
            t0=$SECONDS
            # CONCURRENTLY нельзя выполнять внутри транзакции -> отдельный -c
            sudo -n -u postgres psql -d "$DB_NAME" -X -q -v ON_ERROR_STOP=1 \
                -c "CREATE INDEX CONCURRENTLY IF NOT EXISTS ${INDEX_NAME} ON admin_panel_book (publisher, created_at DESC);"
            info "${INDEX_NAME} готов за $((SECONDS - t0)) с"
        fi

        INVALID="$(psql_db -tAc "SELECT count(*) FROM pg_index WHERE NOT indisvalid;" | tr -d '[:space:]')"
        if [ "${INVALID:-0}" -gt 0 ]; then
            warn "после CONCURRENTLY осталось невалидных индексов: ${INVALID}"
            warn "посмотрите их: SELECT indexrelid::regclass FROM pg_index WHERE NOT indisvalid;"
            warn "такие индексы надо DROP и создать заново"
        else
            info "все индексы валидны"
        fi

        info "обновляю статистику таблицы"
        psql_db -c "ANALYZE admin_panel_book;"
    fi
fi

# -----------------------------------------------------------------------------
log "5/5. Мёртвый деплой /var/www/ready"
OLD_PIDS="$(pgrep -f '/var/www/ready' || true)"
if [ -n "$OLD_PIDS" ]; then
    info "найдены процессы: $(echo "$OLD_PIDS" | tr '\n' ' ')"
    info "nginx проксирует только на /home/semen/ready/ready.sock (проверено ss -xlpn)"
    info "свой сокет этот gunicorn не слушает, каталог /var/www/ready уже удалён"
    confirm
    run sudo -n pkill -f '/var/www/ready' || true
    if [ "$DRY_RUN" -eq 0 ]; then
        sleep 1
        info "осталось процессов: $(pgrep -f '/var/www/ready' | wc -l)"
    fi
else
    info "процессов нет — пропускаем"
fi

# -----------------------------------------------------------------------------
log "Итог"
if [ "$DRY_RUN" -eq 1 ]; then
    echo "    Это был dry-run. Ничего не изменено."
    exit 0
fi
sudo -n systemctl is-active --quiet "$SERVICE"    && info "gunicorn:   работает" || die "gunicorn не поднялся!"
sudo -n systemctl is-active --quiet postgresql    && info "postgresql: работает" || die "postgresql не поднялся!"
info "память: $(free -m | awk '/^Mem:/{print $3" МБ занято из "$2" МБ"}'), swap: $(free -m | awk '/^Swap:/{print $3" МБ из "$2" МБ"}')"
echo
echo "    Проверьте страницу: https://v3144166.hosted-by-vdsina.ru/admin/admin_panel/eksmobook/"
echo "    Точные замеры:      python deploy/measure_admin.py"
echo
echo "    Бэкап для отката:   $BACKUP_DIR"
echo "    Следите за swap:    watch -n5 free -m   (растёт — верните shared_buffers 128MB)"
