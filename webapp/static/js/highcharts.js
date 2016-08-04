var statistics;
var show_blocks = true;

var TABLE_SIZE = 10

// request initial data from server
function requestData() {
    $.ajax({
        url: '/live-data',
        success: function(msg) {
            statistics = msg;

            overall_chart.series[0].setData(msg['overall_pos']);
            overall_chart.series[1].setData(msg['overall_neg']);

            for (i = 0, len = msg['last_tweets'].length; i < len; i++) {
                append_tweet(msg['last_tweets'][i])
            }

            for (i = 0, len = msg['pos_geo'].length; i < len; i++) {
                coord = map_chart.fromLatLonToPoint(msg['pos_geo'][i]);
                map_chart.series[1].addPoint(coord);
            }

            for (i = 0, len = msg['neg_geo'].length; i < len; i++) {
                coord = map_chart.fromLatLonToPoint(msg['neg_geo'][i]);
                map_chart.series[2].addPoint(coord)
            }
        },
        cache: false
    });
}

function append_tweet(obj) {
    var table = document.getElementById("tweets_table");

    // header is part of a table O.o
    if (table.rows.length > TABLE_SIZE) {
        table.deleteRow(TABLE_SIZE);
    }

    var row = table.insertRow(1);
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

function add_data(obj) {
    console.log('adding data')

    console.log(obj['time'], typeof(obj['time']))
    console.log(statistics['overall_pos'][statistics['overall_pos'].length - 1])
    console.log(statistics['overall_pos'][statistics['overall_pos'].length - 1][0] < obj['time'])

    if(show_blocks) {
        overall_chart.series[0].addPoint([obj['time'], obj['overall_pos']], true, true)
        overall_chart.series[1].addPoint([obj['time'], obj['overall_neg']], true, true)  

        if (obj['blocks_pos'] != null) {
            statistics['blocks_pos'].push([obj['time'], obj['blocks_pos']])
            statistics['blocks_neg'].push([obj['time'], obj['blocks_neg']])  
        }
    } else {
        if (obj['blocks_pos'] != null) {
            overall_chart.series[0].addPoint([obj['time'], obj['blocks_pos']], true, true)
            overall_chart.series[1].addPoint([obj['time'], obj['blocks_neg']], true, true)  
        }

        statistics['overall_pos'].push([obj['time'], obj['overall_pos']])
        statistics['overall_neg'].push([obj['time'], obj['overall_neg']])  
    }
}

$(document).ready(function() {

    Highcharts.setOptions({
        global: {
            useUTC: false
        }
    });

    var socket = io.connect('/tweets');
    socket.on('connect', function() {
        console.log("socket connected");
    });

    socket.on('tweet_text', function(data) {
        var obj = jQuery.parseJSON(data);
        // if data isn't JSON
        if (obj == null) {
            obj = data;
        }

        if (obj['type'] == 'tweet') {
            append_tweet(obj);
        }

        if (obj['type'] == 'new_data') {
            add_data(obj)
        }
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

    // var map_div = document.getElementById('map-container')
    // var map = new google.maps.Map(map_div, {
    //       zoom: 13,
    //       center: {lat: 55.751244, lng: -37.618423},
    //     });

    // var heatmap = new google.maps.visualization.HeatmapLayer({
    //       map: map
    //     });

    map_data = Highcharts.maps['custom/world'];
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