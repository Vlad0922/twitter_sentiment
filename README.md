# twitter_sentiment
Анализ тональности сообщений в твиттере по фильтру.

##Зависимости
* scikit-learn
* numpy
* pandas
* scipy
* tweepy
* nltk
* seaborn для графиков в ноутбуках (опционально)

##Инструкция

Необходимо создать файл tokens.txt с ключами API для твиттера. В файле должны содержаться:

```shell
access_token

access_token_secret

consumer_key

consumer_secret

```

В указанном выше порядке.

Работа происходит с помощью двух скриптов

* Для обучения необходимо запустить train.py
* Для запуска стрима твитов надо запустить listen.py

Вывод происходит в виде "тональность | текст твита", так же классифицированные сообщения логгируются в data/stream

Данные для обучения взяты с сайта http://study.mokoron.com/ [статья](http://www.swsys.ru/index.php?page=article&id=3962)
