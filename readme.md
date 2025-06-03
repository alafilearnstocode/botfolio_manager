# 📈 Tradebot: Automated Trading Interface with Alpaca and GPT-4

**Tradebot** is a Python-based trading assistant that combines automated equity trading using a Martingale/DCA strategy with intelligent portfolio analysis powered by GPT-4. It features a basic GUI for managing trading systems and integrates directly with the Alpaca brokerage API.

---

## 🚀 Features

- ✅ Simple user interface built with Tkinter
- 📡 Live integration with [Alpaca](https://alpaca.markets/) for placing limit and market orders
- 🔁 Martingale / Dollar-Cost Averaging (DCA) strategy logic per-symbol
- 🧠 GPT-4-powered LLM responses to analyze portfolio health, risk, diversification, and market outlook
- 💾 Persistent JSON-based configuration for equity positions and strategy levels

---

## 📁 Project Structure

| File | Description |
|------|-------------|
| `bot.py` | Main application script with UI and trade logic |
| `equities.json` | Stores user equity configurations and trade levels |
| `alpaca.ipynb` | Notebook for interacting with Alpaca API |
| `openai.ipynb` | Notebook for testing and analyzing LLM responses |

---

## 🧰 Requirements

- Python 3.8+
- `alpaca-trade-api`
- `python-dotenv`
- `azure-ai-inference`
- `.env` file with the following
  ```env
  APCA_API_KEY_ID=your-alpaca-key
  APCA_API_SECRET_KEY=your-alpaca-secret
  APCA_API_BASE_URL=https://paper-api.alpaca.markets
  GH_TOKEN=your-azure-openai-token