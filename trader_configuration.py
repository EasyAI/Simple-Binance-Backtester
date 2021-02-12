#! /usr/bin/env python3
import logging
import technical_indicators as TI

def technical_indicators(candles):
    indicators = {}

    open_prices     = [candle[1] for candle in candles]
    high_prices     = [candle[2] for candle in candles]
    low_prices      = [candle[3] for candle in candles]
    close_prices    = [candle[4] for candle in candles]
    
    indicators.update({'macd':TI.get_MACD(close_prices)})
    indicators.update({'adx':TI.get_ADX_DI(candles, 9)})
    #indicators.update({'boll':TI.get_BOLL(close_prices, ma_type=21, stDev=2)})

    #indicators.update({'ema':{}})
    #indicators['ema'].update({'ema50':TI.get_EMA(close_prices, 50)})
    #indicators['ema'].update({'ema25':TI.get_EMA(close_prices, 25)})

    return(indicators)


def custom_condition(custom_conditional_data, position_information, previous_trades, position_type, candles, indicators, symbol):
    can_order = True

    ## If trader has finished trade allow it to continue trading straight away.
    if position_information['market_status'] == 'COMPLETE_TRADE':
        position_information['market_status'] = 'TRADING'

    position_information.update({'can_order':can_order})
    return(custom_conditional_data, position_information)


def check_buy_condition(custom_conditional_data, trade_information, indicators, prices, candles, symbol):
    macd = indicators['macd']

    if macd[0]['macd'] > macd[1]['macd'] and macd[0]['signal'] < macd[0]['macd']:
        sell_price = candles[0][4]
        return(sell_price)
    return


def check_sell_condition(custom_conditional_data, trade_information, indicators, prices, candles, symbol):
    macd = indicators['macd']
    
    if macd[0]['macd'] < macd[1]['macd'] and macd[0]['signal'] > macd[0]['macd']:
        buy_price = candles[0][4]
        return(buy_price)
    return