var statistics;
var heatmap;
var charts_dict = {};
var show_overall = true;

var TABLE_SIZE  = 10
var POS_SERIES  = 0
var NEG_SERIES  = 1
var NEUT_SERIES = 2
var POS_TWEET   = 1
var NEUT_TWEET  = 0
var NEG_TWEET   = -1
var MIPT_COORD  = {lat: 55.929695, lng: 37.520203} 
var COLORS = {'green':'rgba(0, 255, 0, 0.3)', 'red':'rgba(255, 0, 0, 0.3)'}

$(".nav-tabs").on("click", "a", function (e) {
        e.preventDefault();
        $(this).tab('show');
    })

function zip(arrays) {
    return arrays[0].map(function(_,i){
        return arrays.map(function(array){return array[i]})
    });
}

// Запрос начальных данных
// Структура данных: data = {'overall_time': кумулятивное время , 'overall_data': кумулятивные данные,
//                           'blocks_time': время по блокам, 'blocks_data': данные по блокам,
//                           'geo': координаты твитов, 'last_tweets': последние твиты, 'universities': университеты}
// Данные по тональности делятся: overall_data -> sentiment -> university
function requestData() {
    $.ajax({
        url: '/live-data',
        success: function(msg) {
            statistics = msg;

            for (i = 0, len = msg['last_tweets'].length; i < len; i++) {
                append_tweet(msg['last_tweets'][i])
            }

            for (i = 0, len = msg['geo'].length; i < len; i++) {
                heatmap.data.push(new google.maps.LatLng(msg['geo'][i].lat, msg['geo'][i].lon)) 
            }

            create_tabs();
        },
        cache: false
    });
}

function create_tabs() {
    var tabs = document.getElementById('charts_tab')

    for (u in statistics['universities']) {
        var name = statistics['universities'][u]
        var tabId = name;

        $('.nav-tabs').append('<li><a href="#' + name + '">' + name + '</a></li>');
        $('.tab-content').append('<div class="tab-pane" id="' + tabId + '"></div>');

        var chart = new Highcharts.StockChart({
                chart: {
                    renderTo: tabId,
                    defaultSeriesType: 'spline',
                    animation: false
                },
                title: {
                    text: 'Статистика числа твитов'
                },
                series: [{
                            name: 'Positive',
                            data: zip([statistics['overall_time'], statistics['overall_data'][POS_TWEET][name]]),
                            color: 'green',
                        },
                        {
                            name: 'Negative',
                            data: zip([statistics['overall_time'], statistics['overall_data'][NEG_TWEET][name]]),
                            color: 'red'
                        },
                        {
                            name: 'Neutral',
                            data: zip([statistics['overall_time'], statistics['overall_data'][NEUT_TWEET][name]]),
                            color: 'grey',
                        }]
            });

        charts_dict[name] = chart;
    }

    $('.nav-tabs li:nth-child(1) a').click();
}

function append_tweet(obj) {
    var table = document.getElementById("tweets_table");

    // Заголовок - это часть таблицы?О.о
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
    text_cell.style.marginLeft = '5px'

    var sentiment_cell = row.insertCell(3);
    
    // Какое-то гейство. В css задать стиль?
    if (obj['sentiment'] == POS_TWEET) {
        row.style.backgroundColor = COLORS['green'];
        sentiment_cell.innerHTML = 'pos';
    } else if (obj['sentiment'] == NEG_TWEET) {
        row.style.backgroundColor = COLORS['red'];
        sentiment_cell.innerHTML = 'neg';
    } else {
        sentiment_cell.innerHTML = 'neutral'
    }

    sentiment_cell.style.textAlign = 'center';

    var geo = obj['geo'];
    if (geo != null) {
        heatmap.data.push(new google.maps.LatLng(geo['coordinates'][0], geo['coordinates'][1])) 
    }
}

// Надо что-то придумать со свичем представления: лагает
// Пробовал div-призрак, в который рендерил неактивное представление
// Но поменять renderTo у графика не получается (не меняется график)
// Два дива в одном таб-контенте тоже не работает (ровно один див без детей должен быть)
function switch_charts() {
    for(var u in charts_dict) {
        var chart = charts_dict[u];
        
        if(show_overall) {
            chart.series[POS_SERIES].setData(zip([statistics['blocks_time'], statistics['blocks_data'][POS_TWEET][u]]))
            chart.series[POS_SERIES].update({type: 'column'});

            chart.series[NEG_SERIES].setData(zip([statistics['blocks_time'], statistics['blocks_data'][NEG_TWEET][u]]))
            chart.series[NEG_SERIES].update({type: 'column'});

            chart.series[NEUT_SERIES].setData(zip([statistics['blocks_time'], statistics['blocks_data'][NEUT_TWEET][u]]))
            chart.series[NEUT_SERIES].update({type: 'column'});

            document.getElementById("blocks_label").style.opacity = 1.
            document.getElementById("overall_label").style.opacity = 0.3
        } else {
            chart.series[POS_SERIES].setData(zip([statistics['overall_time'], statistics['overall_data'][POS_TWEET][u]]))
            chart.series[POS_SERIES].update({type: 'spline'});

            chart.series[NEG_SERIES].setData(zip([statistics['overall_time'], statistics['overall_data'][NEG_TWEET][u]]))
            chart.series[NEG_SERIES].update({type: 'spline'});

            chart.series[NEUT_SERIES].setData(zip([statistics['overall_time'], statistics['overall_data'][NEUT_TWEET][u]]))
            chart.series[NEUT_SERIES].update({type: 'spline'});

            document.getElementById("blocks_label").style.opacity = 0.3
            document.getElementById("overall_label").style.opacity = 1.
        }
    }

    show_overall = !show_overall;
}

function init_map() {
    console.log('initting map')
    
    var map_div = document.getElementById('map_container')
    var map = new google.maps.Map(map_div, {
          zoom: 15, 
          center: MIPT_COORD
        });

    heatmap = new google.maps.visualization.HeatmapLayer({
            map: map
        });
}

function update_statistics(obj) {
    statistics['overall_time'].push(obj['time']);
    
    for (var u in charts_dict) {
        statistics['overall_data'][POS_TWEET][u].push(obj['overall_data'][POS_TWEET][u])
        statistics['overall_data'][NEG_TWEET][u].push(obj['overall_data'][NEG_TWEET][u])
        statistics['overall_data'][NEUT_TWEET][u].push(obj['overall_data'][NEUT_TWEET][u])
    }

    if (obj['blocks_data'] != null) {
        statistics['blocks_data'][POS_TWEET][u].push(obj['blocks_data'][POS_TWEET][u])
        statistics['blocks_data'][NEG_TWEET][u].push(obj['blocks_data'][NEG_TWEET][u])
        statistics['blocks_data'][NEUT_TWEET][u].push(obj['blocks_data'][NEUT_TWEET][u])
    }
}

function add_data(obj) {
    update_statistics(obj);

    for (var u in charts_dict) {
        var chart = charts_dict[u];

        if(show_overall) {
            chart.series[POS_SERIES].addPoint([obj['time'], obj['overall_data'][POS_TWEET][u]], true, true)
            chart.series[NEG_SERIES].addPoint([obj['time'], obj['overall_data'][NEG_TWEET][u]], true, true)  
            chart.series[NEUT_SERIES].addPoint([obj['time'], obj['overall_data'][NEUT_TWEET][u]], true, true)  
        } else if (obj['blocks_data'] != null){
            chart.series[POS_SERIES].addPoint([obj['time'], obj['blocks_data'][POS_TWEET][u]], true, true)
            chart.series[NEG_SERIES].addPoint([obj['time'], obj['blocks_data'][NEG_TWEET][u]], true, true)  
            chart.series[NEUT_SERIES].addPoint([obj['time'], obj['blocks_data'][NEUT_TWEET][u]], true, true) 
        }
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
        // если получилен не JSON
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

    init_map();
    requestData();
});