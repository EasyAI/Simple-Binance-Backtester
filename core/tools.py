DOUBLE_DEPTH_INDICATORS = ['ema', 'sma']
UN_SEQUENTIAL_DATA = ['tops_bottoms']


def get_max_length(indicators):
    get_ma_len = lambda ma_type : [len(indicators[ma_type][ind_key]) for ind_key in indicators[ma_type].keys()] if ma_type in indicators else [999999999]
    
    base_ind_lens = [len(indicators[ind_key]) for ind_key in indicators.keys() if not ind_key in DOUBLE_DEPTH_INDICATORS]

    return(min(base_ind_lens+get_ma_len('ema')+get_ma_len('sma')))


def build_empty_indicators(indicators):
    base_inds = {ind_key:{} for ind_key in indicators.keys()}

    for ma in DOUBLE_DEPTH_INDICATORS:
        if ma in indicators.keys():
            base_inds[ma].update({ind_key:{} for ind_key in indicators[ma].keys()})

    return(base_inds)


def timestamp_indicators(candleData, indicators):
    stampped_ind = build_empty_indicators(indicators)

    for ind_key in indicators.keys():
        if ind_key in UN_SEQUENTIAL_DATA:
            stampped_ind[ind_key].update({ ind[0]:ind[1] for ind in indicators[ind_key] })
        else:
            if ind_key in DOUBLE_DEPTH_INDICATORS:
                for ma_type in indicators[ind_key]:
                    for index, candle in enumerate(candleData):
                        timestamp = candle[0]
                        stampped_ind[ind_key][ma_type].update({ timestamp:indicators[ind_key][ma_type][index] })
            else:
                for index, candle in enumerate(candleData):
                    timestamp = candle[0]
                    stampped_ind[ind_key].update({ timestamp:indicators[ind_key][index] })

    return(stampped_ind)