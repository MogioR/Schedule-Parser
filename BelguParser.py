from Parser import TimeTableParserInterface
from bs4 import BeautifulSoup
from urllib.request import urlopen, Request
import requests
import time
import re
import json

from tqdm import tqdm

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 '
                         'Safari/537.3'}
SLEEP_TIME = 0

HEADERS_FOR_AJAX_JSON = {
"Accept": "application/json, text/javascript, */*; q=0.01",
"Accept-Encoding": "gzip, deflate, br",
"Accept-Language": 'ru,en;q=0.9',
"Connection": 'keep-alive',
"Host": 'www.bsu.edu.ru',
"Referer": 'https://www.bsu.edu.ru/bsu/resource/schedule/groups/',
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/92.0.4515.159 YaBrowser/21.8.2.381 Yowser/2.5 Safari/537.36",
"X-Requested-With": "XMLHttpRequest"}

class BelguParser(TimeTableParserInterface):
    def __init__(self):
        self.homeUrl = 'https://www.bsu.edu.ru/bsu/resource/schedule'
        self.groupsUrl = self.homeUrl + '/groups/'
        self.groupsListUrl = self.homeUrl + '/groups/group_json.php?fak={0}&frm={1}'
        self.lecturersUrl = self.homeUrl + '/teachers/'
        self.lecturersKafUrl = self.homeUrl + '/teachers/cath_json.php?fac={0}'
        self.lecturersListUrl = self.homeUrl + '/teachers/teach_json.php?cath={0}'
        self.thisWeekUrl = self.homeUrl + '/week/week_json.php?week=1309202119092021&act=this_week'
        self.nextWeekUrl = self.homeUrl + '/week/week_json.php?week={0}&act=next_week'
        self.getScheduleUrl = self.homeUrl + '/teachers/show_schedule.php'

    def getSite(self, url, headers):
        req_current = Request(url=url, headers=headers)
        html_current = urlopen(req_current).read()
        return BeautifulSoup(html_current, 'html.parser')

    def getDayId(self, day):
        if day == "Понедельник":
            return 1
        elif day == "Вторник":
            return 2
        elif day == "Среда":
            return 3
        elif day == "Четверг":
            return 4
        elif day == "Пятница":
            return 5
        elif day == "Суббота":
            return 6
        elif day == "Воскресенье":
            return 7
        else:
            return -1

    def delSpace(self, string):
        newString = ""

        for i in range(0, len(string)-2):
            if string[i] != ' ':
                newString += string[i]
            elif string[i+1] != ' ':
                newString += string[i]

        return newString+string[-1]


    def parseWeek(self, weekId, lecturer, isNumerator):
        classes = []

        site = BeautifulSoup((requests.post(self.getScheduleUrl, data={'week': weekId, 'teach': lecturer[0]},
                                            headers=HEADERS_FOR_AJAX_JSON).content.decode('cp1251')), 'html.parser')

        schedule = site.find('table', {'id': 'shedule'})
        lines = schedule.contents

        classNum = 0
        classDay = 0
        classStartTime = ""
        classEndTime = ""
        className = ""
        classGroup = []
        classLocation = ""

        for line in lines:
            if(line != '\n'):
                data = line.find_all('td')
                if len(data) == 1:
                    classDay = self.getDayId(data[0].find('b').text.split(' ')[-2])
                    if classDay == -1:
                        print('Day Error')
                        print(lecturer)
                        print(weekId)
                        print(classDay)

                elif len(data) == 6:
                    if len(classGroup) != 0:
                        classes.append({"name": className, "start_time": classStartTime, "end_time": classEndTime,
                            "day": classDay, "num": classNum, "lecturer": lecturer[1], "groups": classGroup,
                            "location": classLocation, "isNumerator": isNumerator})


                    classTime = data[1].find('nobr').text.split(' - ')

                    classNum = data[0].find('nobr').text.split(' ')[0]
                    classStartTime = classTime[0]
                    classEndTime = classTime[1]
                    className = data[2].text.replace('\n', '') + ' ' + self.delSpace(re.sub("\(([^\[\]]+)\)", "",
                                                re.sub(r'(\<(/?[^>]+)>)', '', data[3].text).replace('\n', '')))
                    classGroup = [data[4].find('a').text]
                    classLocation = self.delSpace(re.sub("\(([^\[\]]+)\)","",re.sub(r'(\<(/?[^>]+)>)', '',
                                                            data[5].text).replace('\n', '').replace('\t\xa0', '')))
                elif len(data) == 4:
                    classGroup.append(data[2].find('a').text)
                else:
                    print(lecturer)
                    print(weekId)
                    print(len(data))
                    print(line)
        if className != '':
            classes.append({"name": className, "start_time": classStartTime, "end_time": classEndTime,
                            "day": classDay, "num": classNum, "lecturer": lecturer[1], "groups": classGroup,
                            "location": classLocation, "isNumerator": isNumerator})

        return classes

    def getClassesTest(self):
        classes = []
        facult = 0
        dep = 0
        lector = 1

        thisWeekCode = json.loads(requests.post(self.thisWeekUrl, headers=HEADERS_FOR_AJAX_JSON).content)[0]

        site = self.getSite(self.lecturersUrl, HEADERS)
        select = site.find('select', {'id': 'faculty'}).find_all('option')
        departments = (json.loads(requests.post(self.lecturersKafUrl.format(select[facult+1].attrs['id']),
                                                headers=HEADERS_FOR_AJAX_JSON).content))
        lecturersRaw = (json.loads(requests.post(self.lecturersListUrl.format(departments[dep][0]),
                                                 headers=HEADERS_FOR_AJAX_JSON).content))
        classes += self.parseWeek(thisWeekCode, lecturersRaw[lector], True)

        print(len(classes))
        newClasses = []
        for i in range(0, len(classes)):
            temp = [classes[i]["lecturer"]]
            if classes[i]["name"] != '@':
                for j in range(i + 1, len(classes)):
                    if classes[i]["day"] == classes[j]["day"] and classes[i]["num"] == classes[j]["num"] \
                            and classes[i]["isNumerator"] == classes[j]["isNumerator"] \
                            and classes[i]["location"] == classes[j]["location"] \
                            and classes[j]["lecturer"] not in temp:
                        temp.append(classes[j]["lecturer"])
                        classes[j]["name"] = '@'
                newClasses.append({'name': classes[i]["name"], 'start_time': classes[i]["start_time"],
                                   'end_time': classes[i]["end_time"], 'day': classes[i]["day"],
                                   'num': classes[i]["num"],
                                   'lecturers': temp, 'groups': classes[i]["groups"],
                                   'location': classes[i]["location"],
                                   'isNumerator': classes[i]["isNumerator"]})
        print(len(newClasses))

        return classes

    def getClasses(self):
        classes = []
        site = self.getSite(self.lecturersUrl, HEADERS)
        select = site.find('select', {'id': 'faculty'}).find_all('option')

        thisWeekCode = json.loads(requests.post(self.thisWeekUrl, headers=HEADERS_FOR_AJAX_JSON).content)[0]
        nextWeekCode = json.loads(requests.post(self.nextWeekUrl.format(thisWeekCode),
                                                headers=HEADERS_FOR_AJAX_JSON).content)[0]

        for i in range(1, len(select) - 1):
            departments = (json.loads(requests.post(self.lecturersKafUrl.format(select[i].attrs['id']),
                                                    headers=HEADERS_FOR_AJAX_JSON).content))
            time.sleep(SLEEP_TIME)
            for department in departments:
                lecturersRaw = (json.loads(requests.post(self.lecturersListUrl.format(department[0]),
                                                        headers=HEADERS_FOR_AJAX_JSON).content))
                time.sleep(SLEEP_TIME)

                for lecturer in lecturersRaw:
                    classes += self.parseWeek(thisWeekCode, lecturer, True)
                    classes += self.parseWeek(nextWeekCode, lecturer, False)

        newClasses = []
        for i in range(0, len(classes)):
            temp = [classes[i]["lecturer"]]
            if classes[i]["name"] != '@':
                for j in range(i + 1, len(classes)):
                    if classes[i]["day"] == classes[j]["day"] and classes[i]["num"] == classes[j]["num"] \
                            and classes[i]["isNumerator"] == classes[j]["isNumerator"] \
                            and classes[i]["location"] == classes[j]["location"] \
                            and classes[j]["lecturer"] not in temp:
                        temp.append(classes[j]["lecturer"])
                        classes[j]["name"] = '@'
                newClasses.append({'name': classes[i]["name"], 'start_time': classes[i]["start_time"],
                                   'end_time': classes[i]["end_time"], 'day': classes[i]["day"],
                                   'num': classes[i]["num"],
                                   'lecturers': temp, 'groups': classes[i]["groups"],
                                   'location': classes[i]["location"],
                                   'isNumerator': classes[i]["isNumerator"]})

        return newClasses

    def getLecturersNames(self):
        lecturers = []
        site = self.getSite(self.lecturersUrl, HEADERS)
        select = site.find('select', {'id': 'faculty'}).find_all('option')

        for i in range(1, len(select) - 1):
            departments = (json.loads(requests.post(self.lecturersKafUrl.format(select[i].attrs['id']),
                                                    headers=HEADERS_FOR_AJAX_JSON).content))
            time.sleep(SLEEP_TIME)
            for department in departments:
                lecturersRaw = (json.loads(requests.post(self.lecturersListUrl.format(department[0]),
                                                    headers=HEADERS_FOR_AJAX_JSON).content))
                time.sleep(SLEEP_TIME)
                for lecturer in lecturersRaw:
                    lecturers.append(lecturer[1])

        return list(set(lecturers))

    def getGroupsNames(self):
        groups = []

        site = self.getSite(self.groupsUrl, HEADERS)
        select = site.find('select', {'id': 'faculty'}).find_all('option')

        for i in range(1, len(select)-1):
            groupsPairs = json.loads(
                requests.post(self.groupsListUrl.format(select[i].attrs['id'], '2'), headers=HEADERS_FOR_AJAX_JSON)
                      .content)
            for pair in groupsPairs:
                groups.append(pair[0])
            time.sleep(SLEEP_TIME)

            groupsPairs = json.loads(
                requests.post(self.groupsListUrl.format(select[i].attrs['id'], '3'), headers=HEADERS_FOR_AJAX_JSON)
                .content)
            for pair in groupsPairs:
                groups.append(pair[0])
            time.sleep(SLEEP_TIME)

            groupsPairs = json.loads(
                requests.post(self.groupsListUrl.format(select[i].attrs['id'], '4'), headers=HEADERS_FOR_AJAX_JSON)
                .content)
            for pair in groupsPairs:
                groups.append(pair[0])
            time.sleep(SLEEP_TIME)

        return groups

    def isNumerator(self):
        return True