#! /usr/bin/env python3

'''
Botcore

'''
import os
import sys
import time
import json
import copy
import hashlib
import logging
import threading
from decimal import Decimal
import trader_configuration as TC
from flask import Flask, render_template, url_for, request

## Binance API modules
from binance_api import rest_master
from binance_api import socket_master

import data_interface as DI
import technical_indicators as TI


APP = Flask(__name__)


##
DATA_INF    = None

INVERT_FOR_BTC_FIAT = False

IS_LIVE = False # Used to determin if active updates should be sent via socket.
IS_READ = False # Used to determin if a file is just being read to print trade results to web ui


def dated_url_for(endpoint, **values):
    '''
    This is uses to overide the normal cache for loading static resources.
    '''
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(APP.root_path,
                                    endpoint,
                                    filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


@APP.context_processor
def override_url_for():
    return(dict(url_for=dated_url_for))


@APP.route('/', methods=['GET'])
def control_panel():
    return(render_template('main_page.html'))


@APP.route('/rest-api/v1/get_trade_data', methods=['GET'])
def get_candles():
    candleData = DATA_INF.get_candle_data_all()

    indicators = TC.technical_indicators(candleData)

    max_len = get_max_length(indicators)

    candleData = candleData[:max_len]

    ts_inds = timestamp_indicators(candleData, indicators)

    # Used indicators to place orders/simulate conditional trades.
    orders = test_orders(ts_inds, candleData)

    positive = 0
    total = 0

    total_outcome = 0

    for index, order in enumerate(orders):
        if index != len(orders)-1:
            if order[2] == 'buy':
                outcome = orders[index+1][1] - order[1]
                if outcome > 0:
                    positive += 1
                total_outcome += outcome
                total += 1

    prec = 0
    if total != 0:
        if positive != 0:
            prec = (positive/total)*100

    print(total_outcome)
    print('trades: '+str(positive)+'/'+str(total)+' '+str(prec)+'%')

    return(json.dumps({'call':True, 'data':
        {'candleData':candleData,
        'indicators':ts_inds,
        'orders':orders}}))


def build_empty_indicators(indicators):
    base_inds = {ind_key:{} for ind_key in indicators.keys()}

    for ma in ['ema', 'sma']:
        if ma in indicators.keys():
            base_inds[ma].update({ind_key:{} for ind_key in indicators[ma].keys()})

    return(base_inds)


def get_max_length(indicators):
    get_ma_len = lambda ma_type : [len(indicators[ma_type][ind_key]) for ind_key in indicators[ma_type].keys()] if ma_type in indicators else [999999999]

    base_ind_lens = [len(indicators[ind_key]) for ind_key in indicators.keys() if not ind_key in ['ema', 'sma']]

    return(min(base_ind_lens+get_ma_len('ema')+get_ma_len('sma')))


def timestamp_indicators(candleData, indicators):
    stampped_ind = build_empty_indicators(indicators)

    # Loop to assign timestamps to each relevent indicator.
    for index, candle in enumerate(candleData):
        timestamp = candle[0] # Pull the timestamp for the indicators (open time is used).

        for ind_key in indicators.keys():
            if ind_key in ['ema', 'sma']:
                for ma_type in indicators[ind_key]:
                    stampped_ind[ind_key][ma_type].update({timestamp:indicators[ind_key][ma_type][index]})
            else:
                stampped_ind[ind_key].update({timestamp:indicators[ind_key][index]})

    return(stampped_ind)


def test_orders(indicators, candles):

    # Chunk of variables used to mimic the real trader to allow for easy exporting of the coinditions.
    custom_conditional_data = {}
    trade_information = {
        'side':'buy',
        'buy_price':0,
        'market_status':'TRADING'}
    orders = []

    # Get range to look over (subtract 1 as lists start at 0 not 1)
    d_index = len(candles)-1

    # Set a lookback that is required if conditions look back several candles/indicators.
    required_offset_period = 10

    cInds = build_empty_indicators(indicators)

    # Setup a list of just the timestamps to use as keys.
    date_list = [candle[0] for candle in candles]

    run_test = False
    start_time = time.time()

    for index in range(d_index):
        print(index)
        # Skip until the treshold has been reached.
        if not(index > required_offset_period):
            continue

        # Get the current index of the historic data feed.
        c_index = d_index-index

        # Get the current timerange.
        time_range = date_list[c_index:c_index+required_offset_period]

        # Get current candles data.
        cCandles = candles[c_index:c_index+required_offset_period]

        for ind_key in indicators.keys():
            if ind_key in ['ema', 'sma']:
                for ma_type in cInds[ind_key]:
                    cInds[ind_key].update({ma_type:[indicators[ind_key][ma_type][key] for key in indicators[ind_key][ma_type] if key in time_range]})
            else: 
                cInds.update({ind_key:[indicators[ind_key][key] for key in indicators[ind_key] if key in time_range]}) 

        if run_test:
            continue

        if trade_information['market_status'] != "TRADING":
            continue

        if trade_information['side'] == 'buy':
            buy_results = TC.check_buy_condition(custom_conditional_data, trade_information, cInds, "PLACE_HOLDER", cCandles, "PLACE_HOLDER")

            if buy_results:
                orders.append([time_range[0], buy_results, 'buy'])

            if len(orders) > 0:
                if orders[-1][2] == 'buy':
                    trade_information['side'] = 'sell'

        elif trade_information['side'] == 'sell':
            sell_results = TC.check_sell_condition(custom_conditional_data, trade_information, cInds, "PLACE_HOLDER", cCandles, "PLACE_HOLDER")

            if sell_results:
                orders.append([time_range[0], sell_results, 'sell'])

            if orders[-1][2] == 'sell':
                trade_information['side'] = 'buy'

    print('Runtime took: {0}'.format(time.time()-start_time))
    return(orders)


def pull_data(symbol, interval, limit):
    print('Pulling {2} candles for {0} at {1}'.format(symbol, interval, limit))

    di = symbol.index('-')

    symbol = '{0}{1}'.format(symbol[di+1:], symbol[:di])

    # Pull candles.
    candles = rest_master.Binance_REST().get_custom_candles(symbol=symbol, interval=interval, limit=limit)

    # Saved the candles
    with open('hist_data/candles_'+interval+'_'+symbol+'.json', 'w') as file:
        file_data = json.dump({'data':candles}, file)


def startWeb(data_source, symbol=None, interval=None, limit=None):
    global DATA_INF

    if data_source != 'live':
        with open('hist_data/{0}'.format(data_source), 'r') as file:
            file_data = json.load(file)
        DATA_INF = DI.hist_data_interface(file_data['data'][:int(limit)])

    else:
        DATA_INF = DI.live_data_interface(symbol=symbol, interval=interval, max_candles=int(limit))
        DATA_INF.start()

    APP.run(debug=True)


if __name__ == '__main__':

    # Create the folder where historic candles are stored in.
    if not os.path.exists('hist_data/'):
        os.mkdir('hist_data/')

    # Check to make sure valid number of parameters are passed.
    if len(sys.argv) < 2 or len(sys.argv[2:]) % 2 != 0:
        print(sys.argv)
        print('Invalid param EUR-BTC')
        sys.exit()

    # Extract the cmd into KV pair.
    args = sys.argv[2:]
    params = {args[i*2].replace('-', '').lower():args[(i*2)+1] for i in range(int(len(sys.argv[2:])/2))}

    # Progress to the called option.
    if sys.argv[1].lower() == 'pull':
        pull_data(params['s'], params['i'], params['l'])

    elif sys.argv[1].lower() == 'test':
        if params['ds'] == 'live':
            IS_LIVE = True
            startWeb(params['ds'], symbol=params['s'], interval=params['i'], limit=params['l'])
        else:
            startWeb(params['ds'], limit=params['l'])

    elif sys.argv[1].lower() == 'load':
        IS_READ = True
        startWeb(params['ds'])
        