import jwt
import requests
import json
from time import time
from bs4 import BeautifulSoup
import os 
import shutil
import smtplib
from datetime import datetime

# These are the API keys for the Zoom API 
# These can be put into a variable environment file so they aren't hardcoded
API_KEY = ''
API_SEC = ''

# create a function to generate a JWT token
# using the pyjwt library
def generateToken():
    
    token = jwt.encode(
        
        # Create a payload of the token containing
        # API Key & expiration time
        {'iss': API_KEY, 'exp': time() + 5000},
        
        # Secret used to generate token signature
        API_SEC,
        
        # Specify the hashing algorithm
        #the zoom api accepts HS256
        algorithm='HS256'
    )
    #returns the newly created token used for authentication
    return token


def list_users():
    """Get a list of all users in the account.
    Any new user will be populated when the script is ran again.
    This function returns a list with these users' email and unique id.
    This function will also create a "data.json" file with the 
    list of users and all of their information.
    """
    #This is a http request header that is required for the API
    #We get the token from the generateToken() function and also specify the content type
    headers = {'authorization': 'Bearer %s' % generateToken(),
            'content-type': 'application/json'}
    #creating the request to the API using the header and the Zoom API url
    #This url must be set to "api.zoomgov.com" or it will not work
    r = requests.get(
        f'https://api.zoomgov.com/v2/users',
    headers=headers)
    
    #loading the json data into a variable
    data = json.loads(r.text)
    
    #writing the data to a file called "data.json"
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    #creating a list that store the data returned from the API
    json_data = []
    
    #adding all the user data to the list
    #this will be the same data written to data.json
    #data.json is not actually used excepted to trace the program easier when debugging
    for _ in data:
        json_data.append(data['users'])
    
    #creating a dictionary that will store the user's email and unique id
    user_list = {}
    
    #adding the user's email and unique id to the dictionary
    for i in range(len(json_data)):
        user_list[json_data[i][i]['email']] = json_data[i][i]['id']
    return user_list

def get_user_id(user_list):
    """This function will return a list of user's unique id.

    Args:
        user_list (list): list of user's unique id.

    Returns:
        list: of user's unique id.
    """
    user_id = []
    for i in user_list:
        user_id.append(user_list[i])
    return user_id
    
def get_recordings(user_id):    
    """This function takes in the user_id and will retrieve cloud recordings
    from the last 24 hours.

    Args:
        file_list (list): list of json files that hold filename data

    Returns:
        returns a list of file names that contain a users' recording data.
        The files will later be used to download the recordings via the download
        url.
        """
    #print(user_id)
    
    #List to save the name of the json files created later
    file_list = []
    
    #Loop to create a json file for each user
    #The loop itereates through the user_id list
    #"i" in this case would be the index of the user_id list
    for i in range(len(user_id)):
        #creating a http request header that is required for the API
        headers = {'authorization': 'Bearer %s' % generateToken(),
                'content-type': 'application/json'}
        #This request will retrieve the recordings from the last 24 hours.  
        #This is different from the other API resquest as it dynamically
        #changes the user_id parameter and also makes a different request
        r = requests.get(
            #this is a f string that will dynamically change the user_id parameter
            f'https://api.zoomgov.com/v2/users/{user_id[i]}/recordings',
        headers=headers)
        #loading the json data into a variable
        data = json.loads(r.text)
        
        #initializing a variable to the string "recordings.json"
        file_name = 'recordings.json'
        #concatenating the user's unique id to the string "recordings.json"
        file_name += user_id[i]
        #adding the file name to the file_list list
        file_list.append(file_name)
        
        #Writing the json data to the file created above.
        #This file name will change everytime the loop itereates
        #and will savbe the data for each user. 
        with open(file_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    return file_list

def send_email(videos):
    now = datetime.now()
    current_time = now.strftime("%H:%M:%S")
    number_of_videos = len(videos)

    gmail_user = ''
    gmail_password = ''

    sent_from = gmail_user
    to = ['', '']
    subject = 'Zoom Cloud Recording'
    body = f'The script has has completed at {current_time} and downloaded {number_of_videos} videos.'

    email_text = """\
    From: %s
    To: %s
    Subject: %s

    %s
    """ % (sent_from, ", ".join(to), subject, body)

    try:
        smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        smtp_server.ehlo()
        smtp_server.login(gmail_user, gmail_password)
        smtp_server.sendmail(sent_from, to, email_text)
        smtp_server.close()
        print ("Email sent successfully!")
    except Exception as ex:
        print ("Something went wrong….",ex)


def load_file(files):
    """This function will load the json files created in the get_recordings().
    This function ectracts the recording data from the json files and downloads
    the recordings from the "download_url" in the json files.
    
    Args:
        files (list): list of json files that hold recording data.
        
    Returns:
        Saved the recordings to the local directory or a specified directory.
        List of videos that have been saved to be used to send email verification.
    """
    
    #creating a dictionary to store the email and unique id
    user_list = list_users()
    #print(user_list)
    
    #empty list to store names of videos downloaded
    videos_downloaded = []
    
    #this is a reversed dictionary that will store the user's unique id and email
    reversed_dictionary = {value : key for (key, value) in user_list.items()}
        
    #print(reversed_dictionary)
    #print(files)
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            #get download url
            #loop through to get download url
            index = int(data['total_records'])
            #print(f"index: {index}")
            
            #loop through to get download url and other data from the json file
            for i in range(index):
                #generating a new token to be used with the download url
                token = generateToken()
                
                #NOTE: this may need tweaking in the future if other file types are added
                #This could potentailly be made more dynamic in the future
                #Checking if the recording is a mp4 file and not m4a
                if data['meetings'][i]['recording_files'][0]['file_type'] == 'mp4':
                    #grabbing the download url from the json file
                    download_url = data['meetings'][i]['recording_files'][0]['download_url']
                    #concatenating the download url with the token
                    #if the token is not added to the download url, the recording will not be downloaded
                    download_url += "?access_token=" + token
                    #print(f"download_url1: {download_url}")
                    
                else:
                    download_url = data['meetings'][i]['recording_files'][1]['download_url']
                    download_url += "?access_token=" + token
                    #print(f"download_url2: {download_url}")
                        
                #print(f"download_url3: {download_url}")
                
                #This section is mostly for naming the video file and could 
                #be made into a function in the future
                #############################################
                #getting the topic of the meeting for the filename
                topic = data['meetings'][i]['topic']
                #getting the start time of the meeting for the filename
                date = data['meetings'][i]['start_time']
                #getting the name of the user for the filename
                host_name = reversed_dictionary[data['meetings'][i]['host_id']]
                host_name = str(host_name.split('@')[0])
                #print(f"host_name: {host_name}")
                #print(date)
                #Date format for the filename and also ensuring that the time format 
                #is in the correct format for the filename IE: no colons
                date = str(date.split('Z')[0])
                date1 = str(date.split('T')[0])
                date2 = str(date.split('T')[1]).replace(':', '-')
                date = date1 + " " +  date2
                meeting_id = str(data['meetings'][i]['id'])
                #print(f"date: {date}")
                name = host_name + " " +  topic + " "  + date +  " "  + meeting_id + " " + ".mp4"
                name = str(name.replace(" ", "_"))
                #print(f"name: {name}")     
                #print(f"index: {i}")
                #file_name = f"video{i}.mp4"
                #file_name = "video" + str(i) + ".mp4"
                #############################################
                
                #adding the name of the current video being downloaded to the list
                videos_downloaded.append(name)
                
                #downloading the video using the link from the users' JSON file
                r = requests.get(download_url, stream = True)
                with open(name, 'wb') as f:
                    for chunk in r.iter_content(chunk_size = 1024*1024):
                        if chunk:
                            f.write(chunk)
                    #print ("%s downloaded!\n"%file_name)
                #print ("All videos downloaded!")
                shutil.move(name, '.\\videos')
                
    send_email(videos_downloaded)
                
   
#calling the functions that will perform the steps required to download the video
# The if call is not necessary, but is conventional syntax for scripts   
if __name__ == '__main__':
    user_list = list_users()
    user_id = get_user_id(user_list)
    files = get_recordings(user_id)
    load_file(files)
