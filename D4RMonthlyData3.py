#!/usr/bin/python
import sys, getopt, traceback, datetime
from os import listdir
from os.path import isfile, join
import numpy as np

# global constants used in program
# Related with day
NUMBER_OF_HOURS_IN_A_DAY   = 24
NUMBER_OF_MONTHS_IN_A_YEAR = 12
NUMBER_OF_DAYS_IN_A_YEAR   = 365

# location of each ID
CALLER_ID   = 0
TIME        = 1
LOCATION_ID = 2
CITY        = 3

# format of the supported time
DATE_FORMAT = '%d-%m-%Y %H:%M'

# Ids of the unknown locations in the disctrict mapping file
UnknownLocationIds = [738, 762, 776]

# log levels
DEBUG   = 2
WARNING = 1
ERROR   = 0

# log names
LogNames = {"Error: ", "Warning: ", "Debug: "}

"""
Log Entry Type
"""
class LogEntry(object):

    """
    Constructor for the Log Entry class
    log   => Log to be stored
    level => level of the log
    """
    def __init__(self, log, level):
        self.Log   = log
        self.Level = level
        
    def __repr__(self):
        out = LogNames[self.Level] + self.Log
        return out

    def __str__(self):
        out = LogNames[self.Level] + self.Log
        return out

"""
Logger
"""    
class Logger(object):
    """
    Constructor for the Log Entry class
    fileName   => Full Path of the Log File Name
    """
    def __init__(self, fileName):
        self.Log      = []
        self.Level    = DEBUG
        self.FileName = fileName

    def AddLog(self, log, level):
        curTime = str(datetime.datetime.now().time())
        newLog = LogEntry(curTime+":"+log, level)

    """
    Add an error log
    log => Log to be stored
    """
    def AddError(self, log):
        self.AddLog(log, ERROR)
    
    """
    Add a warning log
    log => Log to be stored
    """    
    def AddWarning(self, log):
        self.AddLog(log, WARNING)
    
    """
    Add a debug log
    log => Log to be stored
    """    
    def AddDebug(self, log):
        self.AddLog(log, DEBUG)

    """
    Set print level to DEBUG
    """
    def SetOutDebug(self):
        self.Level = DEBUG

    """
    Set print level to WARNING
    """
    def SetOutWarning(self):
        self.Level = WARNING

    """
    Set print level to ERROR
    """
    def SetOutError(self):
        self.Level = ERROR
        
    def __repr__(self):
        out = ""
        for log in self.Log:
            if self.Level >= log.Level:
                out += Logger.LogNames[i]+log 
        return out
    
    """
    Print the contents of the Logs based on the set level
    """
    def Logout(self):
        with open(self.FileName, "w+") as f:
            f.write(self.__repr__())

"""
Class to store the date from the file
"""
class TimeLocation(object):
    BeginningDate = datetime.datetime.strptime('01-01-2017 00:00', DATE_FORMAT)
    """
    Constructor to set the time format
    time => Formatted time string '%d-%m-%Y %H:%M'
    """
    def __init__(self, time, location):
        # always assume invalid format
        self.ValidFormat   = False
        self.Year          = -1
        self.Month         = -1
        self.Day           = -1
        self.Hour          = -1
        self.Minute        = -1
        self.Location      = location
        self.NumberOfDays  = -1
        try:
            # read the supported time format from file
            Time = datetime.datetime.strptime(time, DATE_FORMAT)

            # store only what makes sense
            self.ValidFormat = True
            self.Year        = Time.year
            self.Month       = Time.month
            self.Day         = Time.day
            self.Hour        = Time.hour
            self.Minute      = Time.minute
            self.Location    = location

            # calculate the number of days passed
            self.NumberOfDays = abs((Time-TimeLocation.BeginningDate).days)
            
        except Exception as e:
            print("ERROR ", str(e))
            print(traceback.format_exc())
            pass
        
    def __repr__(self): 
        TimeInStringFormat = str(self.Location)
        TimeInStringFormat += ": "
		# only if it is valid
        if self.ValidFormat:
            TimeInStringFormat += str(self.Year)
            TimeInStringFormat += "-"
            TimeInStringFormat += str(self.Month)
            TimeInStringFormat += "-"
            TimeInStringFormat += str(self.Day)
            TimeInStringFormat += " "
            TimeInStringFormat += str(self.Hour)
            TimeInStringFormat += ":"
            TimeInStringFormat += str(self.Minute)
        else :
            TimeInStringFormat += "XXXX-XX-XX XX:XX"
        return TimeInStringFormat

    def __lt__(self, other):
        ret = False
        # check if both are valid
        if self.ValidFormat and other.ValidFormat:
            # just check which happens before
            if self.Year < other.Year :
                ret = True
            elif self.Year == other.Year:
                if self.Month < other.Month :
                    ret = True
                elif self.Month == other.Month:
                    if self.Day < other.Day :
                        ret = True
                    elif self.Day == other.Day:
                        if self.Hour < other.Hour :
                            ret = True
                        elif self.Hour == other.Hour:
                            if self.Minute < other.Minute :
                                ret = True
                                
        # if other is not valid and self is valid then it is smaller
        if self.ValidFormat and other.ValidFormat == False:
            ret = True
        return ret

class UserTimeSortedLocationData(object):
    """
    Constructor for the user centric storage data
    callerId  => Id of the caller (integer)
    isRefugee => Shows whether the user is a refugee (boolean)
    """
    def __init__(self, callerId, isRefugee):
        self.Id                        = callerId
        self.IsRefugee                 = isRefugee
        self.UserData                  = []
        self.NumberOfCalls             = 0
        self.InvalidTimeFormattedCalls = 0
        self.HourlyNumberOfCalls       = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MonthlyNumberOfCalls      = [0] * NUMBER_OF_MONTHS_IN_A_YEAR
        self.DailyNumberOfCalls        = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.MarkovMatrice             = {}
        self.HourlyNumberOfTrans       = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MonthlyNumberOfTrans      = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.DailyNumberOfTrans        = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.Sorted                    = False

    """
    Add a new location and time of call to the existing user
    time => Time and location of the call (TimeLocation)
    """    
    def AddNewTimeLocation(self, time):
        # append self user data
        self.UserData.append(time)

        # increment total number of calls
        self.NumberOfCalls = self.NumberOfCalls + 1

        # set the corresponding calls
        if time.ValidFormat :
            self.HourlyNumberOfCalls[time.Hour - 1]    = self.HourlyNumberOfCalls[time.Hour - 1] + 1
            self.MonthlyNumberOfCalls[time.Month - 1]  = self.MonthlyNumberOfCalls[time.Month - 1] + 1
            self.DailyNumberOfCalls[time.NumberOfDays] = self.DailyNumberOfCalls[time.NumberOfDays] + 1
        else :
            self.InvalidTimeFormattedCalls = self.InvalidTimeFormattedCalls + 1     

    """
    Calculate the number of daily and monthly user state transitions (location changes)
    """
    def CalculateTransitionStatistics(self):
        if self.Sorted == False:
            # first sort according to call time
            self.UserData.sort()
            self.Sorted = True
            
        # first just find a location transition
        prevLocationId = -1
        
        # go through all possible locations
        for timeLocation in self.UserData:
            # now get the location Id from time location
            if prevLocationId != timeLocation.Location:
                prevLocation = timeLocation.Location
                self.HourlyNumberOfTrans[timeLocation.Hour - 1]    = self.HourlyNumberOfTrans[timeLocation.Hour - 1] + 1
                self.MonthlyNumberOfTrans[timeLocation.Month - 1]  = self.MonthlyNumberOfTrans[timeLocation.Month - 1] + 1
                self.DailyNumberOfTrans[timeLocation.NumberOfDays] = self.DailyNumberOfTrans[timeLocation.NumberOfDays] + 1
            

    """
    Create a transition matrix between states (Districts in our case) for user
    This is done for each user for each entry
    """
    def CreateTransitionMatrix(self):
        if self.Sorted == False:
            # first sort according to call time
            self.UserData.sort()
            self.Sorted = True
        
        # go through all possible locations
        for timeLocation in self.UserData:
            # now get the location Id from time location
            locationId = timeLocation.Location
                
            # check if it is already processed
            if locationId not in self.MarkovMatrice:
                # add this location to the matrice
                self.MarkovMatrice[locationId] = {}

                # tricky call to get all of the members with the same location id and then getting the
                # next elements since they are the next state thus members of the transition matrix
                locations = [i+1 for i,x in enumerate(self.UserData) if x.Location == locationId]

                # for every transition
                for nextLocationIdx in locations:
                    # check if it is the last element
                    if nextLocationIdx < len(self.UserData):
                        # check if already in the map
                        if self.UserData[nextLocationIdx].Location in self.MarkovMatrice[locationId]:
                            self.MarkovMatrice[locationId][self.UserData[nextLocationIdx].Location] = \
                                self.MarkovMatrice[locationId][self.UserData[nextLocationIdx].Location] + 1
                        # the first occurence
                        else :
                            self.MarkovMatrice[locationId][self.UserData[nextLocationIdx].Location] = 1
                    # last element in the known universe
                    elif nextLocationIdx == len(self.UserData):
                        # if already in the row
                        if locationId in self.MarkovMatrice[locationId]:
                            self.MarkovMatrice[locationId][locationId] = \
                                self.MarkovMatrice[locationId][locationId] + 1
                        # the first occurence
                        else:
                            self.MarkovMatrice[locationId][locationId] = 1
                            
                # now normalize with the length
                for nextLocationIdx in self.MarkovMatrice[locationId]:
                    self.MarkovMatrice[locationId][nextLocationIdx] /= len(locations)
        
"""
Class to read the Data Set Three
"""
class DataSetThree(object):
    """
    Constructor for data storage class
    logFileName => Full Path of the Log File
    """
    def __init__(self, logFileName = "DataSet3Log.txt"):
        self.UserLocationData          = {}
        self.Distances                 = {}
        self.Logger                    = Logger(logFileName)

        # data statistics
        # Mean
        self.MeanTotalHourlyNumberOfCalls  = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MeanTotalMonthlyNumberOfCalls = [0] * NUMBER_OF_MONTHS_IN_A_YEAR
        self.MeanTotalDailyNumberOfCalls   = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.MeanRefHourlyNumberOfCalls    = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MeanRefMonthlyNumberOfCalls   = [0] * NUMBER_OF_MONTHS_IN_A_YEAR
        self.MeanRefDailyNumberOfCalls     = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.MeanTotalHourlyNumberOfTrans  = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MeanTotalMonthlyNumberOfTrans = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MeanTotalDailyNumberOfTrans   = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.MeanRefHourlyNumberOfTrans    = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MeanRefMonthlyNumberOfTrans   = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MeanRefDailyNumberOfTrans     = [0] * NUMBER_OF_DAYS_IN_A_YEAR

        # Standard Deviation
        self.StdTotalHourlyNumberOfCalls  = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.StdTotalMonthlyNumberOfCalls = [0] * NUMBER_OF_MONTHS_IN_A_YEAR
        self.StdTotalDailyNumberOfCalls   = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.StdRefHourlyNumberOfCalls    = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.StdRefMonthlyNumberOfCalls   = [0] * NUMBER_OF_MONTHS_IN_A_YEAR
        self.StdRefDailyNumberOfCalls     = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.StdTotalHourlyNumberOfTrans  = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.StdTotalMonthlyNumberOfTrans = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.StdTotalDailyNumberOfTrans   = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.StdRefHourlyNumberOfTrans    = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.StdRefMonthlyNumberOfTrans   = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.StdRefDailyNumberOfTrans     = [0] * NUMBER_OF_DAYS_IN_A_YEAR

        # Min
        self.MinTotalHourlyNumberOfCalls  = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MinTotalMonthlyNumberOfCalls = [0] * NUMBER_OF_MONTHS_IN_A_YEAR
        self.MinTotalDailyNumberOfCalls   = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.MinRefHourlyNumberOfCalls    = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MinRefMonthlyNumberOfCalls   = [0] * NUMBER_OF_MONTHS_IN_A_YEAR
        self.MinRefDailyNumberOfCalls     = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.MinTotalHourlyNumberOfTrans  = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MinTotalMonthlyNumberOfTrans = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MinTotalDailyNumberOfTrans   = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.MinRefHourlyNumberOfTrans    = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MinRefMonthlyNumberOfTrans   = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MinRefDailyNumberOfTrans     = [0] * NUMBER_OF_DAYS_IN_A_YEAR

        # Max
        self.MaxTotalHourlyNumberOfCalls  = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MaxTotalMonthlyNumberOfCalls = [0] * NUMBER_OF_MONTHS_IN_A_YEAR
        self.MaxTotalDailyNumberOfCalls   = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.MaxRefHourlyNumberOfCalls    = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MaxRefMonthlyNumberOfCalls   = [0] * NUMBER_OF_MONTHS_IN_A_YEAR
        self.MaxRefDailyNumberOfCalls     = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.MaxTotalHourlyNumberOfTrans  = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MaxTotalMonthlyNumberOfTrans = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MaxTotalDailyNumberOfTrans   = [0] * NUMBER_OF_DAYS_IN_A_YEAR
        self.MaxRefHourlyNumberOfTrans    = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MaxRefMonthlyNumberOfTrans   = [0] * NUMBER_OF_HOURS_IN_A_DAY
        self.MaxRefDailyNumberOfTrans     = [0] * NUMBER_OF_DAYS_IN_A_YEAR

    """
    Parse and store the data in file
    fileName => Full Path of the dataset three file
    """
    def ParseData(self, fileName):
        # open the file
        with open(fileName) as f:
            # begin counting lines 
            lineNumber = 1
            # parse each line seperately
            for line in f:
                # split comma seperated data and strip contents from white spaces and enter characters
                data = [x.strip('\n ') for x in line.split(",")]
                
                # parsing errors shall not stop us from parsing the file
                try:
                    # assign variables
                    locationId         = int(data[LOCATION_ID]) # id of the location of the caller
                    callerId           = int(data[CALLER_ID][1:]) # id of the caller or callee
                    time               = data[TIME] # time of the call
                    isRefugee          = (data[CALLER_ID][0] == '1') # ids shall begin with a 1:Refugee and 2:Non-Refugee
                    checkRefugeeSanity = ((data[CALLER_ID][0] == '1') or (data[CALLER_ID][0] == '2')) # just check if everything is valid

                    # parse the time
                    timeLocation = TimeLocation(time, locationId)
                    
                    # just a small piece of error handling for the file to check if it is a valid line to be processed
                    process = True
                    # dismiss unknown locations
                    if locationId in UnknownLocationIds:
                        self.Logger.AddError("Unknown Location Ids: ", locationId, " at line ", lineNumber, " in file ", fileName)
                        process = False

                    # dismiss faulty ids
                    if checkRefugeeSanity == False:
                        self.Logger.AddError("Problem with Caller id: ", data[CALLER_ID], " at line ", lineNumber, " in file ", fileName)
                        process = False

                    # dismiss invalid time entries
                    if timeLocation.ValidFormat == False:
                        self.Logger.AddError("Problem with Time Format: ", data[TIME], " at line ", lineNumber, " in file ", fileName)
                        process = False

                    # process valid entries only
                    if process :
                        # check if the user is already inside the data
                        if callerId not in self.UserLocationData :
                            self.UserLocationData[callerId] = UserTimeSortedLocationData(callerId, isRefugee)
                        self.UserLocationData[callerId].AddNewTimeLocation(timeLocation)
                        
                # exceptions shall be logged and parsing shall continue   
                except Exception as e:
                    # just log the exception
                    self.Logger.AddError(str(e))
                    self.Logger.AddError(traceback.format_exc())
                    pass

                # increment line number
                lineNumber += 1
        
    """
    Get the distance between two districts
    id1 => id of the first district
    id2 => id of the second district
    """
    def GetDistanceInBetween(self, id1, id2):
        dist = 0
        if id1 != id2 :
            dist = -1
            if id1 in self.Distances and id2 in self.Distances:
                if id2 in self.Distances[id1]:
                    dist = self.Distances[id1][id2]
                elif id1 in self.Distances[id2]:
                    dist = self.Distances[id2][id1]
            elif id1 in self.Distances:
                if id2 in self.Distances[id1]:
                    dist = self.Distances[id1][id2]
            elif id2 in self.Distances:
                if id1 in self.Distances[id2]:
                    dist = self.Distances[id2][id1]
        return dist

    """
    Parse the contents of distance data between given districts in Turkey
    fileName => Full Path of the district distances file 
    """
    def ParseDistanceData(self, fileName):
        with open(fileName) as f:
            lineNumber = 1
            for line in f:
                data = [x.strip('\n ') for x in line.split(",") if x.strip('\n ') != '']
                if len(data) > 1:
                    self.Distances[int(data[0])] = {}
                    for d in data[1:]:
                        s = [x.strip('\n ') for x in d.split(":")]
                        if len(s) == 2:
                            self.Distances[int(data[0])][int(s[0])] = float(s[1])
                        else:
                            self.Logger.AddError("Wrong input at line: ", lineNumber, " for input: ", s)
                    lineNumber += 1
                    

    """
    Print either to a file or system out
    fileName => Name of the file (if left blank direct to sys out)
    """
    def PrintUserLocationData(self, fileName = None):
        out = ""
        for userId,user in self.UserLocationData:
            out += str(userId) + "=>" + str(user.UserData)
            out += str(userId) + "=>" + str(user.MarkovMatrice)
        if fileName == None:
            print(out)
        else:
            with open(fileName) as f:
                f.write(out)

    """
    Print either to a file or system out in csv format
    fileName => Name of the file (if left blank direct to sys out)
    """
    def PrintUserStatistics(self, fileName = None):
        # print out monthly statistics
        out = "Monthly Statistics;January;February;March;April;May,June;July;August;September;October;November;December\n"
        out += "Total Mean Number Of Calls"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.MeanTotalMonthlyNumberOfCalls[i])
        out += "\n"
        out += "Refugee Mean Number Of Calls"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.MeanRefMonthlyNumberOfCalls[i])
        out += "\n"
        out += "Total Mean Number Of Transitions"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.MeanTotalMonthlyNumberOfTrans[i])
        out += "\n"
        out += "Refugee Mean Number Of Transitions"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.MeanRefMonthlyNumberOfTrans[i])
        out += "\n"
        out += "Total Std Number Of Calls"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.StdTotalMonthlyNumberOfCalls[i])
        out += "\n"
        out += "Refugee Std Number Of Calls"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.StdRefMonthlyNumberOfCalls[i])
        out += "\n"
        out += "Total Std Number Of Transitions"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.StdTotalMonthlyNumberOfTrans[i])
        out += "\n"
        out += "Refugee Std Number Of Transitions"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.StdRefMonthlyNumberOfTrans[i])
        out += "Total Min Number Of Calls"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.MinTotalMonthlyNumberOfCalls[i])
        out += "\n"
        out += "Refugee Min Number Of Calls"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.MinRefMonthlyNumberOfCalls[i])
        out += "\n"
        out += "Total Min Number Of Transitions"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.MinTotalMonthlyNumberOfTrans[i])
        out += "\n"
        out += "Refugee Min Number Of Transitions"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.MinRefMonthlyNumberOfTrans[i])
        out += "Total Max Number Of Calls"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.MaxTotalMonthlyNumberOfCalls[i])
        out += "\n"
        out += "Refugee Max Number Of Calls"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.MaxRefMonthlyNumberOfCalls[i])
        out += "\n"
        out += "Total Max Number Of Transitions"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.MaxTotalMonthlyNumberOfTrans[i])
        out += "\n"
        out += "Refugee Max Number Of Transitions"
        for i in range(NUMBER_OF_MONTHS_IN_A_YEAR):
            out += ";" + str(self.MaxRefMonthlyNumberOfTrans[i])
        out += "\n"
        out += "\n"
        out += "\n"
                
        # print out daily statistics
        out += "Daily Statistics"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(i)
        out += "\n"
        out += "Total Mean Number Of Calls"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.MeanTotalDailyNumberOfCalls[i])
        out += "\n"
        out += "Refugee Mean Number Of Calls"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.MeanRefDailyNumberOfCalls[i])
        out += "\n"
        out += "Total Mean Number Of Transitions"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.MeanTotalDailyNumberOfTrans[i])
        out += "\n"
        out += "Refugee Mean Number Of Transitions"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.MeanRefDailyNumberOfTrans[i])
        out += "\n"
        out += "Total Std Number Of Calls"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.StdTotalDailyNumberOfCalls[i])
        out += "\n"
        out += "Refugee Std Number Of Calls"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.StdRefDailyNumberOfCalls[i])
        out += "\n"
        out += "Total Std Number Of Transitions"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.StdTotalDailyNumberOfTrans[i])
        out += "\n"
        out += "Refugee Std Number Of Transitions"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.StdRefDailyNumberOfTrans[i])
        out += "\n"
        out += "Total Min Number Of Calls"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.MinTotalDailyNumberOfCalls[i])
        out += "\n"
        out += "Refugee Std Number Of Calls"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.MinRefDailyNumberOfCalls[i])
        out += "\n"
        out += "Total Min Number Of Transitions"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.MinTotalDailyNumberOfTrans[i])
        out += "\n"
        out += "Refugee Min Number Of Transitions"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.MinRefDailyNumberOfTrans[i])
        out += "\n"
        out += "Total Max Number Of Calls"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.MaxTotalDailyNumberOfCalls[i])
        out += "\n"
        out += "Refugee Max Number Of Calls"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.MaxRefDailyNumberOfCalls[i])
        out += "\n"
        out += "Total Max Number Of Transitions"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.MaxTotalDailyNumberOfTrans[i])
        out += "\n"
        out += "Refugee Max Number Of Transitions"
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            out += ";" + str(self.MaxRefDailyNumberOfTrans[i])
        out += "\n"
        out += "\n"
        out += "\n"

        # print out hourly statistics
        out += "Hourly Statistics"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(i) + "-" + str(i+1)
        out += "\n"
        out += "Total Mean Number Of Calls"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.MeanTotalHourlyNumberOfCalls[i])
        out += "\n"
        out += "Refugee Mean Number Of Calls"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.MeanRefHourlyNumberOfCalls[i])
        out += "\n"
        out += "Total Mean Number Of Transitions"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.MeanTotalHourlyNumberOfTrans[i])
        out += "\n"
        out += "Refugee Mean Number Of Transitions"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.MeanRefHourlyNumberOfTrans[i])
        out += "\n"
        out += "Total Std Number Of Calls"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.StdTotalHourlyNumberOfCalls[i])
        out += "\n"
        out += "Refugee Std Number Of Calls"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.StdRefHourlyNumberOfCalls[i])
        out += "\n"
        out += "Total Std Number Of Transitions"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.StdTotalHourlyNumberOfTrans[i])
        out += "\n"
        out += "Refugee Std Number Of Transitions"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.StdRefHourlyNumberOfTrans[i])
        out += "\n"
        out += "Total Min Number Of Calls"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.MinTotalHourlyNumberOfCalls[i])
        out += "\n"
        out += "Refugee Min Number Of Calls"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.MinRefHourlyNumberOfCalls[i])
        out += "\n"
        out += "Total Min Number Of Transitions"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.MinTotalHourlyNumberOfTrans[i])
        out += "\n"
        out += "Refugee Min Number Of Transitions"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.MinRefHourlyNumberOfTrans[i])
        out += "\n"
        out += "Total Max Number Of Calls"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.MaxTotalHourlyNumberOfCalls[i])
        out += "\n"
        out += "Refugee Max Number Of Calls"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.MaxRefHourlyNumberOfCalls[i])
        out += "\n"
        out += "Total Max Number Of Transitions"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.MaxTotalHourlyNumberOfTrans[i])
        out += "\n"
        out += "Refugee Max Number Of Transitions"
        for i in range(NUMBER_OF_HOURS_IN_A_DAY):
            out += ";" + str(self.MaxRefHourlyNumberOfTrans[i])

        # print out the contents
        if fileName == None:
            print(out)
        else:
            with open(fileName, "w+") as f:
                f.write(out)

    """
    Create the transition matrix for each user
    """ 
    def CreateTransitionMatrix(self):
        for userId,user in self.UserLocationData:
            user.CreateTransitionMatrix()
    """
    Calculate some of the user statistics such as
    Mean of Daily Number of Calls
    Standard Deviation of Daily Number Of Calls
    Mean of Monthly Number Of Calls
    Standard Deviation of Monthly Number Of Calls
    Mean Of Number Of Daily and Monthly User Transitions
    """
    def CalculateUserStatistics(self):
        # first calculate the number of transitions
        for userId, user in self.UserLocationData.items():
            user.CalculateTransitionStatistics()
  
        # get monthly and daily statistics
        for i in range(NUMBER_OF_DAYS_IN_A_YEAR):
            if i < NUMBER_OF_MONTHS_IN_A_YEAR:
                # multi use
                numberOfCalls = [user.MonthlyNumberOfCalls[i] for userId,user in self.UserLocationData.items()]
                numberOfTrans = [user.MonthlyNumberOfTrans[i] for userId,user in self.UserLocationData.items()]
                numberOfRefCalls = [user.MonthlyNumberOfCalls[i] for userId,user in self.UserLocationData.items() if user.IsRefugee == True]
                numberOfRefTrans = [user.MonthlyNumberOfTrans[i] for userId,user in self.UserLocationData.items() if user.IsRefugee == True]
                
                # calculate monthly mean
                self.MeanTotalMonthlyNumberOfCalls[i] = np.mean(numberOfCalls)
                self.MeanTotalMonthlyNumberOfTrans[i] = np.mean(numberOfTrans)
                self.MeanRefMonthlyNumberOfCalls[i]   = np.mean(numberOfRefCalls )
                self.MeanRefMonthlyNumberOfTrans[i]   = np.mean(numberOfRefTrans )

                # calculate monthly standard deviation
                self.StdTotalMonthlyNumberOfCalls[i] = np.std(numberOfCalls)
                self.StdTotalMonthlyNumberOfTrans[i] = np.std(numberOfTrans)
                self.StdRefMonthlyNumberOfCalls[i]   = np.std(numberOfRefCalls)
                self.StdRefMonthlyNumberOfTrans[i]   = np.std(numberOfRefTrans)

                # calculate monthly min
                self.MinTotalMonthlyNumberOfCalls[i] = min(numberOfCalls)
                self.MinTotalMonthlyNumberOfTrans[i] = min(numberOfTrans)
                self.MinRefMonthlyNumberOfCalls[i]   = min(numberOfRefCalls)
                self.MinRefMonthlyNumberOfTrans[i]   = min(numberOfRefTrans)

                # calculate monthly min
                self.MaxTotalMonthlyNumberOfCalls[i] = max(numberOfCalls)
                self.MaxTotalMonthlyNumberOfTrans[i] = max(numberOfTrans)
                self.MaxRefMonthlyNumberOfCalls[i]   = max(numberOfRefCalls)
                self.MaxRefMonthlyNumberOfTrans[i]   = max(numberOfRefTrans)

            if i < NUMBER_OF_HOURS_IN_A_DAY:
                # multi use
                numberOfCalls = [user.HourlyNumberOfCalls[i] for userId,user in self.UserLocationData.items()]
                numberOfTrans = [user.HourlyNumberOfTrans[i] for userId,user in self.UserLocationData.items()]
                numberOfRefCalls = [user.HourlyNumberOfCalls[i] for userId,user in self.UserLocationData.items() if user.IsRefugee == True]
                numberOfRefTrans = [user.HourlyNumberOfTrans[i] for userId,user in self.UserLocationData.items() if user.IsRefugee == True]
                # calculate hourly mean
                self.MeanTotalHourlyNumberOfCalls[i] = np.mean(numberOfCalls)
                self.MeanTotalHourlyNumberOfTrans[i] = np.mean(numberOfTrans)
                self.MeanRefHourlyNumberOfCalls[i]   = np.mean(numberOfRefCalls)
                self.MeanRefHourlyNumberOfTrans[i]   = np.mean(numberOfRefTrans)

                # calculate hourly standard deviation
                self.StdTotalHourlyNumberOfCalls[i] = np.std(numberOfCalls)
                self.StdTotalHourlyNumberOfTrans[i] = np.std(numberOfTrans)
                self.StdRefHourlyNumberOfCalls[i]   = np.std(numberOfRefCalls)
                self.StdRefHourlyNumberOfTrans[i]   = np.std(numberOfRefTrans)

                # calculate monthly min
                self.MinTotalHourlyNumberOfCalls[i] = min(numberOfCalls)
                self.MinTotalHourlyNumberOfTrans[i] = min(numberOfTrans)
                self.MinRefHourlyNumberOfCalls[i]   = min(numberOfRefCalls)
                self.MinRefHourlyNumberOfTrans[i]   = min(numberOfRefTrans)

                # calculate monthly min
                self.MaxTotalHourlyNumberOfCalls[i] = max(numberOfCalls)
                self.MaxTotalHourlyNumberOfTrans[i] = max(numberOfTrans)
                self.MaxRefHourlyNumberOfCalls[i]   = max(numberOfRefCalls)
                self.MaxRefHourlyNumberOfTrans[i]   = max(numberOfRefTrans)

            # multi use
            numberOfCalls = [user.DailyNumberOfCalls[i] for userId,user in self.UserLocationData.items()]
            numberOfTrans = [user.DailyNumberOfTrans[i] for userId,user in self.UserLocationData.items()]
            numberOfRefCalls = [user.DailyNumberOfCalls[i] for userId,user in self.UserLocationData.items() if user.IsRefugee == True]
            numberOfRefTrans = [user.DailyNumberOfTrans[i] for userId,user in self.UserLocationData.items() if user.IsRefugee == True]
                
            # calculate daily mean
            self.MeanTotalDailyNumberOfCalls[i] = np.mean(numberOfCalls)
            self.MeanTotalDailyNumberOfTrans[i] = np.mean(numberOfTrans)
            self.MeanRefDailyNumberOfCalls[i]   = np.mean(numberOfRefCalls)
            self.MeanRefDailyNumberOfTrans[i]   = np.mean(numberOfRefTrans)

            # calculate daily standard deviation
            self.StdTotalDailyNumberOfCalls[i] = np.std(numberOfCalls)
            self.StdTotalDailyNumberOfTrans[i] = np.std(numberOfTrans)
            self.StdRefDailyNumberOfCalls[i]   = np.std(numberOfRefCalls)
            self.StdRefDailyNumberOfTrans[i]   = np.std(numberOfRefTrans)
            
            # calculate monthly min
            self.MinTotalDailyNumberOfCalls[i] = min(numberOfCalls)
            self.MinTotalDailyNumberOfTrans[i] = min(numberOfTrans)
            self.MinRefDailyNumberOfCalls[i]   = min(numberOfRefCalls)
            self.MinRefDailyNumberOfTrans[i]   = min(numberOfRefTrans)

            # calculate monthly min
            self.MaxTotalDailyNumberOfCalls[i] = max(numberOfCalls)
            self.MaxTotalDailyNumberOfTrans[i] = max(numberOfTrans)
            self.MaxRefDailyNumberOfCalls[i]   = max(numberOfRefCalls)
            self.MaxRefDailyNumberOfTrans[i]   = max(numberOfRefTrans)
          
    """
    Log Out
    """
    def Logout(self):
        self.Logger.Logout()

"""
Main script to run the Data Set Three
"""
class MainDataSetThreeScript(object):
    """
    Run the algorithm
    The following will be done in the given order:
     - Parse the distances file and store the distance between two districts
     - Parse each data set 3 file and store them
     - Create state transition diagram
     - Print Location data if requested by user
     - Print Logs
    Usage:
     D4R.py -i <Data Set Three Files Folder Path> -d <Distances File Path> -p <Yes/No> -P <File To Print Markov Out>
     -p and -P are optional
    """
    def Run(argv):
        inputfile = None
        distances = None
        markovOut = None
        printOut  = False
        out = 'D4R.py -i <Data Set Three Files Folder Path> -d <Distances File Path> -p <Yes/No> -P <File To Print Markov Out>'
        try:
           opts, args = getopt.getopt(argv,"hi:d:p:P:",["ifile=dfile=pfile=Pfile="])
        except getopt.GetoptError:
           print (out)
           sys.exit(2)
        for opt, arg in opts:
            if opt == '-h':
                print (out)
                sys.exit()
            elif opt in ("-i", "--ifile"):
                inputfile = arg
            elif opt in ("-d", "--dfile"):
                distances = arg
            elif opt in ("-p", "--pfile"):
                printOut = (arg.strip().lower == "yes")
            elif opt in ("-P", "--Pfile"):
                markovOut = arg
                
        # check if the file exists
        if inputfile is not None and distances is not None:  
            # parse and process data
            MainDataSetThreeScript.MainRun(inputfile, distances, printOut, markovOut)
        else:
            print (out)
    """
    Main Run
    inputfolder => full path of the folder containing Data Set 3 files
    distances   => full path of the distances file
    printOut    => Flag to select whether user data and transition matrix shall be printed (optional default = No)
    outFile     => full path of the file if user data is to be written out
    """
    def MainRun(inputfolder, distances, printOut=False, outFile = None):
        # create a new set
        DataSet = DataSetThree()
        DataSet.ParseDistanceData(distances)

        # get the list of files only
        files = [join(inputfolder, f) for f in listdir(inputfolder) if isfile(join(inputfolder, f)) ]
        
        # iterate through all files
        for inputfile in files:
            print("Processing file ", inputfile, " started")
            DataSet.ParseData(inputfile)
            print("Processing file ", inputfile, " finished")

        # create per user state transition matrix
        DataSet.CreateTransitionMatrix()

        # create the transition statistics

        if printOut :
            # print out the data
            DataSet.PrintUserLocationData(outFile)

        # log everything
        DataSet.Logout()

    def StatisticsRun(inputfolder, distances, printOut=False, outFile = None):
         # create a new set
        DataSet = DataSetThree()
        DataSet.ParseDistanceData(distances)

        # get the list of files only
        files = [join(inputfolder, f) for f in listdir(inputfolder) if isfile(join(inputfolder, f)) ]
        
        # iterate through all files
        for inputfile in files:
            print("Processing file ", inputfile, " started")
            DataSet.ParseData(inputfile)
            print("Processing file ", inputfile, " finished")

        # create the transition statistics
        DataSet.CalculateUserStatistics()

        if printOut :
            # print out the data
            DataSet.PrintUserStatistics(outFile)

        # log everything
        DataSet.Logout()

# run the code
if len(sys.argv) > 1:
    MainDataSetThreeScript.Run(sys.argv[1:])
else:
    # MainDataSetThreeScript.MainRun("D:\\work\\D4R\\Dataset3New", "distances.txt", True, "Markov.out")
    MainDataSetThreeScript.StatisticsRun("D:\\work\\D4R\\Dataset3New", "distances.txt", True, "Statistics.csv")
print("Operation Finished")

