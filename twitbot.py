import time, configparser
from sys import exit
from rauth import OAuth1Service
from multiprocessing import Process, Queue
from os.path import isfile


def make_session(strConsumer_key, strConsumer_secret, 
                 strRequest_token, strRequest_secret, intPin):
    twitter = OAuth1Service(
        name='twitter',
        consumer_key = strConsumer_key,
        consumer_secret = strConsumer_secret,
        request_token_url='https://api.twitter.com/oauth/request_token',
        access_token_url='https://api.twitter.com/oauth/access_token',
        authorize_url='https://api.twitter.com/oauth/authorize',
        base_url='https://api.twitter.com/1.1/')

    if not (strRequest_token or strRequest_secret, intPin):
        request_token, request_token_secret = twitter.get_request_token()
        authorize_url = twitter.get_authorize_url(request_token)
        while(True):
            print 'Visit this URL in your browser: ' + authorize_url + '\n'
            pin = raw_input('Enter PIN from browser: ')

            try:
                session = twitter.get_auth_session(request_token, 
                                                   request_token_secret, method='POST',
                                                   data={'oath_verifier':pin})
                break
            except KeyError:
                print "You need to enter a PIN!"
    else:
        session = twitter.get_auth_session(request_token, 
                                           request_token_secret, method='POST',
                                           data={'oath_verifier':pin})
                

    intStatus_code = session.get('account/verify_credentials.json').status_code
    if intStatus_code == 200:
        print 'Account successfully verified'
    else:
        print 'Something went wrong, status code: {0}'.format(intStatus_code)
        #ipdb.set_trace()

    return session, strRequest_token, strRequest_secret, intPin



def dictTweet(session, data):
    r = session.post('statuses/update.json', 
                     data={'status':data['status'],
                           'in_reply_to_status_id':`data['in_reply_to_status_id']`})
    if r.status_code == 200:
        print 'dictTweet: Successfully posted {0}'.format(data)
    else:
        print 'dictTweet: Something went wrong! Status code is {0}'.format(r.status_code)
        print 'dictTweet: dumping the body of the return {0}'.format(r.text)

def initializeProcesses(tsScraper, twWrtiter):
    # set up the two processes and return a tuple containing them
    q = Queue()
    p1 = Process(target = tsScraper.run, args=(q,))
    p2 = Process(target = twWriter.run, args=(q,))
    p2.start()
    p1.start()

    return (p1, p2)

class TweetGeneric:
    def __init__(self, strConsumer_key, strConsumer_secret, 
                 strRequest_token = '', strRequest_secret = '', intPin = ''):
        self.session, self.strRequest_token, self.strRequest_secret, 
        self.intPin = make_session(strConsumer_key, 
                                   strConsumer_secret, strRequest_token, 
                                   strRequest_secret, intPin)
        return

class TweetScraper(TweetGeneric):
    def __init__(self, strConsumer_key, strConsumer_secret, 
                 strRequest_token = '', strRequest_secret = '', intPin = ''):
        print "TweetScraper: Initializing an account to scrape tweets on."
        TweetGeneric.__init__(self, strConsumer_key, strConsumer_secret, 
                              strRequest_token, strRequest_secret, intPin)
        self.strSn = ''
        self.strSince_id = ''
        self.strFilter = '' #exclude tweets containing the given string
        self.intMax_tweets = 0 #maximum number of tweets to go back
        return

    def configure(self):
        print "Settings for the scraping account\n-----------"
        self.strSn = raw_input("What screenname do you want to retweet? ")
        self.strSince_id = raw_input("What is the id of the most recent tweet you'd like to scrape? [1] ") 
        self.intMax_tweets = raw_input("How many old tweets should be processed? [20] ")
        if not self.strSince_id:
            self.strSince_id = '1'
        if not self.intMax_tweets :
            self.intMax_tweets = 0
        return
    

    def run(self, q):
        while True:
            print 'scrape_tweets: Scraping tweets in an infinite loop'
            posts = self.session.get('statuses/user_timeline.json',
                                     params = {'screen_name':self.strSn,
                                               'since_id':self.strSince_id,
                                               'count':20,
                                               'exclude_replies':'false'}).json()
            for post in reversed(posts):
                print type(post)
                passed = {'status':post['text'],
                          'in_reply_to_status_id':post['in_reply_to_status_id'],
                          'place_id':post['geo']}
                      
                if not self.strFilter in passed['status']:
                    q.put(passed)
                self.strSince_id = post['id']
        

                #fix timing: the API rate limits requests more frequent than every 5 seconds
                time.sleep(6)
                #take a break if ther aren't any new posts coming in
                if not posts:
                    time.sleep(180)
                    return

class TweetWriter(TweetGeneric):
    def __init__(self, strConsumer_key, strConsumer_secret, 
                 strRequest_token = '', strRequest_secret = '', intPin = ''):
        print "TweetWriter: Initializing an account to write tweets from."
        TweetGeneric.__init__(self, strConsumer_key, strConsumer_secret, 
                              strRequest_token, strRequest_secret, intPin)
        self.strAppend = ''
        return

    def configure(self):
            print "Settings for the tweeting account\n-----------"
            self.strAppend = raw_input("Is there anything you want me to append" +
                                       " to these tweets? [blank for nothing] ")
            return

    def run(self, q):
        while True:
            print "write_tweets: Blocking to get a new tweet."
            data = q.get(True, None)
            data['status'] = ' '.join([data['status'], self.strAppend])
            print "write_tweets: Tweeting the following: {0}".format(data)
            dictTweet(self.session, data)
        

def main():
    config = configparser.ConfigParser()
    if isfile('.config'):
        config.read('.config')
        def localAssign(strType):
            return TweetScraper(config[strType]['strConsumer_key'],
                                config[strType]['strConsumer_secret']
                                config[strType]['strRequest_token'],
                                config[strType]['strRequest_secret'],
                                config[strType]['intPin'])
        tsScraper = localAssign('SCRAPER')
        tsScraper.strSn = config['SCRAPER']['strSn']
        tsScraper.strSince_id = config['SCRAPER']['strSince_id']
        tsScraper.strFilter = config['SCRAPER']['strFilter']
        tsScraper.intMax_tweets = config['SCRAPER']['intMax_tweets']

        tsWriter = localAssign('WRITER')
        tsWriter.strAppend = config['WRITER']['strAppend']

    else:
        open('.config').close()
        tsScraper = TweetScraper('juKgzsgl5LYnBKocnq4mg',
                                 'vIw1vUec4bMkyL5hQpCISe3svTf767suzXyVh6YKA')
        tsScraper.configure()
        twWriter = TweetWriter('C2XWyJSzHpVx8iT7Bbabsw',
                               'uoxWh9wj4pDExn1GoQ5P4e5NdVAFATdAnYdao1Musw')
        twWriter.configure()
        tsScraper.strFilter = twWriter.strAppend


    p1, p2 = initializeProcesses(tsScraper, twWriter)

    while True:
        print "Available commands: [h]elp [q]uit [s]ave [m]odify."
        input = raw_input('? ')
        if input == 'h':
            print "Implement me."
        if input == 'q':
            p1.terminate()
            p2.terminate()
            exit(0)
        if input == 's':
            config['SCRAPER'] = tsScraper.__dict__
            config['WRITER'] = twWriter.__dict__
        if input == 'm':
            c = raw_input('Modify [s]craper or [w]riter? ')
            if c == 's':
                tsScraper.configure()
            if c == 'w':
                twWriter.configure()
                    
    return
    
if __name__ == '__main__':
    main()
