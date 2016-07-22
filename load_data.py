# -*- coding: utf-8 -*-

from tweepy import API as tweepy_API
from tweepy import OAuthHandler
from tweepy import Stream
from tweepy import Cursor

from tweepy.streaming import StreamListener

import codecs

def process_tweet(tweet):
    with open('online.json', 'a') as f:
        f.write(tweet)

#listner for online processing
class StdOutListener(StreamListener):
    def __init__(self, proc_func):
        self.msg_count_ = 0
        self.proc_func_ = proc_func

    def on_data(self, data):
        with open('python.json', 'a') as f:
            self.msg_count_ += 1
            print 'got %d messages' % self.msg_count_

            self.proc_func_(data)

        return True
 
    def on_error(self, status):
        print status

        return True

keywords = {
    'MIPT': ' OR '.join([u'МФТИ', u'физтех', u'\"Московский физико-технический институт\"', 'MIPT', 'phystech']),
    'MSU': ' OR '.join([u'МГУ', u'\"Московский Государственный Университет\"']), #MSU count as Michigan state university in most tweets
    'ITMO': ' OR '.join([u'ИТМО', 'ITMO']),
    'SPAU': 'СПбАУ',
    'SPBU': ' OR '.join([u'СПбГУ', 'SPBU']),
}

if __name__ == '__main__':
    
    #load twitter API tokens from file  
    with open('tokens.txt') as f:
        (access_token, access_token_secret,
            consumer_key, consumer_secret) = f.read().split()

    tweets = dict()

    #init tweets table
    for u in keywords:
        tweets[u] = list()

    auth = OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy_API(auth)

    for u in keywords:
        finded = 0
        for tweet in Cursor(api.search,
                                   q=keywords[u],
                                   rpp=100,
                                   result_type="recent").items():
            finded += 1

            msg = tweet.text.replace('\n', ' ').replace('\r', ' ')
            tweets[u].append(msg)

        #removing non-unique tweets
        tweets[u] = list(set(tweets[u]))

        print u, finded

    for u in tweets:
        with codecs.open('data/' + u + '.csv', 'w', 'utf-8') as f:
            f.write(';\n'.join(tweets[u]))
