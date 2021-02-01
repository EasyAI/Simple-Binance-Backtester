
const request = new XMLHttpRequest();
var candle_data = [];

window.Apex = {
    chart: {
        animations: {
            enabled: false
        }
    },
    autoScaleYaxis: false
}

var current_boll = 0;


function draw_chart(chartingData){

    var candleData = chartingData["candleData"];

    console.log(chartingData);

    var list_of_ema144 = [];
    var list_of_ema2584 = [];
    var list_of_Data = [];
    var volume_chart = [];

    for (i=0;i<candleData.length;i++) {
        list_of_Data.push({
            x: new Date(candleData[i][0]),
            y: [
                candleData[i][1],
                candleData[i][2],
                candleData[i][3],
                candleData[i][4]
            ]
        });

        volume_chart.push({
            x: new Date(candleData[i][0]),
            y: Math.round(candleData[i][5])
        });
    }

    // Build skelatal chart.
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

    // Add the placed orders onto a chart.
    if (chartingData["orders"]!=null) {

        var orders = chartingData["orders"];
        var indicators = chartingData["indicators"];
        var b_orders = [];
        var s_orders = [];

        for (i=0;i<orders.length;i++) {
            if (orders[i][2] == "buy") {
                b_orders.push({
                    x: orders[i][0],
                    y: orders[i][1]
                });
            } else {
                s_orders.push({
                    x: orders[i][0],
                    y: orders[i][1]
                });
            }
        }

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

    if ("boll" in indicators) {
        build_mulit_line_indicator(base_candle_chart_configuration, indicators["boll"]);
    }

    // Add SMA indicators to the existing candles.
    if ("sma" in indicators) {
        console.log("adding SMA");

        for (var sma_type in indicators['sma']) {
            build_single_line_indicator(base_candle_chart_configuration, indicators['sma'][sma_type], sma_type)
        }

    }

    // Add EMA indicators to the existing candles.
    if ("ema" in indicators) {
        console.log("adding EMA");

        for (var sma_type in indicators['ema']) {
            build_single_line_indicator(base_candle_chart_configuration, indicators['ema'][sma_type], sma_type)
        }

    }

    // Finally add the candle to the displayed chart.
    base_candle_chart_configuration["series"].push({
        name: 'candle',
        type: 'candlestick',
        data: list_of_Data
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

    // Add volume to the display.
    new ApexCharts(document.querySelector("#volumes_chart"), {
        series: [{
            name: 'Volume',
            type: 'bar',
            data: volume_chart
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
    }).render();


    new ApexCharts(document.querySelector("#macd_chart"), build_indicator_macd({
        series: [],
        chart: {
            height: 350,
            id: 'macd_chart',
            group:'indicators-link-charts',
            type: 'line'
        },
        title: {
            text: 'MACD Chart',
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
            shared: true,
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
    }, indicators["macd"])).render();

    /*new ApexCharts(document.querySelector("#stoch_chart"), build_indicator_stoch()).render();*/

    candle_chart.render()
    candle_chart.zoomX(list_of_Data[150]['x'].getTime(), list_of_Data[0]['x'].getTime());

}


function build_single_line_indicator(chart_obj, ind_obj, ind_name) {
    var indicator_lines = [];
    
    for (var timestamp in ind_obj) {
        current_line = ind_obj[timestamp]

        indicator_lines.push({
            x: new Date(parseInt(timestamp)),
            y: current_line.toFixed(8)
        });
    }

    chart_obj["series"].push({
        name: ind_name,
        type: 'line',
        data: indicator_lines});

    chart_obj["stroke"]["width"].push(2);
    chart_obj["markers"]["size"].push(0);

    chart_obj["tooltip"]["custom"].push(
        function({seriesIndex, dataPointIndex, w}) {
            return w.globals.series[seriesIndex][dataPointIndex]
    });

    return(chart_obj);
}


function build_mulit_line_indicator(chart_obj, ind_obj) {
    console.log(ind_obj);

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

    var ind_series = [];
    for (var sub_ind_name in indicator_lines) {

        chart_obj["series"].push({
            name: sub_ind_name,
            type: 'line',
            data: indicator_lines[sub_ind_name]});

        chart_obj["stroke"]["width"].push(2);
        chart_obj["markers"]["size"].push(0);
        
        chart_obj["tooltip"]["custom"].push(
            function({seriesIndex, dataPointIndex, w}) {
                return w.globals.series[seriesIndex][dataPointIndex]
        });

    }
    return(chart_obj);
}


function build_indicator_macd(chart_obj, macd_data) {
    // Function used to build the macd indicator to a passed chart.
    var macd_signal = [];
    var macd_macd = [];
    var macd_hist = [];

    for (var timestamp in macd_data) {
        current_band = macd_data[timestamp]

        macd_signal.push({
            x: new Date(parseInt(timestamp)),
            y: macd_data[timestamp]["signal"].toFixed(8),
        });
        macd_macd.push({
            x: new Date(parseInt(timestamp)),
            y: macd_data[timestamp]["macd"].toFixed(8),
        });
        macd_hist.push({
            x: new Date(parseInt(timestamp)),
            y: macd_data[timestamp]["hist"].toFixed(8),
        });
    }

    chart_obj["series"].push({
        name: 'Signal',
        type: 'line',
        data: macd_signal
    }, {
        name: 'MACD',
        type: 'line',
        data: macd_macd
    }, {
        name: 'Hist',
        type: 'bar',
        data: macd_hist
    });
    console.log('MACD');
    console.log(chart_obj["series"]);
    return(chart_obj);
}


function pull_candles(){
    console.log('Getting candles');
    candle_data = rest_api('GET', 'get_trade_data');
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
          draw_chart(JSON.parse(request.response).data);
        } else {
          console.log(`error ${request.status} ${request.statusText}`);
        }
    }
}

pull_candles();