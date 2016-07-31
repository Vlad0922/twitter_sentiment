var statistics;
var show_blocks = true;

// request initial data from server
function requestData() {
    $.ajax({
        url: '/live-data',
        success: function(msg) {
            statistics = msg;

            overall_chart.series[0].setData(msg['overall_pos']);
            overall_chart.series[1].setData(msg['overall_neg']);

            // block_chart.series[0].setData(msg['blocks_pos']);
            // block_chart.series[1].setData(msg['blocks_neg']);


            for (i = 0, len = msg['last_tweets'].length; i < len; i++) {
                append_tweet(msg['last_tweets'][i])
            }

            for (i = 0, len = msg['pos_geo'].length; i < len; i++) {
                coord = map_chart.fromLatLonToPoint(msg['pos_geo'][i]);
                map_chart.series[1].addPoint(coord);
            }

            for (i = 0, len = msg['neg_geo'].length; i < len; i++) {
                coord = map_chart.fromLatLonToPoint(msg['neg_geo'][i]);
                map_chart.series[1].addPoint(coord);
            }
        },
        cache: false
    });
}

function isJson(str) {
    try {
        JSON.parse(str);
    } catch (e) {
        return false;
    }
    return true;
}

function append_tweet(data) {
    if(isJson(data)) {
        var obj = jQuery.parseJSON(data);
    } else {
        var obj = data;
    }

    var table = document.getElementById("tweets_table");

    // header is part of a table O.o
    if (table.rows.length > 5) {
        table.deleteRow(1);
    }

    var row = table.insertRow(table.rows.length);
    var author_cell = row.insertCell(0);
    author_cell.innerHTML = obj['name'];

    var time_cell = row.insertCell(1);
    time_cell.innerHTML = obj['time'];

    var text_cell = row.insertCell(2);
    text_cell.innerHTML = obj['text'];

    var sentiment_cell = row.insertCell(3);
    
    if (obj['sentiment'] == 1) {
        row.style.backgroundColor = 'rgba(0, 255, 0, 0.3)';
        sentiment_cell.innerHTML = 'pos';
    } else {
        row.style.backgroundColor = 'rgba(255, 0, 0, 0.3)';
        sentiment_cell.innerHTML = 'neg';
    }  

    sentiment_cell.style.textAlign = "center";

    var geo = obj['geo'];
    if (geo != null) {
        coord = map_chart.fromLatLonToPoint({'lat': geo['coordinates'][0], 'lon': geo['coordinates'][1]});
        map_chart.series[1].addPoint(coord);

        console.log(coord);
    }
}

function switch_charts() {
    if(show_blocks) {
        overall_chart.series[0].setData(statistics['blocks_pos']);
        overall_chart.series[0].update({type: 'column'});

        overall_chart.series[1].setData(statistics['blocks_neg']);
        overall_chart.series[1].update({type: 'column'});

        document.getElementById("blocks_label").style.opacity = 1.
        document.getElementById("overall_label").style.opacity = 0.3
    } else {
        overall_chart.series[0].setData(statistics['overall_pos']);
        overall_chart.series[0].update({type: 'spline'});

        overall_chart.series[1].setData(statistics['overall_neg']);
        overall_chart.series[1].update({type: 'spline'});

        document.getElementById("blocks_label").style.opacity = 0.3
        document.getElementById("overall_label").style.opacity = 1.
    }

    show_blocks = !show_blocks;
}

$(document).ready(function() {
    var socket = io.connect('/tweets');
    socket.on('connect', function() {
        console.log("socket connected");
    });

    socket.on('tweet_text', function(data) {
        append_tweet(data);
    });

    overall_chart = new Highcharts.StockChart({
        chart: {
            renderTo: 'overall-container',
            defaultSeriesType: 'spline',
            animation: false
        },
        title: {
            text: 'Overall tweets'
        },
        // xAxis: {
        //     type: 'datetime',
        //     tickPixelInterval: 150,
        //     maxZoom: 20 * 1000
        // },
        // yAxis: {
        //     minPadding: 0.2,
        //     maxPadding: 0.2,
        //     title: {
        //         text: 'Value',
        //         margin: 80
        //     }
        // },
        series: [{
                    name: 'Positive',
                    data: [],
                    color: 'green',
                },
                {
                    name: 'Negative',
                    data: [],
                    color: 'red'
                }]
    });

    // block_chart = new Highcharts.StockChart({
    //     chart: {
    //         renderTo: 'block-container',
    //         defaultSeriesType: 'column'
    //     },
    //     title: {
    //         text: 'Tweets by blocks'
    //     },
    //     // xAxis: {
    //     //     type: 'datetime',
    //     //     tickPixelInterval: 150,
    //     //     maxZoom: 20 * 1000
    //     // },
    //     series: [{
    //                 name: 'Positive',
    //                 data: [],
    //                 color: 'green'
    //             },
    //             {
    //                 name: 'Negative',
    //                 data: [],
    //                 color: 'red'
    //             }]
    // })

    map_data = Highcharts.maps['custom/world'];
    //map_data = Highcharts.maps['countries/ru/ru-all'];
    map_chart = new Highcharts.Map({
        chart: {
            renderTo: 'map-container'
        },
        title: {
            text: 'Tweet map'
        },
        series: [{
                    name: 'Map',
                    mapData: map_data,
                    enableMouseTracking: false,
                    color: '#E0E0E0'
                },
                {
                    type: 'mapbubble',
                    mapData: map_data,
                    name: 'Negative',
                    data: [],
                    color: 'rgba(255, 0, 0, 0.3)',
                    tooltip: { pointFormat: '{point.code}' },
                    minSize: 4,
                    maxSize: 6,
                },
                {
                    type: 'mapbubble',
                    mapData: map_data,
                    name: 'Positive',
                    data: [],
                    color: 'rgba(0, 255, 0, 0.3)',
                    tooltip: { pointFormat: '{point.code}' },
                    minSize: 4,
                    maxSize: 6,
                }]
    })

    requestData();
});