from Parser import TimeTableParserInterface
from bs4 import BeautifulSoup
from urllib.request import urlopen, Request
from urllib.parse import quote
import requests
import time
import re


HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 '
                         'Safari/537.3'}
SLEEP_TIME = 0

HEADERS_FOR_AJAX = {"Accept": "*/*",
"Accept-Encoding": "gzip, deflate, br",
"Accept-Language": "ru,en;q=0.9",
"Connection": "keep-alive",
"Host": "www.bstu.ru",
"Referer": "https://www.bstu.ru/about/useful/schedule/staff",
"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/92.0.4515.159 YaBrowser/21.8.2.381 Yowser/2.5 Safari/537.36",
"X-Requested-With": "XMLHttpRequest"}

class BstuParser(TimeTableParserInterface):
    def __init__(self):
        self.homeUrl = "https://www.bstu.ru/about/useful/schedule"
        self.lecturersUrl = self.homeUrl+'/staff/'

    def getSite(self, url, headers):
        req_current = Request(url=url, headers=headers)
        html_current = urlopen(req_current).read().decode('utf8')
        return BeautifulSoup(html_current, 'html.parser')

    def getEndTime(self, startTime):
        splitTime = startTime.split(':')
        hours = int(splitTime[0])
        minutes = int(splitTime[1]) + 95

        while minutes >= 60:
            minutes -= 60
            hours+=1

        return str(hours) + ':' + str(minutes)

    def parseWeek(self, group, weekRaw):
        classes = []
        rowsClasses = weekRaw.contents
        rowTable = []

        upper_time = []
        bottom_time = []

        for i in range(3, 9):
            if rowsClasses[i].find('td', {'class': 'time'}) is None:
                print(group)
                print(i)
            timeRaw = rowsClasses[i].find('td', {'class': 'time'}).find_all('p')
            upper_time.append([timeRaw[0].text, self.getEndTime(timeRaw[0].text)])
            bottom_time.append([timeRaw[1].text, self.getEndTime(timeRaw[1].text)])
            rowTable.append(rowsClasses[i].find_all('td', {'class': 'schedule_std'}))

        timeClasses = [upper_time, bottom_time]

        for i in range(0, 6):
            classes += self.parseDay(group, timeClasses, rowTable, i)

        return classes

    def parseDay(self, group, timeClasses, table, day):
        classes = []

        isNumeratorUpper = True
        isDenominatorUpper = True

        halfThirdClass = table[2][day].find_all('td', {'class': "schedule_half"})
        qatroThirdClass = table[2][day].find_all('td', {'class': "schedule_quarter"})

        if len(halfThirdClass) == 0 and len(qatroThirdClass) == 0:
            if table[2][day].find('div', {'class': 'break_top'}) is None:
                isNumeratorUpper = False
                isDenominatorUpper = False
        elif len(halfThirdClass)>0:
            if halfThirdClass[0].find('div', {'class': 'break_top'}) is None:
                isNumeratorUpper = False
            if halfThirdClass[1].find('div', {'class': 'break_top'}) is None:
                isDenominatorUpper = False
        else:
            if qatroThirdClass[0].find('div', {'class': 'break_top'}) is None:
                isNumeratorUpper = False
            if qatroThirdClass[1].find('div', {'class': 'break_top'}) is None:
                isDenominatorUpper = False
            if qatroThirdClass[2].find('div', {'class': 'break_top'}) is None:
                isDenominatorUpper = False
            if qatroThirdClass[3].find('div', {'class': 'break_top'}) is None:
                isDenominatorUpper = False



        for i in range(0, 6):
            classes += self.parseClass(group, timeClasses, isNumeratorUpper, isDenominatorUpper, day, i, table[i][day])

        return classes

    def parseCell(self, group, timeClasses, isUpper, day, num, isNumerator, cellType, raw):
        if raw.text != ' ':
            if raw.find('div', {'class': 'place_'+cellType}) is None:
                #print(group)
                return []
            classLocation = raw.find('div', {'class': 'place_'+cellType}).find('a').text
            className = raw.find('div', {'class': 'subject_'+cellType}).attrs["title"]

            if isUpper:
                classStartTime = timeClasses[1][num][0]
                classEndTime = timeClasses[1][num][1]
            else:
                classStartTime = timeClasses[0][num][0]
                classEndTime = timeClasses[0][num][1]

            lecturers = raw.find('div', {'class': 'sp_'+cellType}).find_all('a')
            classLecturers = []

            for lecturer in lecturers:
                buf = lecturer.attrs["title"].split(' ')
                if len(buf) > 1:
                    classLecturers.append(buf[-2] + ' ' + buf[-1])
                else:
                    classLecturers.append(lecturer.attrs["title"])


            return [{"name": className, "start_time": classStartTime, "end_time": classEndTime,
                            "day": day + 1, "num": num + 1, "lecturers": classLecturers, "group": group,
                            "location": classLocation, "isNumerator": isNumerator}]
        else:
            return []

    def parseClass(self, group, timeClasses, isNumeratorUpper, isDenominatorUpper, day, num, raw):
        classes = []

        halfClass = raw.find_all('td', {'class': "schedule_half"})
        qatroClass = raw.find_all('td', {'class': "schedule_quarter"})
        hqClass = raw.find_all('td', {'class': "schedule_hq"})

        if len(halfClass) == 0 and len(qatroClass) == 0 and len(hqClass) == 0:
            classes += self.parseCell(group, timeClasses, isNumeratorUpper, day, num, True, 'std', raw)
            classes += self.parseCell(group, timeClasses, isNumeratorUpper, day, num, False, 'std', raw)

        elif len(halfClass)>0:
            classes += self.parseCell(group, timeClasses, isNumeratorUpper, day, num, True, 'half',
                                          halfClass[0])
            classes += self.parseCell(group, timeClasses, isDenominatorUpper, day, num, False, 'half',
                                          halfClass[1])
        elif len(qatroClass)>0:
            classes += self.parseCell(group, timeClasses, isNumeratorUpper, day, num, True, 'quarter',
                                          qatroClass[0])
            classes += self.parseCell(group, timeClasses, isNumeratorUpper, day, num, True, 'quarter',
                                          qatroClass[1])
            classes += self.parseCell(group, timeClasses, isDenominatorUpper, day, num, False, 'quarter',
                                          qatroClass[2])
            classes += self.parseCell(group, timeClasses, isDenominatorUpper, day, num, False, 'quarter',
                                          qatroClass[3])
        else:
            classes += self.parseCell(group, timeClasses, isNumeratorUpper, day, num, True, 'hq', hqClass[0])
            classes += self.parseCell(group, timeClasses, isNumeratorUpper, day, num, False, 'hq', hqClass[1])

        return classes

    def getClassesTest(self):
        classes = []

        site = self.getSite(self.homeUrl, HEADERS)
        allGropsBlocks = site.find_all("div", {"class": "schedule-group-item"})
        # К211
        group1 = allGropsBlocks[1]
        group = group1.find_all('a')[4]
        print(group.attrs["href"])
        timeTableWeek = self.getSite(group.attrs["href"], HEADERS).find("table", {'class': 'schedule'})
        classes = self.parseWeek(group.text.replace('-', '').replace(' ', ''), timeTableWeek)

        return classes

    def getClasses(self):
        classes = []

        site = self.getSite(self.homeUrl, HEADERS)
        allGropsBlocks = site.find_all("div", {"class": "schedule-group-item"})

        i = 0
        for block in allGropsBlocks:
            i+=1
            groups = block.find_all('a')
            if i != 6:
                for group in groups:
                    timeTableWeek = self.getSite(group.attrs["href"], HEADERS).find("table", {'class': 'schedule'})
                    classes += self.parseWeek(group.text.replace('-', '').replace(' ', ''), timeTableWeek)
                    time.sleep(SLEEP_TIME)

        newClasses = []
        for i in range(0, len(classes)):
            temp = [classes[i]["group"]]
            if classes[i]["name"] != '@':
                for j in range(i + 1, len(classes)):
                    if classes[i]["day"] == classes[j]["day"] and classes[i]["num"] == classes[j]["num"] \
                            and classes[i]["isNumerator"] == classes[j]["isNumerator"] \
                            and classes[i]["location"] == classes[j]["location"] \
                            and classes[j]["group"] not in temp:
                        temp.append(classes[j]["group"])
                        classes[j]["name"] = '@'
                newClasses.append({'name': classes[i]["name"], 'start_time': classes[i]["start_time"],
                                   'end_time': classes[i]["end_time"], 'day': classes[i]["day"],
                                   'num': classes[i]["num"],
                                   'lecturers': classes[i]["lecturers"], 'groups': temp,
                                   'location': classes[i]["location"],
                                   'isNumerator': classes[i]["isNumerator"]})

        return newClasses

    def getLecturersNames(self):
        lecturersNames = []
        alphabet = ['А', 'Б', 'В', 'Г', 'Д', 'Е',  'Ж', 'З', 'И', 'К', 'Л', 'М', 'Н',
                    'О', 'П', 'Р', 'С', 'Т', 'У',  'Ф', 'Х', 'Ц', 'Ч', 'Ш', 'Щ', 'Ю', 'Я']

        for char in alphabet:
            lecturersNames += re.sub(r'(\<(/?[^>]+)>)', '',
                                     requests.post(self.lecturersUrl + quote(char),
                                                   headers=HEADERS_FOR_AJAX).content.decode('UTF-8')).split("\n")
            time.sleep(SLEEP_TIME)

        lecturersNames = [i for i in lecturersNames if i]

        return lecturersNames

    def getGroupsNames(self):
        groupsNames = []
        site = self.getSite(self.homeUrl, HEADERS)
        allGropsBlocks = site.find_all("div", {"class": "schedule-group-item"})

        i=0
        for block in allGropsBlocks:
            i+=1
            groups = block.find_all('a')
            for group in groups:
                if i != 6:
                    groupsNames.append(group.text.replace('-', '').replace(' ', ''))

        return groupsNames

    def isNumerator(self):
        site = self.getSite(self.homeUrl, HEADERS)
        return not site.text.find("ЗНАМЕНАТЕЛЕМ")
