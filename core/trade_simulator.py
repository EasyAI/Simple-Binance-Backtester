import json
import time
import logging
import threading
import core.tools as tools
import core.data_interface as DI
import trader_configuration as TC

DOUBLE_DEPTH_INDICATORS = ['ema', 'sma', 'rma']
UN_SEQUENTIAL_DATA = ['tops_bottoms']


class TradeSimulator():

    def __init__(self):
        self.candles = []
        self.indicators = []
        self.orders = []


    def setup(self, is_live, is_save, data_source, symbol=None, interval=None, limit=None):
        ## Setup the initial config for the trade simulator for either backtest of live test.
        self.is_live = is_live
        self.is_save = is_save

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
            max_len         = tools.get_max_length(indicators)

            self.candles    = candleData[:max_len]
            self.indicators = tools.timestamp_indicators(self.candles, indicators)

            self.required_offset_period = 100
            self.d_index    = max_len-1

            # Setup a list of just the timestamps to use as keys.
            self.date_list = [candle[0] for candle in self.candles]


    def start(self):
        testRunner_th = threading.Thread(target=self._test_run)
        testRunner_th.start()

        return(True)


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
        pattern_count = 0

        if 'tops_bottoms' in self.indicators:
            self.indicators.update({'patterns_data_points':{}})
            self.indicators.update({'patterns_data_lines':{}})

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
                            if 'is_pattern' in buy_results:
                                pattern_id = pattern_id = 'pattern{0}'.format(pattern_count)
                                pattern_points_len = len(custom_conditional_data['pattern_points'])
                                self.indicators['patterns_data_points'].update({pattern_id+'points':{point[0]:point[1] for point in cInds['tops_bottoms'][1:pattern_points_len+1]}})
                                self.indicators['patterns_data_lines'].update({pattern_id+'lines':{point[0]:point[1] for point in cInds['tops_bottoms'][1:pattern_points_len+1]}})
                                pattern_count+=1

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
                            if 'is_pattern' in sell_results:
                                pattern_id = pattern_id = 'pattern{0}'.format(pattern_count)
                                pattern_points_len = len(custom_conditional_data['pattern_points'])
                                self.indicators['patterns_data_points'].update({pattern_id+'points':{point[0]:point[1] for point in cInds['tops_bottoms'][1:pattern_points_len+1]}})
                                self.indicators['patterns_data_lines'].update({pattern_id+'lines':{point[0]:point[1] for point in cInds['tops_bottoms'][1:pattern_points_len+1]}})
                                pattern_count+=1


                    if self.orders[-1][3].split('-')[0] == 'SELL':
                        print('SELL_DONE')
                        trade_information['buy_price'] = 0
                        trade_information['order_side'] = 'BUY'

        if not self.is_live:
            if self.is_save:
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
            max_len             = tools.get_max_length(self.raw_indicators)
            current_candles     = candleData[:max_len]
            self.candles        = current_candles
        else:
            c_index = self.d_index-c_iter
            current_candles = self.candles[c_index:c_index+self.required_offset_period]

        return(current_candles)


    def _update_indicators(self, c_iter):
        if self.is_live:
            self.indicators = tools.timestamp_indicators(self.candles, self.raw_indicators)

            cInds = tools.build_empty_indicators(self.indicators)

            for ind_key in self.indicators.keys():
                if ind_key in DOUBLE_DEPTH_INDICATORS:
                    for ma_type in cInds[ind_key]:
                        cInds[ind_key].update({ma_type:[self.indicators[ind_key][ma_type][key] for key in self.indicators[ind_key][ma_type] if key in self.indicators[ind_key][ma_type].keys()]})
                else: 
                    cInds.update({ind_key:[self.indicators[ind_key][key] for key in self.indicators[ind_key] if key in self.indicators[ind_key].keys()]})

        else:
            c_index = self.d_index-c_iter
            time_range = self.date_list[c_index:c_index+self.required_offset_period]

            cInds = tools.build_empty_indicators(self.indicators)

            for ind_key in self.indicators.keys():
                if ind_key in UN_SEQUENTIAL_DATA:
                    ordered_timestamps = sorted([key for key in self.indicators[ind_key] if key in time_range], reverse=True)
                    cInds.update({ind_key:[[key, self.indicators[ind_key][key]] for key in ordered_timestamps]})

                else:
                    if ind_key in DOUBLE_DEPTH_INDICATORS:
                        for ma_type in cInds[ind_key]:
                            cInds[ind_key].update({ma_type:[self.indicators[ind_key][ma_type][key] for key in self.indicators[ind_key][ma_type] if key in time_range]})
                    else: 
                        cInds.update({ind_key:[self.indicators[ind_key][key] for key in self.indicators[ind_key] if key in time_range]}) 

        return(cInds)