
import tweepy
from tweepy import OAuthHandler
from tweepy import API
from secretes import Secretes
from time import sleep
from datastore import DataStore
from hmyclient import HmyClient
from utility import Utility
import subprocess

class TwitterTipBot():
    auth = None
    api = None
    stream = None
    twitter_uid = "1190625904717959169"
    bot_twitter_handle = "prarysoft"
    dataStore = None
    explorer_url = 'https://explorer.pops.one/#' #'https://explorer.harmony.one/#'

    def __init__( self ):
        try:
            self.auth = OAuthHandler(Secretes._twitterConsumerApiKey, Secretes._twitterConsumerApiSecret)
            self.auth.secure = True
            self.auth.set_access_token(Secretes._twitterAccessToken, Secretes._twitterAccessTokenSecret)
            self.api = API(self.auth)
            self.dataStore = DataStore()
        except BaseException as e:
            print("Error in main()", e)
        self.tweetCount = 0

    def startTwitterTipBot(self):
        while 1:
            twitter_event_details = self.dataStore.getNotAddressedTwitterEvents()
            if twitter_event_details != None:
                try:
                    text = twitter_event_details['event_text']
                    if f'@{self.bot_twitter_handle} !tip' in text:
                        self.process_tip(twitter_event_details['event_id'], text, twitter_event_details['sender_handle'], twitter_event_details['receiver_handle'])
                    elif text == '!history':
                        self.history(twitter_event_details['sender_handle'], twitter_event_details['sender_id'])
                    elif text == '!help':
                        self.help(twitter_event_details['sender_id'])
                    elif text == '!balance':
                        self.balance(twitter_event_details['sender_handle'], twitter_event_details['sender_id'])
                    elif text.startswith("!withdraw"):
                        self.withdraw(text, twitter_event_details['sender_handle'], twitter_event_details['sender_id'])
                    elif text.startswith("!deposit"):
                        self.deposit(twitter_event_details['sender_handle'], twitter_event_details['sender_id'])                        
                except Exception as ex:
                    print(ex)
                finally:
                    if 'event_id' in twitter_event_details:
                        twitter_event_details['addressed'] = True
                        self.dataStore.saveTwitterEventDetails(twitter_event_details)
            sleep(10)

    # When someone wants to deposit one to his account
    def deposit(self, sender_handle, sender_id):
        try:
            user_details = self.dataStore.getUserDetailsByTwitterHandle(f'@{sender_handle}')
            if user_details != None:
                one_address = user_details['one_address']
                try:
                    img = self.api.media_upload(Utility.getQRCodeImageFilePath(one_address))
                    self.api.send_direct_message(text=f'Your Deposit address {one_address}', recipient_id=sender_id, attachment_type='media', attachment_media_id=img.media_id)
                except Exception as e:
                    self.api.send_direct_message(text=f'Your Deposit address {one_address}', recipient_id=sender_id)
                    print(e)
            else:
                self.api.send_direct_message(text="You\'re not registered!, please register to deposit ONE, please register using Telegram bot (https://t.me/onetipbot)", recipient_id=sender_id)
        except Exception as ex:
            print(ex)


    def withdraw(self, text, sender_handle, sender_id):
        parts = text.split(" ")
        withdraw_address = ""
        amount = 0
        inputInValid = False
        reply_message = ""
        user_details = self.dataStore.getUserDetailsByTwitterHandle(f'@{sender_handle}')
        from_address = user_details['one_address']
        if len(parts) >= 3:
            if parts[0] == "!withdraw":
                print(text)
                try:
                    amount = float(parts[1])
                except Exception as ex:
                    inputInValid = True
                    reply_message = "Invalid withdrawal amount."
                    print(ex)
                if not inputInValid:
                    if amount < 0.00000000:
                        reply_message = f"Withdraw amount cannot be negative value."
                        print(reply_message)
                        inputInValid = True
                    else:
                        if HmyClient.getBalace(from_address) + 0.00000021 < float(amount):
                            inputInValid = True
                            reply_message = f"Please make sure you have enough funds for transfer {amount} in your account including fees, please reduce the withdraw amount and try again."
                            print(reply_message)
                if not inputInValid:                
                    withdraw_address = parts[2]
                    if not HmyClient.validateONEAdress(withdraw_address):
                        inputInValid = True        
                        reply_message = "Invalid ONE address, transfer cancelled"
                        print(reply_message)

        if not inputInValid:
            res = HmyClient.transfer(from_address, withdraw_address, amount)
            res = eval(res)
            if 'transaction-hash' in res:
                reply_message = f"Withdraw is complete, here is the receipt {self.explorer_url}/tx/{res['transaction-hash']}"
            else:
                reply_message = "Withdraw is failed with unknown error"
        else:
            if reply_message == "":
                reply_message = "Unknown Error!"

        print(f'Withdraw reply :{reply_message}')        
        self.api.send_direct_message(text=reply_message, recipient_id=sender_id)

    # When someone wants to deposit one to his account
    def balance(self, sender_handle, sender_id):
        try:
            # If they're not registered nor have they received any tips without an account
            user_details = self.dataStore.getUserDetailsByTwitterHandle(f'@{sender_handle}')
            if user_details != None:
                one_address = user_details['one_address']
                balance = HmyClient.getBalace(one_address)
                self.api.send_direct_message(text=f'Your Wallet Balace \n{balance}', recipient_id=sender_id)
            else:
                self.api.send_direct_message(text=f'You\'re not registered!, please register to get balance please register using Telegram bot (https://t.me/onetipbot), if you are already registered please link you twitter handle.', recipient_id=sender_id)
            # Save the data
        except Exception as ex:
            print(ex)

    # When someone wants to see the History of his account
    def history(self, sender_handle, sender_id):
        try:
            # If they're not registered nor have they received any tips without an account
            user_details = self.dataStore.getUserDetailsByTwitterHandle(f'@{sender_handle}')
            if user_details != None:
                one_address = user_details['one_address']
                self.api.send_direct_message(text=f'Account History\n{self.explorer_url}/address/{one_address}', recipient_id=sender_id)
            else:
                self.api.send_direct_message(text=f'You\'re not registered!, please register to get Account History please register using Telegram bot (https://t.me/onetipbot)', recipient_id=sender_id)                
        except Exception as ex:
            print(ex)

    def help(self, sender_id):
        try:
            help_text = u"Deposit \n----------------\n\nTo get started using Telegram bot (https://t.me/onetipbot) you need to deposit funds to your address. DM \" !deposite\" to to find your deposit address.\n\n\nWithdraw\n----------------\n\nTo Withdraw funds from your @OneTipBot you need to send \"!withdraw <amount> <one_address>\" Make sure you have enough balance to cover the network fees and your withdrawal amount.\n\n\nTip\n-----------------\n\nYou can tip anyone by Tweeting @OneTipBot !tip <tip_amount> <receivers_handle> \n\n\nRegister/Update Twitter handle\n-----------------\n\n\nTo register or update your Twitter handle you need to user our Telegram bot @OneTipBot at (https://t.me/onetipbot) then click on \"Register twitter handle/update twitter handle\". Follow the prompts and you will be able to register/update your twitter handle.\n\n\nDisclaimer\n-----------------\n\nPrivate keys are managed by @OneTipBot and securely stored. The bot uses the private key to create transactions on your behalf via telegram bot. It is not recommended to store large quantities of your crypto on @OneTipBot."
            self.api.send_direct_message(text=help_text, recipient_id=sender_id)
        except Exception as ex:
            print(ex)
        

    def process_tip(self, tweet_id, text, sender_handle, receiver):
        tip = 0
        success = "yes"
        failure_reason = ""
        tweet_type = "tweet"
        reply_text = ""
        print(text)
        print(f'@{self.bot_twitter_handle} !tip')
        if f'@{self.bot_twitter_handle} !tip' in text:
            if not self.dataStore.checkIftweetDataExists(tweet_id): 
                sender_details = self.dataStore.getUserDetailsByTwitterHandle(f'@{sender_handle}')
                if sender_details != None:
                    parts = text.split(" ")
                    for i in range(0, len(parts)):
                        if parts[i] == "!tip":
                            if i + 1 < len(parts):
                                tip = float(parts[i + 1])
                                break
                    from_address = sender_details['one_address']
                    sender = sender_handle
                    if receiver != "":
                        # Can't tip yourself
                        if sender != receiver:                            				
                            # Can't tip more than you have
                            from_balance = HmyClient.getBalace(from_address)
                            if tip + 0.00000021 > from_balance:
                                reply_text = f'@{sender_handle}, your balance is low to tip {tip} ONE'
                            else:
                                receiver_details = self.dataStore.getUserDetailsByTwitterHandle(f'@{receiver}')
                                if receiver_details == None:
                                    reply_text = f"@{sender_handle}, @{receiver} is not registered with ONE Tipping bot, please register using Telegram bot (https://t.me/onetipbot)"
                                else:
                                    if 'one_address' in receiver_details:
                                        res = HmyClient.transfer(from_address, receiver_details['one_address'], tip)
                                        res = eval(res)
                                        if 'transaction-hash' in res:
                                            reply_text = f"Hi @{receiver}, @{sender_handle} just tipped you {tip} ONE"
                                        else:
                                            print(f"Tip failed from  {sender} to {receiver} tip {tip} ONE")
                                    else:
                                        print('Receiver ONE address is missing')
                        else:
                            reply_text = f'@{sender_handle} You can\'t tip yourself!'
                    else:
                        reply_text = f'@{sender_handle} Please mention a receiver to tip.'
                else:
                    success = "no"
                    failure_reason = "account does not exists"
                    reply_text = f'@{sender_handle} You are not registered with ONE Tipping bot, please register using Telegram bot (https://t.me/onetipbot).'
                if reply_text != "":
                    self.api.update_status(status = reply_text, in_reply_to_status_id = tweet_id)
                    print(reply_text)
                tweetDetails = {
                    'tweet_id' : tweet_id,
                    'sender' : sender_handle,
                    'receiver' : receiver,
                    'tip' : tip,
                    'text' : text,
                    'replied' : "yes",
                    'success' : success,
                    'failure_reason' : failure_reason,
                    'tweet_type' : tweet_type,
                    'reply_text' : reply_text
                }
                self.dataStore.saveTweetDetails(tweetDetails)
            else:
                print("Tweet already served")
        else:
            print("Not a Tipping tweet")            
    
twitterBot = TwitterTipBot()
twitterBot.startTwitterTipBot()
