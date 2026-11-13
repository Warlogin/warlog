# Ice Snake Test Lab — независимый испытательный стенд

Это самостоятельная **приближённая** модель игры «Ледовая змейка» для разработки и тестирования расширения Chrome. Это **не оригинальная игра** и **не копия исходного кода** рекламного сайта. Код, графика и генератор сценариев написаны для данного стенда.

## Что уже воспроизведено

- Поле 18×10, шаг 40 px, оригинальная геометрическая область Canvas 1148×646.
- Начальная позиция головы (514,344), направление вправо, длина 3.
- Непрерывное движение с начальной скоростью ~236 px/s, очередь поворотов по стрелкам, отказ от немедленного разворота на 180°, Space для паузы.
- Отрисовка отдельных `moose`, `red`, `blue`, `gift`, `girl`, `flake`, `drift`, `speed`, `rink` через `canvas.drawImage` с ожидаемыми именами PNG; элемент `#snakeCanvas` и показатели `#score`, `#len`, `#best`.
- Начальное окно «Играть», пауза «Продолжить», окончание «Играть заново».
- Появление подарков по фиксированному seed: обычный, все 52 краевые клетки, четыре угла. Подарок = +500.
- Моделирование проблемных последовательностей поворотов: `Right → Up → Left`, `Up → Left → Down`.

**Не подтверждены относительно оригинальной игры:** алгоритм спавна и исчезновения предметов, точные размеры коллизий, тайминг очереди поворотов, поведение бонусов, механика роста, анимационные задержки, реальные картинки и часть правил окончания. Их необходимо калибровать по оригинальному JavaScript или реальным записям кадров.

## Быстрый запуск

```bash
python3 -m pip install Pillow
python3 scripts/generate_assets.py
python3 scripts/server.py
```

Откройте `http://127.0.0.1:8765/games/snake/`.

Сценарии: `?scenario=edge-gifts&seed=42` или `?scenario=corners&seed=42`. Для скорости и таймингов: `?speed=236&spawnMs=1800&ttlMs=14000`. Дополнительный необязательный рост: `?grow=1`.

## Тесты

```bash
npm test
python3 -m pip install playwright Pillow
python3 -m playwright install chromium
python3 scripts/generate_assets.py
python3 scripts/browser_smoke.py
```

Юнит-тесты проверяют математическую модель без браузера. Browser smoke запускает **настоящий Chromium**, движущийся Canvas, стрелки, бонусы и паузу. Это разные уровни проверки.

### Полноценная проверка Chrome-расширения

Внутри ZIP находится **испытательная версия только стенда**. Исходники стороннего расширения не публикуются.

Передайте путь к своему ZIP v0.6.9 (или любой следующей версии):

```bash
python3 scripts/extension_smoke.py \
  --extension-zip /путь/к/ice-snake-bot-v0.6.9-turn-sync-recovery.zip \
  --seconds 60 --scenario edge-gifts --seed 2026 \
  --report extension-smoke-report.json
```

Скрипт извлекает расширение во **временный каталог**, меняет только разрешённый тестовый URL в манифесте, worker и popup, загружает реальное MV3 расширение в Chromium, отправляет `START`, собирает настоящие CDP-команды и журнал, а затем сохраняет `extension-smoke-report.json`. Не используется прямое изменение счёта или состояния игры ботом; диагностический `window.__ICE_SNAKE_LAB__` доступен только тестовому раннеру.

Проводите тесты в обычной собственной среде Chromium. Ограничения корпоративной политики браузера могут запрещать расширения и локальные адреса.

### Extension smoke runner v0.1.1

The extension test uses a temporary extension-origin bridge page to send the START message and read `chrome.storage.local`. It does not call `Worker.evaluate()`, because MV3 service workers can stop between Playwright operations. The report is written atomically before launch and again in a `finally` block, including stage, traceback, browser state, simulator events, and any readable extension log on failure. Windows HTTP server shutdown is also guarded.

After replacing the lab folder with this revision, run the same command as before. The report is saved at the exact path passed to `--report`, even if the browser test fails.

## Автоматическая проверка GitHub

`.github/workflows/check.yml` запускает Node.js тесты и тест браузера на GitHub Actions. Прогон расширения с закрытым исходным кодом запускается **локально** с ZIP; он не загружается на GitHub.

## Оговорка по надёжности

Даже несколько успешных тестовых партий на этом стенде **не гарантируют** работоспособности расширения на сайте производителя. Главное улучшение качества — выявление регрессий до выхода версии и тесты настоящего CDP ввода. Для полного совпадения следует сверить оригинальную JS-механику, если её удастся получить законно через страницу игры.