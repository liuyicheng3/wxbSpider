# wxbSpider

一个韦小宝爬虫，每次爬取当天的的带图片的更新帖   

# 使用方法   

* 首页： http://127.0.0.1:5000/wxb  

* 提供的接口： http://127.0.0.1:5000/wxb/news?from=0&to=9999999999999&catgory=旅行&size=4

from和to 代表是这段时间爬取的   
catgory: 代表需要获取的哪一个分类的    
size： 返回的数量  

可以直接run spider_app.py启动    
也可以gunicorn -c gun.conf spider_app:app  


# 需要配置的文件   
cookie.txt: 利用charles抓包即可  

若快：WebSpider.py里配置 rc = RClient('****', '****', '****', '****')

自动邮件：MailService.py 里配置 


