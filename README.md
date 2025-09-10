# Binance Futures Risk Manager (USDT-M)

Monitors all **USDT-M futures** positions on Binance.
If your current position’s volume exceeds `MAX_NOTIONAL`, it sends a **reduce-only market** order to trim the excess.

---

## What you need

* Python 3.10+
* Binance API key/secret with **Futures** trading permission
* Dependencies:

  ```txt
  python-binance>=1.0.19
  ```

Install:

```bash
pip install python-binance
# or if you keep a requirements file:
# pip install -r requirements.txt
```

---

## Configure keys & limits

**Choose ONE of the two:**

**A) Hard-code in `risk_manager.py`**

```python
BINANCE_API_KEY_HARDCODE = "your_key"
BINANCE_API_SECRET_HARDCODE = "your_secret"
MAX_NOTIONAL_HARDCODE = 100 # Choose your MAX $Volume    
SLEEP_INTERVAL_HARDCODE = 5
# optional
# MAX_NOTIONAL = Decimal("1100")
# SLEEP_INTERVAL = 5
```

**B) Use environment variables (Windows)**
Open Command Prompt (Run as Administrator if you want system-wide):

```bat
setx BINANCE_API_KEY your_key
setx BINANCE_API_SECRET your_secret
setx MAX_NOTIONAL 1100
setx SLEEP_INTERVAL 5
```

> Open a **new** terminal/window after `setx` so the variables are available.

---

## Test run

```bash
python risk_manager.py
```

You should see lines like:

```
BTCUSDT   | qty=+0.025000 @ 58000.00000000 -> $1450.00
BTCUSDT: closed excess 0.006 (orderId=123456789)
```

Logs are also written to `risk_manager.log` (same folder as the script).

---

## Run in background on Windows (hidden)

1. Create `windows_start_hidden.vbs` (adjust both paths):

```vb
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:/Path/To/Python/python.exe"" ""C:/Path/To/risk_manager/risk_manager.py""", 0
```

2. Task Scheduler

* **Action**: *Start a program* → `wscript.exe`
* **Arguments**: `C:\Path\To\risk_manager\windows_start_hidden.vbs`
* **Trigger**: *At log on* (or your schedule)
* **General**: *Run whether user is logged on or not* (optional)

That’s it: the script runs headless and trims any position above your cap.

---

## Notes

* `MAX_NOTIONAL` is the per-position USD cap. Default: `100`.
* `SLEEP_INTERVAL` is the poll interval in seconds. Default: `5`.
