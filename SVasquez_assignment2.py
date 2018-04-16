# -*- coding: utf-8 -*-
"""
Created on Sunday Apr  9 8:59:30 2018

@author: sjv1030
"""

import numpy as np
import pandas as pd
import datetime
import json
import time
import gdax
import seaborn as sns
import matplotlib.pyplot as plt

from urllib.request import urlopen
from pymongo import MongoClient

plt.switch_backend('TKAgg')  
#%%
# Create a class named Portfolio to keep track of each portfolio created
class Portfolio(object):
    
    # Initialize every portfolio with required data structures
    def __init__(self,begVal):
        self.cash = begVal
        print('')
        print("Portfolio initiated with balance of: ${:,.2f}".format(self.cash))
        self.holdings_long = {}
        self.holdings_short = {}
        self.RPL = {}
        self.UPL = {}
        self.audit = pd.DataFrame()
        self.pnl = pd.DataFrame()
        self.show_menu
    
    # A menu of options to print for the user
    def show_menu(self):
        print("1 - Trade")
        print("2 - Show Blotter")
        print("3 - Show P/L")
        print("4 - Quit")
    
    # Show blotter
    def show_blotter(self):
        print(self.audit.sort_index(inplace=False, ascending=False))
    
    # Show P/L
    def show_pnl(self):
        if self.holdings_long:
            self.pnl = pd.DataFrame.from_records([self.holdings_long]).transpose() 
            self.pnl[['Shares','VWAP']] = self.pnl[0].apply(pd.Series)
            del self.pnl[0]
            self.pnl['Position'] = 'Long'
            
            if self.holdings_short:
                temp = pd.DataFrame.from_records([self.holdings_short]).transpose() 
                temp[['Shares','VWAP']] = temp[0].apply(pd.Series)
                del temp[0]
                temp['Position'] = 'Short'
                self.pnl = self.pnl.append(temp)
            
            # Get latest market price (ask price)
            self.update_UPL()
    
            temp1 = pd.DataFrame.from_records([self.UPL]).transpose()
            temp1[['UPL','Price']] = temp1[0].apply(pd.Series)
            del temp1[0]
    
            self.pnl = pd.concat([self.pnl,temp1],axis=1,ignore_index=False)
            
            rpl_flag = False
            if self.RPL:
                temp2 = pd.DataFrame.from_records([self.RPL]).transpose()
                self.pnl = pd.concat([self.pnl,temp2], axis=1,ignore_index=False)
                rpl_flag = True
            
            if rpl_flag:
                self.pnl.columns = ['Shares','VWAP','Position','UPL','Mkt Price','RPL']
                rename = ['Position','Shares','Mkt Price','VWAP','UPL','RPL']
                self.pnl = self.pnl[rename]
            else:
                self.pnl.columns = ['Shares','VWAP','Position','UPL','Mkt Price']
                rename = ['Position','Shares','Mkt Price','VWAP','UPL']   
                self.pnl = self.pnl[rename]
                self.pnl['RPL'] = 0
                        
        elif self.RPL:
            self.pnl = pd.DataFrame.from_records([self.RPL]).transpose()
            self.pnl.columns = ['RPL']
            self.pnl['Shares']=0
            self.pnl['Mkt Price'] = self.pnl.apply(lambda x: self.getPrice(x.name,flag=0),axis=1)
            self.pnl['VWAP']=0
            self.pnl['UPL']=0
            rename = ['Shares','Mkt Price','VWAP','UPL','RPL']
            self.pnl = self.pnl[rename]
            
        # Drop rows where Position column is NA
        self.pnl.dropna(subset=['Position'],inplace=True)
        # Replace NAs with 0s
        self.pnl.fillna(value=0, inplace=True, axis=1)
        a = np.array(self.pnl['Shares'])
        b = np.array(self.pnl['Mkt Price'])
        total_cap = np.dot(a,b) # calculate total invested positions
        
        self.pnl['Total P/L'] = self.pnl['UPL'] + self.pnl['RPL']
        self.pnl['Allocation By Shares %'] = 100*self.pnl['Shares']/self.pnl['Shares'].sum()
            
        self.pnl['Allocation By Dollars %'] =  100 * \
                (self.pnl['Shares'] * self.pnl['Mkt Price']) / total_cap
        print(self.pnl)
    
    # Update audit dataframe with new trades
    # then persist audit dataframe rows in MongoDB    
    def update_audit(self,time,trade,ticker,shares,price,flag=1):
        temp = pd.DataFrame.from_records([{'Time':time,'Trade':trade, 
                                'Ticker':ticker.upper(),'Quantity':shares,
                                'Executed Price':price,'Money In/Out':price*shares,
                                'Cash':self.cash}],index='Time')
        
        self.audit = self.audit.append(temp)
        
        # persist blotter in MongoDB if flag == 1
        if flag == 1:
            client = MongoClient('mongodb://192.168.99.100:27017')
            db = client.blotter
            collect = db.blotter
            collect.insert_one({'Time':time,'Trade':trade, 
                                    'Ticker':ticker.upper(),'Quantity':shares,
                                    'Executed Price':price,'Money In/Out':price*shares,
                                    'Cash':self.cash})
            client.close()
            
    # Update RPL dataframe by adding/subtracting on latest value        
    def update_RPL(self,ticker,value):
        self.RPL[ticker] = self.RPL.get(ticker,0) + value
    
    def update_UPL(self):
        if self.holdings_long:
            for k in self.holdings_long.keys():
                sh,wap = self.holdings_long[k]
                price = self.getPrice(k,flag=0)
                self.UPL[k] = (sh * (price-wap),price)
        if self.holdings_short:
            for k in self.holdings_short.keys():
                sh,wap = self.holdings_short[k]
                price = self.getPrice(k,flag=0)
                self.UPL[k] = (sh * (wap-price),price)
    
    def add_cash(self,amount):
        self.cash += amount
        
    def wdraw(self,amount):
        if self.cash < 0: 
            print("Cannot overdraw cash account.\n")
        else:
            self.cash -= amount
    
    # Get Price of asset
    # if request is coming from updateUPL(), then default is to get ask price
    def getPrice(self,coin,trade='buy',flag=1):
        if flag == 1:
            return 100
        else:
            bid_ask = gdax_client.get_product_order_book(coin+'-USD', level=1)
            bid = bid_ask['bids'][0][0]
            ask = bid_ask['asks'][0][0]
        if trade == 'buy':
            return float(ask)
        if trade == 'sell':
            return float(bid)

    # Get 24-hour statistics
    def get_24hr_data(self,coin):
        ## Download history from Cryptocompare.com
        url2 = 'https://min-api.cryptocompare.com/data/histominute?fsym='+coin+'&tsym=USD&limit=3000&aggregate=3&e=BITTREX'
        data2 = urlopen(url2).read()
        d2 = json.loads(data2.decode())
        
        ## Convert time to human readable format
        for item in d2['Data']:
            t = item['time']        
            t_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t))
            item['time'] = t_date
        
        coin_24hr = dict()        
        ## Extract only time and close price
        for elem in d2['Data']:
            if elem['close'] == 0: continue
            if not coin_24hr.get(elem['time'],False):
                coin_24hr[elem['time']] = elem['close']
            else:
                coin_24hr[elem['time']].append(elem['close'])
        
        coin_24df = pd.DataFrame.from_dict(coin_24hr,orient='index')
        coin_24df.columns = [coin]
        coin_24df.index = pd.to_datetime(coin_24df.index)
        coin_24df.sort_index(inplace=True)
        
        sns.set_style("darkgrid")
        
        start = coin_24df.index[-1] - pd.Timedelta(days=1)
        end = coin_24df.index[-1]
        
        
        stats24 = dict()
        stats24['24hr_avg'] = round(coin_24df.loc[start:end].mean(),2)
        stats24['24hr_sd'] = round(coin_24df.loc[start:end].std(),2)
        stats24['24hr_min'] = round(coin_24df.loc[start:end].min(),2)
        stats24['24hr_max'] = round(coin_24df.loc[start:end].max(),2)
        
        print(pd.DataFrame.from_dict(stats24,orient='index'))
        
        price = pd.DataFrame(crypto_price[coin],columns=['Date',coin])
        price['Date'] = pd.DatetimeIndex(price['Date']).normalize()
        price.set_index('Date',inplace=True)
        price['20daySMA'] = price[coin].rolling(20).mean()
        price[-100:].plot(rot=45, title="100-day Price Chart")
        plt.show()
    
    def __str__(self):
        return "Cash balance is ${:,.2f} \n".format(self.cash)
    
    def buy(self,ticker,shares,price,flag=True):
        ticker = ticker.upper()    
        
        # Check if purchase is feasible
        if self.cash >= shares*price:
            # If feasible, withdraw funds from cash
            self.wdraw(shares*price)
            # Record txn date and time
            txn_date = datetime.datetime.now()
            # Update audit table
            if flag:
                self.update_audit(txn_date,'buy',ticker,shares,price)
            
            # Check if stock is currently shorted
            if ticker in self.holdings_short.keys():
                oldAmt, oldWAP = self.holdings_short[ticker]
                # Check if we're closing short and going net long
                if shares > oldAmt:
                    del self.holdings_short[ticker]
                    if ticker in self.UPL.keys(): del self.UPL[ticker]
                    self.update_RPL(ticker,(oldAmt*(oldWAP-price)))
                    self.buy(ticker,shares-oldAmt,price,flag=False)
                # Check if partial close and staying net short
                elif shares < oldAmt:
                    # WAP doesn't change as per instructor on Slack
                    self.holdings_short[ticker] = (oldAmt-shares,oldWAP)
                    self.update_RPL(ticker,(shares*(oldWAP-price)))
                # When oldAmt == shares
                else:
                    del self.holdings_short[ticker]
                    if ticker in self.UPL.keys(): del self.UPL[ticker]
                    self.update_RPL(ticker,(shares*(oldWAP-price)))
                    self.add_cash(shares*price)
            # Check if stock is currently held long
            elif ticker in self.holdings_long.keys():
                oldAmt, oldWAP = self.holdings_long[ticker]
                
                a = np.array([oldAmt,shares])
                b = np.array([oldWAP,price])
                newWAP = np.dot(a,b)/sum(a)
                
                self.holdings_long[ticker] = (sum(a),newWAP)            
            else:
                self.holdings_long[ticker] = (shares, price)   
        else:
            print("Not enough funds available.\n")
        
    def sell(self,ticker,shares,price,flag=True):
        txn_date = datetime.datetime.now()
        ticker = ticker.upper()
        self.add_cash(shares*price)
        if flag:
            self.update_audit(txn_date,'sell',ticker,shares,price)
        
        # Check if stock is currently held long
        if ticker in self.holdings_long.keys():
            oldAmt, oldWAP = self.holdings_long[ticker]
            if shares < oldAmt:
                print("You just sold " + str(shares) + " shares of " + ticker + " at " + str(price))              
                self.holdings_long[ticker] = (oldAmt-shares,oldWAP)
                self.update_RPL(ticker,(shares*(price-oldWAP)))
            elif shares == oldAmt:
                print("You just sold " + str(shares) + " shares of " + ticker + " at " + str(price))
                self.update_RPL(ticker,(shares*(price-oldWAP)))
                del self.holdings_long[ticker]
                if ticker in self.UPL.keys(): del self.UPL[ticker]
            # when shares are more than held short
            else:
                # Closing all long positions
                print("Selling " + str(oldAmt) + " shares of " + ticker + " at " + str(price))
                self.update_RPL(ticker,(oldAmt*(price-oldWAP)))
                
                # Going short rest of shares
                print("Going short " + str(shares-oldAmt) + " shares of " + ticker + " at " + str(price))
                del self.holdings_long[ticker]
                self.sell(ticker,shares-oldAmt,price,flag=False)
                if ticker in self.UPL.keys(): del self.UPL[ticker]
        else:
            # Going short full amount of shares
            if ticker in self.holdings_short.keys():
                oldAmt, oldWAP = self.holdings_short[ticker]
                
                a = np.array([oldAmt,shares])
                b = np.array([oldWAP,price])
                newWAP = np.dot(a,b)/sum(a)
                
                self.holdings_short[ticker] = (sum(a),newWAP)
            else:
                print('Going short '+str(shares)+' shares of '+ticker+' at '+str(price))
                self.holdings_short[ticker] = (shares, price)
             

#%%

gdax_client = gdax.PublicClient()
  
pd.options.display.float_format = '{:,.2f}'.format

# Get historical data for various coins to create database
client = MongoClient('mongodb://192.168.99.100:27017')
client.drop_database('crypto_hist')


# check if database exists
if not 'blotter' in client.database_names():
    # if not, then start a new portfolio
	p = Portfolio(100000000)
else:
    # else get cash value from post prior trades
    db = client.blotter
    collect = db.blotter 
    value = list(collect.find())[-1]['Cash']
    p = Portfolio(value)

    # get prior trades and populate blotter to make history available
    for doc in collect.find():
        cash = doc['Cash']
        trade = doc['Trade']
        shares = doc['Quantity']
        tick = doc['Ticker']
        hist_time = doc['Time']
        price = doc['Executed Price']    
        p.update_audit(hist_time,trade,tick,shares,price,flag=0)



# list of crypto
crypto = ['BTC','LTC','BCH','ETH']
crypto_price = dict()

# if database of historical crypto currencies exists, then delete
# and create a new database with current prices
if 'crypto_hist' in client.database_names():
    client.drop_database('crypto_hist')
for coin in crypto:
    url = 'https://min-api.cryptocompare.com/data/histoday?fsym='+coin+'&tsym=USD&limit=830&aggregate=1&e=BITTREX'
    data = urlopen(url).read()
    d = json.loads(data.decode())
    
    ## Convert time
    for item in d['Data']:
        t = item['time']        
        t_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(t))
        item['time'] = t_date

    db = client.crypto_hist
    col = db[coin+'-full']
    result = col.insert_many(d['Data'])
    
    ## Extract only time and close price
    for doc in col.find():
        if doc['close'] == 0: continue
        if not crypto_price.get(coin,False):
            crypto_price[coin] = [[doc['time'],doc['close']]]
        else:
            crypto_price[coin].append([doc['time'],doc['close']])         
client.close()            

# Create table of crypto with numbers
coin_dict = dict()
for pair in enumerate(crypto):
    k,v = pair
    coin_dict[k]=v

coin_df = pd.DataFrame.from_dict(coin_dict,orient='index')
coin_df.columns = ['Crypto']

while True:
    print('*************')
    p.show_menu()
    opt_menu = input('Enter number corresponding with requested action:\n')

    try:
        pick = int(opt_menu)
        if pick == 1:
            # Display table of crypto and number associated with them
            print('*************')
            print(coin_df)
            
            while True:
                print('*************')
                coin = int(input("Enter a ticker from the table above to trade:\n"))
                opt_stk = coin_df.iloc[coin].values[0]
                if opt_stk.upper() in coin_dict.values():
                    break
                else:
                    print("That ticker isn't available to trade.\n")
            
            while True:
                print('*************')
                opt_shares = input("Enter quantity (whole amounts without commas) of shares to trade:\n")
                try:
                    amt = int(opt_shares)
                    break
                except ValueError:
                    print("Invalid entry. Try again.\n")
              
            while True:
                print('*************')
                opt_trade = input("Enter 'buy' or 'sell' (without quotes) for your trade: \n")
                if opt_trade.lower() == 'buy':
                    break
                elif opt_trade.lower() == 'sell':
                    break
                else:
                    print('Incorrect entry.\n')
            
            while True:
                if opt_trade.lower() == 'buy':
                    trade_price = p.getPrice(opt_stk,flag=0)
                    print('*************')
                    p.get_24hr_data(opt_stk)
                    print("\nYou are about to buy " + "{:,.0f}".format(amt) + " shares of " + opt_stk.upper() + " at ${:,.2f}".format(trade_price))
                    confirm = input("Enter 'y' for yes or 'n' for no to proceed:\n")
                    if confirm.lower() == 'y':
                        p.buy(opt_stk,amt,trade_price)
                        break
                    elif confirm.lower() == 'n':
                        break
                    else:
                        print('Incorrect entry.\n')
                if opt_trade.lower() == 'sell':
                    trade_price = p.getPrice(opt_stk,'sell',flag=0)
                    print('*************')
                    p.get_24hr_data(opt_stk)
                    print("\nYou are about to sell " + "{:,.0f}".format(amt) + " shares of " + opt_stk.upper() + " at ${:,.2f}".format(trade_price))
                    confirm = input("Enter 'y' for yes or 'n' for no to proceed:\n")
                    if confirm.lower() == 'y':
                        p.sell(opt_stk,amt,trade_price)
                        break
                    elif confirm.lower() == 'n':
                        break
                    else:
                        print('Incorrect entry.\n')
                
        elif pick == 2:
            if p.audit.empty:
                print('No trades have been submitted yet.\n')
            else:
                p.show_blotter()
#                print(p)
        
        elif pick == 3: 
            if p.RPL: 
                print('***** P/L *****')
                print('***************')
                p.show_pnl()
                print(p)
            elif not p.holdings_long:
                print('You need to have some long positions first.\n')
            else:
                print('***** P/L *****')
                print('***************')
                p.show_pnl()
                print(p)
        
        elif pick == 4:
            break
        else:
            print("Invalid entry. Try again.\n")
    except ValueError:
        print("Invalid entry. Please enter number corresponding to selection.\n")
        
