import time
import re
from urllib.parse import quote
from bs4 import BeautifulSoup
from urllib.request import urlopen, Request
from Parser import TimeTableParserInterface

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 '
                         'Safari/537.3'}
SLEEP_TIME = 0

class BukepParser(TimeTableParserInterface):
    def __init__(self):
        self.homeUrl = "http://rasp.bukep.ru/Default.aspx?idFil=1000"
        self.facultiesUrl = self.homeUrl + "&tr=1"
        self.specializationsUrl = self.homeUrl + "&tr=s&f={0}"
        self.coursesUrl = self.homeUrl + "&tr=k&f={0}&s={1}"
        self.groupsUrl = self.homeUrl + "&tr=g&f={0}&s={1}&k={2}"
        self.departmentsUrl = self.homeUrl + "&tr=2"
        self.lecturersUrl = self.homeUrl + "&tr=p&k={0}"
        self.classesUrl = self.homeUrl + "&tr=pweek&k={0}&p={1}"

    def getSite(self, url, headers):
        req_current = Request(url=url, headers=headers)
        html_current = urlopen(req_current).read().decode('utf8')
        return BeautifulSoup(html_current, 'html.parser')

    def getIdByScript(self, script):
        result = ""
        skipPhase = 2

        for char in script:
            if char == '$' and skipPhase != 0:
                skipPhase -= 1
            elif char != '\'' and skipPhase == 0:
                result += char
            elif char == '\'' and skipPhase == 0:
                break

        return result

    def getFaculties(self):
        faculties = []
        site = self.getSite(self.facultiesUrl, HEADERS)

        parseResult = site.find("table", {"class": "zv"}).find_all("a")

        for faculty in parseResult:
            faculties.append({"name": faculty.text, "id": self.getIdByScript(faculty.attrs["href"])})
        return faculties

    def getSpecializations(self):
        specializations = []
        faculties = self.getFaculties()

        for faculty in faculties:
            site = self.getSite(self.specializationsUrl.format(faculty['id']), HEADERS)

            parseResult = site.find("table", {"class": "zv"}).find_all("a")

            for specialization in parseResult:
                specializations.append({"name": specialization.find("span").text,
                                        "id": self.getIdByScript(specialization.attrs["href"]),
                                        "faculty_id": faculty['id']})
            time.sleep(SLEEP_TIME)
        return specializations

    def getCourses(self):
        courses = []
        specializations = self.getSpecializations()

        for specialization in specializations:
            site = self.getSite(self.coursesUrl.format(specialization["faculty_id"], quote(specialization["id"])),
                                HEADERS)

            parseResult = site.find("table", {"class": "zv"}).find_all("a")

            for course in parseResult:
                courses.append({"name": course.find("span").text,
                                "id": self.getIdByScript(course.attrs["href"]),
                                "specialization_id": specialization['id'],
                                "faculty_id": specialization['faculty_id']})

            time.sleep(SLEEP_TIME)
        return courses

    def getGroups(self):
        groups = []
        courses = self.getCourses()

        for course in courses:
            site = self.getSite(self.groupsUrl.format(course["faculty_id"], quote(course["specialization_id"]),
                                                       course["id"]), HEADERS)
            if site.find("div", {"id": "ctl00_head_pNotRasp"}) is not None:
                continue
            else:
                parseResult = site.find("table", {"class": "zv"}).find_all("a")
                for group in parseResult:
                    groups.append({"name": re.sub("\(([^\[\]]+)\)","",group.find("span").text).replace("-",""),
                                    "id": self.getIdByScript(group.attrs["href"]),
                                    "course_id": course['id'],
                                    "specialization_id": course['specialization_id'],
                                    "faculty_id": course['faculty_id']})
            time.sleep(SLEEP_TIME)

        return groups

    def getDepartments(self):
        departments = []
        site = self.getSite(self.departmentsUrl, HEADERS)

        parseResult = site.find("table", {"class": "zv"}).find_all("a")

        for faculty in parseResult:
            departments.append({"name": faculty.text, "id": self.getIdByScript(faculty.attrs["href"])})

        return departments

    def getLecturers(self):
        lecturers = []
        departments = self.getDepartments()

        for department in departments:
            site = self.getSite(self.lecturersUrl.format(department['id']), HEADERS)
            parseResult = site.find("table", {"class": "zv"}).find_all("a")

            for lecturer in parseResult:
                buf = lecturer.find("span").text.split(" ")
                lec = {"name": buf[-3] + ' ' + buf[-2] + ' ' + buf[-1],
                       "id": self.getIdByScript(lecturer.attrs["href"]),
                       "department_id": department['id']}
                if lec not in lecturers:
                    lecturers.append(lec)

            time.sleep(SLEEP_TIME)
        return lecturers

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

    def normaliseTime(self, time):
        time = time.replace("<br>", "-")
        buf = time.split("–")
        return buf[0] + ' ' + buf[-1]

    def getClassesTimes(self):
        site = self.getSite(self.homeUrl, HEADERS)
        classesTimeTable = site.find("table", {"class": "knock"}).find_all("tr")

        workTime = []
        weekendsTime = []

        listOfTimes = [2,4,8,13,15,17,19]
        for n in listOfTimes:
            classesTime = classesTimeTable[n].find_all("td", {"class": "time"})
            workTime.append(self.normaliseTime(classesTime[0].text))
            weekendsTime.append(self.normaliseTime(classesTime[1].text))

        return [workTime, weekendsTime]

    def parseWeek(self, lecturer, isNumerator, classesTimes, week):
        classes = []

        for day in week:
            classes += self.parseDay(lecturer, isNumerator, classesTimes, day)

        return classes

    def parseDay(self, lecturer, isNumerator, classesTimes, day):

        classes = []
        classDay = self.getDayId(day.find('tr', {"class": "day"}).find('td').text)

        classesNums = day.find_all('td', {"class": "num_para"})
        classesData = day.find_all('td', {"class": "para"})

        dayType = 1
        if classDay < 6:
            dayType = 0

        for i in range(0, len(classesNums)):
            classNum = int(classesNums[i].text)
            data = classesData[i].find_all('span')
            classLocation = str(data[1].text)

            buf0 = str(data[0]).replace('</span>', '')
            buf0 = buf0.replace('<span>', '')
            buf1 = buf0.split('<br/>')
            className = buf1[0]
            classGroups = []
            buf2 = buf1[1].split(',')
            if len(buf2) == 1:
                buf3 = buf1[1].split(' ')
                buf3[-1] = buf3[-1].replace(' ', '')
                buf3[-1] = buf3[-1].replace('-', '')
                classGroups.append(buf3[-1])
                if buf3[0] == 'Лекционное':
                    className = 'Лекц. ' + buf1[0]
                elif buf3[0] == 'Практическое':
                    className = 'Практ. ' + buf1[0]
                elif buf3[0] == 'Лабораторное':
                    className = 'Лаб. ' + buf1[0]
                elif buf3[0] == 'Экзамен':
                    className = 'Экз. ' + buf1[0]
                elif buf3[0] == 'Зачет':
                    className = 'Зач. ' + buf1[0]
                elif buf3[0] == 'Консультация':
                    className = 'Конс. ' + buf1[0]
            else:
                for j in range(1, len(buf2)):
                    buf2[j] = buf2[j].replace(' ', '')
                    buf2[j] = buf2[j].replace('-', '')
                    classGroups.append(buf2[j])
                buf3 = buf2[1].split(' ')
                buf3[-1] = buf3[-1].replace('-', '')
                classGroups.append(buf3[-1])

                if buf2[0] == 'Лекционное':
                    className = 'Лекц. ' + buf1[0]
                elif buf2[0] == 'Практическое':
                    className = 'Практ. ' + buf1[0]
                elif buf2[0] == 'Лабораторное':
                    className = 'Лаб. ' + buf1[0]
                elif buf2[0] == 'Экзамен':
                    className = 'Экз. ' + buf1[0]
                elif buf2[0] == 'Зачет':
                    className = 'Зач. ' + buf1[0]
                elif buf2[0] == 'Консультация':
                    className = 'Конс. ' + buf1[0]

            #buf0 = buf0.replace('Лекционное занятие', '@')
            #buf0 = buf0.replace('Практическое занятие', '@')
            #buf0 = buf0.replace('Лабораторное занятие', '@')
            #buf0 = buf0.replace('Экзамен', '@')
            #buf0 = buf0.replace('Зачет', '@')
            #buf0 = buf0.replace('Консультация перед экзаменом', '@')
            #buf0 = buf0.replace('КоclassName = buf1[0]нсультация', '@')
            #buf0 = buf0.replace('Курсовая работа', '@')
            #buf0 = buf0.replace('Контрольная работа', '@')
            #buf0 = buf0.replace('Курсовой проект', '@')
            #buf0 = buf0.replace('Курсовой проект', '@'

            times = classesTimes[dayType][classNum-1].split(' ')
            classStartTime = times[0]
            classEndTime = times[1]

            classes.append({"name": className, "start_time": classStartTime, "end_time": classEndTime, "day": classDay,
                            "num": classNum, "lecturer": lecturer['name'], "groups": classGroups,
                            "location": classLocation, "isNumerator": isNumerator})

        return classes


    def isNumerator(self):
        site = self.getSite(self.homeUrl, HEADERS)
        parseResult = site.find("div", {"id": "watch"})

        if parseResult.text.find("Числитель") == -1:
            return True
        else:
            return False

    def getGroupsNames(self):
        names = []
        groups = self.getGroups()

        for group in groups:
            names.append(group["name"])

        return list(set(names))

    def getLecturersNames(self):
        names = []
        lecturers = self.getLecturers()

        for lecturer in lecturers:
            names.append(lecturer["name"])

        return names

    def getClasses(self):
        classes = []
        isNumerator = self.isNumerator()
        classesTimes = self.getClassesTimes()
        lecturers = self.getLecturers()

        for lecturer in lecturers:
            site = self.getSite(self.classesUrl.format(lecturer['department_id'], lecturer['id']), HEADERS)

            if site.find('table', {"id": "tbl_page1"}) is None:
                continue
            thisWeek = site.find('table', {"id": "tbl_page1"}).find_all('table', {"class": "tbl_day"})
            nextWeek = site.find('table', {"id": "tbl_page2"})

            classes += self.parseWeek(lecturer, isNumerator, classesTimes, thisWeek)

            if nextWeek is not None:
                classes += self.parseWeek(lecturer, not isNumerator, classesTimes,
                                          nextWeek.find_all('table', {"class": "tbl_day"}))
            else:
                classes += self.parseWeek(lecturer, not isNumerator, classesTimes, thisWeek)

            time.sleep(SLEEP_TIME)

        newClasses = []
        for i in range(0, len(classes)):
            temp = [classes[i]["lecturer"]]
            if classes[i]["name"] != '@':
                for j in range(i+1, len(classes)):
                    if classes[i]["day"] == classes[j]["day"] and classes[i]["num"] == classes[j]["num"] \
                        and classes[i]["isNumerator"] == classes[j]["isNumerator"] \
                        and classes[i]["location"] == classes[j]["location"] \
                        and classes[j]["lecturer"] not in temp:
                        temp.append(classes[j]["lecturer"])
                        classes[j]["name"] = '@'
                newClasses.append({'name': classes[i]["name"], 'start_time': classes[i]["start_time"],
                               'end_time': classes[i]["end_time"], 'day': classes[i]["day"], 'num': classes[i]["num"],
                               'lecturers': temp, 'groups': classes[i]["groups"], 'location': classes[i]["location"],
                               'isNumerator': classes[i]["isNumerator"]})

        return newClasses