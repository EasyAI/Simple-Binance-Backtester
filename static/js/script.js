const main_chart_indicators = ['ichi', 'rma', 'ema', 'sma', 'boll'];

const multi_line_indicators = ['ichi', 'boll', 'adx', 'stock'];
const single_line_indicators = ['ema', 'sma', 'rma', 'rsi', 'mfi', 'cci'];
const macd_indicators = ['zerolagmacd', 'macd'];

const double_depth_indicators = ['ema', 'sma'];

const socket = io('http://127.0.0.1:5000');
const request = new XMLHttpRequest();

var main_inds = document.getElementById("charts_display_panel");
var active_charts = [];
var candle_chart = [];

let candle_data = [];
let indicator_data = [];
let complete_orders = [];

window.Apex = {
    chart: {
        animations: {
            enabled: false
        }
    },
    autoScaleYaxis: false
};

var current_boll = 0;

socket.on('update_data', function(data) {
    var charting_data   = data['data'];

    if (candle_data[0][0]!=charting_data['candleData'][0][0]) {
        candle_data.unshift(charting_data['candleData'][0]);
        candle_data[0] = charting_data['candleData'][1];
    } else {
        candle_data[0] = charting_data['candleData'][0];
        candle_data[1] = charting_data['candleData'][1];
    }

    for (var indicator in charting_data['indicators']) {
        if (indicator in double_depth_indicators) {
            for (var sub_ind in charting_data['indicators'][indicator]) {
                for (var sub_ind in charting_data['indicators'][indicator][sub_ind]) {
                    indicator_data[indicator][sub_ind][timestamp] = charting_data['indicators'][indicator][sub_ind][timestamp];
                }   
            }
        } else {
            for (var timestamp in charting_data['indicators'][indicator]) {
                indicator_data[indicator][timestamp] = charting_data['indicators'][indicator][timestamp];
            }
        }
    }

    console.log(indicator_data);

    complete_orders = charting_data['orders'];

    update_charts();
});


function update_charts()  {
    var built_data = build_candle_data(candle_data);
    var built_candle_data = built_data[0];

    var orders = build_order_data(complete_orders);
    var b_orders = orders[0];
    var s_orders = orders[1];

    candle_chart['series']['w']['config']['series']['Buy'] = b_orders;
    candle_chart['series']['w']['config']['series']['Sell'] = s_orders;
    candle_chart['series']['w']['config']['series']['candle'] = built_candle_data;

    for (var ind in indicator_data) {
        if (ind in main_chart_indicators) {
            if (ind in multi_line_indicators) {
                indicator =  build_multiline_timeseries(indicator_data[ind])
            } else if (ind in single_line_indicators) {
                indicator =  build_singleline_timeseries(indicator_data[ind])
            }
            for (var sub_ind in indicator) {
                candle_chart['series']['w']['config']['series'][sub_ind] = indicator[sub_ind]
            }
        } else if (ind in active_charts) {
            console.log(ind);
            if (ind in multi_line_indicators) {
                indicator =  build_multiline_timeseries(indicator_data[ind])
            } else if (ind in single_line_indicators) {
                indicator =  build_singleline_timeseries(indicator_data[ind])
            } else {
                indicator = build_macd_timeseries(indicator_data[ind])
            }
            console.log(indicator);
            for (var sub_ind in indicator) {
                candle_chart['series']['w']['config']['series'][sub_ind] = indicator[sub_ind]
            }
        }
    }  
}


function setup(charting_data) {
    candle_data         = charting_data['candleData'];
    indicator_data      = charting_data['indicators'];
    complete_orders     = charting_data['orders'];

    // Add main chart candles
    var mc = document.createElement('div');
    mc.setAttribute("id", "candles_chart");
    main_inds.append(mc)

    // Add main chart volumes.
    var mc = document.createElement('div');
    mc.setAttribute("id", "volumes_chart");
    main_inds.append(mc)

    add_chart_ids(indicator_data);

    draw_charts();
}


function build_candle_data(cd) {
    var built_candle_data = [];
    var built_volume_data = [];
    for (i=0;i<cd.length;i++) {
        built_candle_data.push({
            x: new Date(cd[i][0]),
            y: [
                cd[i][1],
                cd[i][2],
                cd[i][3],
                cd[i][4]
            ]
        });

        built_volume_data.push({
            x: new Date(cd[i][0]),
            y: Math.round(cd[i][5])
        });
    }
    return([built_candle_data, built_volume_data]);
}


function build_order_data(raw_orders) {
    var b_orders = [];
    var s_orders = [];

    for (i=0;i<raw_orders.length;i++) {
        if (raw_orders[i][3].split("-")[0] == "BUY") {
            b_orders.push({
                x: raw_orders[i][0],
                y: raw_orders[i][1]
            });
        } else {
            s_orders.push({
                x: raw_orders[i][0],
                y: raw_orders[i][1]
            });
        }
    }
    return([b_orders, s_orders]);
}


function draw_charts() {
    var list_of_Data = [];
    var volume_chart = [];

    // Add main chart candles
    var mc = document.createElement('div');
    mc.setAttribute("id", "candles_chart");
    main_inds.append(mc);

    // Add main chart volumes.
    var mc = document.createElement('div');
    mc.setAttribute("id", "volumes_chart");
    main_inds.append(mc);

    var built_data = build_candle_data(candle_data);
    var built_candle_data = built_data[0];
    var built_volume_data = built_data[1];

    // Chart template for main chart.
    var base_candle_chart_configuration = {
        series: [],
        chart: {
            height: 800,
            id: 'main_Chart',
            group:'indicators-link-charts',
            type: 'line'
        },
        fill: {
            type:'solid',
        },
        markers: {
            size: []
        },
        //colors: [],
        stroke: {
            width: []
        },
        tooltip: {
            custom: []
        },
        xaxis: {
            type: 'datetime',
        },
        yaxis: {
            labels: {
                minWidth: 40,
                formatter: function (value) { return Math.round(value); }
            },
        }
    };


    // Chart template for indicators
    var base_indicator_chart_configuration = {
        series: [],
        chart: {
            height: 350,
            id: 'chart',
            group:'indicators-link-charts',
            type: 'line'
        },
        title: {
            text: 'Chart',
            align: 'left'
        },
        fill: {
            type:'solid',
        },
        markers: {
            size: []
        },
        stroke: {
            width: []
        },
        tooltip: {
            shared: true
        },
        xaxis: {
            type: 'datetime'
        },
        yaxis: {
            labels: {
                minWidth: 40,
                formatter: function (value) { return Math.round(value); }
            }
        }
    };


    // Add the placed orders onto a chart.
    if (complete_orders!=null) {
        var orders = build_order_data(complete_orders);
        var b_orders = orders[0];
        var s_orders = orders[1];

        base_candle_chart_configuration["series"].push({
            name: 'Buy',
            type: 'scatter',
            data: b_orders
        }, {
            name: 'Sell',
            type: 'scatter',
            data: s_orders
        });
        base_candle_chart_configuration["markers"]["size"].push(8, 8);
        base_candle_chart_configuration["stroke"]["width"].push(0,0);
        //base_candle_chart_configuration.colors.push('#12C500', '#D24300');
        base_candle_chart_configuration["tooltip"]["custom"].push(
            function({seriesIndex, dataPointIndex, w}) {
                return w.globals.series[seriesIndex][dataPointIndex]
            },
            function({seriesIndex, dataPointIndex, w}) {
                return w.globals.series[seriesIndex][dataPointIndex]
            }
        );
    }

    // Add BOLL indicators to the existing main chart.
    if ("boll" in indicator_data) {
        build_mulit_line_indicator(base_candle_chart_configuration, indicator_data["boll"]);
    }

    // Add Ichimoku indicators to the existing main chart.
    if ("ichi" in indicator_data) {
        build_mulit_line_indicator(base_candle_chart_configuration, indicator_data["ichi"]);
    }

    // Add SMA indicators to the existing main chart.
    if ("sma" in indicator_data) {
        for (var sma_type in indicator_data['sma']) {
            build_single_line_indicator(base_candle_chart_configuration, indicator_data['sma'][sma_type], sma_type)
        }
    }

    // Add EMA indicators to the existing main chart.
    if ("ema" in indicator_data) {
        for (var ema_type in indicator_data['ema']) {
            build_single_line_indicator(base_candle_chart_configuration, indicator_data['ema'][ema_type], ema_type)
        }
    }

    // Add RMA indicators to the existing main chart.
    if ("rma" in indicator_data) {
        for (var rma_type in indicator_data['rma']) {
            build_single_line_indicator(base_candle_chart_configuration, indicator_data['rma'][rma_type], rma_type)
        }
    }

    // Finally add the candle to the displayed chart.
    base_candle_chart_configuration["series"].push({
        name: 'candle',
        type: 'candlestick',
        data: built_candle_data
    });
    base_candle_chart_configuration["stroke"]["width"].push(.1);
    base_candle_chart_configuration["tooltip"]["custom"].push(function({seriesIndex, dataPointIndex, w}) {
        var o = w.globals.seriesCandleO[seriesIndex][dataPointIndex]
        var h = w.globals.seriesCandleH[seriesIndex][dataPointIndex]
        var l = w.globals.seriesCandleL[seriesIndex][dataPointIndex]
        var c = w.globals.seriesCandleC[seriesIndex][dataPointIndex]
        return (`O:${o}<br>H:${h}<br>L:${l}<br>C:${c}`)
    });

    candle_chart = new ApexCharts(document.querySelector("#candles_chart"), base_candle_chart_configuration);

    /*
    // Add volume to the display.
    new ApexCharts(document.querySelector("#volumes_chart"), {
        series: [{
            name: 'Volume',
            type: 'bar',
            data: built_volume_data
        }],
        chart: {
            height: 150,
            id:'volume_chart',
            group:'indicators-link-charts'
        },
        title: {
            text: 'Volume Chart',
            align: 'left'
        },
        fill: {
            type:'solid',
        },
        markers: {
            size: [1]
        },
        stroke: {
            width: [1]
        },
        xaxis: {
            type: 'datetime'
        },
        yaxis: {
            labels: {
                minWidth: 40,
                formatter: function (value) { return Math.round(value); }
            }
        }
    }).render();*/

    // Add RSI indicators to the existing main chart.
    if ('rsi' in indicator_data) {
        active_charts['rsi'] = new ApexCharts(document.querySelector("#rsi_chart"), build_single_line_indicator(JSON.parse(JSON.stringify(base_indicator_chart_configuration)), indicator_data["rsi"], 'rsi', 'RSI'));
    }

    // Add MACD indicators to the existing main chart.
    if ('macd' in indicator_data) {
        active_charts['macd'] = new ApexCharts(document.querySelector("#macd_chart"), build_indicator_macd(JSON.parse(JSON.stringify(base_indicator_chart_configuration)), indicator_data["macd"], 'MACD'));
    }

    // Add ZeroLag MACD indicators to the existing main chart.
    if ('zerolagmacd' in indicator_data) {
        active_charts['zerolagmacd'] = new ApexCharts(document.querySelector("#zerolagmacd_chart"), build_indicator_macd(JSON.parse(JSON.stringify(base_indicator_chart_configuration)), indicator_data["zerolagmacd"], 'ZeroLag MACD'));
    }

    // Add Stochastics RSI indicators to the existing main chart.
    if ('stock' in indicator_data) {
        active_charts['stock'] = new ApexCharts(document.querySelector("#stock_chart"), build_mulit_line_indicator(JSON.parse(JSON.stringify(base_indicator_chart_configuration)), indicator_data["stock"], 'Stochastics RSI'));
    }

    // Add ADX indicators to the existing main chart.
    if ('adx' in indicator_data) {
        active_charts['adx'] = new ApexCharts(document.querySelector("#adx_chart"), build_mulit_line_indicator(JSON.parse(JSON.stringify(base_indicator_chart_configuration)), indicator_data["adx"], 'ADX'));
    }

    // Add CCI indicators to the existing main chart.
    if ('cci' in indicator_data) {
        active_charts['cci'] = new ApexCharts(document.querySelector("#cci_chart"), build_single_line_indicator(JSON.parse(JSON.stringify(base_indicator_chart_configuration)), indicator_data["cci"], 'cci', 'CCI'));
    }

    // Add MFI indicators to the existing main chart.
    if ('mfi' in indicator_data) {
        active_charts['mfi'] = new ApexCharts(document.querySelector("#mfi_chart"), build_single_line_indicator(JSON.parse(JSON.stringify(base_indicator_chart_configuration)), indicator_data["mfi"], 'mfi', 'MFI'));
    }

    for (chart in active_charts) {
        active_charts[chart].render();
    }

    candle_chart.render()
    candle_chart.zoomX(built_candle_data[150]['x'].getTime(), built_candle_data[0]['x'].getTime());
}


function add_chart_ids(ind_obj) {
    for (var key in ind_obj) {
        if (!(key in main_chart_indicators)) {
            console.log(`${key}_chart`);
            var mc = document.createElement('div');
            mc.setAttribute("id", `${key}_chart`);
            main_inds.append(mc)
        }
    }
}


function build_macd_timeseries(base_data) {
    var macd_signal = [];
    var macd_macd = [];
    var macd_hist = [];

    for (var timestamp in base_data) {
        current_band = base_data[timestamp]

        macd_signal.push({
            x: new Date(parseInt(timestamp)),
            y: base_data[timestamp]["signal"].toFixed(8),
        });
        macd_macd.push({
            x: new Date(parseInt(timestamp)),
            y: base_data[timestamp]["macd"].toFixed(8),
        });
        macd_hist.push({
            x: new Date(parseInt(timestamp)),
            y: base_data[timestamp]["hist"].toFixed(8),
        });
    }
    return({'signal':macd_signal, 'macd':macd_macd, 'hist':macd_hist})
}


function build_multiline_timeseries(ind_obj) {
    var indicator_lines = [];
    var keys = []
    for (var timestamp in ind_obj) {
        current_set = ind_obj[timestamp]

        for (var sub_ind in current_set) {
            if (!keys.includes(sub_ind)) {
                keys.push(sub_ind)
                indicator_lines[sub_ind] = []
            }
            indicator_lines[sub_ind].push({
                x: new Date(parseInt(timestamp)),
                y: ind_obj[timestamp][sub_ind].toFixed(8)
            });
        }
    }
    return(indicator_lines);
}


function build_singleline_timeseries(ind_obj) {
    var indicator_lines = [];
    for (var timestamp in ind_obj) {
        current_line = ind_obj[timestamp]

        indicator_lines.push({
            x: new Date(parseInt(timestamp)),
            y: current_line.toFixed(8)
        });
    }
    return(indicator_lines);
}


function build_single_line_indicator(chart_obj, ind_obj, line_name, ind_name=null) {
    var indicator_lines = build_singleline_timeseries(ind_obj);
    chart_obj["series"].push({
        name: line_name,
        type: 'line',
        data: indicator_lines});

    chart_obj["stroke"]["width"].push(2);
    chart_obj["markers"]["size"].push(0);

    if ('custom' in ind_obj) {
        chart_obj["tooltip"]["custom"].push(
            function({seriesIndex, dataPointIndex, w}) {
                return w.globals.series[seriesIndex][dataPointIndex]
        });
    }

    if (!(ind_name == null)) {
        chart_obj['chart']['id'] = `${ind_name}_chart`
        chart_obj['title']['text'] = ind_name
    }

    return(chart_obj);
}


function build_mulit_line_indicator(chart_obj, ind_obj, ind_name=null) {
    var indicator_lines = build_multiline_timeseries(ind_obj);
    for (var sub_ind_name in indicator_lines) {

        chart_obj["series"].push({
            name: sub_ind_name,
            type: 'line',
            data: indicator_lines[sub_ind_name]});

        chart_obj["stroke"]["width"].push(2);
        chart_obj["markers"]["size"].push(0);

    }

    if ('custom' in ind_obj) {
        for (ind in ind_obj) {
            chart_obj["tooltip"]["custom"].push(
                function({seriesIndex, dataPointIndex, w}) {
                    return w.globals.series[seriesIndex][dataPointIndex]
            });
        }
    }

    if (!(ind_name == null)) {
        chart_obj['chart']['id'] = `${ind_name}_chart`
        chart_obj['title']['text'] = ind_name
    }

    return(chart_obj);
}


function build_indicator_macd(chart_obj, macd_data, ind_name) {
    // Function used to build the macd indicator to a passed chart.
    var timeseries = build_macd_timeseries(macd_data);

    chart_obj["series"].push({
        name: 'Signal',
        type: 'line',
        data: timeseries['signal']
    }, {
        name: 'MACD',
        type: 'line',
        data: timeseries['macd']
    }, {
        name: 'Hist',
        type: 'bar',
        data: timeseries['hist']
    });

    chart_obj['chart']['id'] = `${ind_name}_chart`
    chart_obj['title']['text'] = ind_name

    return(chart_obj);
}


function pull_candles(){
    rest_api('GET', 'get_trade_data');
}


function rest_api(method, endpoint, data=null){
    // if either the user has requested a force update on bot data or the user has added a new market to trade then send an update to the backend.
    request.open(method, '/rest-api/v1/'+endpoint, true);

    if (data == null){
      request.send();
    } else {
      request.setRequestHeader('content-type', 'application/json');
      request.send(JSON.stringify(data));
    }

    request.onload = () => {
        if (request.status == 200){
          console.log(JSON.parse(request.response));
          setup(JSON.parse(request.response).data);
        } else {
          console.log(`error ${request.status} ${request.statusText}`);
        }
    }
}

pull_candles();