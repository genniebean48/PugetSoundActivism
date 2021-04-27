# ACTivism Hub Web App application layer filename
# Manya Mutschler-Aldine
# Last edited: 3/22/21
# This file handles routing, SQL queries, and data manipulation
# If running on a local machine, both flask and flask-mysqldb must be installed (on CL: pip install flask,
# pip install flask--mysqldb) - see instructions.txt for more details on how to run

########################################################################################################################
##### Initial setup ####################################################################################################

from flask import Flask, request, render_template, session, redirect, jsonify
from flask_mysqldb import MySQL
import os, datetime, secrets, json, time
from werkzeug.utils import secure_filename
import smtplib, ssl, hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
# SERVER_NAME="http://activism-hub.pugetsound.edu"
# CLUB_TABLE='club'
# EVENT_TABLE='club_event'
# ADMIN_TABLE='website_admin'
# CAR_TABLE = 'rideShare_car'
# PASSENGER_TABLE = 'rideShare_passenger'
# TRACKING_TABLE = 'tracking'
#for testing
SERVER_NAME="http://localhost:5000"
CLUB_TABLE ='testClub'
EVENT_TABLE ='testClub_event'
ADMIN_TABLE ='website_admin'
CAR_TABLE = 'testRideShare_car'
PASSENGER_TABLE = 'testRideShare_passenger'
TRACKING_TABLE = 'tracking'

#salt for password hashing
salt = '1kn0wy0ulov3m3'


def printClubs():
    cursor = mysql.connection.cursor()
    cursor.execute('''SELECT * FROM %s'''%CLUB_TABLE)
    result = cursor.fetchall()
    for club in result:
        print(club)

def addAdmin():
   cursor = mysql.connection.cursor()
   cursor.execute('''INSERT INTO website_admin (web_admin_name,web_admin_email) VALUES ("Manya","manyam686@gmail.com")''')
   mysql.connection.commit()

def addManyaAdminInfo():
    cursor = mysql.connection.cursor()
    cursor.execute('''SELECT web_adminID from %s WHERE web_admin_email="manyam686@gmail.com"'''%(ADMIN_TABLE,))
    adminID=cursor.fetchall()[0]['web_adminID']
    saltedPassword = "manyapassword" + salt
    password = hashlib.sha256(saltedPassword.encode()).hexdigest()
    cursor.execute('''UPDATE %s SET password=%%s WHERE web_adminID=%%s'''%(ADMIN_TABLE,),(password,adminID,))
    mysql.connection.commit()


########################################################################################################################
##### Main pages #######################################################################################################

#Route with nothing appended (in our local machine, localhost:5000, in our server, activism-hub.pugetsound.edu)
@app.route("/")
def index(message=""):
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
   for event in events:
        #get cars for event
        cursor.execute('''SELECT * FROM %s WHERE eventID=%%s'''%(CAR_TABLE,),(event['eventID'],))
        cars = cursor.fetchall()
        #get passengers for each car
        #NOTE - possibly need to make car and passenger dicts JSON strings too
        for car in cars:
            car['depart_time_formatted']=formatTimeFromSql(car['depart_time'])
            car['return_time_formatted']=formatTimeFromSql(car['return_time'])
            cursor.execute('''SELECT * FROM %s WHERE carID=%%s'''%(PASSENGER_TABLE,),(car['carID'],))
            car['passengers'] = cursor.fetchall()
            car = json.dumps(car,default=str)
        #add JSON string of cars to event
        event['cars'] = json.dumps(cars,default=str)
        #add formatted date and times
        event['event_date_formatted']=formatDateFromSql(event['event_date'])
        event['start_time_formatted']=formatTimeFromSql(event['start_time'])
        event['end_time_formatted']=formatTimeFromSql(event['end_time'])

   stats = getStats()
   #render homepage
   return render_template("homePage.html",events=events,clubs=clubs,message=message,stats=stats)


#gets stats
def getStats():
    #Establish connection
    cursor = mysql.connection.cursor()

    #get current totals
    cursor.execute('''SELECT count(*) AS total_current_clubs FROM %s WHERE email_activated = 1''' %(CLUB_TABLE,))
    results = cursor.fetchall()[0]
    total_current_clubs = results['total_current_clubs']

    cursor.execute('''SELECT count(*) AS total_current_events FROM %s''' %(EVENT_TABLE,))
    results = cursor.fetchall()[0]
    total_current_events = results['total_current_events']

    cursor.execute('''SELECT count(*) AS total_current_cars FROM %s''' %(CAR_TABLE,))
    results = cursor.fetchall()[0]
    total_current_cars = results['total_current_cars']

    cursor.execute('''SELECT count(*) AS total_current_passengers FROM %s''' %(PASSENGER_TABLE,))
    results = cursor.fetchall()[0]
    total_current_passengers = results['total_current_passengers']

    #get overall totals
    cursor.execute('''SELECT * FROM %s WHERE trackingID = 1''' %(TRACKING_TABLE,))
    results = cursor.fetchall()[0]
    total_overall_clubs = results['total_clubs']
    total_overall_events = results['total_events']
    total_overall_cars = results['total_cars']
    total_overall_passengers = results['total_passengers']

    stats = {"total_current_clubs":total_current_clubs, "total_current_events":total_current_events,"total_current_cars":total_current_cars,
             "total_current_passengers":total_current_passengers,"total_overall_clubs":total_overall_clubs,"total_overall_events":total_overall_events,
             "total_overall_cars":total_overall_cars,"total_overall_passengers":total_overall_passengers}

    return stats

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

   stats = getStats()

   return render_template("clubPage.html",info=info,events=events,clubs=clubs,stats=stats)


########################################################################################################################
##### Login/logout #####################################################################################################

#Route when user clicks login
@app.route("/login")
def login_page(message=""):
   #sample list of dicts of clubs
   clubs = getClubs()
   stats = getStats()
   return render_template("login.html",clubs=clubs,message=message, stats=stats)


#Route when user clicks submit on login page
@app.route("/doLogin",methods=["POST"])
def do_login():
   cursor = mysql.connection.cursor()
   #get user and password
   user = request.form['Email']
   password = request.form['Password']

   #check if club email exists
   cursor.execute('''SELECT clubID, password, email_activated FROM %s WHERE club_email = %%s'''%(CLUB_TABLE,),(user,))
   result = cursor.fetchall()
   if len(result)==1:
       #get club ID and correct password
       result = result[0]
       clubID = result['clubID']
       correct_password = result['password']
       active = result['email_activated']
       #hash inputted password
       saltedPassword = password + salt
       password = hashlib.sha256(saltedPassword.encode()).hexdigest()
       #authentication
       if password == correct_password:
           if active ==1:
               #add clubID to session and reroute to homepage
               session['club_id']=clubID
               return index()
           else:
               #if club not active, reload login page
               return login_page(user+" not verified. Check your email for a verification link.")
       else:
           #if password incorrect, reload login page
           return login_page("Incorrect password.")
   else:
       #check if admin
       cursor.execute('''SELECT web_adminID, password FROM %s WHERE web_admin_email = %%s'''%(ADMIN_TABLE,),(user,))
       result = cursor.fetchall()
       if len(result)==1:
            #salt and hash their inputted password
            saltedPassword = password + salt
            password = hashlib.sha256(saltedPassword.encode()).hexdigest()
            #if passwords matches
            if password == result[0]['password']:
                session['admin_id']=result[0]['web_adminID']
                return index()
            else:
                return login_page("Incorrect password.")
       else:
            return login_page(user+" is not associated with an account.")


#Route when user clicks logout
@app.route("/logout")
def logout():
   #if club signed in
   if 'club_id' in session:
        session.pop('club_id',None)
   #if admin signed in
   else:
        session.pop('admin_id',None)
   #reroute to home page
   return index()


########################################################################################################################
##### Club Account #####################################################################################################

#Route when user clicks create account from login page
@app.route("/createAccount")
def create_account(message=""):
   #sample list of dicts of clubs
   clubs = getClubs()
   stats=getStats()
   return render_template("create-account.html",clubs=clubs,message=message,stats=stats)


#Route when user clicks submit on the create account page
@app.route("/enterAccount",methods=["POST"])
def enter_account():
   #instantiate cursor
   cursor = mysql.connection.cursor()
   #get form info
   club_email = request.form['clubEmail']
   club_name = request.form['club-name']
   about_info = request.form['club-description']
   password = request.form['password']
   club_email_display = request.form.get('club_email_display') != None
   #if email already associated with a club, display error and return
   cursor.execute('''SELECT clubID FROM %s WHERE club_email=%%s'''%(CLUB_TABLE,),(club_email,))
   emailExists = len(cursor.fetchall())>0
   #TODO - add message that email is already taken - popup?
   if emailExists:
        message = "There is already an account using "+club_email+"."
        return create_account(message)
   #hash password
   saltedPassword = password + salt
   password = hashlib.sha256(saltedPassword.encode()).hexdigest()
   #Create activation hash
   activation_hash = secrets.token_urlsafe()


   #get current time stamp
   cursor.execute('''SELECT NOW() + 0''')
   time_last_edited = cursor.fetchall()[0]['NOW() + 0']

   #Insert new account info into club table
   cursor.execute('''INSERT INTO %s(club_name,about_info,club_email,password,club_email_display,activation_hash,
       email_activated,time_last_edited) VALUES(%%s,%%s,%%s,%%s,%%s,%%s,0,%%s)'''%(CLUB_TABLE,),(club_name,about_info,club_email,password,
       club_email_display,activation_hash,time_last_edited))

   #send request for account to admin
   cursor.execute('''SELECT clubID FROM %s WHERE club_name=%%s AND club_email=%%s'''%(CLUB_TABLE,),(club_name,club_email))
   clubID=cursor.fetchall()[0]['clubID']
   requestApproval(clubID)
#    #Create text for email verification and send email
#    texts = verifyEmailText(club_email,activation_hash)
#    sendEmail(club_email,texts['html'],texts['text'],"Verify your email")
   #TODO - render page with message about sent email
   #reroute to home page
   return index('''An email has been sent to the website admin to review your request for an account. Once you are
        approved, an email will be sent to '''+club_email+ " with an verification link.")


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

    #update time stamp
    cursor.execute('''SELECT NOW() + 0''')
    time_last_edited = cursor.fetchall()[0]['NOW() + 0']

    #Put new info in database
    cursor.execute('''UPDATE %s SET club_name=%%s,about_info=%%s,meet_time=%%s,meet_day=%%s,meet_location=%%s,
                    facebook_link=%%s,instagram_link=%%s,twitter_link=%%s,website_link=%%s,club_image=%%s,
                    club_email_display=%%s,time_last_edited=%%s WHERE
                    clubID = %%s'''%(CLUB_TABLE,),(club_name,about_info,meet_time,meet_day,meet_location,
                    facebook_link,instagram_link,twitter_link,website_link,club_image,club_email_display,time_last_edited,clubID))
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

    #get a list of all the events associated with club
    cursor.execute('''SELECT eventID FROM %s where clubID = %%s'''%(EVENT_TABLE,),(clubID,))
    results = cursor.fetchall()
    for event in results:
        eventID = event['eventID']
        doDeleteEvent(eventID)

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
    facebook_event_link = request.form['facebook_link']

    #if optional fields empty, set as null
    if event_type == '':
        event_type = None
    if facebook_event_link=='':
        facebook_event_link = None
    #instantiate cursor
    cursor = mysql.connection.cursor()
    #get club name
    cursor.execute('''SELECT club_name FROM %s where clubID = %%s'''%(CLUB_TABLE,),(clubID,))
    club_name=cursor.fetchall()[0]['club_name']

    #put new event in table NOTE - does not include image
    cursor.execute('''INSERT INTO %s(event_name,club_name,clubID,event_date,start_time,end_time,event_location,
            event_description,event_type,facebook_event_link) VALUES(%%s,%%s,%%s,%%s,%%s,%%s,%%s,%%s,%%s,%%s)'''%(EVENT_TABLE,),(event_name,
            club_name,clubID,event_date,start_time,end_time,event_location,event_description,event_type,facebook_event_link))
    mysql.connection.commit()

    #update time stamp
    cursor.execute('''SELECT NOW() + 0''')
    time_last_edited = cursor.fetchall()[0]['NOW() + 0']
    cursor.execute('''UPDATE %s SET time_last_edited=%%s WHERE clubID=%%s'''%(CLUB_TABLE,),(time_last_edited,clubID))
    mysql.connection.commit()

    #increment total events for tracking
    # cursor.execute('''UPDATE %s SET total_events = total_events + 1 WHERE trackingID = 1'''%(TRACKING_TABLE,))
    # mysql.connection.commit()

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

    doDeleteEvent(eventID)

    #rerender club page
    return redirect(f"/clubPage?q={clubID}")

def doDeleteEvent(eventID):
    #instantiate cursor
    cursor = mysql.connection.cursor()

    #get a list of all cars associated with this event, go through each car and delete cars and passengers
    cursor.execute('''SELECT carID FROM %s where eventID = %%s'''%(CAR_TABLE,),(eventID,))
    results = cursor.fetchall()
    for car in results:
        carID = car['carID']
        doDeleteCar(carID)

    #delete event from database
    cursor.execute('''DELETE FROM %s WHERE eventID = %%s'''%(EVENT_TABLE,),(eventID,))
    mysql.connection.commit()

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

    #update time stamp
    cursor.execute('''SELECT NOW() + 0''')
    time_last_edited = cursor.fetchall()[0]['NOW() + 0']
    cursor.execute('''UPDATE %s SET time_last_edited=%%s WHERE clubID=%%s'''%(CLUB_TABLE,),(time_last_edited,clubID))
    mysql.connection.commit()

    #rerender club page
    return redirect(f"/clubPage?q={clubID}")

########################################################################################################################
##### Ride Sharing #####################################################################################################

#route when user clicks submit on adding a car
@app.route("/addCar",methods=["POST"])
def addCar():
    #Get which event
    eventID = request.form['eventID']

    #get form info
    driver_name = request.form['driver_name']
    driver_email = request.form['driver_email']
    num_seats_total = request.form['num_seats_total']
    num_seats_available = request.form['num_seats_total']
    depart_time = request.form['depart_time']
    return_time = request.form['return_time']
    meeting_location = request.form['meeting_location']

    #instantiate cursor
    cursor = mysql.connection.cursor()
    #add car
    cursor.execute('''INSERT INTO %s(driver_name,driver_email,num_seats_total,num_seats_available,
        depart_time,return_time,meeting_location,eventID) VALUES(%%s,%%s,%%s,%%s,%%s,%%s,%%s,%%s)'''%(CAR_TABLE,),
        (driver_name,driver_email,num_seats_total, num_seats_available,depart_time,return_time,meeting_location,eventID))
    mysql.connection.commit()

    #increment total overall cars for tracking
    # cursor.execute('''UPDATE %s SET total_cars = total_cars + 1 WHERE trackingID = 1'''%(TRACKING_TABLE,))
    # mysql.connection.commit()

    #get carID from just inserted car
    cursor.execute('''SELECT last_insert_id()''')
    results = cursor.fetchall()[0]
    carID = results['last_insert_id()']

    # Get depart_time,driver_email using carID
    cursor.execute('''SELECT depart_time,driver_email FROM %s WHERE carID = %%s''' %(CAR_TABLE,),(carID,))
    results = cursor.fetchall()[0]
    depart_time = results['depart_time']
    driver_email = results['driver_email']

    #get event_name and date using eventID
    cursor.execute('''SELECT event_name, event_date FROM %s WHERE eventID = %%s''' %(EVENT_TABLE,),(eventID,))
    results = cursor.fetchall()[0]
    event_name = results['event_name']
    date = results['event_date']

    #format date and time from SQL
    date = formatDateFromSql(date)
    depart_time = formatTimeFromSql(depart_time)

    #Notify driver that car has been added
    texts = addCarDriverText(event_name,date,depart_time)
    subject = 'Car Successfully Added!'
    sendEmail(driver_email,texts['html'],texts['text'],subject)

    #reroute to home page
    return index()

#route when user clicks delete a car
@app.route("/deleteCar")
def deleteCar():
    #Get which car
    carID = request.args.get("id")

    doDeleteCar(carID)
    #reroute to home page -- I DON'T THINK THIS IS WHAT WE WANT THO, GO BACK TO SPLIT SCREEN OF RIDES AND DESCRIPTION --
    return index()

def doDeleteCar(carID):
    #instantiate cursor
    cursor = mysql.connection.cursor()

    # Get eventID and depart_time using carID
    cursor.execute('''SELECT eventID,depart_time,driver_email FROM %s WHERE carID = %%s''' % (CAR_TABLE,),(carID,))
    results = cursor.fetchall()[0]
    eventID = results['eventID']
    depart_time = results['depart_time']
    driver_email = results['driver_email']

    #get event_name and date using eventID
    cursor.execute('''SELECT event_name, event_date FROM %s WHERE eventID = %%s''' %(EVENT_TABLE,),(eventID,))
    results = cursor.fetchall()[0]
    event_name = results['event_name']
    date = results['event_date']

    #format date and time from SQL
    date = formatDateFromSql(date)
    depart_time = formatTimeFromSql(depart_time)

    #notify driver
    texts = deleteCarDriverText(event_name,date,depart_time)
    subject = 'Your Car Has Been Deleted'
    sendEmail(driver_email,texts['html'],texts['text'],subject)

    #loop through all passengers in car and send cancellation  email
    cursor.execute('''SELECT passenger_email FROM %s WHERE carID = %%s''' % (PASSENGER_TABLE,),(carID,))
    results = cursor.fetchall()
    subject = 'Car No Longer Available'
    for passenger in results:
        passenger_email = passenger['passenger_email']
        texts = deleteCarPassText(event_name,depart_time,date)
        sendEmail(passenger_email,texts['html'],texts['text'],subject)

    #delete car and all passengers in car
    cursor.execute('''DELETE FROM %s where carID = %%s''' %(CAR_TABLE,),(carID,))
    mysql.connection.commit()

    if len(results) > 0:
        cursor.execute('''DELETE FROM %s where carID = %%s''' %(PASSENGER_TABLE,),(carID,))
    mysql.connection.commit()

#route when user clicks edit a car
@app.route("/editCar",methods=["POST"])
def editCar():
    #get which car
    carID = request.form['carID']

    #get form info
    driver_name = request.form['driver_name']
    driver_email = request.form['driver_email']
    num_seats_total = int(request.form['num_seats_total'])
    depart_time = request.form['depart_time']
    return_time = request.form['return_time']
    meeting_location = request.form['meeting_location']

    #instantiate cursor
    cursor = mysql.connection.cursor()

    # get num_seats taken
    cursor.execute('''SELECT num_seats_taken, num_seats_available FROM %s WHERE carID=%%s'''%(CAR_TABLE,),(carID,))
    results = cursor.fetchall()[0]
    num_seats_taken = results['num_seats_taken']
    num_seats_available = results['num_seats_available']

    if num_seats_taken > num_seats_total:
        # show an error and go back to unedited form?
        print("still gotta do this")
    else:
        # otherwise reset number of seat available to total - taken
        num_seats_available = num_seats_total - num_seats_taken

    #get eventID using carID
    cursor.execute('''SELECT eventID FROM %s WHERE carID = %%s''' %(CAR_TABLE,),(carID,))
    eventID = cursor.fetchall()[0]['eventID']

    #Update car
    cursor.execute('''UPDATE %s SET driver_name=%%s,driver_email=%%s,num_seats_total=%%s,num_seats_available=%%s,depart_time=%%s,return_time=%%s,
            meeting_location=%%s WHERE carID = %%s'''%(CAR_TABLE,),(driver_name,driver_email,num_seats_total,num_seats_available, depart_time,return_time,meeting_location,carID))
    mysql.connection.commit()

    #get event_name and date using eventID
    cursor.execute('''SELECT event_name, event_date FROM %s WHERE eventID = %%s''' %(EVENT_TABLE,),(eventID,))
    results = cursor.fetchall()[0]
    event_name = results['event_name']
    date = results['event_date']

    #format depart_time and return_time  from SQL
    date = formatDateFromSql(date)
    depart_time = formatTimeFromSql(depart_time)

    #Notify driver that car has been added
    texts = editCarDriverText(event_name,date,depart_time)
    subject = 'Car Successfully Edited!'
    sendEmail(driver_email,texts['html'],texts['text'],subject)

    #loop through all passengers in car and send update email
    cursor.execute('''SELECT passenger_email FROM %s WHERE carID = %%s''' % (PASSENGER_TABLE,),(carID,))
    results = cursor.fetchall()
    subject = 'Car Has Been Edited'
    for passenger in results:
        passenger_email = passenger['passenger_email']
        texts = editCarPassText(event_name,depart_time,date)
        sendEmail(passenger_email,texts['html'],texts['text'],subject)

    #reroute to home page
    return index()


#route when user clicks delete a car
@app.route("/requestCar")
def requestCar():
    #get eventID for requested car
    eventID = request.args.get("id")

    print("eventID = " + str(eventID))

    #instantiate cursor
    cursor = mysql.connection.cursor()
    #get event info and clubID
    cursor.execute('''SELECT event_name, event_date,clubID FROM %s WHERE eventID = %%s''' %(EVENT_TABLE,),(eventID,))
    results = cursor.fetchall()[0]
    event_name = results['event_name']
    date = results['event_date']
    clubID = results['clubID']

    #get club_name and club_email using clubID
    cursor.execute('''SELECT club_name,club_email FROM %s WHERE clubID = %%s''' %(CLUB_TABLE,),(clubID,))
    results = cursor.fetchall()[0]
    club_name = results['club_name']
    club_email = results['club_email']

    #Notify club that someone has requested a car for an event
    texts = carRequestText(club_name,event_name,date)
    subject = 'Car Request for Your Event'
    sendEmail(club_email,texts['html'],texts['text'],subject)

    mysql.connection.commit()
    #reroute to home page
    # -- I DON'T THINK THIS IS WHAT WE WANT THO, GO BACK TO SPLIT SCREEN OF RIDES AND DESCRIPTION --
    return index()

#route when user clicks submit on reserving a seat
@app.route("/addPassenger",methods=["POST"])
def addPassenger():
    #Get which car
    carID = request.form['carID']

    #get form info
    passenger_name = request.form['passenger_name']
    passenger_email = request.form['passenger_email']

    #instantiate cursor
    cursor = mysql.connection.cursor()
    #add passenger
    cursor.execute('''INSERT INTO %s(passenger_name,passenger_email,carID) VALUES (%%s,%%s,%%s)'''%(PASSENGER_TABLE,),(passenger_name,passenger_email,carID))
    mysql.connection.commit()

    #decrement number of available seats for specific car
    cursor.execute('''UPDATE %s SET num_seats_available = num_seats_available - 1 WHERE carId = %%s'''%(CAR_TABLE,),(carID,))
    mysql.connection.commit()
    #increment number of seats taken or specific car
    cursor.execute('''UPDATE %s SET num_seats_taken = num_seats_taken + 1 WHERE carId = %%s'''%(CAR_TABLE,),(carID,))
    mysql.connection.commit()

    #increment total passengers for tracking
    # cursor.execute('''UPDATE %s SET total_passengers = total_passengers + 1 WHERE trackingID = 1'''%(TRACKING_TABLE,))
    # mysql.connection.commit()

    # Get eventID,depart_time,driver_email using carID
    cursor.execute('''SELECT eventID,depart_time,driver_email FROM %s WHERE carID = %%s''' %(CAR_TABLE,),(carID,))
    results = cursor.fetchall()[0]
    eventID = results['eventID']
    depart_time = results['depart_time']
    driver_email = results['driver_email']

    #get event_name and date using eventID
    cursor.execute('''SELECT event_name, event_date FROM %s WHERE eventID = %%s''' %(EVENT_TABLE,),(eventID,))
    results = cursor.fetchall()[0]
    event_name = results['event_name']
    date = results['event_date']

    #format date and time from SQL
    date = formatDateFromSql(date)
    depart_time = formatTimeFromSql(depart_time)

    #Notify driver that someone has added themselves to their car
    texts = addPassengerDriverText(event_name,date,depart_time)
    subject = 'New Passenger Added to Your Car!'
    sendEmail(driver_email,texts['html'],texts['text'],subject)

    #Notify passenger that they've been added to the car
    texts = addPassengerText(event_name,date,depart_time)
    subject = 'Successfully Added to a Car!'
    sendEmail(passenger_email,texts['html'],texts['text'],subject)

    #reroute to home page -- I DON'T THINK THIS IS WHAT WE WANT THO, GO BACK TO SPLIT SCREEN OF RIDES AND DESCRIPTION --
    return index()

#route when user clicks to delete a single passenger
@app.route("/deletePassenger")
def deletePassenger():
    print("i made it!!")
    #Get passengerID
    passengerID = request.args.get("id")

    print("passengerID =" + str(passengerID))

    #instantiate cursor
    cursor = mysql.connection.cursor()

    #get carID using passengerID
    cursor.execute('''SELECT carID FROM %s WHERE passengerID = %%s''' % (PASSENGER_TABLE,),(passengerID,))
    results = cursor.fetchall()[0]
    carID = results['carID']

    #get eventID and depart_time using carID
    cursor.execute('''SELECT eventID,depart_time,driver_email FROM %s WHERE carID = %%s''' % (CAR_TABLE,),(carID,))
    results = cursor.fetchall()[0]
    eventID = results['eventID']
    depart_time = results['depart_time']

    #get event_name and date using eventID
    cursor.execute('''SELECT event_name, event_date FROM %s WHERE eventID = %%s''' %(EVENT_TABLE,),(eventID,))
    results = cursor.fetchall()[0]
    event_name = results['event_name']
    date = results['event_date']

    #format date and time from SQL
    date = formatDateFromSql(date)
    depart_time = formatTimeFromSql(depart_time)

    #send cancellation email to passenger
    cursor.execute('''SELECT passenger_email FROM %s WHERE passengerID = %%s''' % (PASSENGER_TABLE,),(passengerID,))
    results = cursor.fetchall()[0]
    passenger_email = results['passenger_email']
    subject = 'Passenger Successfully Deleted'
    texts = deletePassengerText(event_name,depart_time,date)
    sendEmail(passenger_email,texts['html'],texts['text'],subject)

    #delete passenger
    cursor.execute('''DELETE FROM %s where passengerID = %%s''' %(PASSENGER_TABLE,),(passengerID,))
    mysql.connection.commit()

    #increment number of available seats for specific car
    cursor.execute('''UPDATE %s SET num_seats_available = num_seats_available + 1 WHERE carId = %%s'''%(CAR_TABLE,),(carID,))
    mysql.connection.commit()
    #decremement number of seats taken for specific car
    cursor.execute('''UPDATE %s SET num_seats_taken = num_seats_taken - 1 WHERE carId = %%s'''%(CAR_TABLE,),(carID,))
    mysql.connection.commit()

    #reroute to home page
    return index()

#returns a dict with the html and plain text versions of adding car email
def addCarDriverText(event_name,date,time):
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               You have successfully added a car for the {event_name} event leaving on {date} at {time}.<br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        You have successfully added a car for the {event_name} event leaving on {date} at {time}.

        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}

#returns a dict with the html and plain text versions of adding passenger email -- ADD EVENT_NAME
def addPassengerDriverText(event_name,date,time):
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               A new person has been added to your car for {event_name} leaving on {date} at {time}.<br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        A new person has been added to your car for {event_name} leaving on {date} at {time}.

        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}

#returns a dict with the html and plain text versions of adding passenger email
def addPassengerText(event_name,date,time):
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               You have been added to a car for {event_name} leaving on {date} at {time}.<br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        You have been added to a car for {event_name} leaving on {date} at {time}.

        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}

#returns a dict with the html and plain text versions of deleting car send to passenger email
def deleteCarPassText(event_name,date,time):
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               The car you reserved for {event_name} leaving on {date} at {time} is no longer available.
               Please visit ACTivism Hub and check for other cars. If there are no other cars, feel free
               to a request a car and we will notify the club leader.<br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        The car you reserved for {event_name} leaving on {date} at {time} is no longer available.
        Please visit ACTivism Hub and check for other cars. If there are no other cars, feel free
        to a request a car and we will notify the club leader.

        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}

#returns a dict with the html and plain text versions of deleting car send to driver email
def deleteCarDriverText(event_name,date,time):
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               Your car for {event_name} leaving on {date} at {time} has been deleted.
               If this was a mistake, please return to ACTivism Hub and add your car again.<br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        Your car for {event_name} leaving on {date} at {time} has been deleted. If this was a mistake, please return to ACTivism Hub and add your car again.

        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}

#returns a dict with the html and plain text versions of passenger requesting car email
def carRequestText(club_name, event_name,date):
    html=f"""\
        <html>
          <body>
            <p>Hello {club_name},<br><br>
               There has been a car request made for the {event_name} event on {date}. <br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello {club_name},

        There has been a car request made for the {event_name} event leaving on {date}.

        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}

#returns a dict with the html and plain text versions of adding passenger email
def deletePassengerText(event_name,date,time):
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               You have been successfully deleted from your car for {event_name} leaving on {date} at {time}.<br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        You have been successfully deleted from your car for {event_name} leaving on {date} at {time}.<br><br>

        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}


#returns a dict with the html and plain text versions of editing car send to driver email
def editCarDriverText(event_name,date,time):
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               Your car has successfully been edited. It is scheduled to leave on {date} at {time} for {event_name}.
               If this was a mistake, please return to ACTivism Hub and change your car details.<br><br>
               Best,<br>
               The ACTivism Hub Team<br><br>
             
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        Your car has successfully been edited. It is scheduled to leave on {date} at {time} for {event_name}.
        If this was a mistake, please return to ACTivism Hub and change your car details.<br><br>
               
        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}

#returns a dict with the html and plain text versions of editing car send to passenger email
def editCarPassText(event_name,time, date):
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               A car you reserved has been edited and some details may have been changed. It is now leaving on {date} at {time} for {event_name}.
               Please visit ACTivism Hub and check that this still works with your schedule. <br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        A car you reserved has been edited and some details may have been changed. It is now leaving on {date} at {time} for {event_name}.
        Please visit ACTivism Hub and check that this still works with your schedule.
            
        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}


########################################################################################################################
##### Helper functions #################################################################################################

#Gets list of club names and IDs
def getClubs():
   cursor = mysql.connection.cursor()
   cursor.execute('''SELECT club_name, clubID FROM %s WHERE email_activated=1 ORDER BY club_name''' % (CLUB_TABLE,))
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
def formatTimeFromSql(sqlTime):

    # if time is string type
    if isinstance(sqlTime, str):
        sqlTime = sum(x * int(t) for x, t in zip([3600, 60, 1], sqlTime.split(":")))
        hours = (int)(sqlTime/3600)
        min = (int)((sqlTime/60)%60)
        if min<10:
            min='0' + str(min)
        ampm = 'AM'
        if hours>12:
            hours=hours-12
            ampm='PM'
        return str(hours)+":"+str(min)+" "+ampm

    hours = (int)(sqlTime.seconds/3600)
    min = (int)((sqlTime.seconds/60)%60)
    if min<10:
        min='0' + str(min)
    ampm = 'AM'
    if hours>12:
        hours=hours-12
        ampm='PM'
    return str(hours)+":"+str(min)+" "+ampm

########################################################################################################################
##########General Email Functions#######################################################################################

#Sends an email with the given html and plain text messages and subject to the given email
#from activismhub@gmail.com
def sendEmail(receiver_email,html_text,plain_text,subject):
    sender_email='activismhub@gmail.com'
    password = 'cscap7285!' #Need to figure out how to do this more securely

    message = MIMEMultipart('alternative')
    message['Subject']=subject
    message['From']=sender_email
    message['To']=receiver_email

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(plain_text, "plain")
    part2 = MIMEText(html_text, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part1) #plain text version, email client will render if html fails
    message.attach(part2) #html version, email client will try to render first

    # Create secure connection with server and send email
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
        server.login(sender_email, password)
        server.sendmail(
            sender_email, receiver_email, message.as_string()
        )


########################################################################################################################
########## Verifying Emails ##############################################################################################

#Returns a dict with html and plain versions of a verify password email body
def verifyEmailText(email,hash):
    link=f"{SERVER_NAME}/verifyEmail?e={email}&h={hash}"
    html=f"""\
        <html>
            <body>
                <p>Hello,<br><br>
                    Welcome to ACTivism Hub!<br>
                    Please verify your email by clicking <a href={link}>here</a>.<br><br>
                    Best,<br>
                    The ACTivism Hub Team
                </p>
            </body>
        </html>
        """
    text = f"""\
        Hello,

        Welcome to ACTivism Hub!
        Please verify your email by clicking the link below.

        Best,
        The ACTivism Hub Team

        {link}
        """
    return {'html':html,'text':text}


@app.route("/verifyEmail")
def verifyEmail():
    #email and hash from url
    club_email = request.args.get("e")
    hash = request.args.get("h")
    #get clubID and hash associated with this email from database
    cursor = mysql.connection.cursor()
    #NOTE - is it possible there would be none/more than one of this email in the db
    cursor.execute('''SELECT clubID, activation_hash, email_activated FROM %s WHERE club_email=%%s'''%(CLUB_TABLE,),(club_email,))
    r = cursor.fetchall()
    #if no account with that email
    if len(r) == 0:
        return create_account(club_email+" is not associated with an account.")
    #else get ID, hash, activation status
    results = r[0]
    clubID=results['clubID']
    db_hash = results['activation_hash']
    active = results['email_activated']
    #check if hash matches what we have stored for this email and account isn't active
    if active == 1:
        return login_page(club_email+" has already been verified.")
    if db_hash != hash:
        return create_account("Email verification failed.")
        #how to reroute here?? With popup
    #activate club
    cursor.execute('''UPDATE %s SET email_activated=1 WHERE clubID=%%s'''%(CLUB_TABLE,),(clubID,))
    mysql.connection.commit()
    #reroute to login page
    return login_page("Email verification successful.")


########################################################################################################################
########## Resetting Passwords ###########################################################################################

#When click forgot password on login page
@app.route("/forgotPassword")
def forgotPassword(message=""):
    clubs = getClubs()
    stats=getStats()
    return render_template("forgotPassword.html",clubs=clubs,message=message,stats=stats)


#When click reset password button in forgot password page
@app.route("/preparePasswordReset",methods=["POST"])
def preparePasswordReset():
   #get email from form
   club_email=request.form['club_email']
   #Get clubID for that email
   cursor = mysql.connection.cursor()
   cursor.execute('''SELECT clubID, activation_hash, club_approved FROM %s WHERE club_email=%%s'''%(CLUB_TABLE,),(club_email,))
   result = cursor.fetchall()
   #if that email isn't in the database
   if len(result) == 0:
        return forgotPassword(club_email+" is not associated with an account.")
   #check if club approved
   clubID=result[0]['clubID']
   if result[0]['club_approved']:
       #Prepare text and send email
       activation_hash = result[0]['activation_hash']
       texts = resetPasswordText(club_email,activation_hash)
       sendEmail(club_email,texts['html'],texts['text'],"Reset your password")
       #TODO - where to return when email sent? Add pop up
       return index("An email has been sent to "+club_email+" with a reset link.")
   else:
      return forgotPassword(club_email+" has not yet been approved to make an account.")


#route for link clicked in email
@app.route("/resetPassword")
def resetPassword():
    #email and hash from url
    club_email = request.args.get("e")
    hash = request.args.get("h")
    #get clubID and hash associated with this email from database
    cursor = mysql.connection.cursor()
    #NOTE - is it possible there would be none/more than one of this email in the db
    cursor.execute('''SELECT clubID, activation_hash from %s WHERE club_email=%%s'''%(CLUB_TABLE,),(club_email,))
    results = cursor.fetchall()
    #if no account with that email
    if len(results)==0:
        return create_account(club_email+" is not associated with an account.")
    #else get clubID and hash for that email
    results=results[0]
    clubID=results['clubID']
    db_hash = results['activation_hash']
    #check if hash matches what we have stored for this email and account is active
    #if passes, render a reset password page, pass in clubID
    if db_hash == hash:
        clubs = getClubs()
        stats=getStats()
        return render_template("resetPassword.html",clubs=clubs,clubID=clubID,stats=stats)
    else:
        return forgotPassword("Reset password via email failed")


#When click submit on reset password form
@app.route("/doPasswordReset",methods=["POST"])
def doPasswordReset():
    #get info from form
    password = request.form['password']
    clubID = request.form['clubID']

    cursor = mysql.connection.cursor()

    #check if club approved
    cursor.execute('''SELECT club_approved,club_email FROM %s WHERE clubID=%%s'''%(CLUB_TABLE,),(clubID,))
    result = cursor.fetchall()
    #if no club with that id
    if len(result)==0:
        return forgotPassword(result[0]['club_email']+" is not associated with an account.")
    #if club approved
    club_approved=result[0]['club_approved']
    if club_approved:
        #hash password
        saltedPassword = password + salt
        password = hashlib.sha256(saltedPassword.encode()).hexdigest()
        #update password in database, set club to active if not already (this counts as email verification)
        cursor.execute('''UPDATE %s SET password=%%s,email_activated=1 WHERE clubID=%%s'''%(CLUB_TABLE,),(password,clubID))
        mysql.connection.commit()
        #render login page
        return login_page("Password successfully reset.")
    else:
        return login_page(result[0]['club_email']+" has not yet been approved to make an account.")


#returns a dict with the html and plain text versions of a reset password email
def resetPasswordText(email,hash):
    link=f"{SERVER_NAME}/resetPassword?e={email}&h={hash}"
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               If you are not trying to reset your password on ACTivism Hub, ignore this email.<br>
               Otherwise, reset your password <a href={link}>here</a>.<br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        If you are not trying to reset your password on ACTivism Hub, ignore this email.
        Otherwise, reset your password by clicking the link below.

        Best,
        The ACTivism Hub Team

        {link}
        """
    return {'html':html,'text':text}


########################################################################################################################
##########Club Approval#################################################################################################

def requestApproval(clubID):
    #get admin email
    cursor=mysql.connection.cursor()
    cursor.execute('''SELECT web_admin_email FROM %s'''%(ADMIN_TABLE))
    #NOTE - this assumes there is one, and only gets the first one - is this what we want??
    admin_email=cursor.fetchall()[0]['web_admin_email']
    #get club info
    cursor.execute('''SELECT * FROM %s WHERE clubID=%%s'''%(CLUB_TABLE,),(clubID,))
    #Will only be called right after inserting a club, there will be an account
    club_info = cursor.fetchall()[0]
    #prepare html and plain text emails
    texts = requestApprovalTexts(club_info)
    #send email
    sendEmail(admin_email,texts['html'],texts['text'],"Approve or Deny New Club Account")


#prepares email text for email to admin when club requests an account
def requestApprovalTexts(club_info):
    approval_link=f"{SERVER_NAME}/approveClub?id={club_info['clubID']}"
    denial_link=f"{SERVER_NAME}/denyClub?id={club_info['clubID']}"
    html = f"""\
        <html>
            <body>
                <p>Hello,<br><br>
                    A new club is requesting to make an account on ACTivism Hub.<br><br>
                    Club Name: {club_info['club_name']}<br>
                    Club Email: {club_info['club_email']}<br>
                    Club Description: {club_info['about_info']}<br><br>
                    If this club puts on activism related programming,
                    please approve their request to make an account: <a href={approval_link}>Approve</a><br>
                    If not, please deny their request to make an account: <a href={denial_link}>Deny</a><br><br>
                    Best,<br>
                    The ACTivism Hub Team
                </p>
            </body>
        </html>
        """

    text = f"""\
        Hello,

        A new club is requesting to make an account on ACTivism Hub.

        Club Name: {club_info['club_name']}<br>
        Club Email: {club_info['club_email']}<br>
        Club Description: {club_info['about_info']}<br><br>

        If this club puts on activism related programming,please
        approve their request to make an account: {approval_link}
        If not, please deny their request to make an account: {denial_link}

        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}

@app.route("/approveClub")
def approveClub():
    #get clubID
    clubID=request.args.get('id')
    #set as approved
    cursor = mysql.connection.cursor()
    cursor.execute('''UPDATE %s SET club_approved=1 WHERE clubID=%%s'''%(CLUB_TABLE,),(clubID,))
    mysql.connection.commit()
    #get info for that club
    cursor.execute('''SELECT * FROM %s WHERE clubID=%%s'''%(CLUB_TABLE,),(clubID,))
    club_info = cursor.fetchall()[0]
    #send verification email
    texts = verifyEmailText(club_info['club_email'],club_info['activation_hash'])
    sendEmail(club_info['club_email'],texts['html'],texts['text'],"Verify your email")

    #increment total clubs for tracking
    # cursor.execute('''UPDATE %s SET total_clubs = total_club + 1 WHERE trackingID = 1'''%(TRACKING_TABLE,))
    # cursor.connection.commit()

    #load home page with message that club was approved
    return index(club_info['club_name']+" successfully approved. An email has been sent to the club to verify their email.")


@app.route("/denyClub")
def denyClub():
    #get clubID
    clubID=request.args.get('id')
    #check if club was already approved
    cursor = mysql.connection.cursor()
    #get info for club
    cursor.execute('''SELECT * FROM %s WHERE clubID=%%s'''%(CLUB_TABLE,),(clubID,))
    #NOTE- add check? Would only trigger if they approved club, the club deleted itself, then they clicked deny
    club_info = cursor.fetchall()[0]
    club_approved=club_info['club_approved']
    if not club_approved:
        #get admin email
        cursor.execute('''SELECT web_admin_email FROM %s'''%(ADMIN_TABLE))
        #NOTE - this assumes there is one, and only gets the first one - is this what we want??
        admin_email=cursor.fetchall()[0]['web_admin_email']
        #remove club from database
        cursor.execute('''DELETE FROM %s WHERE clubID=%%s'''%(CLUB_TABLE,),(clubID))
        cursor.connection.commit()
        #send email to club informing them of denial
        texts=clubDeniedTexts(admin_email)
        sendEmail(club_info['club_email'],texts['html'],texts['text'],"Request to make club account denied")
        #load home page with message that club was denied
        return index(club_info['club_name']+'''\'s request to make an account was denied. An email has been sent to the club
            to inform them of their denial.''')
    else:
        return index("Denial failed. "+club_info['club_name']+" was previously approved.")


#Prepares text for emails if club was denied an account
def clubDeniedTexts(admin_email):
    html=f"""\
        <html>
            <body>
                <p>
                    Hello,<br><br>
                    Your request to make an account on ACTivism Hub has been denied by the website admin.<br>
                    If you think this was a mistake or want more information, email {admin_email}.<br><br>
                    Best,<br>
                    The ACTivism Hub Team
                </p>
            </body>
        </html>
        """

    text = f"""\
        Hello,

        Your request to make an account on ACTivism Hub has been denied by the website admin.
        If you think this was a mistake or want more information, email {admin_email}.

        Best,<br>
        The ACTivism Hub Team
        """

    return {'html':html,'text':text}










