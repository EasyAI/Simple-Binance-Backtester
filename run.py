#! /usr/bin/env python3

import os
import csv
import sys
import time
import json
import logging
import threading
from flask_socketio import SocketIO
from flask import Flask, render_template, url_for, request

## Binance API modules.
from binance_api import rest_master

## Import core objects.
from core.pattern_finder import PatternFinder
from core.trade_simulator import TradeSimulator


DOUBLE_DEPTH_INDICATORS = ['ema', 'sma', 'rma', 'order', 'order_comp', 'patterns_data_points', 'patterns_data_lines']

APP         = Flask(__name__)
SOCKET_IO   = SocketIO(APP)


## Trade Simulator Object Placeholder.
TS = None

## Pattern Finder Object Placeholder.
PF = None

is_live = False # Used to determin if active updates should be sent via socket.
is_save = False # Used to determin if once complete the results should be written to a file.
is_read = False # Used to determin if a file is just being read to print trade results to web ui

is_compare = False
comparison_data = []

lookback_range = 600


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
    if is_live:
        web_updater_thread = threading.Thread(target=web_updater)
        web_updater_thread.start()

    return(render_template('main_page.html'))


@APP.route('/rest-api/v1/get_data', methods=['GET'])
def get_data():

    data_results = {
        'call':True, 
        'type':'live' if is_live else 'once', 
        'data': {}
    }

    if TS != None:
        # Data to be returned for trade simulater.
        candles_data = TS.candles[:lookback_range]
        orders = TS.orders
        print_order_results(orders)
        raw_indicators = TS.indicators

        raw_indicators.update({'order':{
            'buy':{order[0]:order[1] for order in orders if order[3].split("-")[0] == "BUY"},
            'sell':{order[0]:order[1] for order in orders if order[3].split("-")[0] == "SELL"}
        }})

        if is_compare:
            # If data is being used compare it will be formatted here.
            formatted_comp = [[int(i[0]*1000), i[1], i[2], i[3], i[4]] for i in comparison_data]
            raw_indicators.update({'order_comp':{
                'buy':{order[0]:order[1] for order in formatted_comp if order[4].split("-")[0] == "BUY"},
                'sell':{order[0]:order[1] for order in formatted_comp if order[4].split("-")[0] == "SELL"}
            }})        

    elif PF != None:
        # Data to be returned for pattern finder.
        raw_indicators = PF.indicators
        candles_data = PF.candles[:lookback_range]

    # O/H/L/C/V
    data_results['data'].update({
        'candleData':{candle[0]:[candle[1], candle[2], candle[3], candle[4], candle[6]] for candle in candles_data},
        'indicators':shorten_indicators(raw_indicators, candles_data[-1][0], candles_data[0][0])
    })

    return(json.dumps(data_results))


def print_order_results(orders):
    if len(orders) != 0:
        overall = 0
        num_pos = 0
        num_neg = 0
        total = int((len(orders) if len(orders) % 2 == 0 else len(orders)-1)/2)
        for i in range(total):
            c_order = orders[i*2]
            n_order = orders[(i*2)+1]

            if c_order[3].split('-')[1] == 'LONG':
                outcome = n_order[1] - c_order[1]
            elif c_order[3].split('-')[1] == 'SHORT':
                outcome = c_order[1] - n_order[1]

            if outcome > 0:
                num_pos += 1
            else:
                num_neg += 1

            overall += outcome

        print('Total trades: {0}, P/N: {1}/{2}, prec: {3:.2f}%'.format(num_neg+num_pos, num_pos, num_neg, num_pos if num_neg == 0 else (num_pos/(num_neg+num_pos))*100))
        print('Total: {0}'.format(overall))


def web_updater():
    # For live updating if live trade monitoring is occuring.
    last_close = None

    while True:

        if TS != None:
            orders = TS.orders
            candles_data = TS.candles[:2]
            raw_indicators = TS.indicators

            raw_indicators.update({'order':{
                'buy':{order[0]:order[1] for order in orders if order[3].split("-")[0] == "BUY"},
                'sell':{order[0]:order[1] for order in orders if order[3].split("-")[0] == "SELL"}
            }})
        elif PF != None:
            candles_data = PF.candles[:2]
            raw_indicators = PF.indicators

        SOCKET_IO.emit('update_data', {'action':'success', 'time':time.time(), 'data':{
            'candleData':{candle[0]:[candle[1], candle[2], candle[3], candle[4], candle[5]] for candle in candles_data},
            'indicators':shorten_indicators(raw_indicators, candles_data[-1][0], candles_data[0][0])
        }})

        time.sleep(10)


def shorten_indicators(indicators, start_time, end_time):
    # Conserve space when sending data to via the socket.
    short_indicators = {}

    for ind in indicators.keys():
        print(ind)
        if ind in DOUBLE_DEPTH_INDICATORS:
            short_indicators.update({ind:{}})
            for sub_ind in indicators[ind]:
                sorted_time_values = sorted(indicators[ind][sub_ind].keys(), reverse=True)
                e_i, l_i = find_earliest_latest(sorted_time_values, start_time, end_time)
                s_i = {c_time:indicators[ind][sub_ind][c_time] for c_time in sorted_time_values[l_i:e_i]}
                if s_i != {}:
                    short_indicators[ind].update({sub_ind:s_i})
            if short_indicators[ind] == {}:
                del short_indicators[ind]
        else:
            sorted_time_values = sorted(indicators[ind].keys(), reverse=True)
            e_i, l_i = find_earliest_latest(sorted_time_values, start_time, end_time)
            s_i = {c_time:indicators[ind][c_time] for c_time in sorted_time_values[l_i:e_i]}
            if s_i != {}:
                short_indicators.update({ind:s_i})

    return(short_indicators)


def find_earliest_latest(time_values, start_time, end_time=None):
    start_index = 0
    end_index = 0

    for timestamp in time_values:
        if timestamp < start_time:
            break
        start_index += 1

    if end_time != None:
        last_timestamp = 0
        for timestamp in time_values:
            if timestamp <= end_time:
                break
            end_index += 1

    return(start_index, end_index)


def pull_data(symbol, interval, limit):
    ''' Used to pull candles used for historic data checks '''
    print('Pulling {2} candles for {0} at {1}'.format(symbol, interval, limit))
    di = symbol.index('-')
    symbol = '{0}{1}'.format(symbol[di+1:], symbol[:di])
    # Pull candles.
    candles = rest_master.Binance_REST().get_custom_candles(symbol=symbol, interval=interval, limit=limit)
    # Saved the candles
    with open('hist_data/candles_'+interval+'_'+symbol+'.json', 'w') as file:
        file_data = json.dump({'data':candles}, file)


if __name__ == '__main__':

    # Create the folder where historic candles are stored in.
    if not os.path.exists('hist_data/'):
        os.mkdir('hist_data/')

    # Check to make sure valid number of parameters are passed.
    if len(sys.argv) < 2 or len(sys.argv[2:]) % 2 != 0:
        print(sys.argv)
        sys.exit()

    # Extract the cmd into KV pair.
    args = sys.argv[2:]
    params = {args[i*2].replace('-', '').lower():args[(i*2)+1] for i in range(int(len(sys.argv[2:])/2))}

    # Progress to the called option.
    if sys.argv[1].lower() == 'pull':
        pull_data(params['s'], params['i'], params['l'])

    else:
        if sys.argv[1].lower() == 'test':
            # This is for any trading being done with with trade simulator.
            TS = TradeSimulator()

            if params['ds'] == 'live':
                # For live trades against the current market.
                is_live = True
                TS.setup(is_live, False, params['ds'], params['l'], symbol=params['s'], interval=params['i'])
            else:
                # For trades to be done over historic candles.
                if 'comp' in params:
                    # This can be used to compare results for trades from Simple-Binance-Trader against historic results.
                    is_compare = True
                    with open(params['comp'], 'r') as f:
                        comparison_data = json.loads(f.read())['data'][0]['trade_recorder']

                if 'save' in params:
                    # This is used to save trades done by the trader.
                    is_save = True

                TS.setup(False, is_save, params['ds'], limit=params['l'])
            TS.start()

        elif sys.argv[1].lower() == 'load':
            # Used to reload data carried out by the trader previously. 
            is_read = True

        elif sys.argv[1].lower() == 'pattern':
            # Used to setup pattern finder.
            PF = PatternFinder()
            PF.setup(params['ds'], params['l'], get_pattern=True, segment_span=4, price_point=0)
            PF.start()

        SOCKET_IO.run(APP, 
            debug=True, 
            use_reloader=False)
        