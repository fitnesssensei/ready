/**
 * TagInputWidget — теговый input для множественных значений
 *
 * Преобразует <input class="vTagInput"> в интерфейс с тегами.
 * Значения хранятся в оригинальном input через разделитель "; ".
 *
 * Поддержка:
 * - Enter для добавления тега
 * - Backspace для удаления последнего тега
 * - Автодополнение через fetch (search_field_view)
 * - Стрелки ↑↓ и Enter для выбора из дропдауна
 * - Escape для закрытия дропдауна
 * - Tab для добавления текущего текста и перехода к следующему полю
 * - Клик вне области для закрытия дропдауна
 * - Touch-события для мобильных
 * - MutationObserver для синхронизации с программными изменениями
 */

(function() {
    'use strict';

    var fieldSearchUrl = null;

    function getFieldSearchUrl() {
        if (fieldSearchUrl) return fieldSearchUrl;
        if (typeof window.__fieldSearchUrl !== 'undefined') {
            fieldSearchUrl = window.__fieldSearchUrl;
            return fieldSearchUrl;
        }
        var el = document.querySelector('[data-search-url]');
        if (el) {
            fieldSearchUrl = el.getAttribute('data-search-url');
            return fieldSearchUrl;
        }
        return null;
    }

    function escapeHtml(text) {
        var d = document.createElement('div');
        d.textContent = text || '';
        return d.innerHTML;
    }

    function splitTags(value, delimiter) {
        if (!value || !value.trim()) return [];
        var items = value.split(delimiter);
        var result = [];
        for (var i = 0; i < items.length; i++) {
            var trimmed = items[i].trim();
            if (trimmed) result.push(trimmed);
        }
        return result;
    }

    function joinTags(tags, delimiter) {
        return tags.join(delimiter);
    }

    function initTagInput(input) {
        if (input.dataset.tagInputInited) return;
        input.dataset.tagInputInited = '1';

        var delimiter = input.getAttribute('data-delimiter') || '; ';
        var searchUrl = getFieldSearchUrl();
        var tags = splitTags(input.value, delimiter);
        var activeDropdownIndex = -1;

        input.style.display = 'none';
        input.setAttribute('autocomplete', 'off');

        var container = document.createElement('div');
        container.className = 'tag-input-container';

        var dropdown = document.createElement('div');
        dropdown.className = 'tag-input-dropdown';
        document.body.appendChild(dropdown);

        var field = document.createElement('input');
        field.type = 'text';
        field.className = 'tag-input-field';
        field.placeholder = input.getAttribute('placeholder') || 'Введите значение, нажмите Enter';
        field.setAttribute('autocomplete', 'off');

        container.appendChild(field);
        input.parentNode.insertBefore(container, input.nextSibling);

        function renderTags() {
            var items = container.querySelectorAll('.tag-item');
            for (var i = 0; i < items.length; i++) items[i].remove();

            for (var i = 0; i < tags.length; i++) {
                var tagEl = document.createElement('span');
                tagEl.className = 'tag-item';
                tagEl.textContent = tags[i];

                var removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'tag-remove';
                removeBtn.innerHTML = '&times;';
                removeBtn.setAttribute('aria-label', 'Удалить: ' + tags[i]);

                (function(idx) {
                    removeBtn.addEventListener('click', function(e) {
                        e.preventDefault(); e.stopPropagation(); removeTag(idx);
                    });
                    removeBtn.addEventListener('touchend', function(e) {
                        e.preventDefault(); e.stopPropagation(); removeTag(idx);
                    });
                })(i);

                tagEl.appendChild(removeBtn);
                container.insertBefore(tagEl, field);
            }

            input.value = joinTags(tags, delimiter);
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }

        function addTag(value) {
            var trimmed = (value || '').trim();
            if (!trimmed) return false;
            for (var i = 0; i < tags.length; i++) {
                if (tags[i].toLowerCase() === trimmed.toLowerCase()) return false;
            }
            tags.push(trimmed);
            renderTags();
            hideDropdown();
            field.value = '';
            field.focus();
            return true;
        }

        function removeTag(index) {
            if (index < 0 || index >= tags.length) return;
            tags.splice(index, 1);
            renderTags();
            field.focus();
        }

        function showDropdown() { dropdown.style.display = 'block'; }

        function hideDropdown() {
            dropdown.style.display = 'none';
            dropdown.innerHTML = '';
            activeDropdownIndex = -1;
        }

        function positionDropdown() {
            var rect = container.getBoundingClientRect();
            dropdown.style.left = rect.left + 'px';
            dropdown.style.top = (rect.bottom + 2) + 'px';
            dropdown.style.width = Math.max(rect.width, 200) + 'px';
        }

        function fetchSuggestions(query) {
            if (!searchUrl || query.length < 1) { hideDropdown(); return; }
            var fieldName = input.name;
            var url = searchUrl + '?field=' + encodeURIComponent(fieldName) + '&q=' + encodeURIComponent(query);
            fetch(url, {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin',
            })
            .then(function(r) { return r.json(); })
            .then(function(data) { renderDropdown(data.results || [], query); })
            .catch(function() { hideDropdown(); });
        }

        function renderDropdown(items, query) {
            dropdown.innerHTML = '';
            if (!items.length) {
                var empty = document.createElement('div');
                empty.className = 'dropdown-empty';
                empty.textContent = 'Нет совпадений';
                dropdown.appendChild(empty);
                showDropdown();
                positionDropdown();
                return;
            }

            var lowerQ = query.toLowerCase();
            for (var i = 0; i < items.length; i++) {
                var item = document.createElement('div');
                item.className = 'dropdown-item';
                item.setAttribute('data-value', items[i]);
                item.setAttribute('role', 'option');

                var text = items[i];
                var idx = text.toLowerCase().indexOf(lowerQ);
                if (idx >= 0) {
                    item.innerHTML = escapeHtml(text.substring(0, idx))
                        + '<strong>' + escapeHtml(text.substring(idx, idx + query.length)) + '</strong>'
                        + escapeHtml(text.substring(idx + query.length));
                } else {
                    item.textContent = text;
                }

                (function(val) {
                    item.addEventListener('click', function(e) { e.preventDefault(); addTag(val); field.focus(); });
                    item.addEventListener('touchend', function(e) { e.preventDefault(); addTag(val); field.focus(); });
                })(items[i]);

                dropdown.appendChild(item);
            }

            activeDropdownIndex = -1;
            showDropdown();
            positionDropdown();
        }

        function selectDropdownItem(index) {
            var items = dropdown.querySelectorAll('.dropdown-item');
            if (index < 0 || index >= items.length) return;
            for (var i = 0; i < items.length; i++) items[i].classList.remove('active');
            items[index].classList.add('active');
            items[index].scrollIntoView({ block: 'nearest' });
        }

        // === События ===

        container.addEventListener('click', function(e) {
            if (e.target === container) field.focus();
        });

        container.addEventListener('touchstart', function(e) {
            if (e.target === container) field.focus();
        }, { passive: true });

        var debounceTimer = null;
        field.addEventListener('input', function() {
            var val = field.value;
            clearTimeout(debounceTimer);
            if (val.length >= 1) {
                debounceTimer = setTimeout(function() { fetchSuggestions(val); }, 300);
            } else {
                hideDropdown();
            }
        });

        field.addEventListener('keydown', function(e) {
            var dItems = dropdown.querySelectorAll('.dropdown-item');

            if (e.key === 'Enter') {
                e.preventDefault();
                if (activeDropdownIndex >= 0 && activeDropdownIndex < dItems.length) {
                    var sel = dItems[activeDropdownIndex].getAttribute('data-value');
                    if (sel) addTag(sel);
                } else {
                    addTag(field.value);
                }
                hideDropdown();
                return;
            }

            if (e.key === 'Backspace') {
                if (field.value === '' && tags.length > 0) {
                    e.preventDefault();
                    removeTag(tags.length - 1);
                }
                return;
            }

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                if (!dItems.length) return;
                activeDropdownIndex = Math.min(activeDropdownIndex + 1, dItems.length - 1);
                selectDropdownItem(activeDropdownIndex);
                return;
            }

            if (e.key === 'ArrowUp') {
                e.preventDefault();
                if (!dItems.length) return;
                activeDropdownIndex = Math.max(activeDropdownIndex - 1, 0);
                selectDropdownItem(activeDropdownIndex);
                return;
            }

            if (e.key === 'Escape') { hideDropdown(); return; }

            if (e.key === 'Tab') {
                hideDropdown();
                if (field.value.trim()) { e.preventDefault(); addTag(field.value); }
            }
        });

        field.addEventListener('blur', function() {
            setTimeout(function() { hideDropdown(); }, 200);
        });

        field.addEventListener('focus', function() {
            if (field.value.length >= 1) fetchSuggestions(field.value);
        });

        // Синхронизация при изменении value оригинального input
        input.addEventListener('change', function() {
            var newTags = splitTags(input.value, delimiter);
            if (JSON.stringify(newTags) !== JSON.stringify(tags)) {
                tags = newTags;
                renderTags();
            }
        });

        var observer = new MutationObserver(function() {
            var newTags = splitTags(input.value, delimiter);
            if (JSON.stringify(newTags) !== JSON.stringify(tags)) {
                tags = newTags;
                renderTags();
            }
        });
        observer.observe(input, { attributes: true, attributeFilter: ['value'] });

        document.addEventListener('click', function(e) {
            if (!dropdown.contains(e.target) && e.target !== field && e.target !== container) {
                hideDropdown();
            }
        });

        document.addEventListener('scroll', function() {
            if (dropdown.style.display !== 'none') positionDropdown();
        }, true);

        window.addEventListener('resize', function() {
            if (dropdown.style.display !== 'none') positionDropdown();
        });

        // Публичный API
        input._tagInput = {
            addTag: addTag,
            removeTag: removeTag,
            getTags: function() { return tags.slice(); },
            setTags: function(newTags) {
                tags = Array.isArray(newTags) ? newTags.slice() : splitTags(String(newTags), delimiter);
                renderTags();
            },
            destroy: function() {
                observer.disconnect();
                container.remove();
                dropdown.remove();
                input.style.display = '';
                delete input.dataset.tagInputInited;
                delete input._tagInput;
            }
        };

        renderTags();
    }

    // === Инициализация ===

    function initAllTagInputs() {
        // Устанавливаем URL поиска полей (если есть на body)
        var bodySearchUrl = document.body && document.body.getAttribute('data-field-search-url');
        if (bodySearchUrl) window.__fieldSearchUrl = bodySearchUrl;

        var inputs = document.querySelectorAll('input.vTagInput');
        for (var i = 0; i < inputs.length; i++) initTagInput(inputs[i]);

        // Запускаем MutationObserver для динамически добавляемых полей
        if (document.body) {
            var mo = new MutationObserver(function(mutations) {
                for (var i = 0; i < mutations.length; i++) {
                    var added = mutations[i].addedNodes;
                    for (var j = 0; j < added.length; j++) {
                        if (added[j].querySelectorAll) {
                            var ni = added[j].querySelectorAll('input.vTagInput');
                            for (var k = 0; k < ni.length; k++) initTagInput(ni[k]);
                        }
                    }
                }
            });
            mo.observe(document.body, { childList: true, subtree: true });
        }
    }

    // Запускаем инициализацию после полной загрузки DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAllTagInputs);
    } else {
        initAllTagInputs();
    }

    window.TagInput = { init: initTagInput, initAll: initAllTagInputs };

})();
