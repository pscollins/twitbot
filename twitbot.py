import time
from rauth import OAuth1Service
from multiprocessing import Process, Queue

def make_session(strConsumer_key, strConsumer_secret):
    twitter = OAuth1Service(
        name='twitter',
        consumer_key = strConsumer_key,
        consumer_secret = strConsumer_secret,
        request_token_url='https://api.twitter.com/oauth/request_token',
        access_token_url='https://api.twitter.com/oauth/access_token',
        authorize_url='https://api.twitter.com/oauth/authorize',
        base_url='https://api.twitter.com/1.1/')

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

    intStatus_code = session.get('account/verify_credentials.json').status_code
    if intStatus_code == 200:
        print 'Account successfully verified'
    else:
        print 'Something went wrong, status code: {0}'.format(intStatus_code)
        #ipdb.set_trace()

    return session


def dictTweet(session, data):
   #ipdb.set_trace()
    r = session.post('statuses/update.json', 
                     data={'status':data['status'],
                           'in_reply_to_status_id':`data['in_reply_to_status_id']`})
    if r.status_code == 200:
        print 'dictTweet: Successfully posted {0}'.format(data)
    else:
        print 'dictTweet: Something went wrong! Status code is {0}'.format(r.status_code)
        print 'dictTweet: dumping the body of the return {0}'.format(r.text)


def write_tweets(session, strAppend, q):
    while True:
        print "write_tweets: Blocking to get a new tweet."
        data = q.get(True, None)
        data['status'] = ''.join([data['status'], strAppend])
        print "write_tweets: Tweeting the following: {0}".format(data)
        dictTweet(session, data)


def scrape_tweets(session, strSn, strSince_id, q):
    while True:
        print 'scrape_tweets: Scraping tweets in an infinite loop'
        posts = session.get('statuses/user_timeline.json',
                            params = {'screen_name':strSn,
                                      'since_id':strSince_id,
                                      'count':20,
                                      'exclude_replies':'true'}).json()
        for post in reversed(posts):
            print type(post)
            passed = {'status':post['text'],
                      'in_reply_to_status_id':post['in_reply_to_status_id'],
                      'place_id':post['geo']}
                      
            q.put(passed)
            strSince_id = post['id']
        
        time.sleep(6) #the API rate-limits requests more frequent than every 5 seconds
        #take a break if there aren't any new tweets coming in
        if not posts:
            time.sleep(180)
            

def main():

    # scraping account settings
    print "Settings for the scraping account\n-----------"
    print "Initialize an account to scrape tweets on:"
    sessScraper = make_session('juKgzsgl5LYnBKocnq4mg',
                               'vIw1vUec4bMkyL5hQpCISe3svTf767suzXyVh6YKA')
    strSn = raw_input("What screenname do you want to retweet? ")
    strSince_id = raw_input("What is the id of the most recent tweet you'd like to scrape? [1] ")

    if strSince_id == '':
        strSince_id = '1'

    # tweeting account settings
    print "Settings for the tweeting account\n-----------"
    print "Initialize an account to tweet from:"
    sessTweeter = make_session('C2XWyJSzHpVx8iT7Bbabsw',
                               'uoxWh9wj4pDExn1GoQ5P4e5NdVAFATdAnYdao1Musw')
    strAppend = raw_input("Is there anything you want me to append" +
                          " to these tweets? [blank for nothing] ")


    # initialize the main routine
    q = Queue()
    p1 = Process(target = write_tweets, args=(sessTweeter, strAppend, q))
    p2 = Process(target = scrape_tweets, args=(sessScraper, strSn, strSince_id, q))
    p2.start()
    p1.start()
    pass
#    scrape_tweets(sessScraper, strSn, strSince_id, q)
    
if __name__ == '__main__':
    main()
