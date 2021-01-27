#! /etc/bin/env python3
import os
import sys
import json
import time
import hashlib
import logging
import threading

## Binance API modules
from binance_api import rest_master
from binance_api import socket_master


class hist_data_interface(object):

    def __init__(self, candles=None, depth=None, candle_range=None, depth_range=None):
        ''''''

        # setup
        self.c_count = 0
        self.b_count = 0

        # Setup the hostoric candle/book values and their ranges.
        if candles != None:
            candle_range        = candle_range if candle_range != None else len(candles)
            self.h_candles      = None if candles == None else candles[:candle_range]
            self.candle_range   = candle_range

        if depth != None:
            depth_range         = depth_range if depth_range != None else len(depth_range)
            self.h_depth        = None if depth == None else depth[:depth_range]
            self.depth_range    = depth_range

        if depth_range != None:
            if candle_range != None:
                self.max_range = candle_range if candle_range > depth_range else depth_range
            else:
                self.max_range = depth_range
        else:
            self.max_range = candle_range

        # Initilise a trader object so back testing via the trader script can be done.
        self.trader = None


    def get_candle_data(self, symbol):
        '''
        '''
        logging.debug('{0}/{1}'.format(self.c_count, (len(self.h_candles)-self.max_range)))

        if (self.c_count+1) >= (len(self.h_candles)-self.max_range):
            self.trader.stop()

        self.c_count+=1
        return(self.h_candles[-(self.c_count+self.candle_range):-self.c_count])


    def get_depth_data(self, symbol):
        '''
        '''
        if (self.b_count+1) >= (len(self.h_depth)-self.max_range):
            self.trader.stop()

        self.b_count+=1
        last_price = self.h_depth[-(self.b_count+self.candle_range)]
        return({'a':[[last_price[4]]], 'b':[[last_price[4]]]})


    def get_candle_data_all(self):
        '''return all candle data'''
        return(self.h_candles)


    def get_depth_data_all(self):
        '''return all depth data'''
        return(self.h_depth)


## Object used for the data interface that feeds live candles
class sim_live_data_interface(object):

    def __init__(self, dataPath=None, fixed_length=50):
        self.liveDataPath = dataPath if dataPath != None else "{0}/live_collect".format(os.getcwd())

        print(self.liveDataPath )

        self.marketData = {}

        ## This holds the simulated live candles.
        self.refined_candles = []
        self.collected_candles = []

        ## Timestamp used to indicate new candles.
        self.last_timestamp = 0

        ## This is used for candle data offsetting, used to simulate the live candles.
        self.candle_offset  = 0
        self.candle_base    = 0
        self.fixed_length   = fixed_length


    def start(self, set_live=True):
        self._load_data()
        self._build_initial_historic(limit=(self.fixed_length if set_live else None))
        return(True)


    def _load_data(self):
        lmarketData = {}
        lcandleData = {}

        for index, file_name in enumerate(os.listdir(self.liveDataPath)):
            f_indexed, l_indexed, f_type, f_symbol = file_name.split('_')

            # Read in teh data from the file and store the date in its relevent file.
            with open(self.liveDataPath+'/'+file_name, 'r') as f:
                if f_type == 'candles':
                    lcandleData.update(json.loads(f.read())['d'])
                elif f_type == 'marketPrices':
                    lmarketData.update(json.loads(f.read())['d'])

        self.refined_candles = self._organise_candles(lcandleData)
        self.marketData = lmarketData


    def _organise_candles(self, raw_candles):
        refined_candles = []

        # Organise the keys for the dictionary into order.
        sorted_keys = sorted(list(raw_candles.keys()))

        # Print out candle order type.
        order = "[ORDER] latest > oldest" if sorted_keys[0] > sorted_keys[-1] else "[ORDER] oldest > latest"
        print(order)

        # Build the ordered candles based on the key order.
        ordered_candles = [raw_candles[key] for key in sorted_keys]

        # Improve runtime/reduce overheard by removing duplicate candles.
        existing_candles = []
        for index, candle in enumerate(ordered_candles):
            # Generate hash to check if candle already exists.
            #candle_hash = hashlib.md5(str(candle).encode('utf-8')).hexdigest()
            #if candle_hash not in existing_candles:
            #    existing_candles.append(candle_hash)
            refined_candles.append(candle)

        return(refined_candles)


    def _build_initial_historic(self, limit):
        c_c_c = self.refined_candles[0][6]
        candles = []

        # Build initial backlog of full candles.
        for index, c_candle_status in enumerate(self.refined_candles):

            # if the current candle close time is not equal to that of whats expected then a new candle is created.
            if c_c_c != c_candle_status[6]:

                # Add the new candle to the list of full candles.
                # [1607641620000, 0.004106, 0.004107, 0.004106, 0.004107, 2.22, 1607641679999]
                c_c = self.refined_candles[(index-1)]
                candles.append([c_c[0],c_c[1],c_c[2],c_c[3],c_c[4],c_c[5],c_c[6]])

                # once all the candles have been built to the required range then break out and set the base of candles.
                if limit:
                    if len(candles) == self.fixed_length:
                        self.candle_base = index
                        break
                c_c_c = c_candle_status[6]

        self.collected_candles = candles.copy()
        self.last_timestamp = self.collected_candles[-1][6]


    def get_candle_data(self):
        current_index = self.candle_base+self.candle_offset
        self.candle_offset += 1
        
        # Update candles.
        if self.last_timestamp != self.refined_candles[-1][6]:
            self.collected_candles = self.collected_candles[1:]+[self.refined_candles[current_index]]
            self.last_timestamp = self.refined_candles[-1][6]
        else:
            self.collected_candles = self.collected_candles[:-1]+[self.refined_candles[current_index]]

        return(self.collected_candles)


    def get_depth_data(self):
        '''  '''

    def get_candle_data_all(self):
        '''returns all of the candles'''
        return(self.collected_candles)


    def get_depth_data_all(self):
        '''returns all of the depth'''


## Object used for the data interface that feeds live candles
class live_data_interface(object):

    def __init__(self, symbol='BTC-ETH', interval='1m', max_candles=500, max_depth=10):
        self.symbol     = symbol
        self.interval   = interval
        self.max_candles= max_candles
        self.max_depth  = max_depth
        self.socket_api = None


    def start(self, asynch=False):
        '''
        Allow data to be collected asynchronously.
        '''
        if asynch:
            DC_thread = threading.Thread(target=self._data_collector)
            DC_thread.start()
        else:
            self._data_collector()


    def _data_collector(self):
        ''' Main live data collection function, only requires the symbol to be passed ETHBTC, NEOBTC, eg. '''
        logging.debug('Setting up live collector')

        # Create empty varables to store the collected data in.
        candle_data = {}
        market_data = {}

        rest_api = rest_master.Binance_REST()

        # Create the socket api that will be used.
        self.socket_api = socket_master.Binance_SOCK()

        # Setup the streams that will be used to collect data.
        self.socket_api.set_candle_stream(symbol=self.symbol, interval=self.interval)
        self.socket_api.set_manual_depth_stream(symbol=self.symbol, update_speed='1000ms')

        # Setup the candles range that is to be used and the depth.
        self.socket_api.BASE_CANDLE_LIMIT = self.max_candles
        self.socket_api.BASE_DEPTH_LIMIT = self.max_depth

        # Create the query that will be used and setup live data collection with low historic range.
        self.socket_api.build_query()
        self.socket_api.set_live_and_historic_combo(rest_api)
        print(self.socket_api.query)

        self.socket_api.start()


    def get_candle_data(self):
        '''  '''

    def get_depth_data(self):
        '''  '''

    def get_candle_data_all(self):
        '''returns all of the candles'''
        dash_index = self.symbol.index('-')
        print(dash_index)
        print()
        shortSymbole = self.symbol[dash_index+1:]+self.symbol[:dash_index]
        return(self.socket_api.get_live_candles()[shortSymbole])


    def get_depth_data_all(self):
        '''returns all of the depth'''