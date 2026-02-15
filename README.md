# ValutaTrade Hub

Консольное приложение для отслеживания и симуляции торговли валютами (фиат + крипто). Два сервиса: **Core Service** (регистрация, портфель, сделки) и **Parser Service** (автоматический сбор курсов с CoinGecko и ExchangeRate-API).

## Структура проекта

```
project3_Bakoev_Faridun/
├── data/
│    ├── users.json               # пользователи
│    ├── portfolios.json          # портфели и кошельки
│    ├── rates.json               # локальный кеш курсов (Core Service)
│    └── exchange_rates.json      # история курсов (Parser Service)
├── valutatrade_hub/
│    ├── __init__.py
│    ├── logging_config.py        # настройка логов (RotatingFileHandler)
│    ├── decorators.py            # @log_action (логирование операций)
│    ├── core/
│    │    ├── __init__.py
│    │    ├── currencies.py       # ABC Currency, FiatCurrency, CryptoCurrency
│    │    ├── exceptions.py       # InsufficientFundsError, CurrencyNotFoundError, ApiRequestError
│    │    ├── models.py           # классы User, Wallet, Portfolio
│    │    ├── usecases.py         # бизнес-логика (buy/sell/get-rate/register/login)
│    │    └── utils.py            # хеширование паролей, валидация
│    ├── infra/
│    │    ├── __init__.py
│    │    ├── settings.py         # Singleton SettingsLoader (TTL, пути, конфиг)
│    │    └── database.py         # Singleton DatabaseManager (JSON-хранилище)
│    ├── parser_service/
│    │    ├── __init__.py
│    │    ├── config.py           # ParserConfig (API-ключи, эндпоинты, валюты)
│    │    ├── api_clients.py      # BaseApiClient, CoinGeckoClient, ExchangeRateApiClient
│    │    ├── updater.py          # RatesUpdater (координатор обновления)
│    │    ├── storage.py          # RatesStorage (атомарная запись rates/history)
│    │    └── scheduler.py        # Scheduler (периодическое обновление)
│    └── cli/
│         ├── __init__.py
│         └── interface.py        # командный интерфейс (CLI)
├── logs/                         # логи действий (actions.log, ротация)
├── main.py                       # точка входа
├── .env                          # API-ключ (НЕ в git)
├── Makefile
├── poetry.lock
├── pyproject.toml
├── README.md
└── .gitignore
```

## Установка

```bash
git clone https://github.com/frdnfrdn/project3_Bakoev_Faridun.git
cd project3_Bakoev_Faridun
make install
```

## Настройка API-ключа

Для получения реальных фиатных курсов нужен бесплатный ключ ExchangeRate-API:

1. Зарегистрируйтесь на [exchangerate-api.com](https://www.exchangerate-api.com/)
2. Создайте файл `.env` в корне проекта:

```
EXCHANGERATE_API_KEY=ваш_ключ
```

Файл `.env` включён в `.gitignore` и не попадает в git.
Криптовалюты (CoinGecko) работают без ключа.

## Запуск

```bash
make project
# или
poetry run project
```

## Кеш и TTL курсов

Курсы хранятся локально в `data/rates.json` (кеш). При запросе `get-rate` проверяется TTL — если данные устарели, приложение сообщит об этом и предложит обновить. TTL настраивается в `SettingsLoader` (по умолчанию 7 дней).

Файл `data/exchange_rates.json` хранит историю всех полученных курсов с метаданными (источник, время запроса, статус-код).

## Команды CLI

### Управление аккаунтом

| Команда | Описание |
|---------|----------|
| `register --username <имя> --password <пароль>` | Регистрация |
| `login --username <имя> --password <пароль>` | Вход в систему |

### Портфель и торговля

| Команда | Описание |
|---------|----------|
| `show-portfolio [--base <валюта>]` | Показать портфель с оценкой |
| `buy --currency <код> --amount <кол-во>` | Купить валюту |
| `sell --currency <код> --amount <кол-во>` | Продать валюту |

### Курсы валют

| Команда | Описание |
|---------|----------|
| `get-rate --from <код> --to <код>` | Курс между двумя валютами |
| `update-rates [--source <coingecko\|exchangerate>]` | Обновить курсы из API |
| `show-rates [--currency <код>] [--top <N>] [--base <валюта>]` | Показать кеш курсов |
| `currencies` | Список поддерживаемых валют |

### Прочее

| Команда | Описание |
|---------|----------|
| `help` | Справка по командам |
| `exit` | Выход из приложения |

## Демо

[![asciicast](https://asciinema.org/a/68U4st9g1jCMVcRf.svg)](https://asciinema.org/a/68U4st9g1jCMVcRf)

Полный цикл: register -> login -> buy/sell -> show-portfolio -> get-rate -> update-rates -> show-rates, включая обработку ошибок (недостаточно средств, неизвестная валюта).

## Примеры работы

### Регистрация и покупка

```
vtHub> register --username alice --password test1234
Пользователь 'alice' зарегистрирован (id=1). Войдите: login --username alice --password ****

vtHub> login --username alice --password test1234
Добро пожаловать, alice! (id=1)

vtHub> buy --currency BTC --amount 0.05
Куплено 0.0500 BTC. Баланс: 0.0500 BTC
  Оценочная стоимость: ~2966.86 USD
  [CRYPTO] BTC — Bitcoin (Algo: SHA-256, MCAP: 1.12e+12)

vtHub> show-portfolio
Портфель пользователя 'alice' (id=1)
Общая оценочная стоимость: 2966.86 USD
----------------------------------------
  BTC: 0.0500 (~2966.86 USD)
```

### Курсы и Parser Service

```
vtHub> get-rate --from BTC --to EUR
Курс BTC/EUR: 55013.174485
Обновлено: 2026-02-15T12:00:00
  [CRYPTO] BTC — Bitcoin (Algo: SHA-256, MCAP: 1.12e+12)
  [FIAT] EUR — Euro (Issuing: Eurozone)

vtHub> update-rates
INFO: Starting rates update...
INFO: Fetching from CoinGecko... OK (5 rates)
INFO: Fetching from ExchangeRate-API... OK (5 rates)
INFO: Writing 10 rates to data/rates.json...
Update successful. Total rates updated: 10. Last refresh: 2026-02-15T17:33:10+00:00

vtHub> show-rates --top 3
Rates from cache (updated at 2026-02-15T17:33:10+00:00):
  - BTC_USD: 68927.00
  - ETH_USD: 1996.70
  - SOL_USD: 87.27
```

### Обработка ошибок

```
vtHub> sell --currency BTC --amount 999
Ошибка: Недостаточно средств: доступно 0.0500 BTC, требуется 999.0000 BTC

vtHub> buy --currency UNKNOWN --amount 1
Ошибка: Неизвестная валюта 'UNKNOWN'
Поддерживаемые валюты: BTC, CNY, DOGE, ETH, EUR, GBP, JPY, RUB, SOL, USD, XRP
```

## Архитектура

### Core Service

- **models.py**: `User` (SHA-256 + соль, приватные атрибуты), `Wallet` (`InsufficientFundsError`), `Portfolio` (оценка стоимости)
- **usecases.py**: бизнес-логика с `@log_action`, валидация через `get_currency()`, TTL-проверка кеша
- **currencies.py**: ABC `Currency` -> `FiatCurrency` / `CryptoCurrency`, фабрика `get_currency()`, реестр 11 валют

### Parser Service

- **api_clients.py**: ABC `BaseApiClient` -> `CoinGeckoClient` (крипто) / `ExchangeRateApiClient` (фиат)
- **updater.py**: `RatesUpdater` — отказоустойчивый координатор (один клиент упал — другой продолжает)
- **storage.py**: атомарная запись (tmp -> rename), журнал `exchange_rates.json`, кеш `rates.json`

### Инфраструктура

- **SettingsLoader** (Singleton): пути, TTL, уровень логов
- **DatabaseManager** (Singleton): абстракция над JSON-хранилищем
- **@log_action**: декоратор логирования (INFO/ERROR, verbose before/after)
- **logging_config.py**: RotatingFileHandler (1 МБ, 5 бэкапов)

## Линтер

```bash
make lint
# All checks passed!
```

## Makefile

| Цель | Команда |
|------|---------|
| `make install` | Установить зависимости |
| `make project` | Запустить приложение |
| `make build` | Собрать пакет |
| `make publish` | Опубликовать (dry-run) |
| `make package-install` | Установить из whl |
| `make lint` | Проверка Ruff |

## Технологии

- **Python 3.11+**
- **Poetry** — управление зависимостями
- **requests** — HTTP-клиент для API
- **python-dotenv** — загрузка .env
- **prettytable** — форматированный вывод
- **Ruff** — линтер (PEP8)
- **Стандартная библиотека**: json, shlex, hashlib, logging, abc, threading, datetime

## Автор

Фаридун Бакоев
