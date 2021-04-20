// Base connection constants
const socket = io('http://127.0.0.1:5000');
const request = new XMLHttpRequest();

// Indicator meta details
const indicator_chart_types_mapping = {'patterns_data_lines':'line', 'patterns_data_points':'scatter', 'tops_bottoms':'scatter', 'data_lines':'line', 'ichi':'line', 'boll':'line', 'adx':'line', 'stock':'line', 'order':'scatter', 'ema':'line', 'sma':'line', 'rma':'line', 'rsi':'line', 'mfi':'line', 'cci':'line', 'zerolagmacd':'macd', 'macd':'macd'}
const indicator_home_type_mapping = {'patterns_data_lines':'MAIN', 'patterns_data_points':'MAIN', 'tops_bottoms':'MAIN', 'data_lines':'MAIN', 'ichi':'MAIN', 'boll':'MAIN', 'adx':'OWN', 'stock':'OWN', 'order':'MAIN', 'ema':'MAIN', 'sma':'MAIN', 'rma':'MAIN', 'rsi':'OWN', 'mfi':'OWN', 'cci':'OWN', 'zerolagmacd':'OWN', 'macd':'OWN'}
const indicator_is_single_mapping = ['patterns_data_lines', 'patterns_data_points', 'tops_bottoms', 'data_lines', 'order', 'ema', 'sma', 'rma', 'rsi', 'mfi', 'cci']
const double_depth_indicators = ['ema', 'sma', 'order', 'order_comp', 'patterns_data_points', 'patterns_data_lines'];

// Base Apex chart configuration.
window.Apex = {
    chart: {
        animations: {
            enabled: false
        }
    },
    autoScaleYaxis: false
};

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
        shared: true,
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

// Charting storage/display details.
var main_inds = document.getElementById("charts_display_panel");
var active_charts = [];
var candle_chart = null;

// Local storage for recived data.
let candle_data = [];
let indicator_data = [];


function pull_candles(){
    rest_api('GET', 'get_data');
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


function setup(charting_data) {
    candle_data         = charting_data['candleData'];
    indicator_data      = charting_data['indicators'];

    // Add main chart candles
    var mc = document.createElement('div');
    mc.setAttribute("id", "candles_chart");
    main_inds.append(mc)

    // Add main chart volumes.
    var mc = document.createElement('div');
    mc.setAttribute("id", "volumes_chart");
    main_inds.append(mc)

    add_chart_ids(indicator_data);

    initial_build();
}


function initial_build() {
    // Add main chandle chart position.
    var mc = document.createElement('div');
    mc.setAttribute("id", "candles_chart");
    main_inds.append(mc);

    populate_charts("initial");

    var built_data = build_candle_data(candle_data);
    var built_candle_data = built_data[0];

    // Finally add the candle to the displayed chart.
    base_candle_chart_configuration["series"].push({
        name: 'candle',
        type: 'candlestick',
        data: built_candle_data
    });
    base_candle_chart_configuration["stroke"]["width"].push(1);
    base_candle_chart_configuration["markers"]["size"].push(0);
    base_candle_chart_configuration["tooltip"]["custom"].push(function({seriesIndex, dataPointIndex, w}) {
        var o = w.globals.seriesCandleO[seriesIndex][dataPointIndex]
        var h = w.globals.seriesCandleH[seriesIndex][dataPointIndex]
        var l = w.globals.seriesCandleL[seriesIndex][dataPointIndex]
        var c = w.globals.seriesCandleC[seriesIndex][dataPointIndex]
        return (`Open:${o}<br>High:${h}<br>Low:${l}<br>Close:${c}`)
    });

    candle_chart = new ApexCharts(document.querySelector("#candles_chart"), base_candle_chart_configuration);

    for (chart in active_charts) {
        active_charts[chart].render();
    }

    candle_chart.render();
}


function add_chart_ids(ind_obj) {
    for (var key in ind_obj) {
        if (indicator_home_type_mapping[key] == 'OWN') {
            var mc = document.createElement('div');
            mc.setAttribute("id", `${key}_chart`);
            main_inds.append(mc);
        }
    }
}


function build_candle_data(candle_data) {
    var built_candle_data = [];
    var built_volume_data = [];
    var sorted_timestamps = sort_timestamps(candle_data);

    for (var i in sorted_timestamps) {
        var timestamp = sorted_timestamps[i];
        built_candle_data.push({
            x: new Date(parseInt(timestamp)),
            y: [
                candle_data[timestamp][0],
                candle_data[timestamp][1],
                candle_data[timestamp][2],
                candle_data[timestamp][3]
            ]
        });

        built_volume_data.push({
            x: new Date(parseInt(timestamp)),
            y: Math.round(candle_data[timestamp][4])
        });
    }
    return([built_candle_data, built_volume_data]);
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


function build_timeseries(ind_obj) {
    var indicator_lines = [];
    var keys = []
    var sorted_timestamps = sort_timestamps(ind_obj);

    // Use sorted timestamp to print out.
    for (var i in sorted_timestamps) {
        var timestamp = sorted_timestamps[i];
        var current_set = ind_obj[timestamp]
        if (typeof current_set == 'number') {
            indicator_lines.push({
                x: new Date(parseInt(timestamp)),
                y: ind_obj[timestamp].toFixed(8)
            });
        } else {
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
    }
    return(indicator_lines);
}


function build_basic_indicator(chart_obj, ind_obj, chart_type, line_name=null, return_chart=false, ind_name=null) {
    var indicator_lines = build_timeseries(ind_obj);

    if (!(line_name == null)) {
        chart_obj["series"].push({
            name: line_name,
            type: chart_type,
            data: indicator_lines
        });
        if (chart_type == "scatter") {
            chart_obj["stroke"]["width"].push(2);
            chart_obj["markers"]["size"].push(8);
        } else {
            chart_obj["stroke"]["width"].push(2);
            chart_obj["markers"]["size"].push(0);
        }
    } else {
        for (var sub_ind_name in indicator_lines) {
            chart_obj["series"].push({
                name: sub_ind_name,
                type: chart_type,
                data: indicator_lines[sub_ind_name]});
            if (chart_type == "scatter") {
                chart_obj["stroke"]["width"].push(2);
                chart_obj["markers"]["size"].push(8);
            } else {
                chart_obj["stroke"]["width"].push(2);
                chart_obj["markers"]["size"].push(0);
            }
        }
    }

    if ('custom' in chart_obj["tooltip"]) {
        if (!(line_name == null)) {
            chart_obj["tooltip"]["custom"].push(
                function({seriesIndex, dataPointIndex, w}) {
                    return w.globals.series[seriesIndex][dataPointIndex]
            });
        } else {
            for (var ind in indicator_lines) {
                chart_obj["tooltip"]["custom"].push(
                    function({seriesIndex, dataPointIndex, w}) {
                        return w.globals.series[seriesIndex][dataPointIndex]
                });
            }
        }
    }

    if (return_chart == true) {
        chart_obj['chart']['id'] = `${ind_name}_chart`
        chart_obj['title']['text'] = ind_name
        return(chart_obj);
    } else {
        return null;
    }
}


function build_indicator_macd(chart_obj, ind_obj, chart_type, line_name=null, return_chart=false, ind_name=null) {
    // Function used to build the macd indicator to a passed chart.
    var timeseries = build_macd_timeseries(ind_obj);

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

    if (return_chart == true) {
        chart_obj['chart']['id'] = `${ind_name}_chart`
        chart_obj['title']['text'] = ind_name
        return(chart_obj);
    } else {
        return null;
    }
}

socket.on("update_data", function(data) {
    var charting_data   = data["data"];

    for (var timestamp in charting_data["candleData"]) {
        candle_data[timestamp] = charting_data["candleData"][timestamp]
    }

    for (var indicator in charting_data["indicators"]) {
        if (indicator in double_depth_indicators) {
            for (var sub_ind in charting_data["indicators"][indicator]) {
                for (var sub_ind in charting_data["indicators"][indicator][sub_ind]) {
                    indicator_data[indicator][sub_ind][timestamp] = charting_data["indicators"][indicator][sub_ind][timestamp];
                }   
            }
        } else {
            for (var timestamp in charting_data["indicators"][indicator]) {
                indicator_data[indicator][timestamp] = charting_data["indicators"][indicator][timestamp];
            }
        }
    }

    populate_charts("update");
});


function populate_charts(population_type) {
    var main_chart = [];
    var sub_chart = {};

    for (var indicator in indicator_data) {
        var current_ind = indicator_data[indicator];
        var chart_type = indicator_chart_types_mapping[indicator];
        var home_chart = indicator_home_type_mapping[indicator];
        var line_name = null;
        var return_chart = null;
        var seriesData = null;

        var ind_name = null;

        if (home_chart == "MAIN") {
            target_chart = base_candle_chart_configuration;
        } else if (home_chart == "OWN") {
            ind_name = indicator;
            target_chart = JSON.parse(JSON.stringify(base_indicator_chart_configuration));
            return_chart = true;
            sub_chart[indicator] = [];
        }

        if (double_depth_indicators.includes(indicator)) {
            for (var sub_ind in current_ind) {
                line_name = sub_ind;
                if (population_type == "update") { 
                    seriesData = update_series(current_ind, chart_type, line_name);
                    if (home_chart == "MAIN") {
                        main_chart = main_chart.concat(seriesData);
                    } else if (home_chart == "OWN") {
                        sub_chart[indicator] = sub_chart[indicator].concat(seriesData);
                    }
                } else { 
                    var built_chart = build_basic_indicator(target_chart, current_ind[sub_ind], chart_type, line_name, return_chart, ind_name);
                }
            }
        } else {
            if (indicator_is_single_mapping.includes(indicator)) {
                line_name = indicator;
            }
            if (chart_type == "macd") {
                var built_chart = build_indicator_macd(target_chart, current_ind, chart_type, line_name, return_chart, ind_name);
            } else {
                if (population_type == "update") { 
                    seriesData = update_series(current_ind, chart_type, line_name);
                    if (home_chart == "MAIN") {
                        main_chart = main_chart.concat(seriesData);
                    } else if (home_chart == "OWN") {
                        sub_chart[indicator] = sub_chart[indicator].concat(seriesData);
                    }
                } else { 
                    var built_chart = build_basic_indicator(target_chart, current_ind, chart_type, line_name, return_chart, ind_name);
                }   
            }
        }

        if (return_chart == true) {
            active_charts[indicator] = new ApexCharts(document.querySelector(`#${indicator}_chart`), built_chart);
        }
    }

    if (population_type == "update") {
        /*for (indicator in sub_chart) {
            if (indicator in active_charts){
                active_charts[indicator].updateSeries(sub_chart[indicator])
            }
        }*/

        main_chart.push({name: "candle", type: "candlestick", data: build_candle_data(candle_data)[0]});
        candle_chart.updateSeries(main_chart);
    }
}


function update_series(ind_obj, chart_type, line_name=null) {
    var indicator_lines = build_timeseries(ind_obj);
    var series = [];
    if (!(line_name == null)) {
        series.push({
            name: line_name,
            type: chart_type,
            data: indicator_lines
        });
    } else {
        for (var sub_ind_name in indicator_lines) {
            series.push({
                name: sub_ind_name,
                type: chart_type,
                data: indicator_lines[sub_ind_name]
            });
        }
    }
    return(series)
}


function sort_timestamps(ind_obj) {
    // Sort the timestamps in acending order.
    var sorted_timestamps = [];
    for (var timestamp in ind_obj) {
        sorted_timestamps.push(parseInt(timestamp))
    }
    return(sorted_timestamps.sort(function(a, b){return a-b}));
}


pull_candles();