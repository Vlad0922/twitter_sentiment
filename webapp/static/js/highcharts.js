var statistics;
var heatmap;
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
            overall_chart.series[2].setData(msg['overall_neut'])

            for (i = 0, len = msg['last_tweets'].length; i < len; i++) {
                append_tweet(msg['last_tweets'][i])
            }

            for (i = 0, len = msg['geo'].length; i < len; i++) {
                heatmap.data.push(new google.maps.LatLng(msg['geo'][i].lat, msg['geo'][i].lon)) 
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
    text_cell.innerHTML = '<a href=\"https://twitter.com/foobar/status/' + obj['id'] + '\">' + obj['text'] + '</a>'

    var sentiment_cell = row.insertCell(3);
    
    if (obj['sentiment'] == 1) {
        row.style.backgroundColor = 'rgba(0, 255, 0, 0.3)';
        sentiment_cell.innerHTML = 'pos';
    } else if (obj['sentiment'] == -1) {
        row.style.backgroundColor = 'rgba(255, 0, 0, 0.3)';
        sentiment_cell.innerHTML = 'neg';
    } else {
        sentiment_cell.innerHTML = 'neutral'
    }

    sentiment_cell.style.textAlign = "center";

    var geo = obj['geo'];
    if (geo != null) {
        heatmap.data.push(new google.maps.LatLng(geo['coordinates'][0], geo['coordinates'][1])) 
    }
}



function switch_charts() {
    if(show_blocks) {
        overall_chart.series[0].setData(statistics['blocks_pos']);
        overall_chart.series[0].update({type: 'column'});

        overall_chart.series[1].setData(statistics['blocks_neg']);
        overall_chart.series[1].update({type: 'column'});

        overall_chart.series[2].setData(statistics['blocks_neut']);
        overall_chart.series[2].update({type: 'column'});

        document.getElementById("blocks_label").style.opacity = 1.
        document.getElementById("overall_label").style.opacity = 0.3
    } else {
        overall_chart.series[0].setData(statistics['overall_pos']);
        overall_chart.series[0].update({type: 'spline'});

        overall_chart.series[1].setData(statistics['overall_neg']);
        overall_chart.series[1].update({type: 'spline'});

        overall_chart.series[2].setData(statistics['overall_neut']);
        overall_chart.series[2].update({type: 'spline'});

        document.getElementById("blocks_label").style.opacity = 0.3
        document.getElementById("overall_label").style.opacity = 1.
    }

    show_blocks = !show_blocks;
}

function init_map() {
    console.log('initting map')
    
    var map_div = document.getElementById('map-container')
    var map = new google.maps.Map(map_div, {
          zoom: 15, //MIPT
          center: {lat: 55.929695, lng: 37.520203}
        });

    heatmap = new google.maps.visualization.HeatmapLayer({
            map: map
        });
}

function add_data(obj) {
    if(show_blocks) {
        overall_chart.series[0].addPoint([obj['time'], obj['overall_pos']], true, true)
        overall_chart.series[1].addPoint([obj['time'], obj['overall_neg']], true, true)  
        overall_chart.series[2].addPoint([obj['time'], obj['overall_neut']], true, true)  

        if (obj['blocks_pos'] != null) {
            statistics['blocks_pos'].push([obj['time'], obj['blocks_pos']])
            statistics['blocks_neg'].push([obj['time'], obj['blocks_neg']]) 
            statistics['blocks_neut'].push([obj['time'], obj['blocks_neut']])   
        }
    } else {
        if (obj['blocks_pos'] != null) {
            overall_chart.series[0].addPoint([obj['time'], obj['blocks_pos']], true, true)
            overall_chart.series[1].addPoint([obj['time'], obj['blocks_neg']], true, true)  
            overall_chart.series[2].addPoint([obj['time'], obj['blocks_neut']], true, true) 
        }

        statistics['overall_pos'].push([obj['time'], obj['overall_pos']])
        statistics['overall_neg'].push([obj['time'], obj['overall_neg']]) 
        statistics['overall_neut'].push([obj['time'], obj['overall_neut']])   
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
                },
                {
                    name: 'Neutral',
                    data: [],
                    color: 'grey',
                }]
    });

    init_map();
    requestData();
});