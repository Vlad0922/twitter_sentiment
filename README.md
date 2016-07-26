# twitter_sentiment
Анализ тональности сообщений в твиттере по фильтру.

##Зависимости
* scikit-learn
* numpy
* pandas
* scipy
* tweepy
* nltk
* matplotlib и seaborn для графиков в ноутбуках (опционально)
* gmaps плагин для jupyter notebooks опционально (https://github.com/pbugnion/gmaps)

##Инструкция

Необходимо создать файл tokens.txt с ключами API для твиттера. В файле должны содержаться:

```shell
access_token

access_token_secret

consumer_key

consumer_secret

```

В указанном выше порядке.

Если использовать google maps, то необходимо указать API key от Google Maps JS API в файле maps_token.txt

Работа происходит с помощью двух скриптов

* Для обучения необходимо запустить train.py
* Для запуска стрима твитов надо запустить listen.py

Вывод происходит в виде "тональность | текст твита", так же классифицированные сообщения логгируются в data/stream

Данные для обучения взяты с сайта http://study.mokoron.com/ [статья](http://www.swsys.ru/index.php?page=article&id=3962)
