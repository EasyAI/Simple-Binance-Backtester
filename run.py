#! /usr/bin/env python3

'''
Botcore

'''
import os
import csv
import sys
import copy
import time
import json
import copy
import hashlib
import logging
import threading
from decimal import Decimal
import trader_configuration as TC
from flask_socketio import SocketIO
from flask import Flask, render_template, url_for, request

## Binance API modules
from binance_api import rest_master
from binance_api import socket_master

import data_interface as DI
import technical_indicators as TI


APP         = Flask(__name__)
SOCKET_IO   = SocketIO(APP)


##
TS = None

INVERT_FOR_BTC_FIAT = False

is_live = False # Used to determin if active updates should be sent via socket.
IS_READ = False # Used to determin if a file is just being read to print trade results to web ui

DOUBLE_DEPTH_INDICATORS = ['ema', 'sma']


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


@APP.route('/rest-api/v1/get_trade_data', methods=['GET'])
def get_candles():

    orders = TS.orders

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

    return(json.dumps({'call':True, 'type':'live' if is_live else 'once', 'data':
        {'candleData':TS.candles[:250],
        'indicators':shorten_indicators(TS.indicators, 250),
        'orders':TS.orders}}))


def web_updater():
    lastHash = None

    while True:
        short_candles = TS.candles[0:3]
        short_indicators = shorten_indicators(TS.indicators)

        SOCKET_IO.emit('update_data', {'data':
            {'candleData':short_candles,
            'indicators':short_indicators,
            'orders':TS.orders}})

        time.sleep(10)


def shorten_indicators(indicators, length=4):
    short_indicators = {}

    for ind in indicators.keys():
        short_indicators.update({ind:{}})
        if ind in DOUBLE_DEPTH_INDICATORS:
            for sub_ind in indicators[ind]:
                short_indicators[ind].update({sub_ind:{}})
                key_time_values = sorted(indicators[ind].keys(), reverse=True)[:length]
                short_indicators[ind][sub_ind] = {c_time:indicators[ind][sub_ind][c_time] for c_time in key_time_values}

        key_time_values = sorted(indicators[ind].keys(), reverse=True)[:length]
        short_indicators[ind] = {c_time:indicators[ind][c_time] for c_time in key_time_values}

    return(short_indicators)



class trade_simulator():

    def __init__(self):
        self.candles = []
        self.indicators = []
        self.orders = []


    def setup(self, is_live, data_source, symbol=None, interval=None, limit=None):
        ## Setup the initial config for the trade simulator for either backtest of live test.
        self.is_live = is_live

        if is_live:
            self.data_inf   = DI.live_data_interface(symbol=symbol, interval=interval, max_candles=int(limit))
            self.data_inf.start()

            self.raw_indicators = []
            self.required_offset_period = 0

        else:
            with open('hist_data/{0}'.format(data_source), 'r') as file:
                file_data   = json.load(file)

            data_inf        = DI.hist_data_interface(file_data['data'][:int(limit)])
            candleData      = data_inf.get_candle_data_all()
            indicators      = TC.technical_indicators(candleData)
            max_len         = self._get_max_length(indicators)

            self.candles    = candleData[:max_len]
            self.indicators = self._timestamp_indicators(self.candles, indicators)

            self.required_offset_period = 10
            self.d_index    = max_len-1

            # Setup a list of just the timestamps to use as keys.
            self.date_list = [candle[0] for candle in self.candles]


    def start(self):
        testRunner_th = threading.Thread(target=self._test_run)
        testRunner_th.start()

        return(True)


    def _build_empty_indicators(self, indicators):
        base_inds = {ind_key:{} for ind_key in indicators.keys()}

        for ma in DOUBLE_DEPTH_INDICATORS:
            if ma in indicators.keys():
                base_inds[ma].update({ind_key:{} for ind_key in indicators[ma].keys()})

        return(base_inds)


    def _get_max_length(self, indicators):
        get_ma_len = lambda ma_type : [len(indicators[ma_type][ind_key]) for ind_key in indicators[ma_type].keys()] if ma_type in indicators else [999999999]

        base_ind_lens = [len(indicators[ind_key]) for ind_key in indicators.keys() if not ind_key in DOUBLE_DEPTH_INDICATORS]

        return(min(base_ind_lens+get_ma_len('ema')+get_ma_len('sma')))


    def _timestamp_indicators(self, candleData, indicators):
        stampped_ind = self._build_empty_indicators(indicators)

        # Loop to assign timestamps to each relevent indicator.
        for index, candle in enumerate(candleData):
            timestamp = candle[0] # Pull the timestamp for the indicators (open time is used).

            for ind_key in indicators.keys():
                if ind_key in DOUBLE_DEPTH_INDICATORS:
                    for ma_type in indicators[ind_key]:
                        stampped_ind[ind_key][ma_type].update({timestamp:indicators[ind_key][ma_type][index]})
                else:

                    stampped_ind[ind_key].update({timestamp:indicators[ind_key][index]})

        return(stampped_ind)


    def _test_run(self):
        # Chunk of variables used to mimic the real trader to allow for easy exporting of the coinditions.
        custom_conditional_data = {}
        trade_information = {
            'order_side':'BUY',
            'buy_price':0,
            'market_status':'TRADING',
            'can_order':True}

        run_test = False
        start_time = time.time()
        c_iter = -1
        t_type = 'LONG'

        print('Started Back Tester...')
        while True:
            c_iter += 1

            if not self.is_live:
                if c_iter == self.d_index:
                    break

            # Skip until the treshold has been reached.
            if not(c_iter > self.required_offset_period):
                continue

            # Get current candles data.
            cCandles = self._update_candles(c_iter)
            cInds = self._update_indicators(c_iter)

            if run_test:
                continue

            if trade_information['market_status'] != "TRADING":
                continue

            custom_conditional_data, trade_information = TC.other_conditions(custom_conditional_data, trade_information, self.orders, t_type, cCandles, cInds, "PLACE_HOLDER")

            if trade_information['can_order']:
                if trade_information['order_side'] == 'BUY':
                    ## Buy sim
                    if t_type == 'LONG':
                        buy_results = TC.long_entry_conditions(custom_conditional_data, trade_information, cInds, "PLACE_HOLDER", cCandles, "PLACE_HOLDER")
                    elif t_type == 'SHORT':
                        buy_results = TC.short_entry_conditions(custom_conditional_data, trade_information, cInds, "PLACE_HOLDER", cCandles, "PLACE_HOLDER")

                    if buy_results:
                        if buy_results['order_type'] != 'WAIT':
                            price = cCandles[0][4] if not('price' in buy_results) else buy_results['price']
                            self.orders.append([cCandles[0][0], price, buy_results['description'], 'BUY-{0}'.format(t_type)])

                    if len(self.orders) > 0:
                        if self.orders[-1][3].split('-')[0] == 'BUY':
                            print('BUY_DONE')
                            trade_information['buy_price'] = price
                            trade_information['order_side'] = 'SELL'

                elif trade_information['order_side'] == 'SELL':
                    ## Sell sim
                    if t_type == 'LONG':
                        sell_results = TC.long_exit_conditions(custom_conditional_data, trade_information, cInds, "PLACE_HOLDER", cCandles, "PLACE_HOLDER")
                    elif t_type == 'SHORT':
                        sell_results = TC.short_exit_conditions(custom_conditional_data, trade_information, cInds, "PLACE_HOLDER", cCandles, "PLACE_HOLDER")

                    if sell_results:
                        if sell_results['order_type'] != 'WAIT':
                            print(sell_results)
                            price = cCandles[0][4] if not('price' in sell_results) else sell_results['price']
                            self.orders.append([cCandles[0][0], price, sell_results['description'], 'SELL-{0}'.format(t_type)])

                    if self.orders[-1][3].split('-')[0] == 'SELL':
                        print('SELL_DONE')
                        trade_information['buy_price'] = 0
                        trade_information['order_side'] = 'BUY'

        if params['ds'] != 'live':
            if 'save' in params:
                header = 'time,candle,'
                indicators = self.indicators
                orders = self.orders

                orders.reverse()

                for indicator in indicators:
                    header+=str(indicator)+','
                header += 'buyOrder,sellOrder'

                save_data = [header.split(',')]
                order_index = 0

                for candle in self.candles:
                    ctime = candle[0]
                    data_line = [ctime, candle]
                    for indicator in indicators:
                        data_line.append(indicators[indicator][ctime])

                    if order_index != len(orders):
                        if orders[order_index][0] == candle[0]:
                            if orders[order_index][3].split('-')[0] == 'BUY':
                                data_line += [orders[order_index][1], 0]
                            else:
                                data_line += [0, orders[order_index][1]]
                            order_index+=1
                        else:
                            data_line += [0, 0]
                    save_data.append(data_line)

                with open('trader.csv', 'w', newline='') as csvfile:
                    csv_writer = csv.writer(csvfile, delimiter=',')
                    for line in save_data:
                        csv_writer.writerow(line)


        print('Runtime took: {0}'.format(time.time()-start_time))


    def _update_candles(self, c_iter):
        if self.is_live:
            candleData          = self.data_inf.get_candle_data_all()
            self.raw_indicators = TC.technical_indicators(candleData)
            max_len             = self._get_max_length(self.raw_indicators)
            current_candles     = candleData[:max_len]
            self.candles        = current_candles
        else:
            c_index = self.d_index-c_iter
            current_candles = self.candles[c_index:c_index+self.required_offset_period]

        return(current_candles)


    def _update_indicators(self, c_iter):
        if self.is_live:
            self.indicators = self._timestamp_indicators(self.candles, self.raw_indicators)

            cInds = self._build_empty_indicators(self.indicators)

            for ind_key in self.indicators.keys():
                if ind_key in DOUBLE_DEPTH_INDICATORS:
                    for ma_type in cInds[ind_key]:
                        cInds[ind_key].update({ma_type:[self.indicators[ind_key][ma_type][key] for key in self.indicators[ind_key][ma_type] if key in self.indicators[ind_key][ma_type].keys()]})
                else: 
                    cInds.update({ind_key:[self.indicators[ind_key][key] for key in self.indicators[ind_key] if key in self.indicators[ind_key].keys()]})

        else:
            c_index = self.d_index-c_iter
            time_range = self.date_list[c_index:c_index+self.required_offset_period]

            cInds = self._build_empty_indicators(self.indicators)

            for ind_key in self.indicators.keys():
                if ind_key in DOUBLE_DEPTH_INDICATORS:
                    for ma_type in cInds[ind_key]:
                        cInds[ind_key].update({ma_type:[self.indicators[ind_key][ma_type][key] for key in self.indicators[ind_key][ma_type] if key in time_range]})
                else: 
                    cInds.update({ind_key:[self.indicators[ind_key][key] for key in self.indicators[ind_key] if key in time_range]}) 

        return(cInds)


def pull_data(symbol, interval, limit):
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
        print('Invalid param EUR-BTC')
        sys.exit()

    # Extract the cmd into KV pair.
    args = sys.argv[2:]
    params = {args[i*2].replace('-', '').lower():args[(i*2)+1] for i in range(int(len(sys.argv[2:])/2))}

    # Progress to the called option.
    if sys.argv[1].lower() == 'pull':
        pull_data(params['s'], params['i'], params['l'])

    elif sys.argv[1].lower() == 'test':
        TS = trade_simulator()

        if params['ds'] == 'live':
            is_live = True
            TS.setup(is_live, params['ds'], symbol=params['s'], interval=params['i'], limit=params['l'])
        else:
            TS.setup(is_live, params['ds'], limit=params['l'])

        TS.start()
        
        '''SOCKET_IO.run(APP, 
            debug=True, 
            use_reloader=False)'''

    elif sys.argv[1].lower() == 'load':
        IS_READ = True
        startWeb(params['ds'])
        