#!/usr/bin/python
# coding=utf-8
import simplelogger
import logging
import json, os
import time
import requests
import hashlib,random
from rk import RClient
from PostInfoSpider import WxSpider
import threading
from MailService import MailThread,Mail
from requests.packages.urllib3.exceptions import InsecureRequestWarning


# 禁用安全请求警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# 获得 simplelogger里面的default logger ，因为python的logger 是公用的在一个地方设置后，其他的都用一个
logger = logging.getLogger()


class CatItem:
    def __init__(self, id):
        self.id = id
        self.owners = []

    def __repr__(self):
        return "%s:%d" % (self.id,len(self.owners))

class BGThread(threading.Thread):
    def __init__(self, spider):
        threading.Thread.__init__(self)
        self.spider = spider
        self.threadStop = True

    def run(self):
        self.threadStop = False
        self.spider.startSpider()
        self.threadStop = True
        timeArray = time.localtime(time.time())
        styleTime = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
        mail = Mail('爬虫停止', '%s:%s' % (styleTime,self.spider.spide_progress))
        mailThread = MailThread(mail)
        mailThread.start()

    def stop(self):
        self.threadStop = True

class OwnerItem:
    def __init__(self, name,wx_alias, id, category):
        self.name = name
        self.category = category
        self.wx_alias = wx_alias
        self.wx_origin_id = id
        self.post_list = []
        self.post_sum = 0

    def __repr__(self):
        return "%s %s :%d" % (self.wx_alias, self.name, self.post_sum)

class PostItem:
    def __init__(self, title, url,time_str):
        self.title = title
        self.covers = []
        self.url = url
        self.time_str = time_str
        timeArray = time.strptime(time_str, "%Y-%m-%d %H:%M")
        self.timestamp = int(time.mktime(timeArray)*1000)

    def __repr__(self):
        return "%s => %s" % (self.title,self.url)

    def is_target(self,target_time_arr):
        start_time = time.mktime(time.struct_time((target_time_arr[0], target_time_arr[1], target_time_arr[2], 0, 0, 0, 0, 0, 0)))*1000-30*60*1000
        end_time = time.mktime(time.struct_time((target_time_arr[0], target_time_arr[1], target_time_arr[2], 23, 59, 0, 0, 0, 0)))*1000 + 30*60*1000
        if end_time >= self.timestamp >= start_time:
            return 0
        elif self.timestamp < start_time:
            return -1
        elif self.timestamp > end_time:
            return 1
        return 0

class WXBSpider(object):
    imgSpider = WxSpider()

    customHeader = {}
    customHeader[
        'User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36'
    customHeader['authority'] = 'data.wxb.com'
    customHeader['scheme'] = 'https'
    customHeader['referer'] = 'https://data.wxb.com/details/postRead?id=gh_363b924965e9'
    # customHeader['path'] = '/account/statArticles/gh_363b924965e9?period=30&page=1&sort='
    customHeader['accept'] = 'application/json, text/plain, */*'
    customHeader['x-requested-with'] = 'XMLHttpRequest'
    customHeader['accept-encoding'] = 'gzip, deflate, br'
    customHeader['accept-language'] = 'zh-CN,zh;q=0.9,en;q=0.8'

    newCookie = {}

    # 公众号的分类列表
    allCat = []

    rank_article_url = 'https://data.wxb.com/rank/article'
    params = {
        'pageSize':20,
        'type':2
    }
    #主要是为了 打个tag 使爬虫线程退出
    is_spide_ing = False

    spide_progress = ''

    def byteify(self,input):
        if isinstance(input, dict):
            inner_dict = {}
            for key, value in input.iteritems():
                inner_dict[self.byteify(key)] = self.byteify(value)
            return inner_dict
        elif isinstance(input, list):
            return [self.byteify(element) for element in input]
        elif isinstance(input, unicode):
            return input.encode('utf-8')
        else:
            return input


    rank_rank_url = 'https://data.wxb.com/rank/day/2018-02-26/'

    owner_post_web_url = 'https://data.wxb.com/account/statArticles/'
    owner_post = 'https://data.wxb.com/account/statArticles/'
    owners = []

    def __init__(self,db_file,category_dir,cookie_file,db_helper):
        self.sqlite_file = db_file
        self.cookie_file = cookie_file
        self.category_dir = category_dir
        self.db_helper = db_helper
        self.aar = time.localtime(time.time()-24*60*60)

    # 获取一个分类下的所有公众号数量
    def get_cat_owner(self,cat_id):
        cat_item = CatItem(cat_id)
        self.allCat.append(cat_item)
        page = 1
        while(True):
            owner_total,result = self.get_cat_owner_by_page(cat_id,page)
            if len(result) > 0:
                cat_item.owners.extend(result)
                self.owners.extend(result)
                if len(cat_item.owners) >= owner_total:
                    break
                else:
                    logger.info('cat %d page %d size %d ' % (cat_id, page,len(result)))
                    sleep_time = random.uniform(1,2)
                    time.sleep(sleep_time)
                    page += 1
            elif owner_total == 0 :
                logger.error('cat %d page %d total count empty '%(cat_id,page))
                break
            elif len(result) == 0 :
                logger.info('cat %d page %d reach end'%(cat_id,page))
                break
            else:
                logger.info('unkown')
                break
        return cat_id,cat_item.owners

    # 获取一个分类下的所有公众号数量
    def get_cat_owner_by_page(self,cat_id, page):
        owner_url = self.rank_rank_url + str(cat_id)
        self.params['category'] = cat_id
        self.params['page'] = page
        self.params['order'] = ''
        self.params['page_size'] = 20

        resp = requests.get(owner_url, params = self.params, headers = self.customHeader, cookies = self.newCookie, verify=False)
        try:
            resp_json = json.loads(resp.content)
            resp_json = self.byteify(resp_json)
            if resp_json.has_key('errcode') and resp_json['errcode'] == 403:
                logger.error(resp.content + " blocking !!!! ")
                while (True):
                    if self.unlock():
                        logger.info('unlock successful')
                        break
                    else:
                        logger.info('unlock failed')
                return self.get_cat_owner_by_page(cat_id,page)
            if resp_json.has_key('totalCount') and resp_json.has_key('errcode') and resp_json['errcode'] == 0:
                count = resp_json['totalCount']
                result = []
                for item in resp_json['data']:
                    result.append(OwnerItem(item['name'],item['wx_alias'],item['wx_origin_id'],"DEFAULT"))
                return count,result
            else:
                logger.error(resp.content)
                return 0,[]
        except Exception,e:
            logger.error('get_cat_owner_by_page '+str(e.message))
            return 0, []

    # 获取一个公众号下面的 指定日期的贴子数量
    def get_owner_post(self,owner):
        if self.db_helper.checkHasSpide(owner):
            timestr = time.strftime("%Y_%m_%d",  time.localtime(time.time()))
            logger.info('%s[%s] %s日已经爬取了！！'%(owner.category,owner.name,timestr))
            return False

        page = 1
        continue_spider = True
        while(continue_spider and self.is_spide_ing):
            count,result = self.get_owner_post_by_page(owner.wx_origin_id,page)
            if count > 0:
                logger.info('%s[%s] page %d => size:%d' % (owner.category,owner.name, page, len(result)))
                for post_item in result:
                    cmp_result = post_item.is_target([self.aar[0],self.aar[1],self.aar[2]])
                    if cmp_result == 0:
                        if self.db_helper.checkHasAdded(post_item.title):
                            # logger.info('%s 已经爬取过了 >> %s' % (post_item.title, post_item.url))
                            continue
                        post_item.covers.extend(self.imgSpider.get_img(post_item.url))
                        if len(post_item.covers) == 0:
                            # logger.info('%s 无封面 >> %s '%(post_item.title,post_item.url))
                            pass
                        else:
                            # logger.info('%s page %d 当天消息: %s  ' % (owner.name, page, str(post_item)))
                            owner.post_list.append(post_item)

                    elif cmp_result > 0:
                        # logger.info('%s page %d 不是今天的消息: %s ' % (owner.name, page, str(post_item)))
                        pass
                    elif cmp_result < 0:
                        # logger.info('%s page %d 老消息: %s' % (owner.name, page, str(post_item)))
                        continue_spider = False
                        break
                if len(owner.post_list) == count:
                    break
                page += 1
            else:
                logger.error(owner.wx_alias+" post empty")
                break

        owner.post_sum = len(owner.post_list)
        self.db_helper.save2sqlite(owner.post_list,owner)
        self.db_helper.markSpideHistory(owner)
        return True


    # 获取一个公众号下面的 指定日期的贴子数量
    def get_owner_post_by_page(self,owner_id, page):
        sleep_time = 1
        time.sleep(sleep_time)
        endFix = '%s?period=30&page=%d&sort='%(owner_id,page)
        post_url = self.owner_post + endFix

        owner_header = self.customHeader.copy()
        #这个接口需要验证refer
        owner_header['referer'] = 'https://data.wxb.com/details/postRead?id=%s'%owner_id

        resp = requests.get(post_url, headers = owner_header, cookies = self.newCookie, verify=False)
        logger.info(post_url)
        try:
            resp_json = json.loads(resp.content)
            resp_json = self.byteify(resp_json)
            if resp_json.has_key('errcode') and resp_json['errcode'] == 403:
                logger.error(resp.content+" blocking !!!! ")
                while(True):
                    if self.unlock():
                        logger.info('unlock successful')
                        break
                    else:
                        logger.info('unlock failed')
                return self.get_owner_post_by_page(owner_id,page)

            elif resp_json.has_key('totalCount') and resp_json.has_key('errcode') and resp_json['errcode'] == 0:
                count = resp_json['totalCount']
                result = []
                if resp_json['data'] == None or len(resp_json['data']) == 0:
                    return 0,[]
                for item in resp_json['data']:
                    post = PostItem(item['title'],item['url'],item['push_date'])
                    result.append(post)

                return count,result
            else:
                logger.error(resp.content)
                return 0,[]
        except Exception,e:
            logger.error('get_owner_post_by_page' + str(e.message))
            return 0, []


    block_url = 'https://data.wxb.com/captcha?from=https%3A%2F%2Fdata.wxb.com%2Frank%3Fcategory%3D-1%26page%3D1'
    unlock_url = 'https://data.wxb.com/unlock'
    change_code_url = 'https://account.wxb.com/index/captcha?t='

    # 下载图片到本地
    def dowmloadPic(self,url ):
        temp_dir = 'temp'
        if not os.path.exists(temp_dir):
            os.mkdir(temp_dir)
        filename = hashlib.md5(url.split("/")[-1].split(".")[0]).hexdigest()
        path =  os.path.join(temp_dir,filename + ".jpg")
        r = requests.get(url,headers = self.customHeader, cookies = self.newCookie, verify=False)
        with open(path, "wb") as code:
            code.write(r.content)
            code.close()
        return path

    # 配置若快client
    rc = RClient('****', '****', '****', '****')
    # 解锁
    def unlock(self):

        requests.get(self.block_url, headers = self.customHeader, cookies = self.newCookie, verify=False)
        code_url = self.change_code_url+str(int(time.time()))
        result = {}
        path = self.dowmloadPic(code_url)
        im = open(path, 'rb').read()

        #{u'Result': u'8fcf', u'Id': u'65d22180-266f-45d9-b182-9dccf67ece3e'}
        resp_json = self.rc.rk_create(im, 3040)
        resp_json = self.byteify(resp_json)
        if resp_json.has_key('Result') :
            logger.info('自动识别验证码图片'+str(resp_json))
            result['captcha'] = resp_json['Result']
        else:
            logger.error('自动识别验证码图片失败')
            return False

        # #人肉识别
        # im = Image.open(path)
        # im.show()
        # verify_code = raw_input('输入验证码?\n')
        # result['captcha'] = verify_code

        resp = requests.post(self.unlock_url,data=result, headers = self.customHeader, cookies = self.newCookie, verify=False)
        resp_json = json.loads(resp.content)
        if resp_json.has_key('errcode') and resp_json['errcode'] == 0:
            logger.info('unlock successful')
            target_file = os.path.join('temp', result['captcha'].lower() + '.jpg')
            if os.path.exists(target_file):
                os.remove(path)
                logger.error('已经存在%s' % target_file)
            else:
                os.rename(path, target_file)
            time.sleep(1)
            return True
        else:
            os.remove(path)
            logger.error('unlock fail:'+resp.content)
            return False




    # 输出到文件夹
    def output2file(self,file,data):
        size = len(data)
        if size == 0:
            logger.error(file+' empty')
            return
        owners_strs = []
        for pos in range(0, size):
            if pos == 0:
                line = '['
            else:
                line = ''
            line += "{\"name\":\"%s\",\"wx_alias\":\"%s\",\"wx_origin_id\":\"%s\"}" % (
                data[pos].name, data[pos].wx_alias, data[pos].wx_origin_id)
            if pos < size - 1:
                line += ','
            else:
                line += ']'
            owners_strs.append(line)

        outPut = open('final/'+file, 'w')
        outPut.writelines(owners_strs)
        outPut.close()

    def init_wxb(self):
        if os.path.exists(self.cookie_file):
            with open(self.cookie_file,'rb') as cookie_file:
                lines = cookie_file.readlines()
                for line in lines:
                    parts = line[8:].split('=')
                    result = map(lambda i:i.replace("\n", "").strip(),parts)
                    self.newCookie[result[0]] = result[1]
        else:
            logger.error("%s not found!!!"%self.cookie_file)

        catfiles = os.listdir(self.category_dir)
        for cat_file in catfiles:
            if not cat_file.endswith('.json'):
                continue
            with open(os.path.join(self.category_dir,cat_file) , 'rb') as opend_file:
                result_content = opend_file.read()
                parts = os.path.splitext(cat_file)
                category = parts[0].split('_')[1]
                owner_json = json.loads(result_content)
                owner_json = self.byteify(owner_json)
                count = 0
                for owner_item in owner_json:
                    self.owners.append(OwnerItem(owner_item['name'], owner_item['wx_alias'], owner_item['wx_origin_id'],category))
                    count += 1
                logger.info('%s 分类=> %d 公众号' % (cat_file, count))
                opend_file.close()


    # 获取所有的
    def get_all_cat_owner(self):
        sum_dict = {}
        total = 0
        for cat in range(2,3):
            result = self.get_cat_owner(cat)
            logging.info('category %d => %d'%(cat,len(result[1])))
            self.output2file('%d.json'%cat, result[1])
            sum_dict[result[0]] = len(result[1])
            total += len(result[1])
        logger.info('total owner: %d'%total)

    def startSpider10000Owner(self):
        self.init_wxb()
        post_total = 0
        self.is_spide_ing = True
        # 获取一个公众号下面的所有post
        for item in self.owners:
            if self.is_spide_ing:
                self.get_owner_post(item)
                logger.info('%s => %d'%(item.name,item.post_sum))
                post_total += item.post_sum
        logger.info('%d 个公众号 ，%d 个消息'%(len( self.owners),post_total))
        self.is_spide_ing = False

    def getTimeDuration(self,startSpideTime):
        useTimeInMin = int((time.time() - startSpideTime) / 60)
        useTimeStr = ''
        if (useTimeInMin >= 60):
            useTimeStr += "%dh" % int(useTimeInMin / 60)
        if useTimeInMin % 60 > 0:
            useTimeStr += "%dmin" % int(useTimeInMin % 60)
        if useTimeInMin <= 0:
            useTimeStr += "%ds" % int(time.time() - startSpideTime)
        return useTimeStr

    def startSpider(self):
        self.init_wxb()
        post_total = 0
        spider_owner_sum = 0
        self.is_spide_ing = True
        startSpideTime = time.time()
        # 获取一个公众号下面的所有post
        all_size = len(self.owners)
        self.spide_progress= "初始化中..."
        for index,item in enumerate(self.owners):
            if self.is_spide_ing:
                if self.get_owner_post(item):
                    spider_owner_sum += 1
                    useTimeStr =self.getTimeDuration(startSpideTime)

                    self.spide_progress = "%s[%s]=>size:%d (本次已经爬取%d个公众号,用时%s,剩余%d个待爬取)"%(item.category,item.name,item.post_sum,spider_owner_sum,useTimeStr,all_size-index)
                    logger.info(self.spide_progress)
                    post_total += item.post_sum
        timestr = time.strftime("%Y_%m_%d", self.aar)
        self.spide_progress ='爬取了%s日的%d个公众号,%d个消息,用时%s' % (timestr, spider_owner_sum, post_total,self.getTimeDuration(startSpideTime))
        logger.info(self.spide_progress)
        self.is_spide_ing = False

    def start_spide_bg(self):
        if self.isSpiderIng() :
            logger.info('当前正在爬取')
        else:
            timeArray = time.localtime(time.time())
            styleTime = time.strftime("%Y-%m-%d %H:%M:%S", timeArray)
            mail = Mail('爬虫启动','%s爬虫启动!'%styleTime)
            mailThread = MailThread(mail)
            mailThread.start()

            self.spiderThread = BGThread(self)
            self.spiderThread.start()

    def stop_spide_bg(self):
        if not self.isSpiderIng():
           logger.info('当前已经停止爬取')
        else:
            self.is_spide_ing = False

    def isSpiderIng(self):
        if not hasattr(self,'spiderThread'):
            return False
        else:
            if self.spiderThread.isAlive():
                return True
            else:
                self.is_spide_ing = False
                return False

# if __name__ == '__main__':
#     db_helper = WXDB('sqlite_file.db')
#     web_spider = WXBSpider('sqlite_file.db', 'category', 'cookie.txt', db_helper)
#     web_spider.init_wxb()
#     web_spider.start_spide_bg()
#     print(web_spider.isSpiderIng())














