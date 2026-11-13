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


## Восстановление испытательного стенда — 13.11.2026

- Ветка `test/ice-snake-v0610-harness` создана от коммита `715e361`, последнего коммита с успешным GitHub Actions CI.
- Ветка сохраняет независимый симулятор, исходные тестовые спрайты, браузерный smoke и юнит-тесты; рабочая ветка `master` не изменяется.
- В тестовую ветку переносится только актуальный runner `extension_smoke.py` v0.1.3. ZIP расширения в публичный репозиторий не загружается.
- Стабильная база расширения — v0.6.7. Версии v0.6.8 и v0.6.9 не используются как база.
- v0.6.10 — кандидат на проверку, не релиз. Офлайн-пакетные тесты 69/69 пройдены; GitHub CI и отдельный extension smoke для v0.6.10 ещё не подтверждены.
- Критерии выпуска: успешный GitHub Actions CI; затем extension smoke на `seed=2026`, `scenario=edge-gifts`, не менее 60 секунд; анализ JSON и журнала на сетку 18×10, сбор только gift, обход girl, краевые/угловые подарки, подтверждённые и синхронизированные повороты, безопасное продолжение после подбора, отсутствие столкновений и ложной защитной остановки.


## Проверка архива v0.6.10 — 13.11.2026, продолжение

- Проверен именно локальный ZIP `ice-snake-bot-v0.6.10-rink-lock-post-pickup-turn.zip`, SHA-256: `ab2b4be1fdbcc7a2c1d020a6cb4978aea035e64cc0c54d04c67e118aedebd88c`.
- ZIP цел: 52 записи, один MV3 manifest, версия `0.6.10`; состав распакованного расширения — 45 файлов.
- `npm test`, запущенный из точной распаковки ZIP: **69/69 пройдены**.
- `node --check` для всех JavaScript-файлов расширения и vendor-кода: пройден.
- Сравнение с утверждённой v0.6.7: 45 файлов в обеих версиях; 32 файла без изменений; 13 изменены; добавленных/удалённых файлов нет.
- GitHub Actions run `43404138738` для восстановленной ветки: **success**. Он проверяет независимый стенд: 27/27 тестов модели, browser smoke симулятора (подарок +500, ArrowUp, пауза, 0 JS errors), компиляцию тестовых раннеров. Он **не загружает и не запускает ZIP v0.6.10**.
- Локальная попытка открыть Chromium-страницу через Playwright остановлена управляемыми политиками среды: `URLBlocklist=["*"]`, `ExtensionInstallBlocklist=["*"]`; Chromium возвращает `net::ERR_BLOCKED_BY_ADMINISTRATOR`. Политики не обходились.
- **Extension smoke v0.6.10 не выполнен**: расширение не установлено в тестовый Chromium, START/CDP-команд не было, 60-секундной партии и проверки реальной игры нет.
- Решение: v0.6.10 остаётся кандидатом, не релизом. v0.6.7 остаётся стабильной базой. ZIP не загружать в публичный репозиторий; `master` не менять.

### Следующий обязательный шаг

Запустить runner v0.1.3 на машине с обычным Chromium, где разрешены локальная навигация и временная загрузка unpacked MV3 extension, с исходным ZIP v0.6.10, параметрами `--seconds 60 --scenario edge-gifts --seed 2026`. Затем разобрать JSON и лог. Только после успешного extension smoke переходить к отдельной проверке на исходном сайте.


## Итог локальной проверки среды — 13.11.2026

- Точный архив v0.6.10 повторно прошёл 69/69 тестов; все JS-файлы прошли синтаксическую проверку; целостность ZIP подтверждена.
- GitHub Actions run #7 (commit `e9f497e`) завершился успешно: независимый симулятор, browser smoke и компиляция раннеров.
- Локальный extension smoke runner v0.1.4 запущен с системным Chromium. Он остановился на открытии локальной страницы с `net::ERR_BLOCKED_BY_ADMINISTRATOR`. Это зафиксировано как `overall=blocked`, а не как PASS/FAIL алгоритма. До загрузки service worker и START не дошло.
- Для следующего прогона подготовлен пакет `ice-snake-test-lab-v0.1.4.zip`; он усиливает критерии успешного прогона и сохраняет отчёт при блокировке.
- Release gate закрыт: не устанавливать v0.6.10. Стабильная контрольная версия — v0.6.7.
