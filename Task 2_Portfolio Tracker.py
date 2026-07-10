import http.server
import socketserver
import json
import threading
import webbrowser
import os
import yfinance as yf
import pandas as pd
from datetime import datetime

# --- 1. PORTFOLIO LOGIC & YFINANCE ---
# Aap yahan apne assets aur unki quantity set kar sakti hain
PORTFOLIO = {
    "AAPL": 10,
    "MSFT": 5,
    "TSLA": 8,
    "GOOGL": 12
}

def fetch_live_portfolio():
    print("Fetching live market data from Yahoo Finance...")
    portfolio_data = []
    total_valuation = 0

    for ticker, shares in PORTFOLIO.items():
        try:
            stock = yf.Ticker(ticker)
            # Fetch the latest closing price
            hist = stock.history(period="1d")
            if not hist.empty:
                current_price = float(hist['Close'].iloc[-1])
            else:
                current_price = 0.0
                
            total_value = current_price * shares
            total_valuation += total_value
            
            portfolio_data.append({
                "ticker": ticker,
                "shares": shares,
                "price": round(current_price, 2),
                "value": round(total_value, 2)
            })
            print(f"✅ Fetched {ticker}: ${round(current_price, 2)}")
        except Exception as e:
            print(f"❌ Could not fetch data for {ticker}: {e}")

    # Export to structured Excel sheet automatically
    if portfolio_data:
        df = pd.DataFrame(portfolio_data)
        
        # Calculate Allocation percentage
        if total_valuation > 0:
            df['Allocation (%)'] = round((df['value'] / total_valuation) * 100, 2)
            
        # Format column names for the Excel sheet
        df.rename(columns={
            'ticker': 'Ticker', 
            'shares': 'Shares Owned', 
            'price': 'Current Price (USD)', 
            'value': 'Total Value (USD)'
        }, inplace=True)

        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Portfolio_Summary_{date_str}.xlsx"
        file_path = os.path.abspath(filename)
        df.to_excel(file_path, index=False)
        print(f"📄 Excel Exported Successfully: {filename}")

    return {
        "status": "success",
        "items": portfolio_data,
        "total": round(total_valuation, 2)
    }

# --- 2. LOCAL SERVER & API BRIDGE ---
class PortfolioHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_UI.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == '/api/sync-live-data':
            # Execute yfinance logic
            result = fetch_live_portfolio()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode('utf-8'))

class ReuseAddrServer(socketserver.TCPServer):
    allow_reuse_address = True

# --- 3. DYNAMIC UI (Matches Image with Live Fetching) ---
HTML_UI = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Real-Time Portfolio Tracker</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        body { font-family: 'Inter', sans-serif; background-color: #121212; color: #e5e7eb; }
        .floating-card { transition: all 0.3s ease; box-shadow: 0 10px 30px rgba(0,0,0,0.5); }
        .row-hover { transition: background-color 0.2s ease; }
        .row-hover:hover { background-color: #1f1f1f; }
        .fade-in { animation: fadeIn 0.4s ease-in-out forwards; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
    </style>
</head>
<body class="min-h-screen flex items-center justify-center p-4">

    <div class="floating-card bg-[#181818] rounded-2xl p-8 border border-[#2a2a2a] w-full max-w-3xl relative">
        
        <div class="flex justify-between items-center mb-8">
            <h2 class="text-3xl font-extrabold text-white tracking-wide">Real-Time Portfolio Tracker</h2>
            <button id="sync-btn" class="bg-indigo-600 text-white px-6 py-2.5 rounded-full text-sm font-bold hover:bg-indigo-500 transition shadow-lg flex items-center gap-2">
                <svg id="sync-icon" class="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
                <span>Sync Market Data</span>
            </button>
        </div>
        
        <div class="overflow-x-auto rounded-xl border border-[#2a2a2a]">
            <table class="w-full text-left text-sm">
                <thead class="bg-[#121212] text-gray-400 uppercase tracking-widest text-xs">
                    <tr>
                        <th class="px-6 py-5">Ticker</th>
                        <th class="px-6 py-5">Shares</th>
                        <th class="px-6 py-5">Price (USD)</th>
                        <th class="px-6 py-5">Total Value</th>
                    </tr>
                </thead>
                <tbody id="table-body" class="divide-y divide-[#2a2a2a] bg-[#1a1a1a]">
                    <tr>
                        <td colspan="4" class="px-6 py-8 text-center text-gray-500">
                            Click "Sync Market Data" to fetch live pricing from Yahoo Finance.
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="mt-8 flex justify-between items-center px-2">
            <span class="text-gray-400 uppercase text-xs font-bold tracking-widest">Total Valuation</span>
            <span id="total-valuation" class="text-3xl font-extrabold text-indigo-400 tracking-tight">$0.00</span>
        </div>
        
        <div id="status-toast" class="absolute -bottom-16 left-1/2 transform -translate-x-1/2 bg-teal-500/10 border border-teal-500/50 text-teal-400 px-4 py-2 rounded-full text-sm font-medium opacity-0 transition-opacity duration-300 pointer-events-none">
            Market data synced & Excel exported!
        </div>

    </div>

    <script>
        const syncBtn = document.getElementById('sync-btn');
        const syncIcon = document.getElementById('sync-icon');
        const tableBody = document.getElementById('table-body');
        const totalValuation = document.getElementById('total-valuation');
        const statusToast = document.getElementById('status-toast');

        // Number formatter for currency
        const formatter = new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
        });

        syncBtn.addEventListener('click', async () => {
            // UI Loading State
            syncIcon.classList.add('animate-spin');
            syncBtn.disabled = true;
            syncBtn.classList.add('opacity-75');
            tableBody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-indigo-400 animate-pulse">Fetching live data from yfinance...</td></tr>`;
            
            try {
                // Fetch data from local python backend
                const response = await fetch('/api/sync-live-data', { method: 'POST' });
                const data = await response.json();

                if (data.status === 'success') {
                    // Clear table
                    tableBody.innerHTML = '';
                    
                    // Render new rows
                    data.items.forEach((item, index) => {
                        const tr = document.createElement('tr');
                        tr.className = 'row-hover fade-in';
                        tr.style.animationDelay = `${index * 0.1}s`;
                        
                        tr.innerHTML = `
                            <td class="px-6 py-5 font-bold text-indigo-400">${item.ticker}</td>
                            <td class="px-6 py-5 text-gray-300">${item.shares}</td>
                            <td class="px-6 py-5 text-gray-300">${formatter.format(item.price)}</td>
                            <td class="px-6 py-5 font-medium text-white">${formatter.format(item.value)}</td>
                        `;
                        tableBody.appendChild(tr);
                    });

                    // Update Total
                    totalValuation.innerText = formatter.format(data.total);

                    // Show success toast
                    statusToast.classList.remove('opacity-0');
                    setTimeout(() => statusToast.classList.add('opacity-0'), 3000);
                }
            } catch (error) {
                tableBody.innerHTML = `<tr><td colspan="4" class="px-6 py-8 text-center text-red-400">Error connecting to local server. Make sure Python is running.</td></tr>`;
            } finally {
                // Restore UI state
                syncIcon.classList.remove('animate-spin');
                syncBtn.disabled = false;
                syncBtn.classList.remove('opacity-75');
            }
        });
    </script>
</body>
</html>
"""

# --- 4. SERVER EXECUTION ---
PORT = 8082

def start_server():
    with ReuseAddrServer(("", PORT), PortfolioHandler) as httpd:
        print(f"✅ Portfolio Tracker running at http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    webbrowser.open(f'http://localhost:{PORT}')
    print("Press Ctrl+C in terminal to stop the server.")
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("\nStopping server...")