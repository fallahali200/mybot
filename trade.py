import requests
from datetime import datetime, timedelta
import pandas as pd
import pandas_ta as ta
import telebot
import time
import yfinance as yf
import json
# Telegram bot token and chat ID
TOKEN = '8981754345:AAE2T6UXr3VxlSN7W4ZiyDnbQ_MSS9TaB4g'
CHAT_ID = '-1004367733318'

bot = telebot.TeleBot(TOKEN)

def calculate_tenkan_sen(high, low):
    return (high.rolling(window=9).max() + low.rolling(window=9).min()) / 2

def calculate_kijun_sen(high, low):
    return (high.rolling(window=26).max() + low.rolling(window=26).min()) / 2

def calculate_senkou_span_a(tenkan_sen, kijun_sen):
    return ((tenkan_sen + kijun_sen) / 2).shift(26)

def calculate_senkou_span_b(high, low):
    return ((high.rolling(window=52).max() + low.rolling(window=52).min()) / 2).shift(26)

def calculate_macd(close_prices, fast_period=12, slow_period=26, signal_period=9):
    macd_line = close_prices.ewm(span=fast_period, adjust=False).mean() - close_prices.ewm(span=slow_period, adjust=False).mean()
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    return macd_line, signal_line



def check_usdt_bollinger():
    now = datetime.now()
    timestamp_now = int(now.timestamp())
    timestamp_100_days_ago = int((now - timedelta(days=100)).timestamp())
    
    my_currency = 'USDTIRT'
    resolution = 'D'
    url = f'https://apiv2.nobitex.ir/market/udf/history?symbol={my_currency}&resolution={resolution}&from={timestamp_100_days_ago}&to={timestamp_now}'
    response = requests.get(url,timeout=10)
    data = response.json()
    
    if not data['c']:
        return
    
    closing_prices = data['c']
    timestamps = data['t']
    
    df = pd.DataFrame({
        'timestamp': pd.to_datetime(timestamps, unit='s'),
        'close': closing_prices
    })
    
    # محاسبه باند بولینگر
    bb = ta.bbands(df['close'], length=20, std=2)
    df['BB_lower'] = bb.iloc[:, 0]
    df['BB_middle'] = bb.iloc[:, 1]
    df['BB_upper'] = bb.iloc[:, 2]
    
    # محاسبه فاصله درصدی باندها نسبت به قیمت
    df['BB_width_pct'] = (df['BB_upper'] - df['BB_lower']) / df['close'] * 100
    print(df['BB_width_pct'].iloc[-1])
    message = ""
    # فشردگی وقتی فاصله کمتر از 4 درصد باشد
    if df['BB_width_pct'].iloc[-1] < 4:
        message += f"{my_currency} Bollinger Bands are squeezed! Width: {df['BB_width_pct'].iloc[-1]:.2f}%\n"
    
    # # بررسی عبور قیمت از باندها (اختیاری)
    # if df['close'].iloc[-1] > df['BB_upper'].iloc[-1]:
    #     message += f"{my_currency} price crossed above the upper Bollinger Band!\n"
    # elif df['close'].iloc[-1] < df['BB_lower'].iloc[-1]:
    #     message += f"{my_currency} price crossed below the lower Bollinger Band!\n"
    if message.strip():
        bot.send_message(CHAT_ID, message)





def check_market():
    now = datetime.now()
    timestamp_now = int(now.timestamp())
    timestamp_100_days_ago = int((now - timedelta(days=100)).timestamp())
    with open('currencies.json', 'r') as json_file:
        data = json.load(json_file)    
    nobitex_list = data["nobitex_rsi"]
    time_resolutions = ['D']
    for my_currency in nobitex_list:
        for resolution in time_resolutions:
            url = f'https://apiv2.nobitex.ir/market/udf/history?symbol={my_currency}&resolution={resolution}&from={timestamp_100_days_ago}&to={timestamp_now}'
            response = requests.get(url,timeout=10)
            data = response.json()
            
            if not data['c']:  
                continue

            closing_prices = data['c']
            high_prices = data['h']
            low_prices = data['l']
            timestamps = data['t']

            df = pd.DataFrame({
                'timestamp': pd.to_datetime(timestamps, unit='s'),
                'close': closing_prices,
                'high': high_prices,
                'low': low_prices
            })  
            df['RSI'] = ta.rsi(df['close'], length=14)
            message = ""
            time_frame_msg ="in 1D timeframe"
            if df['RSI'].iloc[-2] <30 and df['RSI'].iloc[-1] >30:
                message += f"{my_currency} (Nobitex) RSI crossed above 30 {time_frame_msg}!\nBuy {my_currency}"
                
            if df['RSI'].iloc[-2] < 50 and df['RSI'].iloc[-1] > 50:
                message += f"{my_currency} (Nobitex) RSI crossed above 50 {time_frame_msg}\n"
            if message.strip():
                bot.send_message(CHAT_ID, message) 
                
                
            if df['RSI'].iloc[-2] < 100 :
                message += f"{my_currency} (Nobitex) RSI crossed above 50 {time_frame_msg}\n"
            if message.strip():
                bot.send_message(CHAT_ID, message)                 
                
              
    with open('currencies.json', 'r') as json_file:
        data = json.load(json_file)    
    nobitex_list = data["nobitex_list"]
    for my_currency in nobitex_list:
           message = ""
           url = f'https://apiv2.nobitex.ir/market/udf/history?symbol={my_currency}&resolution=D&from={timestamp_100_days_ago}&to={timestamp_now}'
           response = requests.get(url,timeout=10)
           data = response.json()
           
           if not data['c']:  
               continue

           closing_prices = data['c']
           high_prices = data['h']
           low_prices = data['l']
           timestamps = data['t']

           df = pd.DataFrame({
               'timestamp': pd.to_datetime(timestamps, unit='s'),
               'close': closing_prices,
               'high': high_prices,
               'low': low_prices
           })

           df['RSI'] = ta.rsi(df['close'], length=14)
           df['tenkan_sen'] = calculate_tenkan_sen(df['high'], df['low'])
           df['kijun_sen'] = calculate_kijun_sen(df['high'], df['low'])
           df['senkou_span_a'] = calculate_senkou_span_a(df['tenkan_sen'], df['kijun_sen'])
           df['senkou_span_b'] = calculate_senkou_span_b(df['high'], df['low'])
           df['macd'], df['signal'] = calculate_macd(df['close'])
           df['ma'] = df['close'].rolling(window=3).mean()

           df.drop(df.tail(1).index, inplace=True)
           # if df['macd'].iloc[-2] <= df['signal'].iloc[-2] and df['macd'].iloc[-1] > df['signal'].iloc[-1]:
           #     message += f"{my_currency} (Nobitex) MACD Buy signal {time_frame_msg}.\n"
           
           # if df['macd'].iloc[-2] >= df['signal'].iloc[-2] and df['macd'].iloc[-1] < df['signal'].iloc[-1]:
           #     message += f"{my_currency} (Nobitex) MACD Sell Signal {time_frame_msg}.\n"                 

           if df['senkou_span_a'].iloc[-1] > df['senkou_span_b'].iloc[-1]:
               if df['macd'].iloc[-2] <= df['signal'].iloc[-2] and df['macd'].iloc[-1] > df['signal'].iloc[-1]:
                   message += f"{my_currency} (Nobitex) MACD Buy signal above cloud {time_frame_msg}.\n"
               
               if df['macd'].iloc[-2] >= df['signal'].iloc[-2] and df['macd'].iloc[-1] < df['signal'].iloc[-1]:
                   message += f"{my_currency} (Nobitex) MACD Sell Signal above cloud {time_frame_msg}.\n"
               if df['tenkan_sen'].iloc[-2] < df['kijun_sen'].iloc[-2] and df['tenkan_sen'].iloc[-1] > df['kijun_sen'].iloc[-1]:
                   message += f"{my_currency} (Nobitex) Ichimoku Buy signal for green cloud {time_frame_msg}!\nBuy {my_currency}"
                   
               if df['ma'].iloc[-1] > df['senkou_span_b'].iloc[-1]:    
                if df['tenkan_sen'].iloc[-2] > df['kijun_sen'].iloc[-2] and df['tenkan_sen'].iloc[-1] < df['kijun_sen'].iloc[-1]:
                    message += f"{my_currency} (Nobitex) Ichimoku Sell signal for green cloud {time_frame_msg}!\nSell {my_currency}" 
                                                   
               if df['ma'].iloc[-2] < df['senkou_span_a'].iloc[-2] and df['ma'].iloc[-1] > df['senkou_span_a'].iloc[-1]:
                   message += f"{my_currency} (Nobitex) Price crossed above green cloud  {time_frame_msg}!\nBuy {my_currency}"
               if df['ma'].iloc[-2] > df['senkou_span_b'].iloc[-2] and df['ma'].iloc[-1] < df['senkou_span_b'].iloc[-1]:
                   message += f"{my_currency} (Nobitex) Price crossed below green cloud {time_frame_msg}!\nSell {my_currency}"    
                                   
           elif df['senkou_span_a'].iloc[-1] < df['senkou_span_b'].iloc[-1]:
               if df['ma'].iloc[-2] < df['senkou_span_b'].iloc[-2] and df['ma'].iloc[-1] > df['senkou_span_b'].iloc[-1]:
                   message += f"{my_currency} (Nobitex) Price crossed above red cloud {time_frame_msg}!\nBuy {my_currency}"
               if df['ma'].iloc[-2] > df['senkou_span_a'].iloc[-2] and df['ma'].iloc[-1] < df['senkou_span_a'].iloc[-1]:
                   message += f"{my_currency} (Nobitex) Price crossed below red cloud {time_frame_msg}!\nSell {my_currency}"                      
           if message.strip():
                bot.send_message(CHAT_ID,message)
    # with open('currencies.json', 'r') as json_file:
    #     data = json.load(json_file)    
    # binance_rsi = data["binance_rsi"]
    # rsi_interval=["1d","1w"]
    # for my_currency in binance_rsi:
    #  for timeframe_interval in rsi_interval:
    #      url = f'https://api.binance.com/api/v3/klines?symbol={my_currency}&interval={timeframe_interval}&limit=100'
    #      response = requests.get(url,timeout=10)
    #      data = response.json()
         
    #      if not data:  
    #          continue

    #      timestamps = [entry[0] for entry in data]
    #      high_prices = [float(entry[2]) for entry in data]

    #      low_prices = [float(entry[3]) for entry in data]
    #      closing_prices = [float(entry[4]) for entry in data]

    #      df = pd.DataFrame({
    #          'timestamp': pd.to_datetime(timestamps, unit='ms'),
    #          'close': closing_prices,
    #          'high': high_prices,
    #          'low': low_prices
    #      })

    #      df['RSI'] = ta.rsi(df['close'], length=14)
    #      message = ""
    #      timeframe_name = "1D" if timeframe_interval == "1d" else "1W"
    #      if df['RSI'].iloc[-2] < 30 and df['RSI'].iloc[-1] > 30:
    #          message += f"{my_currency} (Binance) RSI crossed above 30 in {timeframe_name} timeframe!\nBuy {my_currency}"
    #      if message.strip():
    #       bot.send_message(CHAT_ID, message)          
        
    # with open('currencies.json', 'r') as json_file:
    #     data = json.load(json_file)    
    # binance_list = data["binance_list"]
    # for my_currency in binance_list:
    #     url = f'https://api.binance.com/api/v3/klines?symbol={my_currency}&interval=1d&limit=100'
    #     response = requests.get(url,timeout=10)
    #     data = response.json()
        
    #     if not data:  
    #         continue

    #     timestamps = [entry[0] for entry in data]
    #     high_prices = [float(entry[2]) for entry in data]
    #     low_prices = [float(entry[3]) for entry in data]
    #     closing_prices = [float(entry[4]) for entry in data]

    #     df = pd.DataFrame({
    #         'timestamp': pd.to_datetime(timestamps, unit='ms'),
    #         'close': closing_prices,
    #         'high': high_prices,
    #         'low': low_prices
    #     })

    #     df['RSI'] = ta.rsi(df['close'], length=14)
    #     df['tenkan_sen'] = calculate_tenkan_sen(df['high'], df['low'])
    #     df['kijun_sen'] = calculate_kijun_sen(df['high'], df['low'])
    #     df['senkou_span_a'] = calculate_senkou_span_a(df['tenkan_sen'], df['kijun_sen'])
    #     df['senkou_span_b'] = calculate_senkou_span_b(df['high'], df['low'])
    #     df['macd'], df['signal'] = calculate_macd(df['close'])
    #     df['ma'] = df['close'].rolling(window=3).mean()

    #     df.drop(df.tail(1).index, inplace=True)

    #     message = ""       
    #     # if df['macd'].iloc[-2] <= df['signal'].iloc[-2] and df['macd'].iloc[-1] > df['signal'].iloc[-1]:
    #     #     message += f"{my_currency} (Binance) MACD Buy signal in 1D timeframe\n"
        
    #     # if df['macd'].iloc[-2] >= df['signal'].iloc[-2] and df['macd'].iloc[-1] < df['signal'].iloc[-1]:
    #     #     message += f"{my_currency} (Binance) MACD Sell Signal in 1D timeframe\n"
                 
    #     if df['senkou_span_a'].iloc[-1] > df['senkou_span_b'].iloc[-1]:
    #         # if df['macd'].iloc[-2] <= df['signal'].iloc[-2] and df['macd'].iloc[-1] > df['signal'].iloc[-1]:
    #         #     message += f"{my_currency} (Binance) MACD Buy signal above cloud in 1D timeframe\n"

    #         # if df['macd'].iloc[-2] >= df['signal'].iloc[-2] and df['macd'].iloc[-1] < df['signal'].iloc[-1]:
    #         #     message += f"{my_currency} (Binance) MACD Sell signal above cloud in 1D timeframe\n"
    #         if df['tenkan_sen'].iloc[-2] < df['kijun_sen'].iloc[-2] and df['tenkan_sen'].iloc[-1] > df['kijun_sen'].iloc[-1]:
    #             message += f"{my_currency} (Binance) Ichimoku Buy signal for green cloud in 1D timeframe!\nBuy {my_currency}" 
    #         if df['ma'].iloc[-1] > df['senkou_span_b'].iloc[-1]:    
    #          if df['tenkan_sen'].iloc[-2] > df['kijun_sen'].iloc[-2] and df['tenkan_sen'].iloc[-1] < df['kijun_sen'].iloc[-1]:
    #           message += f"{my_currency} (Nobitex) Ichimoku Sell signal for green cloud {time_frame_msg}!\nSell {my_currency}" 
                                         
    #         if df['ma'].iloc[-2] < df['senkou_span_a'].iloc[-2] and df['ma'].iloc[-1] > df['senkou_span_a'].iloc[-1]:
    #             message += f"{my_currency} (Binance) Price crossed above green cloud in 1D timeframe!\nBuy {my_currency}"                              
    #         if df['ma'].iloc[-2] > df['senkou_span_b'].iloc[-2] and df['ma'].iloc[-1] < df['senkou_span_b'].iloc[-1]:
    #             message += f"{my_currency} (Binance) Price crossed below green cloud in 1D timeframe!\nSell {my_currency}" 
                               
    #     elif df['senkou_span_a'].iloc[-1] < df['senkou_span_b'].iloc[-1]:
    #         if df['ma'].iloc[-2] < df['senkou_span_b'].iloc[-2] and df['ma'].iloc[-1] > df['senkou_span_b'].iloc[-1]:
    #             message += f"{my_currency} (Binance) Price crossed above red cloud in 1D timeframe!\nBuy {my_currency}"        
    #         if df['ma'].iloc[-2] > df['senkou_span_a'].iloc[-2] and df['ma'].iloc[-1] < df['senkou_span_a'].iloc[-1]:
    #             message += f"{my_currency} (Binance) Price crossed below red cloud in 1D timeframe!\nSell {my_currency}"

    #     if message.strip():
    #         bot.send_message(CHAT_ID, message)
    
    # data = yf.download('GC=F', period='3mo', interval='1d')
    # data['RSI'] = ta.rsi(data['Close'], length=14)
    # data['tenkan_sen'] = calculate_tenkan_sen(data['High'], data['Low'])
    # data['kijun_sen'] = calculate_kijun_sen(data['High'], data['Low'])
    # data['senkou_span_a'] = calculate_senkou_span_a(data['tenkan_sen'], data['kijun_sen'])
    # data['senkou_span_b'] = calculate_senkou_span_b(data['High'], data['Low'])
    # data['macd'], data['signal'] = calculate_macd(data['Close'])

    # data.drop(data.tail(1).index, inplace=True)

    # message = ""

    # if data['RSI'].iloc[-2] < 30 and data['RSI'].iloc[-1] > 30:
    #     message += "GOLD RSI crossed above 30 in 1D timeframe\n"

    # if data['senkou_span_a'].iloc[-1] > data['senkou_span_b'].iloc[-1]:
    #     # if data['macd'].iloc[-2] <= data['signal'].iloc[-2] and data['macd'].iloc[-1] > data['signal'].iloc[-1]:
    #     #  message += "GOLD MACD Buy signal above cloud in 1D timeframe\n"
        
    #     # if data['macd'].iloc[-2] >= data['signal'].iloc[-2] and data['macd'].iloc[-1] < data['signal'].iloc[-1]:
    #     #  message += "GOLD MACD Sell signal above cloud in 1D timeframe\n"
             
    #     # if data['Close'].iloc[-2] <= data['senkou_span_a'].iloc[-2] and data['Close'].iloc[-1] > data['senkou_span_a'].iloc[-1]:
    #     #     message += "GOLD Price crossed above green cloud in 1D timeframe\n"
            
    #     # if data['Close'].iloc[-2] >= data['senkou_span_a'].iloc[-2] and data['Close'].iloc[-1] < data['senkou_span_a'].iloc[-1]:
    #     #     message += "GOLD Price crossed below green cloud in 1D timeframe\n"
    #     pass
                        
    # elif data['senkou_span_a'].iloc[-1] < data['senkou_span_b'].iloc[-1]:
    #     # if data['Close'].iloc[-2] <= data['senkou_span_b'].iloc[-2] and data['Close'].iloc[-1] > data['senkou_span_b'].iloc[-1]:
    #     #   message += "GOLD Price crossed above red cloud in 1D timeframe\n"
            
    #     # if data['Close'].iloc[-2] >= data['senkou_span_a'].iloc[-2] and data['Close'].iloc[-1] < data['senkou_span_a'].iloc[-1]:
    #     #     message += "GOLD Price crossed below red cloud in 1D timeframe\n"
    #     pass            
            
            
    # if message.strip():
    #     bot.send_message(CHAT_ID, message)

while True:
    check_market()
    check_usdt_bollinger()    
    time.sleep(86400)
