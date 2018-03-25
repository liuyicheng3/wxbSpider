#!/usr/bin/python
# coding=utf-8
import simplelogger,logging
from flask import Flask,request
import json
from flask import render_template
from WebSpider import WXBSpider
from PostDB import WXDB

# 获得 simplelogger里面的default logger ，因为python的logger 是公用的在一个地方设置后，其他的都用一个
logger = logging.getLogger()

app = Flask(__name__)
db_helper = WXDB('sqlite_file.db')
web_spider = WXBSpider('sqlite_file.db','category','cookie.txt',db_helper)
web_spider.init_wxb()

@app.route('/wxb/status',methods=['GET'])
def get_info():
    count = db_helper.getCurrentSpideInfo()
    result = {'status': 1000,
              'current_status':'started' if web_spider.isSpiderIng() else 'stopped ',
              'spide_progress':  web_spider.spide_progress,
              'count': count}
    return json.dumps(result)

@app.route('/wxb/news',methods=['GET'])
def get_by_page():
    size = 100
    channel = None
    if request.args !=None and request.args.has_key('from') and request.args.has_key('to'):
        if request.args.has_key('size'):
            size = int(request.args['size'])
        if request.args.has_key('channel'):
            channel = request.args['channel']
        resultArr = db_helper.getByPage( int(request.args['from']),int(request.args['to']),size,channel)

        result = {'status': 1000,
                  'data': {},
                  'count': len(resultArr)}
        arr = map(lambda item: {'id': item[0], 'title': item[1],
                                'images': json.loads(item[2]), 'url': item[3],
                                'publishtime': item[4], 'category': item[5],
                                'src': item[6], 'src_alias': item[7],
                                'src_wx_origin_id': item[8], 'updatetime': item[9],
                                'status': 'add'}
                  , resultArr)
        result['data']['list'] = arr
    else:
        result = {'status': 1006,
                  'desc': 'Parameter Error',
                  }

    return json.dumps(result)


@app.route('/wxb/start',methods=['GET'])
def start_spide():
    if not web_spider.isSpiderIng():
        web_spider.start_spide_bg()
    result = {'status': 1000,
              'desc': "spider has been started"}
    return json.dumps(result)

@app.route('/wxb/stop',methods=['GET'])
def stop_spide():
    if  web_spider.isSpiderIng():
        web_spider.stop_spide_bg()
    result = {'status': 1000,
              'desc':"spider has ben stopped"}
    return json.dumps(result)

@app.route('/wxb')
def index():
    count = db_helper.getCurrentSpideInfo()
    current_status = 'started' if web_spider.isSpiderIng() else 'stopped '
    return render_template('index.html', count = count,status = current_status )

if __name__ == '__main__':
    from werkzeug.contrib.fixers import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app)
    # app.run(host='0.0.0.0',port=8080)
    app.run()

# 通过配置文件启动 spider_app:app左边代表这个py文件，右边代表这个文件的启动类
# gunicorn -c gun.conf spider_app:app