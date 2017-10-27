#-*- coding:utf-8 -*-
import loging
from ip_adress import Ip2Region
import __init__
app = __init__.app
logging = loging.Error()
def Search(ip):
    try:
        dbFile   = "%s/../conf/ip_address.db" %app.root_path
        searcher = Ip2Region(dbFile)
        data = searcher.btreeSearch(ip)
        data = ",".join(data['region'].split('|')[:-1]).replace(',0','')
        searcher.close()
        if len(data.split(',')) >=3:
            data = ','.join(data.split(',')[2:])
        return  data
    except Exception as e:
        logging.error(e)
        return 'None'