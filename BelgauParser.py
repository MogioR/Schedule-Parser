from Parser import TimeTableParserInterface
import requests
import json
import datetime

HEADERS_FOR_AJAX = {
'Accept': 'application/json, text/plain, */*',
'Accept-Encoding': 'gzip, deflate',
'Accept-Language': 'ru,en;q=0.9',
'Connection': 'keep-alive',
'Host': 'ra.belgau.edu.ru',
'Referer': 'http://ra.belgau.edu.ru/group',
'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
              'Chrome/92.0.4515.159 YaBrowser/21.8.2.381 Yowser/2.5 Safari/537.36'}

class BelgauParser(TimeTableParserInterface):
    def __init__(self):
        self.homeUrl = 'http://ra.belgau.edu.ru'
        self.facultyUrl = self.homeUrl + '/api/timetable/group/'
        self.coursesUrl = self.homeUrl + '/api/timetable/group/{0}'
        self.groupsUrl = self.homeUrl + '/api/timetable/group/{0}/{1}'
        self.departmentsUrl = self.homeUrl + '/api/timetable/teacher/'
        self.lecturersUrl = self.homeUrl + '/api/timetable/teacher/{0}'
        self.scheduleUrl = self.homeUrl +'{0}/lessons?start_date={1}&end_date={2}'

    def getGroups(self):
        groups = []
        faculties = (json.loads(requests.get(self.facultyUrl, headers=HEADERS_FOR_AJAX).content.decode('utf-8'))
                         )['options']

        for fac in faculties:
            courses = (json.loads(requests.get(self.coursesUrl.format(fac['id']), headers=HEADERS_FOR_AJAX)
                                  .content.decode('utf-8')))['options']
            for course in courses:
                groupsRaw = (json.loads(requests.get(self.groupsUrl.format(fac['id'], course['id']),
                                                  headers=HEADERS_FOR_AJAX).content.decode('utf-8')))['options']
                for group in groupsRaw:
                    groups.append({'name': group['title'].replace('-', ''), 'link': group['link']})

        return groups

    def getLecturers(self):
        lecturers = []
        departments = (json.loads(requests.get(self.departmentsUrl, headers=HEADERS_FOR_AJAX)
                                      .content.decode('utf-8')))['options']
        for department in departments:
            lecturersRaw = (json.loads(requests.get(self.lecturersUrl.format(department['id']),
                                                    headers=HEADERS_FOR_AJAX).content.decode('utf-8')))['options']
            for lecturersRaw in lecturersRaw:
                buf = lecturersRaw['title'].split(' ')
                name = ""
                for i in range(1, len(buf)):
                    name += buf[i]
                    if i != len(buf)-1:
                        name += ' '
                lecturers.append({'name': name, 'link': lecturersRaw['link']})
        return lecturers

    def getDayId(self, day):
        if day == "Mon":
            return 1
        elif day == "Tue":
            return 2
        elif day == "Wed":
            return 3
        elif day == "Thu":
            return 4
        elif day == "Fri":
            return 5
        elif day == "Sat":
            return 6
        elif day == "Sun":
            return 7
        else:
            return -1

    def getTime(self, timeframe):
        if timeframe == 1:
            return "8:30", "10:05"
        elif timeframe == 2:
            return "10:20", "11:55"
        elif timeframe == 3:
            return "12:40", "14:15"
        elif timeframe == 4:
            return "14:25", "16:00"
        elif timeframe == 5:
            return "16:10", "17:45"
        elif timeframe == 6:
            return "17:55", "19:30"
        elif timeframe == 7:
            return "19:40", "21:15"

    def getClassesByDate(self, group, startDate, endDate, isNumerator):
        classes = []
        classesRaw = (json.loads(requests.get(self.scheduleUrl.format(group['link'], startDate, endDate),
                                              headers=HEADERS_FOR_AJAX).content.decode('utf-8')))
        for lesson in classesRaw:
            classLocation = lesson["auditory"]
            classDay = self.getDayId(lesson["date"].split(',')[0])
            classLecturers = lesson["teacher"].split(',')

            classNum = int(lesson["timeframe"])
            classStartTime, classEndTime = self.getTime(classNum)
            className = lesson["lessonType"] + ', ' + lesson["title"]
            classGroup = group['name']

            classes.append({"name": className, "start_time": classStartTime, "end_time": classEndTime,
                            "day": classDay, "num": classNum, "lecturers": classLecturers, "group": classGroup,
                            "location": classLocation, "isNumerator": isNumerator})

        return classes

    def getClasses(self):
        classes = []
        groups = self.getGroups()

        monday = datetime.date.today() - datetime.timedelta(days=datetime.date.today().weekday())

        for group in groups:
            classes += self.getClassesByDate(group, str(monday), str(monday + datetime.timedelta(days=6)), True)
            classes += self.getClassesByDate(group, str(monday + datetime.timedelta(days=7)),
                                             str(monday + datetime.timedelta(days=13)), False)

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
        lecturers = self.getLecturers()

        for lecturer in lecturers:
            lecturersNames.append(lecturer['name'])

        return lecturersNames

    def getGroupsNames(self):
        groupsNames = []
        groups = self.getGroups()

        for group in groups:
            groupsNames.append(group['name'])

        return groupsNames

