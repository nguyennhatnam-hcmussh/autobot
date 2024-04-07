#-------------------------import libraries-------------------------
import MetaTrader5 as mt5
import configparser
import pandas as pd
# from datetime import datetime, timezone, timedelta
import time
from taa.trend import EMAIndicator, WMAIndicator
from taa.momentum import RSIIndicator
#==================================================================

#-------------------------import data------------------------------
#-----------------read file config.ini
config = configparser.ConfigParser()
config.read("config_demo.ini")
print('>>> config_demo.ini')
#-----------------MT5
print('[MT5]')
account = int(config['MT5']['account'])
print(f'account > {account}')
password = str(config['MT5']['password'])
print(f'password > {password}')
server = str(config['MT5']['server'])
print(f'server > {server}')

#-----------------set variables trade
print('[trade]')
symbol = str(config['trade']['symbol'])
print(f'symbol > {symbol}')
timeframe = str(config['trade']['timeframe'])
print(f'timeframe > {timeframe}')
lot = float(config['trade']['lot'])
print(f'lot > {lot}')
stoploss = float(config['trade']['stoploss'])
print(f'stoploss > {stoploss}')
profit = float(config['trade']['profit'])
print(f'profit > {profit}')
# ema
print('[MA]')
len_rsi = int(config['MA']['RSI'])
print(f'RSI > {len_rsi}')
len_ema = int(config['MA']['EMA'])
print(f'EMA > {len_ema}')
len_wma = int(config['MA']['WMA'])
print(f'WMA > {len_wma}')
# database
new_candle_status = False
new_value_status = False
df = ''
# order
order_active = None
position_current = None
# algorithm
dieukien = None
#===================================================================

#--------------------------functions--------------------------------
def login_mt5():
    #------------------establish connection to the MetaTrader 5 terminal 
    if not mt5.initialize(): 
        print(f"\nMT5 bi loi",mt5.last_error()) 
        quit()
    else:
        #-----------------now connect to trading account specifying the password 
        authorized=mt5.login(account, password=password, server=server)
        #-----------------authorized=mt5.login(account)
        if authorized and mt5.account_info().login == account:
            #------------------select symbol
            selected=mt5.symbol_select(symbol,True)
            if  selected:
                print(f"\nMT5: Da login {account} account thanh cong")
                print(f"     > Da select {symbol}")
                print(f"     > So du hien tai: {mt5.account_info().balance} USD")
            else:
                print(f'\nkhong the select {symbol}')
                mt5.shutdown()
                quit()
                
        else:
            mt5.shutdown()
            print(f'\nkhong the dang nhap tai khoan MT5')
            print(f'> Hay kiem tra lai thong tin tai khoan')
            quit()


def get_database(tf, bar_from, bar_to):
    timeframe = {
        "m1" : mt5.TIMEFRAME_M1,
        "m3" : mt5.TIMEFRAME_M3,
        "m5" : mt5.TIMEFRAME_M5,
        "m15" : mt5.TIMEFRAME_M15,
        "h1" : mt5.TIMEFRAME_H1,
        "h4" : mt5.TIMEFRAME_H4,
        "d1" : mt5.TIMEFRAME_D1,
        "w1" : mt5.TIMEFRAME_W1,
    }
    #-----------------Get Database
    rates = mt5.copy_rates_from_pos(symbol, timeframe[tf], bar_from, bar_to)

    #-----------------create DataFrame out of the obtained data
    df = pd.DataFrame(rates)

    #-----------------Only the columns containt the OHLCV data
    df.drop(columns=["open", "tick_volume", "spread", "real_volume"], axis=1, inplace=True)

    #-----------------Convert time in ms to datetime
    df = df.astype(
        {
            "time": "datetime64[s]",
            "close": float,
        }
    )
    return df


def CheckOrder():
    global order_active, position_current
    positions = mt5.positions_get(symbol=symbol)
    for position in positions:
        # if position.magic == 8888:
        order_active = True
        position_current = position
        # print(f'\nOrder is Active')
        # print(f'\n{str(position_current)}')
        return None

    order_active = False
    position_current = None
    # print(f'\nOrder is not active')


def CheckHistoryOrder(position):
    position_history_orders = mt5.history_deals_get(position=position.identifier)
    print()
    print(f'\n{str(position_history_orders[-1])}')


def NewOrder(order_type):
    if order_type == "buy":
        NOW_PRICE = mt5.symbol_info_tick(symbol).ask
        TYPE = mt5.ORDER_TYPE_BUY
        type = 'Buy'
        # stoploss = NOW_PRICE - 5
        # takeprofit = NOW_PRICE + 0.5
    elif order_type == "sell":
        NOW_PRICE = mt5.symbol_info_tick(symbol).bid
        TYPE = mt5.ORDER_TYPE_SELL
        type = 'Sell'
        # stoploss = NOW_PRICE + 5
        # takeprofit = NOW_PRICE - 0.5
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": float(lot),
        "type": TYPE,
        "price": NOW_PRICE,
        # "sl": stoploss,
        # "tp": takeprofit,
        "deviation": 10,
        "magic": 8888,
        "comment": "nampro",
        "type_time": mt5.ORDER_TIME_GTC,
    }
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f'\n{type} Order has been Successfully Placed')
    else:
        print(f'\n Have an ERROR in PLACING order!!!')

def CloseOrder(position):
    if position.type == mt5.ORDER_TYPE_SELL:
        NOW_PRICE = mt5.symbol_info_tick(position.symbol).ask
        TYPE = mt5.ORDER_TYPE_BUY 
    elif position.type == mt5.ORDER_TYPE_BUY:
        NOW_PRICE = mt5.symbol_info_tick(position.symbol).bid
        TYPE = mt5.ORDER_TYPE_SELL
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": position.symbol,
        "volume": position.volume,
        "type": TYPE,
        "position": position.identifier,
        "price": NOW_PRICE,
        "deviation": 10,
        "magic": position.magic,
        "comment": position.comment,
        "type_time": mt5.ORDER_TIME_GTC,
    }
    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        print(f'\nCurrent Order have been Successfully Closed')
    else:
        print(f'\n Have an ERROR in CLOSING order!!!')


def UpdateDatabase():
    global df, new_candle_status, new_value_status
    bar_from = 0
    bar_to = 2
    new_df = get_database(timeframe, bar_from, bar_to)
    old_value = df.iloc[-1]['close']
    new_value = new_df.iloc[-1]['close']

    if old_value != new_value:
        new_value_status = True
    else:
        new_value_status = False

    if new_df["time"].iloc[-1] != df["time"].iloc[-1]:
        new_candle_status = True
        # print('new candle!')
        df.iloc[-1] = new_df.iloc[-2]
        df = pd.concat([df, new_df.iloc[-1:]], axis=0, ignore_index=True)
        df.drop(labels=0, axis=0, inplace=True)
    else:
        new_candle_status = False
        df.iloc[-1] = new_df.iloc[-1]


def indicator(df):
    rsi = RSIIndicator(close=df['close'], window=len_rsi).rsi()
    ema = EMAIndicator(close=rsi, window=len_ema).ema_indicator()
    wma = WMAIndicator(close=rsi, window=len_wma).wma()

    return {
        'ema': ema.iloc[-2], 
        'wma': wma.iloc[-2], 
        }


def algorithm(indis):
    global dieukien
    dieukien_old = dieukien
    # trend large
    if indis['wma'] >= 50:
        trend = 1
    else:
        trend = 0
    # dieukien
    if indis['ema'] >= indis['wma']:
        dieukien = 1
    else:
        dieukien = 0
    # buy
    if trend == 1 and dieukien_old == 0 and dieukien == 1:
        print('buy...')
        print(order_active)
        return "buy"
    # sell
    if trend == 0 and dieukien_old == 1 and dieukien == 0:
        print('sell...')
        print(order_active)
        return "sell"
    # close buy
    if dieukien_old == 0 and dieukien == 0:
        print('close buy...')
        print(order_active)
        if order_active == True and position_current.type == 0:
            return 'close'
    # close sell
    if dieukien_old == 1 and dieukien == 1:
        print('close sell...')
        print(order_active)
        if order_active == True and position_current.type == 1:
            return 'close'
    return None


if __name__ == "__main__":
    print(f"\n>> action")

    #----------------login mt5
    login_mt5()

    #----------------initial setting and checking
    bar_from = 0
    bar_to = 5000
    df = get_database(timeframe, bar_from, bar_to) # get database
    CheckOrder() # check order status
    indis = indicator(df) # get indicators data
    print(indis)
    algorithm(indis) # get algorithm status

    # #---------------update data
    while True:
        #----------------update database
        time.sleep(0.1)
        UpdateDatabase()

        #----------------New value
        if new_value_status:
            CheckOrder()
            if order_active:
                print(f'\nprofit: {position_current.profit}')
                # stoploss
                if position_current.profit < stoploss:
                    print(f'boi vi: {position_current.profit} < {stoploss} ')
                    CloseOrder(position_current)
                    CheckHistoryOrder(position_current)
                    CheckOrder()
                elif position_current.profit >= profit:
                    print(f'boi vi: {position_current.profit} >= {profit} ')
                    CloseOrder(position_current)
                    CheckHistoryOrder(position_current)
                    CheckOrder()
        
        #----------------New Candle
        if new_candle_status:
            print('\n>>> New Candle!')
            indis = indicator(df) # get indicators data
            print(indis)
            signal = algorithm(indis) # get algorithm status
            print(signal)
            if signal:
                if signal == "buy":
                    if order_active == True:
                        CloseOrder(position_current)
                        CheckHistoryOrder(position_current)
                        CheckOrder()
                    NewOrder(signal)
                    CheckOrder()
                if signal == "sell":
                    if order_active == True:
                        CloseOrder(position_current)
                        CheckHistoryOrder(position_current)
                        CheckOrder()
                    NewOrder(signal)
                    CheckOrder()
                if signal == 'close':
                    CloseOrder(position_current)
                    CheckHistoryOrder(position_current)
                    CheckOrder()

