# Статус проверок

## Среда ChatGPT — 13.11.2026

- `npm test`: 27/27 пройдены (Node.js 22), математическая модель.
- `node --check` для `sim/engine.mjs` и `games/snake/main.mjs`: пройден.
- Исходный сайт `https://dobrycola-promo.ru/games/snake/` не удалось открыть из текущего окружения; исходный JS и механика не извлечены.
- Локальный сервер отвечает HTTP 200.
- **Browser smoke / extension smoke: НЕ ПРОЙДЕНЫ и НЕ ЗАПУЩЕНЫ ДО КОНЦА**. Chromium окружения запрещает навигацию и загрузку расширений политиками `URLBlocklist=["*"]`, `ExtensionInstallBlocklist=["*"]`; Playwright получил `net::ERR_BLOCKED_BY_ADMINISTRATOR` уже при загрузке локальной страницы. Без успешного браузерного прогона нельзя говорить, что расширение успешно прошло реальную игру.
- CI workflow создан, но успешный запуск GitHub Actions нужно подтвердить отдельно.

## Что считается успешным E2E

1. На экране появляется кнопка «Играть» и скрипт запускает игру.
2. Расширение установлено браузером и его MV3 service worker активен.
3. В журнале есть `ВВОД ПОДТВЕРЖДЁН CDP` и подтверждённые повороты.
4. После минимум 60 секунд нет ложного `planner-requested-180-degree-turn`.
5. Проверка подарков в углах и на краях не вызывает гибели и пропусков.
6. Проверка на исходном сайте после симулятора обязательна.

## Harness correction — 13.11.2026

- The first local extension-smoke attempt failed before the START acknowledgement: Playwright lost its direct connection to the MV3 service-worker target (`Worker.evaluate: Could not establish connection`). The HTTP server also raised a Windows socket shutdown error during exception unwinding.
- Runner v0.1.1 replaces direct worker evaluation with a temporary extension-origin bridge page that sends the same `START` runtime message and reads `chrome.storage.local`.
- A JSON report is now created before browser launch and atomically updated on every exit path, including failure. Browser and HTTP server cleanup are handled in `finally`.
- This is a harness fix only. It does not modify or certify extension v0.6.9.


## Stable baseline selection — 13.11.2026

- User selected extension v0.6.7 as the stable reference baseline: `ice-snake-bot-v0.6.7-gift-only-cycle-lookahead.zip`.
- v0.6.9 is not the baseline and is held aside pending separate review.
- The v0.6.9 extension-smoke report showed START acknowledged, then Canvas fallback could not restore semantic sprites and intentionally sent no keys. The simulator then moved straight into the wall. This run is invalid as a comparative autopilot-quality test.
- Runner v0.1.2 records page-error stack traces and console errors and searches all `chrome.storage.local` keys for diagnostic text, improving compatibility with older extension builds.
