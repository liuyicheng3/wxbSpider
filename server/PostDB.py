#!/usr/bin/python
# coding=utf-8
import sqlite3
import os,time,json

class WXDB(object):

    def __init__(self,sqlite_file):
        self.sqlite_file = sqlite_file
        if not os.path.exists(self.sqlite_file):
            conn = sqlite3.connect(self.sqlite_file)
            c = conn.cursor()
            c.execute('''CREATE TABLE POST
                          (ID INTEGER PRIMARY KEY  AUTOINCREMENT ,
                          TITLE           TEXT    NOT NULL,
                          COVER           TEXT    NOT NULL,
                          URL            TEXT     NOT NULL,
                          POST_TIME            INTEGER     NOT NULL,
                          CATEGORY        TEXT NOT NULL,
                          OWNER_NAME        TEXT NOT NULL,
                          OWNER_ALIAS        TEXT NOT NULL,
                          OWNER_WX_ORIGIN_ID         TEXT NOT NULL,
                          TIME            INTEGER     NOT NULL);''')
            c.execute('''CREATE TABLE HISTORY
                                     (ID INTEGER PRIMARY KEY  AUTOINCREMENT ,
                                     OWNER_NAME        TEXT NOT NULL,
                                     OWNER_ALIAS        TEXT NOT NULL,
                                     OWNER_WX_ORIGIN_ID         TEXT NOT NULL,
                                     SPIDER_TIME            TEXT     NOT NULL);''')
            conn.commit()
            conn.close()
            print "Table created successfully";

    def getCurrentSpideInfo(self):
        if not os.path.exists(self.sqlite_file):
            return 0
        else:
            conn = sqlite3.connect(self.sqlite_file)
            cursor = conn.execute(
                "SELECT  COUNT(*) FROM POST")
        result = cursor.fetchone()
        conn.close()
        return result[0]

    def markSpideHistory(self,owner):
        conn = sqlite3.connect(self.sqlite_file)
        conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
        cursor = conn.execute("SELECT * FROM HISTORY WHERE OWNER_NAME LIKE ? ORDER BY ID ASC ", (owner.name,))
        result = cursor.fetchone()
        cursor.close()

        spideTime = int(time.time()*1000)
        if result !=None  and len(result):
            lastTimeArr = eval(result[4])
            lastTimeArr.append(spideTime)
            conn.execute(
                "UPDATE HISTORY SET SPIDER_TIME = ? WHERE OWNER_NAME LIKE ? ",
                (str(lastTimeArr),owner.name))
        else:
            conn.execute(
                "insert into HISTORY(OWNER_NAME,OWNER_ALIAS, OWNER_WX_ORIGIN_ID, SPIDER_TIME) values (?,?,?,?)",
                (owner.name,owner.wx_alias,owner.wx_origin_id,str([spideTime])))
        conn.commit()
        conn.close()

    def checkHasSpide(self,owner):
        conn = sqlite3.connect(self.sqlite_file)
        conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
        cursor = conn.execute("SELECT * FROM HISTORY WHERE OWNER_NAME LIKE ? ORDER BY ID ASC ", (owner.name,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        if result == None or len(result) == 0:
            return False
        else:
            lastSpideTimeAar  = eval( result[4])
            for lastSpideTime in lastSpideTimeAar:
                nowTimeAar = time.localtime(time.time())
                lastTimeAar = time.localtime(lastSpideTime/1000)
                if nowTimeAar[0] == lastTimeAar[0] and nowTimeAar[1] == lastTimeAar[1] and nowTimeAar[2] == lastTimeAar[2]:
                    return True
            return False


    def getByPage(self,startTime,endTime,size = 100, channel =None):
        if not os.path.exists(self.sqlite_file):
            return []
        else :
            conn = sqlite3.connect(self.sqlite_file)
            if channel == None:
                cursor = conn.execute(
                    "SELECT * FROM POST WHERE TIME >= ? AND TIME < ?  ORDER BY ID ASC ",(startTime,endTime))
            else:
                cursor = conn.execute(
                    "SELECT * FROM POST WHERE TIME >= ? AND TIME < ?  AND CATEGORY LIKE ? ORDER BY ID ASC ", (startTime, endTime,channel))
            result = cursor.fetchmany(size)
            conn.close()
        return result

    def checkHasAdded(self,title):
        if not os.path.exists(self.sqlite_file):
            return False
        else:
            conn = sqlite3.connect(self.sqlite_file)
            conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')
            try:
                cursor = conn.execute("SELECT COUNT(*) FROM POST WHERE TITLE LIKE ? ORDER BY ID ASC ",(title,))
                result = cursor.fetchone()
                conn.close()
                return result[0] >= 1
            except Exception,e:
                print('checkHasAdded'+e.message)
                return False

    def save2sqlite(self, posts, owner):

        conn = sqlite3.connect(self.sqlite_file)

        current_time = int(time.time() * 1000)  # 需要转化成毫秒
        conn.text_factory = lambda x: unicode(x, 'utf-8', 'ignore')

        params = [(post_item.title, json.dumps(post_item.covers), post_item.url, post_item.timestamp, owner.category,
                   owner.name, owner.wx_alias, owner.wx_origin_id, current_time) for post_item in posts]

        conn.executemany(
            "insert into POST(TITLE,COVER, URL, POST_TIME, CATEGORY, OWNER_NAME, OWNER_ALIAS, OWNER_WX_ORIGIN_ID,TIME) values (?,?,?,?,?,?,?,?,?)",
            (params))
        conn.commit()
        conn.close()

