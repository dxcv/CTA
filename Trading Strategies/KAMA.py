ai# -*- coding: utf-8 -*-
"""
Created on Wed Jan  2 10:18:35 2019

@author: Administrator
"""

# -*- coding:utf-8 -*-
#Python 3.5.0
from WindPy import w
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import numpy as np
import csv

w.start();

future_name = 'T1812'

start_date = '2018-08-11'

end_date = "2018-11-11"

#csvfile = open(future_name + '_day.csv', 'w')

#writer = csv.writer(csvfile)

# 取数据的命令如何写可以用命令生成器来辅助完成
#wsd_data=w.wsi(future_name+".CFE", "open,high,low,close,chg,volume,amt,oi", "2018-07-11", end_date, "Fill=Previous","BarSize=5")  

wsd_data=w.wsd(future_name+".CFE", "open,high,low,close,chg", "2018-07-11", end_date, "Fill=Previous")  

#演示如何将api返回的数据装入Pandas的DataFrame
fm=pd.DataFrame(wsd_data.Data,index=wsd_data.Fields,columns=wsd_data.Times)

fm=fm.T #将矩阵转置
fm['DATE'] = wsd_data.Times
#print(wsd_data.Times)
fm.set_index('DATE')

try:
    fm['CLOSE'] = fm['close']
    fm['OPEN'] = fm['open']
    fm['HIGH'] = fm['high']
    fm['LOW'] = fm['low']
    
except KeyError:
    print(1)


fm.dropna(inplace=True)  #清除null 
#print(fm)
fm.sort_values(by=['DATE'], inplace=True)

fm.to_csv(future_name+"_daydata.csv",index=False,sep=',')


fm['CHG2'] = fm['CLOSE'].pct_change()

#fm.at[datetime.date(2018, 8, 12),'CHG2'] = 0

#print(fm[['CLOSE','CHG','CHG2']])

fm['复权因子'] = (fm['CHG2'] + 1).cumprod()

term = 10
short_term = 2
long_term = 30

ma_short = 20
ma_long = 60

fm["ma_short"] = fm['CLOSE'].rolling(ma_short).mean()
fm["ma_long"] = fm['CLOSE'].rolling(ma_long).mean()

fm['ma_short'].fillna(value=fm['CLOSE'].expanding().mean(), inplace=True)
fm['ma_long'].fillna(value=fm['CLOSE'].expanding().mean(), inplace=True)

start_date = datetime.datetime.strptime(start_date, "%Y-%m-%d")  

fm.reset_index(inplace=True,drop=True)

for i in range(term,fm.shape[0]):
    #print(fm.at[i,'CLOSE'])
    fm.at[i,'change'] = abs(fm.at[i,'CLOSE'] - fm.at[i-term,'CLOSE'])
    
    fm.at[i,'diff'] = abs(fm.at[i,'CLOSE'] - fm.at[i-1,'CLOSE']) 
    #print(fm.at[i,'CLOSE'])

#print(fm[['CLOSE','change']])

fm['diff'].fillna(value=0,inplace=True)

fm['volatility'] = fm['diff'].rolling(term).sum()

#print(fm[['CLOSE','diff','volatility']])

fastest_sc = 2/(short_term + 1)
slowest_sc = 2/(long_term + 1)

fm['ER'] = fm['change'] / fm['volatility']

print(fm['ER'])

fm['SC'] = (fm['ER'] * (fastest_sc - slowest_sc) + slowest_sc) ** 2

#print(fm['SC'])


#fm = fm[fm['DATE'] > start_date.date()]

print(fm.shape[0])

#挑选活跃时期数据
if (fm.shape[0] > 100):  # 日线数据不会超过100条

    fm = fm[fm['DATE'] > start_date]
    
else:
    
    fm = fm[fm['DATE'] > start_date.date()]
    

fm.reset_index(inplace=True,drop=True)

fm.at[0,'KAMA'] =  fm.at[0,'CLOSE']

#print(fm[['CLOSE','SC','KAMA']])

for i in range(1,fm.shape[0]):
    
    fm.at[i,'KAMA'] = fm.at[i-1,'KAMA'] + fm.at[i,'SC'] * (fm.at[i,'CLOSE'] - fm.at[i-1,'KAMA'])

#print(fm[['CLOSE','SC','KAMA']])

p = 0.8

fm['kama-diff'] = fm['KAMA']-fm['KAMA'].shift(1)

fm['filter'] = fm['kama-diff'].rolling(20,min_periods=1).std() * p

fm['filter'].fillna(value=0,inplace=True) 

print(fm[['KAMA','kama-diff','filter']])

#print(fm['filter'])

fm['min'] = fm['KAMA'].rolling(20,min_periods=1).min()

fm['max'] = fm['KAMA'].rolling(20,min_periods=1).max()

#print(fm[['KAMA','min']])

condition1 = ( (fm['KAMA'] - fm['KAMA'].shift(1)) > fm['filter'])

condition2 = ( (fm['KAMA'].shift(1) - fm['KAMA'].shift(2)) > fm['filter'])

condition5 = (fm['KAMA'] - fm['min'] < fm['filter'])

fm['a'] = fm['min'] - fm['filter']

fm['b'] = fm['max'] - fm['filter']

#condition1 = (fm['ma_short'] > fm['ma_long'])
#condition2 = (fm['ma_short'].shift(1) < fm['ma_long'].shift(1))

fm.loc[condition1 & condition2,'signal'] = 1  #买入信号

condition6 = (fm['max'] - fm['KAMA'] > fm['filter'])

#condition3 = (fm['ma_short'] < fm['ma_long'])
#condition4 = (fm['ma_short'].shift(1) > fm['ma_long'].shift(1))

condition3 = ( (fm['KAMA'] - fm['KAMA'].shift(1)) < -fm['filter'])

condition4 = ( (fm['KAMA'].shift(1) - fm['KAMA'].shift(2)) < -fm['filter'])

fm.loc[condition3 & condition4,'signal'] = 0    #卖出信号

#fm.drop(['ma_short','ma_long'],axis=1,inplace=True)

#fm['pos'] = fm['signal'].shift()  #信号是当天close买入 要第二天才可以买入 

fm['pos'] = fm['signal']

#涨跌停的时候不能买卖

limit_buy = fm['OPEN'] > fm['CLOSE'].shift(1) * 1.02  #涨停 4%

limit_sell = fm['OPEN'] < fm['CLOSE'].shift(1) * 0.98

fm.loc[limit_buy & (fm['pos'] == 1), 'pos'] = None

fm.loc[limit_sell & (fm['pos'] == 0), 'pos'] = None

fm['pos'].fillna(method='ffill',inplace=True)

fm['pos'].fillna(value=0,inplace=True) 

fm['equity_change'] = fm['CHG2'] * fm['pos']

fm['equity_curve'] = (fm['equity_change']+1).cumprod()

#fm = fm[['OPEN','CLOSE','HIGH','LOW','CHG2','pos','DATE']]

#print(fm.loc[fm['pos']==1])
#print(fm)
#print(fm['CLOSE'])


fm.reset_index(inplace=True,drop=True)

#print((fm.at[3509,'DATE'].strftime("%Y-%m-%d %H:%M:%S")[11:])== '15:15:00')

drop_list=[]

for i in range(1,fm.shape[0]):
    
    if (fm.at[i,'DATE'].strftime("%Y-%m-%d %H:%M:%S")[11:] == '11:30:00' or fm.at[i,'DATE'].strftime("%Y-%m-%d %H:%M:%S")[11:] == '15:15:00'):
        
        drop_list.append(i)

fm = fm.drop(drop_list)

fm.reset_index(inplace=True,drop=True)

initial_money = 40000

slippage = 0

commission_rate = 0

tax_rate = 0

fm.at[0,'hold_num'] = 0
fm.at[0,'stock_value'] = 0
#fm.at[0,'equity'] = initial_money
fm.at[0,'liability'] = 1   #1股
fm.at[0,'profit'] = 0
fm.at[0,'profit2'] = 0
buy_price1 = 0
p = 0
cost_value = 0  # 成本价
count = 0
win = 0
open_number = 0
short_number = 0
open_win = 0
short_win = 0
#print('1111111111',type(fm.at[2,'liability']))

#print(fm)
for i in range(1,fm.shape[0]):
    
    if (i == fm.shape[0]-1):  # 最后一天 强制平仓
        
        if fm.at[i-1,'liability'] == 0:  # 之前做空，先平仓
                
                p = (buy_price2 - fm.at[i,'CLOSE']) *50*0.0002*1000000
                
                p2 = (buy_price2 - fm.at[i,'CLOSE'])
                
                fm.at[i,'liability'] = 1
                
                if (buy_price2 - fm.at[i,'CLOSE']) > 0 :
                    
                    win += 1
                    
                    short_win += 1
                
                buy_price2 = 0
                
                print('p1',p)
        
        if fm.at[i-1,'hold_num'] == 1:
            
            #print("pppp",p)
            
            p = (fm.at[i,'CLOSE'] - buy_price1) *50*0.0002*1000000
            
            p2 = (fm.at[i,'CLOSE'] - buy_price1) 
            
            print("之前成本价",buy_price1)
            
            if (fm.at[i,'CLOSE'] - buy_price1) > 0:
                
                win += 1
                
                open_win += 1
            
            print(fm.at[i,'CLOSE'])
            
            print('p2',p)
            
        fm.at[i,'hold_num'] = 0
        
        fm.at[i,'liability'] = 1
        
        fm.at[i,'profit'] = fm.at[i-1,'profit'] + p
        
        print(fm.at[i,'DATE'],fm.at[i,'CLOSE'],(fm.at[i,'profit'])/(50*0.0002*1000000))
        
    else:
    
        if fm.at[i,'pos'] != fm.at[i-1, 'pos']:
            #number = fm.at[i-1,'equity'] * fm.at[i,'pos'] / fm.at[i,'OPEN'] #理论上今天持有的数量
            #print(fm.at[i-1,'equity'], fm.at[i,'pos'] ,fm.at[i,'OPEN'])
            #number = int(number)
            
            
            if fm.at[i,'pos'] == 1:  # 买入
                
                if fm.at[i-1,'liability'] == 0:  # 之前做空，先平仓
                    
                    p = (buy_price2 - fm.at[i,'CLOSE']) *50*0.0002*1000000
                    
                    fm.at[i,'liability'] = 1
                    
                    #print(fm.at[i,'DATE'],fm.at[i,'pos'],'平空',fm.at[i,'CLOSE'],fm.at[i-1,'profit'] + p)
                    
                    print(fm.at[i,'DATE'],fm.at[i,'pos'],'平空',fm.at[i,'CLOSE'],(fm.at[i-1,'profit'] + p)/(50*0.0002*1000000))
                    
                    #writer.writerow((fm.at[i,'DATE'],fm.at[i,'pos'],'平空',fm.at[i,'CLOSE'],(fm.at[i-1,'profit'] + p)/(50*0.0002*1000000)))
                    
                    if (buy_price2 - fm.at[i,'CLOSE']) > 0 :
                    
                        win += 1
                        
                        short_win += 1
                    
                    buy_price2 = 0
                    
                buy_price1 = fm.at[i,'CLOSE']
                
                print(fm.at[i,'DATE'],"买入价",fm.at[i,'CLOSE']) 
                
                #writer.writerow((fm.at[i,'DATE'],"买入价",fm.at[i,'CLOSE']))
                
                fm.at[i,'hold_num'] = 1
                
                fm.at[i,'profit'] = fm.at[i-1,'profit'] + p
                
                cost_value = fm.at[i,'CLOSE']
                
                #open_buy += 1
                
                #print(p)
                
                p = 0
                
                count += 1
                
                open_number += 1
                
                if(np.isnan(fm.at[i,'liability'])):
                    
                    fm.at[i,'liability'] = fm.at[i-1,'liability']
            
            else: #卖出信号
                
                if fm.at[i-1,'liability'] == 1:  # 可以做空，则卖出这股
                    
                    fm.at[i,'liability'] = 0
                    
                    buy_price2 = fm.at[i,'CLOSE']
                    
                    print(fm.at[i,'DATE'],'做空价',fm.at[i,'CLOSE'])
                    
                    #writer.writerow((fm.at[i,'DATE'],'做空价',fm.at[i,'CLOSE']))
                    
                    count += 1
                    
                    short_number += 1
                    
                    #print("sell_price",i,buy_price2) 

                #别的卖出
                
                fm.at[i,'hold_num'] = 0
                
                fm.at[i,'profit'] = fm.at[i-1,'profit'] + (fm.at[i,'CLOSE'] - buy_price1)*50*0.0002*1000000
                
                print(fm.at[i,'DATE'],'卖出价',fm.at[i,'CLOSE'], '买入价', buy_price1)
                
                #writer.writerow((fm.at[i,'DATE'],'卖出价',fm.at[i,'CLOSE'], '买入价', buy_price1))
                
                print(fm.at[i,'DATE'],'平仓',fm.at[i,'profit']/(50*0.0002*1000000))
                
                #writer.writerow((fm.at[i,'DATE'],'平仓',fm.at[i,'profit']/(50*0.0002*1000000)))
                
                if (fm.at[i,'CLOSE'] - buy_price1) > 0:
                    
                    win += 1
                    
                    open_win += 1
                
                buy_price1 = 0
                
                if(np.isnan(fm.at[i,'liability'])):
                    
                    fm.at[i,'liability'] = fm.at[i-1,'liability']
    
        else:
            
            fm.at[i,'hold_num'] = fm.at[i-1,'hold_num']
            
            fm.at[i,'profit'] = fm.at[i-1,'profit']
            
            fm.at[i,'liability'] = fm.at[i-1,'liability']
        
    
    
print("ma_short ",ma_short," ,ma_long ",ma_long)
print(fm[['DATE','pos','profit','hold_num','CLOSE','liability']])
#print(fm[['HIGH','LOW','OPEN','CLOSE','DATE']])

#max_equity = fm['profit'].max()+20000
#print(max_equity)
#min_equity = fm['profit'].min()+20000
#print(min_equity)
#print('最大回撤率',str((max_equity - min_equity)/max_equity * 100 ) + "%")

#print(fm[:1])
for i in range(0,fm.shape[0]):
    
    if (fm[:i]['profit'].max() != 0):
        
        if(i == 3370):
            print(fm.at[i,'profit']-fm[i:]['profit'].min())
        
        fm.at[i,'drawdown'] = (fm.at[i,'profit'] - fm[i:]['profit'].min())/(20000 + fm.at[i,'profit']) * 100
            
    else:
        fm.at[i,'drawdown'] = 0
    #print(fm.at[i,'drawdorn'])

#print(fm['drawdown'])

print('胜率' + " " + str(round(win/count * 100,4)))

print('多头胜率', round(open_win/open_number * 100,4))

print('空头胜率', (round(short_win/short_number * 100,4)))

print('最大回撤率', round(fm['drawdown'].max(),4))

print('收益率',round(fm.iloc[-1]['profit'] / 20000 * 100,4), "%")



#print(fm['DATE'])

#print(fm.at[0,'DATE'].strftime("%Y-%m-%d %H:%M:%S")[11:])

print('交易次数',count,'多头次数',open_number,'空头次数',short_number)


#print(open_buy)
plt.ylabel('close price')
fm.CLOSE.plot()
#fm.a.plot()
#fm.b.plot()
#fm.ma_short.plot()
#fm.ma_long.plot()
#fm.KAMA.plot()




