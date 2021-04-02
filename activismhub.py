# ACTivism Hub Web App application layer filename
# Manya Mutschler-Aldine
# Last edited: 3/22/21
# This file handles routing, SQL queries, and data manipulation
# If running on a local machine, both flask and flask-mysqldb must be installed (on CL: pip install flask,
# pip install flask--mysqldb) - see instructions.txt for more details on how to run

########################################################################################################################
##### Initial setup ####################################################################################################

from flask import Flask, request, render_template, session, redirect
from flask_mysqldb import MySQL
import os, datetime
from werkzeug.utils import secure_filename

#INSTANTIATE
app = Flask(__name__)
app.secret_key = b'1234567'

#Instantiate
mysql = MySQL(app)

#Configure MySQL
app.config['MYSQL_HOST'] = 'activism-hub'
app.config['MYSQL_USER'] = 'dba'
app.config['MYSQL_PASSWORD'] = 'Password321$'
app.config['MYSQL_DB'] = 'remote_activismHub'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' #returns queries as dicts instead of default tuples

#Set start path for images - Change for whether running in server or on localhost
#for server
# IMAGE_PATH='/var/www/ActivismHub/PugetSoundActivism/static'
#for localhost
IMAGE_PATH=os.path.join(os.path.abspath(os.getcwd()),'static')

#Set tables - Change for running in server or localhost if club access is an issue
#for actually running
# CLUB_TABLE='club'
# EVENT_TABLE='club_event'
# ADMIN_TABLE='club_admin'
#for testing
CLUB_TABLE='testClub'
EVENT_TABLE='testClub_event'
ADMIN_TABLE='testClub_admin'

########################################################################################################################
##### Main pages #######################################################################################################

#Route with nothing appended (in our local machine, localhost:5000, in our server, activism-hub.pugetsound.edu)
@app.route("/")
def index():
   #Establish connection
   cursor = mysql.connection.cursor()
   #Get list of clubs and IDs
   clubs = getClubs()
   #Get events
   cursor.execute('''SELECT * FROM %s WHERE event_date > CURDATE()
                     UNION
                     SELECT * FROM %s WHERE event_date = CURDATE() AND start_time > CURTIME()
                     ORDER BY event_date, start_time''' % (EVENT_TABLE,EVENT_TABLE))
   events = cursor.fetchall()
   #add formatted date and times
   for event in events:
        event['event_date_formatted']=formatDateFromSql(event['event_date'])
        event['start_time_formatted']=formatTimeFromSql(event['start_time'])
        event['end_time_formatted']=formatTimeFromSql(event['end_time'])
   return render_template("homePage.html",events=events,clubs=clubs)


#Route when a club page is clicked
@app.route("/clubPage")
def club_page():
   #Establish connection
   cursor = mysql.connection.cursor()
   #Get which club
   clubID = request.args.get("q")
   #Get club info
   cursor.execute('''SELECT * FROM %s WHERE clubID = %%s''' %(CLUB_TABLE,),(clubID,))
   info = cursor.fetchall()[0]
   #Get events
   cursor.execute('''SELECT * FROM %s WHERE event_date > CURDATE() AND clubID=%%s
                     UNION
                     SELECT * FROM %s WHERE event_date = CURDATE() AND start_time > CURTIME() AND
                     clubID=%%s ORDER BY event_date, start_time'''%(EVENT_TABLE,EVENT_TABLE),(clubID,clubID))
   events = cursor.fetchall()
   #add formatted date and times
   for event in events:
           event['event_date_formatted']=formatDateFromSql(event['event_date'])
           event['start_time_formatted']=formatTimeFromSql(event['start_time'])
           event['end_time_formatted']=formatTimeFromSql(event['end_time'])
   #add formatted meet time
   if info['meet_time']!=None:
       info['meet_time_formatted']=formatTimeFromSql(info['meet_time'])
   #Get list of dicts of clubs
   clubs = getClubs()
   return render_template("clubPage.html",info=info,events=events,clubs=clubs)


########################################################################################################################
##### Login/logout #####################################################################################################

#Route when user clicks login
@app.route("/login")
def login_page(message=""):
   #sample list of dicts of clubs
   clubs = getClubs()
   return render_template("login.html",clubs=clubs,message=message)


#Route when user clicks submit on login page
@app.route("/doLogin",methods=["POST"])
def do_login():
   cursor = mysql.connection.cursor()
   #get user and password
   user = request.form['Email']
   password = request.form['Password']
   #check if club email exists
   cursor.execute('''SELECT EXISTS(SELECT * FROM %s WHERE club_email = %%s) AS club_exists'''%(CLUB_TABLE,),(user,))
   if cursor.fetchall()[0]['club_exists']==1:
       #get club ID and correct password
       cursor.execute('''SELECT clubID, password FROM %s where club_email = %%s'''%(CLUB_TABLE,),(user,))
       result=cursor.fetchall()[0]
       clubID = result['clubID']
       correct_password = result['password']
       #simple authentication
       if password == correct_password:
           #add clubID to session and reroute to homepage
           session['club_id']=clubID
           return index()
       else:
           #if password incorrect, reload login page
           return login_page("Incorrect password.")
   else:
       return login_page("There is no account with that email.")


#Route when user clicks logout
@app.route("/logout")
def logout():
   #remove session variable for clubID
   session.pop('club_id',None)
   #reroute to home page
   return index()


########################################################################################################################
##### Club Account #####################################################################################################

#Route when user clicks create account from login page
@app.route("/createAccount")
def create_account():
   #sample list of dicts of clubs
   clubs = getClubs()
   return render_template("create-account.html",clubs=clubs)


#Route when user clicks submit on the create account page
@app.route("/enterAccount",methods=["POST"])
def enter_account():
   #instantiate cursor
   cursor = mysql.connection.cursor()
   #get form info
   email = request.form['clubEmail']
   clubName = request.form['club-name']
   adminName = request.form['admin-name']
   description = request.form['club-description']
   adminEmail = request.form['admin-email']
   password = request.form['password']
   club_email_display = request.form.get('club_email_display') != None
   #Insert new account info into club table
   cursor.execute('''INSERT INTO %s(club_name,about_info,club_email,password,club_email_display)
       VALUES(%%s,%%s,%%s,%%s,%%s)'''%(CLUB_TABLE,),(clubName,description,email,password,club_email_display))
   mysql.connection.commit()
   #get club new club id
   cursor.execute('''SELECT clubID FROM %s where club_name = %%s'''%(CLUB_TABLE,),(clubName,))
   clubID=cursor.fetchall()[0]['clubID']
   #Insert new account info into admin table
   cursor.execute('''INSERT INTO %s(clubID,admin_name,admin_email) VALUES(%%s,%%s,%%s)'''%(ADMIN_TABLE,),
        (clubID,adminName,adminEmail))
   mysql.connection.commit()
   #reroute to home page
   return index()


#when user clicks submit on edit club page
@app.route("/updateClub",methods=["POST"])
def updateClub():
    #get which club
    clubID = session['club_id']
    #instantiate cursor
    cursor = mysql.connection.cursor()
    #get form info
    club_name = request.form['club_name']
    about_info = request.form['about_info']
    meet_time = request.form['meet_time']
    meet_day = request.form['meet_day']
    meet_location = request.form['meet_location']
    facebook_link = request.form['facebook_link']
    instagram_link = request.form['instagram_link']
    twitter_link = request.form['twitter_link']
    website_link = request.form['website_link']
    club_email_display = request.form.get('club_email_display') != None
    #for optional fields, if empty set to none
    if meet_time == '':
            meet_time = None
    if meet_day == '':
            meet_day = None
    if meet_location == '':
            meet_location = None
    if facebook_link == '':
            facebook_link = None
    if instagram_link == '':
            instagram_link = None
    if twitter_link == '':
            twitter_link = None
    if website_link == '':
            website_link = None
    #Get image from form
    image = request.files['club_image']
    #if image inputted, save and make path
    if image.filename != '':
        club_image = "club_image_"+str(clubID)+"_"+secure_filename(image.filename)
        image.save(os.path.join(IMAGE_PATH,'clubImages',club_image))
    #if no image inputted, set image as what was in the database -- NOTE change when we display image on edit
    else:
        cursor.execute('''SELECT club_image FROM %s WHERE clubID=%%s'''%(CLUB_TABLE,),(clubID,))
        club_image = cursor.fetchall()[0]['club_image']
    #Put new info in database
    cursor.execute('''UPDATE %s SET club_name=%%s,about_info=%%s,meet_time=%%s,meet_day=%%s,meet_location=%%s,
                    facebook_link=%%s,instagram_link=%%s,twitter_link=%%s,website_link=%%s,club_image=%%s,
                    club_email_display=%%s WHERE
                    clubID = %%s'''%(CLUB_TABLE,),(club_name,about_info,meet_time,meet_day,meet_location,
                    facebook_link,instagram_link,twitter_link,website_link,club_image,club_email_display,clubID))
    mysql.connection.commit()
    #Update all of that club's events to possibly new club name
    cursor.execute('''UPDATE %s SET club_name = %%s WHERE clubID = %%s'''%(EVENT_TABLE,),(club_name,clubID))
    mysql.connection.commit()
    #reroute to club page
    return redirect(f"/clubPage?q={clubID}")


#Route when user clicks delete club on edit profile page, then confirms
@app.route("/deleteClub")
def delete_club():
    #get which club
    clubID = session['club_id']
    #instantiate cursor
    cursor = mysql.connection.cursor()
    #delete all club events
    cursor.execute('''DELETE FROM %s WHERE clubID = %%s'''%(EVENT_TABLE,),(clubID,))
    mysql.connection.commit()
    #delete club from admin table
    cursor.execute('''DELETE FROM %s WHERE clubID = %%s'''%(ADMIN_TABLE,),(clubID,))
    mysql.connection.commit()
    #delete club from club table
    cursor.execute('''DELETE FROM %s WHERE clubID = %%s'''%(CLUB_TABLE,),(clubID,))
    mysql.connection.commit()
    #logout
    return logout()


########################################################################################################################
##### Events ###########################################################################################################

#route when user clicks add event from add event page
@app.route("/addEvent",methods=["POST"])
def addEvent():
    #get which club
    clubID = session['club_id']
    #get form info
    event_name = request.form['event_name']
    event_type = request.form['event-type']
    event_date = request.form['event_date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    event_location = request.form['event_location']
    event_description = request.form['event-description']
    #if optional fields empty, set as null
    if event_type == '':
        event_type = None
    #instantiate cursor
    cursor = mysql.connection.cursor()
    #get club name
    cursor.execute('''SELECT club_name FROM %s where clubID = %%s'''%(CLUB_TABLE,),(clubID,))
    club_name=cursor.fetchall()[0]['club_name']
    #put new event in table NOTE - does not include image
    cursor.execute('''INSERT INTO %s(event_name,club_name,clubID,event_date,start_time,end_time,event_location,
            event_description,event_type) VALUES(%%s,%%s,%%s,%%s,%%s,%%s,%%s,%%s,%%s)'''%(EVENT_TABLE,),(event_name,
            club_name,clubID,event_date,start_time,end_time,event_location,event_description,event_type))
    mysql.connection.commit()

    #Get image from form
    image = request.files['event_image']
    #if image inputted, save and store
    if image.filename != '':
        #get eventID
        cursor.execute('''SELECT eventID FROM %s WHERE event_name=%%s AND clubID=%%s AND
                event_date=%%s'''%(EVENT_TABLE,),(event_name,clubID,event_date))
        eventID = cursor.fetchall()[0]['eventID']
        #make image name
        event_image = "event_image_"+str(eventID)+"_"+secure_filename(image.filename)
        #save image
        image.save(os.path.join(IMAGE_PATH,'eventImages',event_image))
        #save image name in database
        cursor.execute('''UPDATE %s SET event_image=%%s WHERE eventID=%%s'''%(EVENT_TABLE,),(event_image,
            eventID))
        mysql.connection.commit()

    #rerender club page
    return redirect(f"/clubPage?q={clubID}")


#route when user clicks delete on event on club page
@app.route("/deleteEvent")
def deleteEvent():
    #Get which event
    eventID = request.args.get("q")
    #get which club
    clubID = session['club_id']
    #instantiate cursor
    cursor = mysql.connection.cursor()
    #delete from database
    cursor.execute('''DELETE FROM %s WHERE eventID = %%s'''%(EVENT_TABLE,),(eventID,))
    mysql.connection.commit()
    #rerender club page
    return redirect(f"/clubPage?q={clubID}")


#route when user clicks submit on edit event
@app.route("/updateEvent",methods=["POST"])
def updateEvent():
    #get which club
    clubID = session['club_id']
    #get which event
    eventID = request.form['eventID']
    #get form info
    event_name = request.form['event_name']
    event_type = request.form['event_type']
    event_date = request.form['event_date']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    event_location = request.form['event_location']
    event_description = request.form['event_description']
    #if optional fields empty, set as null
    if event_type == '':
        event_type = None
    #instantiate cursor
    cursor = mysql.connection.cursor()
    #get image from form
    image = request.files['event_image']
    #if image inputted, save and make path
    if image.filename != '':
        event_image = "event_image_"+str(eventID)+"_"+secure_filename(image.filename)
        image.save(os.path.join(IMAGE_PATH,'eventImages',event_image))
    #if no image inputted, set image as what was in the database -- NOTE change when we display image on edit
    else:
        cursor.execute('''SELECT event_image FROM %s WHERE eventID=%%s'''%(EVENT_TABLE,),(eventID,))
        event_image = cursor.fetchall()[0]['event_image']
    #Update event
    cursor.execute('''UPDATE %s SET event_name=%%s,event_date=%%s,start_time=%%s,end_time=%%s,event_location=%%s,
            event_description=%%s,event_type=%%s,event_image=%%s WHERE eventID=%%s'''%(EVENT_TABLE,),(event_name,
            event_date,start_time,end_time,event_location,event_description,event_type,event_image,eventID))
    mysql.connection.commit()

    #rerender club page
    return redirect(f"/clubPage?q={clubID}")


########################################################################################################################
##### Helper functions #################################################################################################

#Gets list of club names and IDs
def getClubs():
   cursor = mysql.connection.cursor()
   cursor.execute('''SELECT club_name, clubID FROM %s''' % (CLUB_TABLE,))
   return cursor.fetchall()


#formats date
def formatDateFromSql(sqlDate):
    months = ['January','February','March','April','May','June','July',
        'August','September','October','November','December']
    year = sqlDate.year
    month = sqlDate.month
    day = sqlDate.day
    return months[month-1]+" "+str(day)+", "+str(year)


#formats times
def formatTimeFromSql(time):
    hours = (int)(time.seconds/3600)
    min = (int)((time.seconds/60)%60)
    if min==0:
        min='00'
    ampm = 'AM'
    if hours>12:
        hours=hours-12
        ampm='PM'
    return str(hours)+":"+str(min)+" "+ampm


