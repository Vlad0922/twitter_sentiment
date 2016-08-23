# twitter_sentiment
Анализ тональности сообщений в твиттере по фильтру.

##Зависимости
* python 2.7
* scikit-learn
* numpy
* pandas
* scipy
* tweepy
* nltk
* flask
* postgresql
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

Монитор твитов осуществляется через веб-приложение. Для его запуска с использование virtualenv:

```shell
1) virtualenv tweet_env

2) source tweet_env/bin/activate

3) pip install -r webapp/requirements.txt

4) pip install -r webapp/conda-requirements.txt

5) python load_data.py

6) python train.py

7) cd webapp

8) python app.py
```

Зависимости разделены на 2 части т.к. scipy/numpy/scikit зависят от си-либ и для деплоя в heroku необходимо использовать дополнительно conda build pack. [Подробнее](https://devcenter.heroku.com/articles/python-c-deps) 

Текущую рабочую версию можно посмотреть [тут](https://tweets-about-universities.herokuapp.com/) 

В случае запуска на localhost, приложение слушает 5000 порт. Открыть приложение можно перейдя на 127.0.0.1:5000

Данные для обучения взяты с сайта http://study.mokoron.com/ [статья](http://www.swsys.ru/index.php?page=article&id=3962)
