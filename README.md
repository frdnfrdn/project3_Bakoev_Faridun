# ValutaTrade Hub

Консольное приложение, имитирующее работу валютного кошелька. Позволяет регистрироваться, покупать и продавать валюты (криптовалюты и фиат), отслеживать портфель и получать актуальные курсы с внешних API.

## Структура проекта

```
project3_Bakoev_Faridun/
├── pyproject.toml                          # Poetry: зависимости, скрипты, ruff
├── Makefile                                # Автоматизация: install, project, lint...
├── README.md
├── valutatrade_hub/                        # Основной пакет
│   ├── main.py                             # Точка входа
│   ├── logging_config.py                   # Настройка логирования с ротацией
│   ├── decorators.py                       # @log_action, @confirm_action, @log_time
│   ├── core/                               # Бизнес-логика
│   │   ├── exceptions.py                   # Доменные исключения
│   │   ├── models.py                       # User, Wallet, Portfolio
│   │   └── usecases.py                     # register, login, buy, sell, get_rate
│   ├── infra/                              # Инфраструктура
│   │   ├── settings.py                     # SettingsLoader (Singleton)
│   │   └── database.py                     # DatabaseManager (Singleton)
│   ├── parser_service/                     # Сервис обновления курсов
│   │   ├── config.py                       # API-ключи, URL, списки валют
│   │   ├── api_clients.py                  # BaseApiClient, CoinGecko, ExchangeRateApi
│   │   ├── storage.py                      # Атомарная запись (tmp → rename)
│   │   └── updater.py                      # RatesUpdater: агрегация источников
│   └── cli/                                # Командный интерфейс
│       └── interface.py                    # REPL-цикл и обработчики команд
└── data/                                   # Данные (JSON-файлы)
    ├── users.json                          # Зарегистрированные пользователи
    ├── portfolios.json                     # Портфели пользователей
    ├── rates.json                          # Текущие курсы валют
    └── exchange_rates.json                 # История обновлений курсов
```

## Установка

```bash
# Клонировать репозиторий
git clone https://github.com/frdnfrdn/project3_Bakoev_Faridun.git
cd project3_Bakoev_Faridun

# Установить зависимости через Poetry
make install
```

## Запуск

```bash
make project
# или
poetry run project
```

## API-ключи

Для получения курсов фиатных валют необходим бесплатный API-ключ от [ExchangeRate-API](https://www.exchangerate-api.com/). После регистрации установите переменную окружения:

```powershell
# PowerShell
$env:EXCHANGE_RATE_API_KEY = "your_api_key_here"
```

```bash
# Bash
export EXCHANGE_RATE_API_KEY="your_api_key_here"
```

Курсы криптовалют (BTC, ETH, SOL, DOGE, XRP) загружаются с CoinGecko без ключа.

## Команды CLI

| Команда                          | Описание                               |
| -------------------------------- | -------------------------------------- |
| `register <username> <password>` | Регистрация нового пользователя        |
| `login <username> <password>`    | Вход в аккаунт                         |
| `logout`                         | Выход из аккаунта                      |
| `show-portfolio`                 | Отобразить портфель с оценкой в USD    |
| `buy <currency> <amount>`        | Купить валюту за USD                   |
| `sell <currency> <amount>`       | Продать валюту за USD                  |
| `get-rate <currency>`            | Показать текущий курс валюты           |
| `update-rates`                   | Обновить курсы с внешних API           |
| `show-rates`                     | Показать все текущие курсы             |
| `help`                           | Справка по командам                    |
| `exit` / `quit`                  | Выход из приложения                    |

## Кэширование курсов и TTL

Курсы валют хранятся в `data/rates.json` с полем `updated_at`. По умолчанию TTL = 3600 секунд (1 час). При попытке купить/продать валюту с устаревшими курсами система выдаст предупреждение и предложит выполнить `update-rates`.

## Parser Service

Сервис обновления курсов (`update-rates`) опрашивает два источника:

- **CoinGecko** — криптовалюты (BTC, ETH, SOL, DOGE, XRP)
- **ExchangeRate-API** — фиатные валюты (EUR, GBP, JPY, RUB, CNY)

Особенности:
- Отказоустойчивость: падение одного источника не останавливает обновление
- Атомарная запись: используется `tmp → rename` для предотвращения повреждения данных
- История: каждое обновление сохраняется в `data/exchange_rates.json`

## Примеры использования

```
ValutaTrade> register alice mypassword
User 'alice' registered successfully!
Starting balance: 10000.00 USD

ValutaTrade> login alice mypassword
Welcome back, alice!

[alice] ValutaTrade> update-rates
Fetching latest exchange rates...
Updated 10 exchange rates successfully!

[alice] ValutaTrade> buy BTC 0.1
Bought 0.1000 BTC for 6700.00 USD (rate: 1 BTC = 67000.0000 USD)

[alice] ValutaTrade> show-portfolio
Portfolio for alice:
+----------+-----------+------------+
| Currency |   Balance | Value (USD) |
+----------+-----------+------------+
| USD      | 3300.0000 |    3300.00 |
| BTC      |    0.1000 |    6700.00 |
+----------+-----------+------------+
Total value: 10000.00 USD

[alice] ValutaTrade> get-rate ETH
1 ETH = 3500.0000 USD  (updated: 2026-02-15T19:30:00)

[alice] ValutaTrade> sell BTC 0.05
Sold 0.0500 BTC for 3350.00 USD (rate: 1 BTC = 67000.0000 USD)

[alice] ValutaTrade> exit
Goodbye!
```

## Линтер

```bash
make lint
# или
poetry run ruff check .
```

## Технологии

- **Python 3.11+**
- **Poetry** — управление зависимостями и сборка пакета
- **prettytable** — форматированный вывод таблиц
- **requests** — HTTP-запросы к API
- **Ruff** — линтер и форматирование (PEP8)
- **Стандартная библиотека**: json, shlex, hashlib, logging, time, os, abc

## Автор

Фаридун Бакоев
