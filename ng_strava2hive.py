#!/usr/bin/env python

import os
import re
import pygsheets
import pandas as pd
import requests
import time
import glob
import hive_work
import boto3
import pipedream_modules
import post_functions
from selenium import webdriver
from boto3.dynamodb.conditions import Key
from selenium.webdriver.common.by import By
from time import sleep
from datetime import datetime, timedelta
from beem.imageuploader import ImageUploader
from beem import Hive
from beem.account import Account
from beem.nodelist import NodeList
from hivesigner.operations import Comment
from hivesigner.client import Client
from hivesigner.operations import CommentOptions

# Functions
def strava_screenshot(activity):
  # Create the command to run on chrome
  #chrome_command = 'google-chrome --headless --screenshot="./screenshot_' + str(activity) + '.png" "https://www.strava.com/activities/' + str(activity) + '"'
  #print(chrome_command)
  #os.system(chrome_command)
  activity_url = "https://www.strava.com/activities/" + str(activity)
  image_name = "image_" + str(activity) + ".png"
  driver = webdriver.Chrome('/bin/chromedriver')
  driver.get(activity_url)
  sleep(10)
  driver.find_element(by=By.CLASS_NAME, value="btn-accept-cookie-banner").click() 
  #driver.find_element_by_class_name("btn-accept-cookie-banner").click() 
  driver.get_screenshot_as_file(image_name)
  driver.quit()
  os.system("ls -l")

def activity_posted(athlete_id, activity_id):
  # Check if an activity has been posted already
  gc = pygsheets.authorize(service_file='strava2hive.json')
  sh = gc.open("StravaActivity")
  wks = sh[1]
  row = []
  posted = False
  cells = wks.get_all_values(majdim='ROWS', include_tailing_empty=False, include_tailing_empty_rows=False)
  total_rows = len(cells)
  for i in range(total_rows):
    row = wks.get_row(i + 1)
    if str(row[1]) == str(activity_id):
      posted = True
      print("Activity has been found, now returning True")
      return posted
      break
  return posted

def record_post(athlete_id, activity_id, activity_type, activity_date, activity_distance, activity_calories, wcount, hive_name):
  # Update the activity spreadsheet once activity has been posted to Hive
  gc = pygsheets.authorize(service_file='strava2hive.json')
  sh = gc.open("StravaActivity")
  wks = sh[1]
  cells = wks.get_all_values(majdim='ROWS', include_tailing_empty=False, include_tailing_empty_rows=False)
  # Add athlete id
  cell_value = "A" + str(len(cells) + 1)
  wks.update_value(cell_value, athlete_id)
  # Now add the activity
  cell_value = "B" + str(len(cells) + 1)
  wks.update_value(cell_value, activity_id)
  # Add activity type
  cell_value = "C" + str(len(cells) + 1)
  wks.update_value(cell_value, activity_type)
  # Now add the activity date
  cell_value = "D" + str(len(cells) + 1)
  wks.update_value(cell_value, activity_date)
  # Now add the activity distance
  cell_value = "E" + str(len(cells) + 1)
  wks.update_value(cell_value, activity_distance)
  # Now add the activity calories
  cell_value = "F" + str(len(cells) + 1)
  wks.update_value(cell_value, activity_calories)
  # Now add the activity word count
  cell_value = "G" + str(len(cells) + 1)
  wks.update_value(cell_value, wcount)
  # Now add the activity hive user name
  cell_value = "H" + str(len(cells) + 1)
  wks.update_value(cell_value, hive_name)
    
def refresh_access_token(athlete):
  # We need to update the access_token in strava every six hours
  try:
    response = requests.post("https://www.strava.com/api/v3/oauth/token",
                             params={'client_id': os.getenv('STRAVA_CLIENT_ID'), 'client_secret': os.getenv('STRAVA_SECRET'), 
                             'code': athlete[9], 'grant_type': 'refresh_token', 'refresh_token': athlete[13] })
    access_info = dict()
    activity_data = response.json()
    access_info['access_token'] = activity_data['access_token']
    access_info['expires_at'] = activity_data['expires_at']
    access_info['refresh_token'] = activity_data['refresh_token']
    hive_work.update_athlete(athlete[10], access_info['access_token'], 'L', "Strava2HiveNewUserSignUp")
    hive_work.update_athlete(athlete[10], access_info['expires_at'], 'M', "Strava2HiveNewUserSignUp")
    print(hive_work.update_athlete(athlete[10], access_info['refresh_token'], 'N', "Strava2HiveNewUserSignUp"))
    
  except:
    print("Log - An Error occurred trying to authenticate with the {} Strava token".format(athlete[10]))
    return False
  
def new_user_access_token(athlete):
  # New users have a different process for getting access tokens
  try:
    response = requests.post("https://www.strava.com/api/v3/oauth/token",
                             params={'client_id': os.getenv('STRAVA_CLIENT_ID'), 'client_secret': os.getenv('STRAVA_SECRET'),
                                     'code': athlete[9], 'grant_type': 'authorization_code'})
    access_info = dict()
    activity_data = response.json()
    access_info['access_token'] = activity_data['access_token']
    access_info['expires_at'] = activity_data['expires_at']
    access_info['refresh_token'] = activity_data['refresh_token']
    hive_work.update_athlete(athlete[10], access_info['access_token'], 'L', "Strava2HiveNewUserSignUp")
    hive_work.update_athlete(athlete[10], access_info['expires_at'], 'M', "Strava2HiveNewUserSignUp")
    print(hive_work.update_athlete(athlete[10], access_info['refresh_token'], 'N', "Strava2HiveNewUserSignUp"))
  except:
    print("Log - An Error occurred trying to authenticate with the Strava token")
    return False
  
def strava_activity_details(activity_id, bearer_header):
  strava_activity_url = "https://www.strava.com/api/v3/activities/" + str(activity_id)
  headers = {'Content-Type': 'application/json', 'Authorization': bearer_header}
  response = requests.get(strava_activity_url, headers=headers, )
  more_activity_data = response.json()
  activity_info = dict()
  activity_info['id'] = activity_id
  activity_info['name'] = more_activity_data['name']
  activity_info['distance'] = more_activity_data['distance']
  activity_info['duration'] = more_activity_data['elapsed_time']
  activity_info['type'] = more_activity_data['type']
  activity_info['start_date_local'] = more_activity_data['start_date_local']
  activity_info['location_country'] = more_activity_data['location_country']
  activity_info['description'] = more_activity_data['description']
  activity_info['calories'] = more_activity_data['calories']
  activity_info['photos'] = more_activity_data['photos']
  return activity_info 
    
def post_to_hive(athlete_id, activity_details):
  nodelist = NodeList()
  nodelist.update_nodes()
  nodes = nodelist.get_hive_nodes()
  #wif_post_key = getpass.getpass('Posting Key: ')
  # Get all the details including the posting keys
  athlete_details = hive_work.get_athlete(athlete_id, "Strava2HiveNewUserSignUp")
  print(athlete_details)
  wif = os.getenv('POSTING_KEY')
  #wif = athlete_details[6]
  hive = Hive(nodes=nodes, keys=[wif])
  author = athlete_details[1]
  distance = str(round(activity_details['distance'] * .001, 2))
  activity_type = activity_details['type'].lower()
  duration = str(round(activity_details['duration'] / 60))
  calories = activity_details['calories']
  if calories == 0:
    calories = hive_work.calc_calories(activity_type, duration)
  print("Log - Downloading images and getting details together")
  strava_screenshot(activity_details['id'])
  # Get athlete profile image
  if activity_details['photos']['primary'] == None:
    prof_image_path = '/home/circleci/project/S2HLogo.PNG'
    prof_image_name = 'S2HLogo.PNG'
    prof_image_uploader = ImageUploader(blockchain_instance=hive)
    prof_img_link = prof_image_uploader.upload(prof_image_path, "strava2hive", image_name=prof_image_name)
    # Now set up the main image
    image_path = '/home/circleci/project/image_' + str(activity_details['id']) + '.png'
    image_name = 'image_' + str(activity_details['id']) + '.png'
    image_uploader = ImageUploader(blockchain_instance=hive)
    img_link = image_uploader.upload(image_path, "strava2hive", image_name=image_name)
  else:
    profile_img = activity_details['photos']['primary']['urls']['600']
    command = 'wget ' + profile_img + ' -O prof_image_' + str(athlete_id) + '.png'
    os.system(command)
    image_path = '/home/circleci/project/prof_image_' + str(athlete_id) + '.png'
    image_name = 'prof_image_' + str(athlete_id) + '.png'
    image_uploader = ImageUploader(blockchain_instance=hive)
    #img_link = image_uploader.upload(image_path, author, image_name=image_name)
    img_link = image_uploader.upload(image_path, "strava2hive", image_name=image_name)
    # The screen shot is now at the bottom of the page
    prof_image_path = '/home/circleci/project/image_' + str(activity_details['id']) + '.png'
    prof_image_name = 'image_' + str(activity_details['id']) + '.png'
    prof_image_uploader = ImageUploader(blockchain_instance=hive)
    prof_img_link = prof_image_uploader.upload(prof_image_path, "strava2hive", image_name=prof_image_name)
  title = activity_details['name']
  hashtags, description, community =  hive_work.description_and_tags(activity_details['description'])
  body = f'''
  ![{image_name}]({img_link['url']})
  {author} just finished a {distance}km {activity_type}, that lasted for {duration} minutes.
  This {activity_type} helped {author} burn {calories} calories.
  ---
  
  **Description from Strava:**  {description}
  
  ---
  If you would like to check out this activity on strava you can see it here:
  https://www.strava.com/activities/{activity_details['id']}
  
  **About the Athlete:** *{athlete_details[2]}*
  
  ![{prof_image_name}]({prof_img_link['url']})
  
  ''' + post_functions.post_footer()
  parse_body = True
  self_vote = False
  #tags = ['exhaust', 'test', 'beta', 'runningproject', 'sportstalk']
  tags = hashtags
  beneficiaries = [{'account': 'strava2hive', 'weight': 500},]
  print("Log - Posting to Hive")
  #hive.post(title, body, author=author, tags=tags, community="hive-176853", parse_body=parse_body, self_vote=self_vote, beneficiaries=beneficiaries)
  # This is the new work with Hivesigner
  c = Client(access_token=athlete_details[6],)
  permlink = hive_work.create_permlink(activity_details['id'])
  comment = Comment(
    author,
    permlink,
    body,
    title=title,
    parent_permlink=community,
    json_metadata={"tags":tags},
  )
  comment_options = CommentOptions(
      author = author,
      permlink = permlink,
      allow_curation_rewards = True,
      allow_votes = True,
      extensions =  [[0,{"beneficiaries": [{"account": "strava2hive", "weight": 500}]}]])
  print("Log - Using Hivesigner to post")
  account_deets = Account(author, blockchain_instance=hive)
  auth = account_deets.get_blog(limit=5)
  
  broadcast_results = c.broadcast([comment.to_operation_structure(),comment_options.to_operation_structure()])
  #broadcast_results = c.broadcast([comment.to_operation_structure()])
  print(broadcast_results)
  if "error" in broadcast_results:
    print("Log - Something went wrong broadcasting with posting for:", author)
    exit()
  hive_work.new_posts_list("@" + author + "/" + permlink)
  
def strava_activity(athlete_deets):
  #athlete_details = hive_work.get_athlete(athlete_id, "Strava2HiveNewUserSignUp")
  athlete_details = athlete_deets
  # activity bearer is needed as part of the data
  print("Log - Searching For New Activities")
  bearer_header = "Bearer " + athlete_details[11]
  headers = {'Content-Type': 'application/json', 'Authorization': bearer_header}
  t = datetime.now() - timedelta(days=1)
  parameters = {"after": int(t.strftime("%s"))}
  #response = requests.get("https://www.strava.com/api/v3/athlete/activities?per_page=3", headers=headers, params=parameters )
  response = requests.get("https://www.strava.com/api/v3/athlete/activities?per_page=3", headers=headers)
  activity_data = response.json()
  if type(activity_data) is dict:
    print(activity_data)
    print("Log - It looks like there is an issue with strava authentication")
    return None
  for i in range(len(activity_data)):
    activity = activity_data[i]
    print(activity['type'])
    if activity['type'] == 'Workout':
      print("Log - Activity is not a run or ride, so we can stop running this")
      continue
    print("Log - Activity is a run or ride, now can we it has a description")
    print("Log - Now get some more detailed information")
    detailed_activity = strava_activity_details(activity['id'], bearer_header)
    print(detailed_activity)
    
    # Testing if the CSV file can be used instead of checking the api
    activity_csv = glob.glob("*.csv")
    print(activity_csv)    
    with open(activity_csv[0], "r") as fp:
      s = fp.read()
    
    if detailed_activity['description'] == None:
      print("Log - Activity does not have a description, move on")
      #break
    elif detailed_activity['description'] == '':
      print("Log - Activity does not have a description, move on")
      #break
    elif str(activity['id']) in s:
      print(datetime.now().strftime("%d-%b-%Y %H:%M:%S"), "Log - Activity is in our CSV file as already posted, move on")
    else:
      posted_val = pipedream_modules.activity_posted_api(activity['id'])
      if posted_val:
        print("Log - Activity has been posted already, move on")
      elif posted_val is False:
        print(datetime.now().strftime("%d-%b-%Y %H:%M:%S"), "Log - There was an error connecting to pipedream")
      else:
        print("Log - Activity has not been posted yet, ship it!!")   
        new_dets = detailed_activity['description'].replace('\r','')
        detailed_activity['description'] = new_dets
        print(detailed_activity['description'])
        post_to_hive(athlete_details[10], detailed_activity)
        print("Log - Add it now to the activity log")
        activity_date = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
        word = detailed_activity['description'].split()
        wcount = len(word)
        record_distance = str(round(activity['distance'] * .001, 2))
        calories = detailed_activity['calories']
        duration = str(round(detailed_activity['duration'] / 60))
        if calories == 0:
          calories = hive_work.calc_calories(activity['type'], duration)
        record_post(athlete_details[10], activity['id'], activity['type'], activity_date, record_distance, calories, wcount, athlete_details[1])
        # Work around for most recent post to be stored in Strava2HiveNewUserSignUp sheet
        hive_work.update_athlete(athlete_details[10], activity_date, "A", "Strava2HiveNewUserSignUp")
        print("Log - Activity posted so we only want one activity at a time for:", athlete_details[10])
        break

##################################################
# NG Strava2Hive Processing
##############################################################33
# Move Processing to DynamoDB

dynamoTable = 'athletes'
sheetName = 'Strava2HiveNewUserSignUp'

dynamodb = hive_work.dynamo_access()
print("Scanning table")
response = dynamodb.Table(dynamoTable).scan()

for i in response['Items']:
    print(i)

athlete_values = hive_work.get_athlete("101635754", sheetName)   
print(athlete_values)

#print("Testing and update post date")
#dynamo_date = response['Items'][0]['last_post_date']
#sheet_date = athlete_values[0]
#if dynamo_date == sheet_date:
#  print("It looks like the date is the same, so do not update")
#else:
#  print("Updating date on dynamo")
#  table = dynamodb.Table(dynamoTable)
#  response = table.update_item(
#    Key={ 'athleteId': int(athlete_values[10])},
#    UpdateExpression='SET last_post_date = :newDate',
#    ExpressionAttributeValues={':newDate': sheet_date },
#    ReturnValues="UPDATED_NEW"
#  )
  

#Start from scratch again
#1. get a list of all the athleteId's(we are doing this the easy way for now)
athlete_list = [101635754]
#2. loop through all the athleteId's
for i in athlete_list:
  print(f'Log - Working throuh activity for the user {i}')
  #	3. get the dynamo details for that athleteId
  dynamodb = hive_work.dynamo_access()
  table = dynamodb.Table(dynamoTable)
  athletedb_response = table.query(
    KeyConditionExpression=Key('athleteId').eq(i)
  )
  print(athletedb_response['Items'])
  #	4. check the last_post_date is more that 12 hours old
  last_activity_date = athletedb_response['Items'][0]['last_post_date']
  post_val = hive_work.check_last_post_date(i, last_activity_date)
  if post_val:
    print(f'Log - The last activity for the user {i} was more than 12 hours ago')
  else:
    print(f'Log - The last activity for the user {i} was NOT more than 12 hours ago')
    continue
  #	5. check if strava token has expired, refresh if not
  strava_expire_date = athletedb_response['Items'][0]['strava_token_expires']
  expire_time = int(strava_expire_date)
  current_time = time.time()
  expired_value = expire_time - int(current_time)
  if expired_value > 0:
    print(datetime.now().strftime(dt), "Log - Strava Token Still Valid")
  else:
    print(datetime.now().strftime(dt), "Log - Strava Token Needs To Be Updated")
    new_strava_access_token, new_strava_expires = hive_work.refresh_dynbamo_access_token(athlete_values)  
    print("Updating strava token on dynamo")
    table = dynamodb.Table(dynamoTable)
    response = table.update_item(
      Key={ 'athleteId': int(i)},
      UpdateExpression='SET strava_access_token = :newStravaToken',
      ExpressionAttributeValues={':newStravaToken': new_strava_access_token },
      ReturnValues="UPDATED_NEW"
    )
    print("And the strava expire date")
    response = table.update_item(
      Key={ 'athleteId': int(athlete_values[10])},
      UpdateExpression='SET strava_token_expires = :newStravaExpire',
      ExpressionAttributeValues={':newStravaExpire': new_strava_expires },
      ReturnValues="UPDATED_NEW"
    )  
    
  #	6. check if hivesigner token has expired, refresh if not
  hive_expire_date = athletedb_response['Items'][0]['hive_signer_expires']
  expire_time = int(hive_expire_date)
  current_time = time.time()
  expired_value = expire_time - int(current_time)
  if expired_value > 0:
    print("Log - Hivesigner Token Still Valid")
  else:
    print("Log - Hivesigner Token Needs To Be Updated")
    new_hive_signer_access_token, new_hive_signer_expires = hive_work.refresh_dynamo_hivesigner_token(athlete_values)
    print("Updating hivesigner token on dynamo")
    table = dynamodb.Table(dynamoTable)
    response = table.update_item(
      Key={ 'athleteId': int(athlete_values[10])},
      UpdateExpression='SET hive_signer_access_token = :newHiveToken',
      ExpressionAttributeValues={':newHiveToken': new_hive_signer_access_token },
      ReturnValues="UPDATED_NEW"
    )
    print("And the token expire date")
    response = table.update_item(
      Key={ 'athleteId': int(athlete_values[10])},
      UpdateExpression='SET hive_signer_expires = :newHiveExpire',
      ExpressionAttributeValues={':newHiveExpire': new_hive_signer_expires },
      ReturnValues="UPDATED_NEW"
    )
    
  #	7. now see if the user has had any activities
  
  print("Log - Searching For New Activities for user {i}")
  activity_data = hive_work.strava_activity_check(athletedb_response['Items'][0]['strava_access_token'])
  if type(activity_data) is dict:
    print(activity_data)
    print("Log - It looks like there is an issue with strava authentication")
    break
  
  
  for i in range(len(activity_data)):
    activity = activity_data[i]
    # a. Check if activity is a run or a ride...not a workout
    print(activity['type'])
    if activity['type'] == 'Workout':
      print("Log - Activity is not a run or ride, so we can stop running this")
      continue
    print("Log - Activity is a run or ride, now can we it has a description")
    detailed_activity = hive_work.strava_activity_details(activity['id'], athletedb_response['Items'][0]['strava_access_token'])
    
    # Testing if the CSV file can be used instead of checking the api
    activity_csv = glob.glob("*.csv")
    print(activity_csv)    
    with open(activity_csv[0], "r") as fp:
      s = fp.read()
    
    if detailed_activity['description'] == None:
      print("Log - Activity does not have a description, move on")
    elif detailed_activity['description'] == '':
      print("Log - Activity does not have a description, move on")
    elif str(activity['id']) in s:
      print("Log - Activity is in our CSV file as already posted, move on")
    else:
      posted_val = pipedream_modules.activity_posted_api(activity['id'])
      if posted_val:
        print("Log - Activity has been posted already, move on")
      elif posted_val is False:
        print("Log - There was an error connecting to pipedream")
      else:
        print("Log - Activity has not been posted yet, ship it!!")   
  
  # Activity Tests
  # b. Check if activity is a run or a ride...not a workout
  # c. Get more details information from strava
  # d. Check if the activity has a description?
  # e. Check if the activity has been posted already?
  
  
# TODO
# Need to do the refress of hivesigner and strava auth