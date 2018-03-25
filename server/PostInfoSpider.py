#!/usr/bin/python
# coding=utf-8
import simplelogger,logging
import logging
import requests
from bs4 import  BeautifulSoup


# sys.path.append(os.path.dirname(__file__) +os.sep+'../go003')

from requests.packages.urllib3.exceptions import InsecureRequestWarning

# 获得 simplelogger里面的default logger ，因为python的logger 是公用的在一个地方设置后，其他的都用一个
logger = logging.getLogger()


class WxSpider(object):

    customHeader = {}
    customHeader[
        'User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
    customHeader['accept'] = 'application/json, text/plain, */*'
    customHeader['x-requested-with'] = 'XMLHttpRequest'
    customHeader['accept-encoding'] = 'gzip, deflate, br'
    customHeader['accept-language'] = 'zh-CN,zh;q=0.9,en;q=0.8'

    def __init__(self):
        pass


    def get_img(self,post_url):
        owner_header = self.customHeader
        resp = requests.get(post_url, headers=owner_header)
        img_urls = []
        try:
            soup = BeautifulSoup(resp.content, 'html.parser')
            itemList = soup.find_all("img")
            match_count = 0
            for item in itemList:
                if item.has_attr('data-src') and item['data-src'] != None and len(item['data-src']) > 5:
                    match_count += 1
                    img_urls.append(item['data-src'])

            size = len(img_urls)
            if size <= 1:
                return img_urls
            elif size >= 2:
                return img_urls[1:1+3]
        except Exception, e:
            logger.error(str(e.message))
            return img_urls
