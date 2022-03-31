#!/usr/bin/env python

import os
import pygsheets
import pandas as pd
import requests
import time


print("Running Strava 2 Hive")

def strava_screenshot(activity):
  # Create the command to run on chrome
  chrome_command = 'google-chrome --headless --screenshot="./screenshot_' + str(activity) + '.png" "https://www.strava.com/activities/' + str(activity) + '"'
  print(chrome_command)
  os.system(chrome_command)
  
def get_last_activity():
  # Last activity from google spreadsheet created by zapier
  gc = pygsheets.authorize(service_file='strava2hive.json')
  sh = gc.open("StravaActivity")
  #select the first sheet
  wks = sh[0]
  cells = wks.get_all_values(majdim='ROWS', include_tailing_empty=False, include_tailing_empty_rows=False)
  print(cells[-1])
  return cells[-1]

def get_athlete(activity):
  gc = pygsheets.authorize(service_file='strava2hive.json')
  sh = gc.open("HiveAthletes")
  wks = sh[0]
  row = []
  athletes = 5
  for i in range(athletes):
    row = wks.get_row(i + 1)
    if row[6] == activity:
      break
  return row

def update_athlete(athlete_id, change_val, column):
  gc = pygsheets.authorize(service_file='strava2hive.json')
  sh = gc.open("HiveAthletes")
  wks = sh[0]
  row = []
  athletes = 5
  for i in range(athletes):
    row = wks.get_row(i + 1)
    if row[6] == athlete_id:
      cell_value = column + str(i)
      print("Cell Value is ", cell_value)
      wks.update_value(cell_value, change_val)
      row = wks.get_row(i + 1)
      break
  return row
    
def strava_activity(athlete_id):
  print("Get latest activity from strava")
  print(athlete_id)
  
  
  
#print("Take screenshot of activity")  
#strava_screenshot(6790387629)

#print("Get the latest Activity")
#activity = get_last_activity()

#print("See if the activity is a Run")
#if activity[6] == "Run":
#  print("Yay, activity is a run, so ship it!!!")
#  athlete = get_athlete(activity[0])
#  print("Here are the athletes details")
  
print("Now use details to get activity from strava")
athlete_values = get_athlete("1778778")
print(athlete_values)

# Test if athlete bearer token is still valid by testing athlete_values[8]
if athlete_values[8] == '':
  print("Log - Expire time is empty, so need to get auth from strava")
else:
  expire_time = int(athlete_values[8])
  current_time = time.time()
  expired_value = expire_time - int(current_time)
  if expired_value > 0:
    print("Strava Token Still Valid")
  else:
    print("Strava Token Needs To Be Updated")

print(update_athlete('1778778', '94e8416188bd24cf88a1f770c01f156edf06bd22', 'H'))
print(update_athlete('1778778', 1648714531, 'I'))
print(update_athlete('1778778', '0a08826321138d99ddca153c0316dff41b6104f6', 'J'))

# Get New refhresh_token
# Update refresh token in spreadsheet





#try:
#  response = requests.post("https://www.strava.com/api/v3/oauth/token",
#                            params={'client_id': os.getenv('STRAVA_CLIENT_ID'), 'client_secret': os.getenv('STRAVA_SECRET'), 'code': 'c97c1a1e4e624972c7512a673c351f22b3d0b12d',
#                            'grant_type': 'authorization_code'})
#  access_info = dict()
#  activity_data = response.json()
#  access_info['access_token'] = activity_data['access_token']
#  print(activity_data)
#  print(access_info)
#except:
#  #print("Log - An Error occurred trying to authenticate with the {} Strava token".format(user_key))
#  print("Log - An Error occurred trying to authenticate with the Strava token")
#  # return False

