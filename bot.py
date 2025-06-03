import tkinter as tk
import tkinter
from tkinter import ttk, messagebox
import json
import time
import threading
import random
import alpaca_trade_api as tradeapi
import dotenv
import os
import openai
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

endpoint = "https://models.github.ai/inference"
model = "openai/gpt-4.1"

DATA_FILE = 'equities.json' #store symbols we're trading and levels

# Load environment variables from .env file
dotenv.load_dotenv()
# 
key = os.getenv('APCA_API_KEY_ID')
secret_key = os.getenv('APCA_API_SECRET_KEY')
BASE_URL = os.getenv('APCA_API_BASE_URL')
token = os.getenv('GH_TOKEN')

api = tradeapi.REST(key, secret_key, BASE_URL)

def fetch_portfolio_data():
    positions = api.list_positions()
    portfolio_data = []
    for position in positions:
        portfolio_data.append({
            "symbol": position.symbol,
            "qty": position.qty,
            "avg_entry_price": position.avg_entry_price,
            "current_price": position.current_price,
            "market_value": position.market_value,
            "unrealized_pl": position.unrealized_pl,
            "cost_basis": position.cost_basis,
            "side": 'long'
        })
    return portfolio_data

def fetch_open_orders_():
    orders = api.list_orders(status='open')
    open_orders = []
    for order in orders:
        open_orders.append({
            "symbol": order.symbol,
            "qty": order.qty,
            "side": order.side,
            "type": order.type,
            "limit_price": order.limit_price,
            "status": 'long'
        })
    return open_orders

def fetch_mock_api(sym):
    return {
        "price" : 100
    }


def llm_response(msg):
    portfolio_data = fetch_portfolio_data()

    open_orders = fetch_open_orders_()

    pre_prompt = f"""

    You are an AI Portfolio Manager responsible for analysing my portfolio and providing insights.
    Your tasks are the following:
    1. Evaluate risk exposures of my current holdings
    2. Analyse my open limit orders and their potential impact on my portfolio
    3. Provide insights into the portfolio health, diversification, trade adj. etc
    4. Speculate on the market outlook based on current market conditions
    5. Identify potential market risks and suggest risk management strategies

    Here is my portfolio data:
    {portfolio_data}

    Here are my open limit orders:
    {open_orders}

    Overall, answer the questions with priority having that background. {msg}

    """
    client = ChatCompletionsClient(
    endpoint=endpoint,
    credential=AzureKeyCredential(token),
    )

    response = client.complete(
    messages=[
        {"role": "user", "content": pre_prompt},
    ],
    temperature=1.0,
    top_p=1.0,
    model=model
    )
    return response['choices'][0]['message']['content']

class Tradebot:

    def __init__(self, root):
        self.root = root
        self.root.title("Tradebot")
        self.equities = self.load_equities()
        self.system_running = False # Flag if we're trading equities in our sys

        self.form_frame = tk.Frame(self.root)
        self.form_frame.pack(pady=10)

        # Create a label and entry for the symbol (new equity)
        tk.Label(self.form_frame, text="Symbol:").grid(row=0, column=0)
        self.symbol_entry = tk.Entry(self.form_frame)
        self.symbol_entry.grid(row=0, column=1)

        # Create a label and entry for the level (new equity)
        tk.Label(self.form_frame, text="Level:").grid(row=0, column=2)
        self.levels_entry = tk.Entry(self.form_frame)
        self.levels_entry.grid(row=0, column=3)

        tk.Label(self.form_frame, text="Drawdown%").grid(row=0, column=4)
        self.drawdown_entry = tk.Entry(self.form_frame)
        self.drawdown_entry.grid(row=0, column=5)

        # Create a button to add a new equity
        self.add_equity_button = tk.Button(self.form_frame, text="Add Equity", command=self.add_equity)
        self.add_equity_button.grid(row=0, column=6)

        # Table to display equities
        self.tree = ttk.Treeview(self.root, columns=("Symbol", "Position" , "Entry Price", "Level", "Status"), show='headings')
        for col in ["Symbol", "Position", "Entry Price", "Level", "Status"]:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.pack(pady=10)

        # Create buttons to control
        self.toggle_system_button = tk.Button(root, text="Toggle Selected System", command=self.toggle_selected_system)
        self.toggle_system_button.pack(pady=5)

        self.remove_button = tk.Button(root, text="Remove Selected System", command=self.remove_equity)
        self.remove_button.pack(pady=5)

        #UI
        self.llm_frame = tk.Frame(root)
        self.llm_frame.pack(pady=10)

        self.llm_input = tk.Entry(self.llm_frame, width=50)
        self.llm_input.grid(row=0, column=0, padx=5)

        self.send_button = tk.Button(self.llm_frame, text="Send", command=self.send_message)
        self.send_button.grid(row=0, column=1)

        self.llm_output = tk.Text(root, height=10, width=50, state=tk.DISABLED)
        self.llm_output.pack()

        self.refresh_table()

        self.running = True
        self.auto_update_thread = threading.Thread(target=self.auto_update, daemon =True)
        self.auto_update_thread.start()

    def add_equity(self):
        symbol = self.symbol_entry.get().upper()
        level = self.levels_entry.get().strip()
        drawdown = self.drawdown_entry.get().strip()

        if not symbol or not level.isdigit() or not drawdown.replace('.', '', 1).isdigit():
            messagebox.showerror("Input Error", "Please fill in all fields.")
            return
        
        level = int(level)
        drawdown = float(drawdown)/100
        entry_price = fetch_mock_api(symbol)["price"]

        level_prices = {i + 1 : round(entry_price * (1 - drawdown * (i+1)), 2) for i in range(level)}

        self.equities[symbol] = {
            "position" : 0,
            "entry_price" : entry_price,
            "level": level_prices, 
            "drawdown" : drawdown,
            "status" : "Off"
            }
        self.save_equities()
        self.refresh_table()

    def toggle_selected_system(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showerror("Selection Error", "Please select a system to toggle.")
            return
        for item in selected_item:
            sym = self.tree.item(item, "values")[0]
            if self.equities[sym]["status"] == "Off":
                self.equities[sym]["status"] = "On"
            else:
                self.equities[sym]["status"] = "Off"

        self.save_equities()
        self.refresh_table()

    def remove_equity(self):
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a system to remove.")
            return
        for item in selected_item:
            sym = self.tree.item(item, "values")[0]
            del self.equities[sym]

        self.save_equities()
        self.refresh_table()

    def send_message(self):
        message = self.llm_input.get()
        if not message:
            return
        response = llm_response(m)

        self.llm_output.config(state=tk.NORMAL)
        self.llm_output.insert(tk.END, f"You: {message}\n")
        self.llm_output.config(state=tk.DISABLED)
        self.llm_input.delete(0, tk.END)
    
    def fetch_data(self, sym):
        try:
            barset = api.get_latest_trade(sym)
            return {"price": barset.price}
        except Exception as e:
            return {"price": -1}

    def check_existing_orders(self, sym, price):
        try:
            orders = api.list_orders(status='open', symbol =sym)
            for order in orders:
                if float(order.limit_price) == price:
                    return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check existing orders: {e}")
        return False

    def get_max_entry_price(self, sym):
        try:
            orders = api.list_orders(status='filled', symbols =[sym], limit=100) #adjust the limit as needed
            price = [float(order.filled_avg_price) for order in orders if order.filled_avg_price and order.symbol == sym]
            return max(price) if price else -1
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get max entry price: {e}")
            return 0
        
    def trade_sym(self):
        for sym, data in self.equities.items():
            if data["status"] == "On":
                position_exists = False
                try:
                    position = api.get_position
                    entry_price = self.get_max_entry_price(sym)
                    if entry_price <= 0:
                        fallback = self.fetch_data(sym)["price"]
                        if fallback > 0:
                            entry_price = fallback
                        else:
                            messagebox.showerror("Error", f"Invalid entry price for {sym}. Cannot place orders.")
                            continue
                    position_exists = True
                except Exception as e:
                    api.submit_order(
                        symbol=sym,
                        qty=1,
                        side='buy',
                        type='market',
                        time_in_force='gtc'
                    )
                    messagebox.showinfo("Order", f"Order placed for {sym} at market price.")
                    time.sleep(2)
                    entry_price = self.get_max_entry_price(sym)
                print(entry_price)
                num_levels = len([k for k in data["level"].keys() if isinstance(k, int) and k > 0])
                level_prices = {i+1: round(entry_price * (1 - data["drawdown"] * (i+1)), 2) for i in range(num_levels)}
                existing_levels = self.equities.get(sym, {}).get("level", {})
                for level, price in level_prices.items():
                    if level not in existing_levels and -level not in existing_levels:
                        existing_levels[level] = price

                self.equities[sym]["level"] = existing_levels
                self.equities[sym]["position"] = 1
                self.equities[sym]["entry_price"] = entry_price

                for level, price in level_prices.items():
                    if level in self.equities[sym]["level"]:
                        self.place_order(sym, price, level)

            self.save_equities() 
            self.refresh_table()
        else:
            return
    
    def place_order(self, sym, price, level):
        if price <= 0:
            print(f"⛔ Skipped placing order for {sym}: invalid price {price}")
            return
        if -level in self.equities[sym]["level"] or '-1' in self.equities[sym]["level"].keys():
            print(f"⚠️ Skipped {sym} level {level}: already placed (found -{level})")
            return
        try:
            api.submit_order(
                symbol=sym,
                qty=1,
                side='buy',
                type='limit',
                limit_price=price,
                time_in_force='gtc'
            )
            self.equities[sym]["level"][-level] = price
            del self.equities[sym]["level"][level]
            print(f"✅ Order placed for {sym} at limit price {price}.")
        except Exception as e:
            print(f"❌ Error placing order for {sym}: {e}")
            messagebox.showerror("Error", f"Failed to place order: {e}")
        


    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for sym, data in self.equities.items():
            self.tree.insert("", "end", values=(sym, data["position"], data["level"], data["entry_price"], data["status"]))

    def auto_update(self):
        while self.running:
            time.sleep(5)
            self.trade_sym()
            
    def save_equities(self):
        with open(DATA_FILE, 'w') as f:
            json.dump(self.equities, f)
    
    def load_equities(self):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Failed to load equities data.")
            return {}
    
    def on_closing(self):
        self.running = False
        self.save_equities()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    tradebot = Tradebot(root)
    root.protocol("WM_DELETE_WINDOW", tradebot.on_closing)
    root.mainloop()
