# Binance Futures Testnet Trading Bot

A **Python-based trading bot** for **Binance Futures Testnet** that supports **market, limit, and stop-limit orders** with robust logging, error handling, and both **interactive and CLI modes**.

---

## Features

* Place **Market Orders** (`BUY`/`SELL`)
* Place **Limit Orders** (`BUY`/`SELL`)
* Place **Stop-Limit Orders**
* Adjust order **quantity** and **price** according to symbol requirements
* View **account balance** and **positions**
* Cancel orders and check **order status**
* View **open orders**
* Close all or specific positions
* Supports both **interactive menu mode** and **command-line arguments**
* Logging to `trading_bot.log` with timestamps

---

## Installation

1. **Clone the repository**

```bash
git clone <repository_url>
cd <repository_folder>
```

2. **Install dependencies**

```bash
pip install python-binance
```

3. **Optional: Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # Linux / Mac
venv\Scripts\activate     # Windows
```

---

## Setup Binance Testnet API

1. Go to [Binance Futures Testnet](https://testnet.binancefuture.com/).
2. Create an account or log in.
3. Navigate to **API Management** and generate a **Testnet API Key and Secret**.
4. Keep the API key and secret secure.

> ⚠️ **Important:** Use the Testnet for testing. Never use real funds until thoroughly tested.

---

## Usage

### Interactive Mode

Run the script without arguments:

```bash
python trading_bot.py
```

You will be prompted for:

* Binance Testnet API Key & Secret
* Interactive menu to:

  * Place orders (market, limit, stop-limit)
  * Check order status
  * Cancel orders
  * View open orders
  * View account balance
  * View positions
  * Close positions

### Command-Line Mode (Optional)

#### Place a Market Order

```bash
python trading_bot.py --api-key YOUR_API_KEY --api-secret YOUR_API_SECRET --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

#### Place a Limit Order

```bash
python trading_bot.py --api-key YOUR_API_KEY --api-secret YOUR_API_SECRET --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 30000
```

#### Place a Stop-Limit Order

```bash
python trading_bot.py --api-key YOUR_API_KEY --api-secret YOUR_API_SECRET --symbol BTCUSDT --side SELL --type STOP_LIMIT --quantity 0.001 --price 30050 --stop-price 30020
```

#### View Account Balance

```bash
python trading_bot.py --api-key YOUR_API_KEY --api-secret YOUR_API_SECRET --balance
```

#### View Open Orders

```bash
python trading_bot.py --api-key YOUR_API_KEY --api-secret YOUR_API_SECRET --open-orders
```

---

## Logging

All bot activity is logged to `trading_bot.log` with:

* Timestamps
* Log levels (INFO, ERROR)
* Details of orders placed, cancelled, or failed

Example log entry:

```
2025-12-03 18:15:00 - __main__ - INFO - Placing market order: BTCUSDT BUY 0.001
```

---

## Notes

* **Testnet Only:** By default, the bot connects to Binance Futures Testnet. Change the `testnet` flag to `False` in `TradingBot` initialization for Mainnet (use with caution).
* **Quantity & Price Adjustment:** The bot automatically adjusts quantities and prices according to Binance’s **LOT_SIZE** and **PRICE_FILTER** requirements.
* **Error Handling:** Includes API, order, and request exceptions to prevent crashes.

---

## Requirements

* Python 3.8+
* [python-binance](https://pypi.org/project/python-binance/)

Install via:

```bash
pip install python-binance
```

---


