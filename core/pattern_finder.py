#! /usr/bin/env python3

import time
import json
import logging
import patterns
import threading
import numpy as np
import core.tools as tools
import core.data_interface as DI
import technical_indicators as TI

'''
x : Price list
y : Last comparible value.
z : Historic comparible value.

# find_high_high
( x : price list, y : last high, z : historic high value )
Return highest value seen vs both recent and historically or None.

# find_high
( x : price list, y : last high )
Return the highest value seen or None.

# find_low_high
( x : price list, y : last high, z : historic high value )
Return highest value seen recently but lower historically or None.

# find_low_low
( x : price list, y : last low, z : historic low value )
Return the lowest value seen vs both recent and historically or None.

# find_low
( x : price list, y : last low )
Return the lowest value seen or None.

# find_high_low
( x : price list, y : last low, z : historic low value )
Return lowest value seen recently but higher historically or None.
'''
## High setups
find_high_high  = lambda x, y, z: x.max() if z < x.max() > y else None
find_high       = lambda x, y: x.max() if x.max() > y else None
find_low_high   = lambda x, y, z: x.max() if z > x.max() > y else None
## Low setup
find_low_low    = lambda x, y, z: x.min() if z > x.min() < y else None
find_low        = lambda x, y: x.min() if x.min() < y else None
find_high_low   = lambda x, y, z: x.min() if z < x.min() < y else None


class PatternFinder():

    def __init__(self):
        self.candles = []
        self.indicators = {}


    def setup(self, data_source, limit, segment_span=4, price_point=0, get_pattern=False):
        '''
        segment_span: segment size to compare for finding moves
        price_point : 0 = low/high, 1 = close, 2 = open
        '''
        ## Setup the initial config for the trade simulator for either backtest of live test.
        with open('hist_data/{0}'.format(data_source), 'r') as file:
            file_data   = json.load(file)

        data_inf        = DI.hist_data_interface(file_data['data'][:int(limit)])
        candleData      = data_inf.get_candle_data_all()
        self.candles    = candleData
        
        self.get_pattern = get_pattern
        self.pattern = None

        if get_pattern:
            self.indicators.update({'patterns_data_points':{}})
            self.indicators.update({'patterns_data_lines':{}})
            self.pattern = patterns.pattern_W()
            self.segment_span = self.pattern.segment_span
            self.price_point = self.pattern.price_point
        else:
            self.indicators.update({'data_lines':{}})
            self.segment_span = segment_span
            self.price_point = price_point
        
        # Setup a list of just the timestamps to use as keys.
        self.date_list = [candle[0] for candle in self.candles]


    def start(self):
        patternBuilder_th = threading.Thread(target=self._pattern_builder_run)
        patternBuilder_th.start()

        return(True)


    def _pattern_builder_run(self):
        start_time = time.time()
        print('Started Pattern Finder...')
        pattern_points = patterns.get_tops_bottoms(self.candles, self.segment_span, self.price_point)

        self.indicators.update({'tops_bottoms':{point[0]:point[1] for point in pattern_points}})

        if self.pattern != None:
            self._find_pattern(self.pattern)

        print('Runtime took: {0}'.format(time.time()-start_time))


    def _find_pattern(self, pattern):
        itter_skip = 0
        total_patterns = 1

        combined_points = self.indicators['tops_bottoms']

        point_intervals = sorted(combined_points.keys(), reverse=True)

        for i in range(len(combined_points.keys())-(self.pattern.required_points+self.pattern.result_points)):
            set_range = self.pattern.required_points+self.pattern.result_points
            start_point = len(combined_points.keys())-(i+set_range)

            current_timestamp_set = point_intervals[start_point:start_point+set_range]
            c_set = np.asarray([combined_points[timestamp] for timestamp in current_timestamp_set[self.pattern.result_points:]])

            if self.pattern.check_condition(c_set):
                full_with_result = [combined_points[timestamp] for timestamp in current_timestamp_set]
                if full_with_result[0] > full_with_result[2]:
                    print('Found Pattern')
                    pattern_id = 'pattern{0}'.format(total_patterns)
                    pattern_points = {timestamp:combined_points[timestamp] for timestamp in current_timestamp_set}
                    self.indicators['patterns_data_points'].update({pattern_id+'points':pattern_points})
                    self.indicators['patterns_data_lines'].update({pattern_id+'lines':pattern_points})
                    total_patterns+=1
                    itter_skip = self.pattern.required_points


if __name__ == "__main__":
    main()