# Portal Market Sniper

<div align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue" alt="Python 3.12">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License MIT">
  <br>
  <h3>⚡ High-Speed NFT Sniper Bot</h3>
  <p>
    Automated NFT sniping tool for Telegram Mini-Apps / Marketplaces.<br>
    Автоматический снайпер NFT для маркетплейсов в Telegram Mini-Apps.
  </p>
  <p>
    <a href="#english">English</a> • <a href="#russian">Русский</a>
  </p>
</div>

---

<a name="english"></a>
## 🇬🇧 English

**Portal Market Sniper** is a high-performance, asynchronous bot designed to monitor and automatically purchase undervalued NFTs on the Portal Market. optimized for speed and efficiency using `aiohttp` and smart caching strategies.

### 🚀 Key Features

- **Ultra-Fast Sniping**: Scanning cycle under 0.4s to catch new listings instantly.
- **Smart Analytics**: Uses real-time market data (velocity, trending status) to decide on purchases.
- **Auto-Profit Calculation**: Automatically calculates potential profit based on floor prices.
- **Resilient Architecture**: Built with `asyncio` for high concurrency, including connection pooling and auto-token refresh.
- **Live Dashboard**: Beautiful terminal UI using `rich` library for real-time monitoring.

### 🛠 Tech Stack

- **Core**: Python 3.12, `asyncio`, `aiohttp`
- **Configuration**: `pydantic-settings` (.env management)
- **UI**: `rich` (console dashboard)
- **Logging**: `structlog` (JSON/Console logs)
- **Quality**: Type-checked with `mypy` (strict mode)

### 📦 Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/h-nft-sniper-bot.git
   cd h-nft-sniper-bot
   ```

2. **Set up virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

### ⚙️ Configuration

1. Copy the example configuration file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your credentials:
   - `API_ID`, `API_HASH`: Get from [my.telegram.org](https://my.telegram.org)
   - `APORTALS_AUTH`: Your marketplace auth token (Bearer ...). Get this from your browser's local storage/cookies after logging into portal-market.com.

3. Customize strategy settings in `.env`:
   - `MIN_PROFIT`: Minimum profit required to trigger a buy (e.g., 0.3 TON).
   - `SCAN_DELAY`: Delay between scans in seconds (default 0.4s).

4. **Authorization & Sessions**:
   - On the first run, the bot will ask for your Telegram phone number and 2FA code.
   - This creates a session file in `data/sessions/`.
   - **Security Note**: This directory is git-ignored. Never share your session files!
   - The session is used to automatically refresh your `APORTALS_AUTH` token if it expires.

### 🏃‍♂️ Usage

Run the bot using the included script (handles meaningful restarts):
```bash
./run_bot.sh
```

Or manually:
```bash
python src/main.py
```

---

<a name="russian"></a>
## 🇷🇺 Русский

**Portal Market Sniper** — это высокопроизводительный асинхронный бот для мониторинга и автоматической покупки недооцененных NFT на Portal Market. Оптимизирован для скорости и эффективности, использует продвинутые стратегии кэширования и аналитики.

### 🚀 Основные возможности

- **Сверхбыстрый снайпинг**: Цикл сканирования менее 0.4 сек позволяет перехватывать новые листинги мгновенно.
- **Умная аналитика**: Использует реальные рыночные данные (скорость продаж, тренды) для принятия решений о покупке.
- **Авто-расчет профита**: Автоматически считает потенциальную прибыль на основе флор-прайса.
- **Устойчивая архитектура**: Построен на `asyncio` для высокой конкурентности, включает пул соединений и авто-обновление токена.
- **Live Dashboard**: Красивый интерфейс в терминале на базе библиотеки `rich` для мониторинга в реальном времени.

### 🛠 Технологический стек

- **Ядро**: Python 3.12, `asyncio`, `aiohttp`
- **Конфигурация**: `pydantic-settings` (управление .env)
- **UI**: `rich` (консольный дашборд)
- **Логирование**: `structlog` (JSON/Console логи)
- **Качество**: Строгая типизация через `mypy`

### 📦 Установка

1. **Клонируйте репозиторий**
   ```bash
   git clone https://github.com/your-username/h-nft-sniper-bot.git
   cd h-nft-sniper-bot
   ```

2. **Настройте виртуальное окружение**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # На Windows: .venv\Scripts\activate
   ```

3. **Установите зависимости**
   ```bash
   pip install -r requirements.txt
   ```

### ⚙️ Настройка

1. Скопируйте файл примера конфигурации:
   ```bash
   cp .env.example .env
   ```

2. Отредактируйте `.env` и заполните ваши данные:
   - `API_ID`, `API_HASH`: Получите на [my.telegram.org](https://my.telegram.org).
   - `APORTALS_AUTH`: Ваш токен авторизации маркетплейса (Bearer ...). Взять можно из Local Storage/Cookies браузера после входа на portal-market.com.

3. Настройте стратегию в `.env`:
   - `MIN_PROFIT`: Минимальный профит для покупки (например, 0.3 TON).
   - `SCAN_DELAY`: Задержка между сканированиями в секундах (по умолчанию 0.4с).

4. **Авторизация и Сессии**:
   - При первом запуске бот попросит ввести номер телефона Telegram и код 2FA.
   - Это создаст файл сессии в `data/sessions/`.
   - **Важно**: Эта директория добавлена в `.gitignore`. Никогда не делитесь файлами сессий!
   - Сессия используется для автоматического обновления токена `APORTALS_AUTH`, если он истечет.

### 🏃‍♂️ Запуск

Запустите бота с помощью скрипта (авто-перезапуск при ошибках):
```bash
./run_bot.sh
```

Или вручную:
```bash
python src/main.py
```

---

## ⚠️ Disclaimer / Отказ от ответственности

**EN**: This software is for educational purposes only. Use at your own risk. The authors are not responsible for any financial losses or bans.

**RU**: Это программное обеспечение предназначено только для образовательных целей. Используйте на свой страх и риск. Авторы не несут ответственности за любые финансовые потери или баны аккаунтов.

## 📄 License / Лицензия

Distributed under the MIT License. See `LICENSE` for more information.
Распространяется под лицензией MIT. Подробнее см. в файле `LICENSE`.
