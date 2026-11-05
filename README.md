# Трекер цен с Codex


[![hexlet-check](https://github.com/ako-develop/vibecoding-claudecode-project-388/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/ako-develop/vibecoding-claudecode-project-388/actions)

Учебный трекер цен на скиллах Codex: сбор публичных цен товаров, история прогонов и уведомления о значимых изменениях в Telegram.

## Подготовка

- Рабочий каркас Codex: `.agents/skills/`.
- `extract-price`: `.agents/skills/extract-price/SKILL.md`; идентичная копия для пути из задания — `.claude/skills/extract-price/SKILL.md`.
- `tracker`: `.agents/skills/tracker/SKILL.md`; копия для задания — `.claude/skills/tracker/SKILL.md`. Полная проверка пяти URL: `docs/tracker-check.md`.
- Ниша: SO-DIMM DDR5-5600 2×16 ГБ и Samsung 980 PRO 1–2 ТБ, Россия, RUB.
- Контракт цены: `KNOWLEDGE.md`. Стартовые пять URL: `products.json`; результаты проверки и ограничения: `docs/url-check.md`.
- История хранится отдельно в приватном `ako-develop/tracker-data`: `YYYY-MM-DD.json` в main, дата по Москве. tracker пишет через GitHub MCP без локального клонирования. Повторный запуск за день обновляет снимок новым коммитом. Первая запись и обратное чтение проверены: `docs/storage-check.md`.
- Проверка скилла на трёх карточках: `docs/extract-price-check.md`. Использовано веб-чтение с возможным кешем; результаты не являются подтверждением свежих цен.

Учебный проект Хекслета: https://ru.hexlet.io/programs/vibecoding-claudecode


## Стек

- Разное

## Установка

<!-- Опишите установку: клонирование, зависимости, переменные окружения -->

```bash
git clone https://github.com/ako-develop/vibecoding-claudecode-project-388.git
cd vibecoding-claudecode-project-388
```

## Использование

Сравнение и проверка двух последовательных прогонов: `docs/diff-check.md`. Локальные проверки расчёта: `PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`.

В диалоге с Codex в этом репозитории: «Прочитай скилл tracker и запусти полный обход». Скилл содержит пять URL и использует extract-price для каждой карточки. Результат — только значимые изменения относительно последнего снимка; полный список сохраняется в tracker-data. Порог ±1% и остальные правила находятся в KNOWLEDGE.md. Это сценарий для агента с веб-инструментом, а не отдельная исполняемая программа.

---

<details>
<summary>Автоматические тесты Хекслета</summary>

Тесты запускаются на каждый коммит. За запуск отвечает файл `.github/workflows/hexlet-check.yml` — не удаляйте и не переименовывайте ни его, ни репозиторий.

</details>

## О Хекслете

[Хекслет](https://ru.hexlet.io/) — школа программирования: авторские программы обучения с практикой, поддержкой наставников и реальными проектами, которые остаются в резюме. Этот репозиторий — один из таких проектов.
