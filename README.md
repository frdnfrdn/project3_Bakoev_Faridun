# ValutaTrade Hub

Консольное приложение — платформа для отслеживания и симуляции торговли валютами. Позволяет регистрироваться, управлять виртуальным портфелем фиатных и криптовалют, совершать сделки по покупке/продаже и отслеживать курсы.

## Структура проекта

```
project3_Bakoev_Faridun/
├── data/
│    ├── users.json             # список пользователей
│    ├── portfolios.json        # портфели и кошельки
│    └── rates.json             # курсы валют (заглушка/кеш)
├── valutatrade_hub/
│    ├── __init__.py
│    ├── core/
│    │    ├── __init__.py
│    │    ├── models.py         # классы User, Wallet, Portfolio
│    │    ├── utils.py          # JSON I/O, хеширование, валидация
│    │    └── usecases.py       # бизнес-логика
│    └── cli/
│         ├── __init__.py
│         └── interface.py      # командный интерфейс
├── main.py                     # точка входа
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

## Запуск

```bash
make project
# или
poetry run project
```

## Команды CLI

| Команда | Описание |
|---------|----------|
| `register --username <имя> --password <пароль>` | Регистрация |
| `login --username <имя> --password <пароль>` | Вход в систему |
| `logout` | Выход из аккаунта |
| `show-portfolio [--base <валюта>]` | Показать портфель |
| `buy --currency <код> --amount <кол-во>` | Купить валюту |
| `sell --currency <код> --amount <кол-во>` | Продать валюту |
| `get-rate --from <валюта> --to <валюта>` | Курс валют |
| `help` | Справка |
| `exit` / `quit` | Выход |

## Примеры

```
> register --username alice --password 1234
Пользователь 'alice' зарегистрирован (id=1). Войдите: login --username alice --password ****

> login --username alice --password 1234
Вы вошли как 'alice'

[alice] > buy --currency BTC --amount 0.05
Покупка выполнена: 0.0500 BTC по курсу 59337.21 USD/BTC
Изменения в портфеле:
  - BTC: было 0.0000 -> стало 0.0500
Оценочная стоимость покупки: 2,966.86 USD

[alice] > show-portfolio
Портфель пользователя 'alice' (база: USD):
  - BTC: 0.0500  -> 2966.86 USD
  ---------------------------------
  ИТОГО: 2,966.86 USD

[alice] > get-rate --from USD --to BTC
Курс USD->BTC: 0.00001685 (обновлено: 2026-02-15 12:00:00)
Обратный курс BTC->USD: 59337.21
```

## Линтер

```bash
make lint
```

## Технологии

- **Python 3.11+**
- **Poetry** — управление зависимостями
- **prettytable** — форматированный вывод
- **Ruff** — линтер (PEP8)
- **Стандартная библиотека**: json, shlex, hashlib, os, datetime

## Автор

Фаридун Бакоев
