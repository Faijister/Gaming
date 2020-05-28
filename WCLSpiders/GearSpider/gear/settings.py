import os

BOT_NAME = 'gear'
SPIDER_MODULES = ['gear.spiders']
NEWSPIDER_MODULE = 'gear.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

# Configure maximum concurrent requests performed by Scrapy (default: 16)
CONCURRENT_REQUESTS = 1

# Override the default request headers:
DEFAULT_REQUEST_HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Sec-Fetch-Dest": "empty",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-Mode": "cors",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7"
}


def check_path(c_path):
    if not os.path.isdir(c_path):
        os.makedirs(c_path)


def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d


config_db_table = """             
                    CREATE TABLE gear (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        team CHAR(50) DEFAULT '',
                        user_name CHAR(50) DEFAULT '',
                        user_type CHAR(50) DEFAULT '',
                        slot CHAR(50) DEFAULT '',
                        equip_name CHAR(50) DEFAULT '',
                        equip_id INTEGER DEFAULT '',
                        enchants CHAR(50) DEFAULT '',
                        create_time datetime default current_timestamp,
                        week_time CHAR(50) DEFAULT ''
                    );
                  """

config_db_path = "./.output/gear.db"
count_sql = "SELECT COUNT(id) c FROM gear WHERE week_time=?;"
insert_sql = "INSERT INTO gear(team, user_name, user_type, slot, equip_name, equip_id, enchants, week_time) " \
             "VALUES(?,?,?,?,?,?,?,?);"
