#!/usr/bin/python
# -*- coding: utf-8 -*-

import requests
import pandas as pd
import common.Helper as Helper
from bs4 import BeautifulSoup
import bs4


#从集思录获取数据源
class JslData():
    def __init__(self):
        #集思录首页
        self.url = 'https://www.jisilu.cn/'
        #集思录网址可转债查询接口
        self.bondUrl = self.url + 'data/cbnew/pre_list/?___jsl=LST___t'
        #集思录网址QDII基金查询接口
        self.qdiiUrl = self.url +'data/qdii/qdii_list/?___jsl=LST___t'
        #集思录网址股票LOF基金查询接口
        self.stockLofUrl = self.url +'data/lof/stock_lof_list/?___jsl=LST___t'
        #集思录网址指数LOF基金查询接口
        self.indexLofUrl = self.url +'data/lof/index_lof_list/?___jsl=LST___t'

    #从网站获取数据并存储为DataFrame格式
    def getDate(self,serverUrl):
        try :
            jsl = requests.get(url=serverUrl)
        except :
            wxPusher = Helper.WxPusher()
            wxPusher.sendMessage(title = '发生未知错误！' , text = '访问集思录网站获取数据失败，请检查代码接口！')
            raise

        data = jsl.json()

        #将json数据转换成列表
        list = []
        for row in data['rows']:
            list.append(row['cell'])

        #创建DataFrame
        stocks = pd.DataFrame(data=list)

        return stocks

    #从集思录获取可转债的数据
    def getBondData(self):
        stocks = self.getDate(self.bondUrl)

        #stocks = stocks.set_index('fund_id')
        #截取需要用到的字段
        bondData = stocks.loc[:,['apply_date','apply_cd','bond_nm','stock_nm','cb_type','rating_cd']]

        return bondData
    

    #从集思录获取基金溢价率数据的共通方法
    def getFundData(self,serverUrl):
        stocks = self.getDate(serverUrl)

        #设置index
        #stocks = stocks.set_index('fund_id')

        #去除百分比%字符
        stocks['discount_rt'] = stocks['discount_rt'].str.replace('%','')
        #将字符串转化为数字格式
        stocks['discount_rt'] = pd.to_numeric(stocks['discount_rt'],errors='ignore')
        stocks['amount_incr'] = pd.to_numeric(stocks['amount_incr'],errors='ignore')
        stocks['volume'] = pd.to_numeric(stocks['volume'],errors='ignore')

        #选取出符合套利条件的基金
        selected = stocks[(stocks['discount_rt'] >= 4) &         #溢价率大于2%
        (stocks['apply_status'].str.contains('开放') == True) &   #开放申购
        (stocks['redeem_status'].str.contains('开放') == True) &  #开放赎回
        #(stocks['amount_incr'] > 0 ) &                            #场内有新增份额
        (stocks['fund_nm'].str.contains('ETF') == False) &       #非ETF基金
        (stocks['volume'] >= 500)].sort_values('discount_rt',ascending=False)   #成交量不小于500万

        #截取需要用到的字段
        selected = selected.loc[:,['fund_id','fund_nm','discount_rt','price','estimate_value']]

        return selected

    #从集思录获取QDII基金数据
    def getQdiiData(self):
        qdiiData = self.getFundData(self.qdiiUrl)
        return qdiiData

    #从集思录获取股票LOF基金数据
    def getStockLofData(self):
        stockLof = self.getFundData(self.stockLofUrl)
        return stockLof

    #从集思录获取指数LOF基金数据
    def getIndexLofData(self):
        indexLof = self.getFundData(self.indexLofUrl)
        return indexLof

#从haoETF获取原油基金的数据
class HaoEtfData():
    def __init__(self):
        #haoETF首页
        self.url = 'http://haoetf.com/'

    def getOilFundData(self):
        try:
            html = requests.get(url = self.url).content.decode('utf-8')
        except :
            wxPusher = Helper.WxPusher()
            wxPusher.sendMessage(title = '发生未知错误！' , text = '访问haoETF网站获取数据失败，请检查代码接口！')
            raise

        soup = BeautifulSoup(html,features='lxml')

        #获取表头
        thead = soup.body.table.thead.tr

        thead_list = []
        for th in thead.contents :
            if th.string != '\n' :
                thead_list.append(th.string)
        
        #通过判断数据类型去除不需要的隐藏字段
        for th in thead_list :
            #print(type(th))
            if isinstance(th,bs4.element.Comment) == True: 
                thead_list.remove(th)
        
        #获取表内容
        tbody = soup.body.table.tbody

        tr_list = []
        for tr in tbody.find_all('tr'):
            td_list = []
            for td in tr.find_all('td'):
                td_list.append(td.string)
            tr_list.append(td_list)

        #创建表
        table = pd.DataFrame(tr_list,columns=thead_list)
        #设定变量字段名
        discount_rt = thead_list[2]  #溢价率
        volume = thead_list[6]       #成交额
        limit = thead_list[-1]       #申购限额

        #去除百分比%字符
        table[discount_rt] = table[discount_rt].str.replace('%','')
        #将字符串转化为数字格式
        table[discount_rt] = pd.to_numeric(table[discount_rt],errors='ignore')
        table[volume] = pd.to_numeric(table[volume],errors='ignore')

        #选取溢价率超过4%且成交额>500万且不开放申购的基金
        table = table[(table[discount_rt] >= 4)  & 
                    (table[limit].str.contains('暂停') == False) &
                    (table[volume] > 500)].sort_values(discount_rt,ascending=False)

        #截取需要用到的字段
        seleted = table.loc[:,['代码','名称',discount_rt,'现价','T-1估值']]

        return seleted