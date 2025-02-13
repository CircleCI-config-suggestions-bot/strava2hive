#!/usr/bin/env python

# This function has been set up to break out the body of the post

import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from beem.imageuploader import ImageUploader
from beem import Hive
from beem.account import Account
from beem.nodelist import NodeList

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
  driver.get_screenshot_as_file(image_name)
  driver.quit()
  os.system("ls -l")
  
def top_image(image_name, image_link):
  # Create the top image for the post
  top_image = f'''
  ![{image_name}]({image_link})
  '''
  return top_image

def activity_summary(author, distance, activity_type, duration, calories):
  # Create the top summary for the post
  act_summary = f'''
  {author} just finished a {distance}km {activity_type}, that lasted for {duration} minutes.
  This {activity_type} helped {author} burn {calories} calories.
  '''
  return act_summary
  
def post_footer():
  # Create a footer for our posts
  footer = f'''
  This is an automated post by @strava2hive and is currently in BETA.
  '''
  return footer

def zero_image_post(author, user_wif, activity_id):
  # Create images for a post with zero photos provided by user
  nodelist = NodeList()
  nodelist.update_nodes()
  nodes = nodelist.get_hive_nodes()
  wif = user_wif
  hive = Hive(nodes=nodes, keys=[wif])
  prof_image_path = '/home/circleci/project/S2HLogo.PNG'
  prof_image_name = 'S2HLogo.PNG'
  prof_image_uploader = ImageUploader(blockchain_instance=hive)
  prof_img_link = prof_image_uploader.upload(prof_image_path, author, image_name=prof_image_name)
  print(prof_img_link)
  # Now set up the main image
  image_path = '/home/circleci/project/image_' + str(activity_id) + '.png'
  image_name = 'image_' + str(activity_id) + '.png'
  image_uploader = ImageUploader(blockchain_instance=hive)
  img_link = image_uploader.upload(image_path, author, image_name=image_name)
  return image_name, img_link, prof_image_name, prof_img_link
  
