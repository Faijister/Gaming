import os
import scrapy
import json
import time
import sqlite3
from .. import settings
from datetime import datetime, timedelta
from calendar import monthrange
import codecs


def days_in_month(dt):
    return monthrange(dt.year, dt.month)[1]


def get_b2json(b):
    return json.loads(bytes.decode(b, 'utf-8')) if type(b) == bytes else {}


def get_week(str_time):
    week_tmp = datetime.strptime(str_time, "%Y-%m-%dT%H:%M:%SZ").isocalendar()
    return str(week_tmp[0]) + "-" + str(week_tmp[1])


class GearSpider(scrapy.Spider):
    name = "gear"
    config_db_path = settings.config_db_path
    config_dir = os.path.dirname(config_db_path)
    init_flag = False
    conn = None
    cur = None
    today = datetime.today()

    this_Tuesday = today - timedelta(days=today.weekday() - 1)

    # change start time by replace the day to be date of this Tuesday every week
    # start = '2021-06-14'
    # start = datetime.strftime(today.replace(day=21), "%Y-%m-%d")
    start = datetime.strftime(this_Tuesday, "%Y-%m-%d")

    # end should be tomorrow in case WCL just uploaded can not be crawled
    tomorrow = datetime.today() + timedelta(days=1)
    end = datetime.strftime(tomorrow, "%Y-%m-%d")

    def __init__(self, *a, **kw):
        super(GearSpider, self).__init__(*a, **kw)

        if not os.path.isfile(self.config_db_path):
            settings.check_path(self.config_dir)
            self.init_flag = True

        self.conn = sqlite3.connect(self.config_db_path, check_same_thread=False)
        self.conn.row_factory = settings.dict_factory
        self.cur = self.conn.cursor()

        if self.init_flag:
            self.cur.execute(settings.config_db_table)
            self.conn.commit()

    def sql_info(self, sql, param=None, query=True):
        if param:
            self.cur.execute(sql, param)
        else:
            self.cur.execute(sql)

        if query:
            return self.cur.fetchall()
        else:
            self.conn.commit()
            return self.cur.lastrowid

    def get_config_val(self, sql, param, c_key="user_name"):
        if isinstance(param, str):
            param = (param,)

        result = self.sql_info(sql, param)
        if result:
            return result[0].get(c_key)
        else:
            return None

    def get_exist(self, sql, param):
        results = self.sql_info(sql, param)
        pre_count = results[0].get('c')
        return True if pre_count > 0 else False

    def start_requests(self):
        # update 2020-05-08  沙顶 转服到 安娜丝塔丽 WCL 地址更新
        # urls = ['https://cn.classic.warcraftlogs.com/guild/calendar/490139/']
        urls = ['https://cn.classic.warcraftlogs.com/guild/calendar/542113/']
        for url in urls:
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        ans_time_stamp = int(time.time() * 1000)
        report_url = "/guild/calendar-feed/542113/0/0?&start=%s&end=%s&_=%s" % (self.start, self.end, ans_time_stamp)
        yield response.follow(report_url, callback=self.parse_report)

    def parse_report(self, response):
        cal_list = get_b2json(response.body)
        friends_url = "/reports/fights-and-participants/%s/0"

        for report in cal_list:
            report_title = report.get('title')
            week_tmp = report.get('end')
            # if report_title.startswith('2') and "BWL" in report_title:
            # if "BWL" in report_title:
            if "格鲁尔" in report_title:
                week = get_week(week_tmp)
                report_id = report.get('url').split('/')[-1]
                meta = {
                    'report_id': report_id,
                    'week_time': week,
                    'title': report_title.strip()
                }
                yield response.follow(friends_url % report_id, meta=meta, callback=self.parse_friends)

    def parse_friends(self, response):
        meta = response.meta
        friends_body = get_b2json(response.body)
        equip_url = "/reports/summary/%s/0/0/%s/%s/0/Any/0/-3.0.0/0"
        report_id = meta.get('report_id')
        friends = friends_body.get('friendlies')
        key = friends_body.get('fights')[-1].get('end_time')
        for user in friends:
            user_name = user.get('name')
            friend_id = user.get('id')
            user_type = user.get('type')
            meta['user_name'] = user_name.strip()
            meta['user_type'] = user_type.strip()
            yield response.follow(equip_url % (report_id, key, friend_id), meta=meta, callback=self.parse_equip)

    def parse_equip(self, response):
        meta = response.meta
        team = meta.get('title')
        if 'C团' in team:
            team = 'C团'
        if '1团' in team:
            team = '一团'
        elif '2团' in team:
            team = '二团'
        elif '3团' in team:
            team = '三团'
        elif '4团' in team:
            team = '四团'
        elif '5团' in team:
            team = '五团'
        user_name = meta.get('user_name')
        user_type = meta.get('user_type')
        if user_type == 'Druid':
            user_type = '德鲁伊'
        elif user_type == 'Priest':
            user_type = '牧师'
        elif user_type == 'Mage':
            user_type = '法师'
        elif user_type == 'Hunter':
            user_type = '猎人'
        elif user_type == 'Warrior':
            user_type = '战士'
        elif user_type == 'Rogue':
            user_type = '盗贼'
        elif user_type == 'Paladin':
            user_type = '圣骑士'
        elif user_type == 'Warlock':
            user_type = '术士'
        elif user_type == 'Shaman':
            user_type = '萨满'
        week_time = meta.get('week_time')
        equips = response.xpath("//div//tr")

        # change week number every week
        week_num = week_time.split('-')[1]
        filename = os.path.join('.output', '逆鳞所有团员装备_2020w' + week_num + '.txt')
        of = codecs.open(filename, 'a+', 'utf-8')
        for equip_item in equips:
            slot_tmp = equip_item.xpath(".//td[@class='num']/text()").extract_first()
            if slot_tmp:
                equip_name_tmp = equip_item.xpath(".//span/text()").extract_first()
                enhance_tmp = equip_item.xpath(".//span[@class='uncommon']/text()").extract_first()
                if enhance_tmp is None:
                    enhance_tmp = ""
                # refactor - make both Chinese and English version work - 2020-04-30
                # Example:
                # Chinese version: +<!--pts1:0:0:144768-->2<!----> 所有属性  --> +4 属性
                # English version: +<!--pts1:0:0:144768-->2<!----> All Stats  --> +4 All Stats
                # elif enhance_tmp == "+<!--pts1:0:0:144768-->2<!----> 所有属性":
                # enhance_tmp = "+4 属性"
                elif "<!--pts1:0:0:144768-->2<!---->" in enhance_tmp:
                    enhance_tmp = enhance_tmp.replace("<!--pts1:0:0:144768-->2<!---->", "4")
                # elif enhance_tmp == "+<!--pts1:0:0:19990-->14886<!----> 生命值":
                # enhance_tmp = "+100 生命"
                elif "<!--pts1:0:0:19990-->14886<!---->" in enhance_tmp:
                    enhance_tmp = enhance_tmp.replace("<!--pts1:0:0:19990-->14886<!---->", "100")
                # elif enhance_tmp == "+<!--pts1:0:0:13824-->0<!----> 所有属性":
                # enhance_tmp = "+3 属性"
                elif "<!--pts1:0:0:13824-->0<!---->" in enhance_tmp:
                    enhance_tmp = enhance_tmp.replace("<!--pts1:0:0:13824-->0<!---->", "3")
                # elif enhance_tmp == "+<!--pts1:0:0:21930-->0<!----> 冰霜法术伤害":
                # enhance_tmp == "+7 冰霜法术伤害"
                elif "<!--pts1:0:0:21930-->0<!---->" in enhance_tmp:
                    enhance_tmp = enhance_tmp.replace("<!--pts1:0:0:21930-->0<!---->", "7")

                elif enhance_tmp == "+$s1 所有抗性":
                    enhance_tmp = "+5 所有抗性"
                elif enhance_tmp == "+$s1 All Resistances":
                    enhance_tmp = "+5 All Resistances"
                elif enhance_tmp == "+0 所有抗性":
                    enhance_tmp = "+5 所有抗性"
                elif enhance_tmp == "+0 All Resistances":
                    enhance_tmp = "+5 All Resistances"

                # https://classic.wowhead.com/item=19785/falcons-call
                elif enhance_tmp == "+12 远程攻击强度，+10 耐力，+10 爆击":
                    enhance_tmp = "+24 远程攻击强度，+10 耐力，+1% 命中几率"
                elif enhance_tmp == "+12 Ranged Attack Power/+10 Stamina/+10 Critical Strike":
                    enhance_tmp = "+24 Ranged Attack Power/+10 Stamina/+%1 Hit Chance"

                equip_href = equip_item.xpath(".//a/@href").extract_first()
                equip_id = str(equip_href).split('item=', 2)[-1]
                slot = slot_tmp.strip()
                if slot == "战袍":
                    slot = "远程"
                elif slot == "Unknown Slot":
                    slot = "公会徽章"
                equip_name = equip_name_tmp.strip()
                equip = (team, user_name, user_type, slot, equip_name, equip_id, enhance_tmp, week_time)
                print(equip)
                of.write(str(equip) + '\n')
                self.sql_info(settings.insert_sql, equip, False)
        of.close()
