# ACTivism Hub Web App application layer
# Manya Mutschler-Aldine
# Last edited: 1/16/2022
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

#Instantiate mysql instance
mysql = MySQL(app)

#Configure MySQL
app.config['MYSQL_HOST'] = 'us-cdbr-east-04.cleardb.com'
app.config['MYSQL_USER'] = 'b23619ece5cddb'
app.config['MYSQL_PASSWORD'] = '5872b43e'
app.config['MYSQL_DB'] = 'heroku_3a423214d0c6425'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor' #returns queries as dicts instead of default tuples

#Set start path for images
IMAGE_PATH=os.path.join(os.path.abspath(os.getcwd()),'static')

#Set tables
SERVER_NAME="http://pugetsoundactivism.com"
CLUB_TABLE='club'
EVENT_TABLE='club_event'
ADMIN_TABLE='website_admin'
CAR_TABLE = 'rideshare_car'
PASSENGER_TABLE = 'rideshare_passenger'
TRACKING_TABLE = 'tracking'
CAR_REQUEST_TABLE = 'car_request'

#salt for password hashing
salt = '1kn0wy0ulov3m3'

#Password for email
EMAIL_PASSWORD='CSCapstone2021'


########################################################################################################################
##### Main pages #######################################################################################################

# Home page (route with nothing appended)
@app.route("/")
def index(message=""):
   #Establish database connection
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
        for car in cars:
            #format times
            car['depart_time_formatted']=formatTimeFromSql(car['depart_time'])
            car['return_time_formatted']=formatTimeFromSql(car['return_time'])
            #get passengers
            cursor.execute('''SELECT * FROM %s WHERE carID=%%s'''%(PASSENGER_TABLE,),(car['carID'],))
            car['passengers'] = cursor.fetchall()
            car = json.dumps(car,default=str)
        #add JSON string of cars to event
        event['cars'] = json.dumps(cars,default=str)
        #add formatted event date and times
        event['event_date_formatted']=formatDateFromSql(event['event_date'])
        event['start_time_formatted']=formatTimeFromSql(event['start_time'])
        event['end_time_formatted']=formatTimeFromSql(event['end_time'])

   #Get website stats and admin info
   stats = getStats()
   admin = getAdmin()

   #render homepage
   return render_template("homePage.html",events=events,clubs=clubs,message=message,stats=stats,admin=admin)


# Club page (route with /clubPage appended)
@app.route("/clubPage")
def club_page(message=""):
   #Establish database connection
   cursor = mysql.connection.cursor()
   #Get which club we are pulling up the page for
   clubID = request.args.get("q")
   #Get that club's info
   cursor.execute('''SELECT * FROM %s WHERE clubID = %%s''' %(CLUB_TABLE,),(clubID,))
   info = cursor.fetchall()[0]

   #Get that club's events
   cursor.execute('''SELECT * FROM %s WHERE event_date > CURDATE() AND clubID=%%s
                     UNION
                     SELECT * FROM %s WHERE event_date = CURDATE() AND start_time > CURTIME() AND
                     clubID=%%s ORDER BY event_date, start_time'''%(EVENT_TABLE,EVENT_TABLE),(clubID,clubID))
   events = cursor.fetchall()
   #add formatted event date and times
   for event in events:
           event['event_date_formatted']=formatDateFromSql(event['event_date'])
           event['start_time_formatted']=formatTimeFromSql(event['start_time'])
           event['end_time_formatted']=formatTimeFromSql(event['end_time'])

   #add formatted meet time
   if info['meet_time']!=None:
       info['meet_time_formatted']=formatTimeFromSql(info['meet_time'])

   #add formatted last edited time
   if info['time_last_edited']!=None:
       info['time_last_edited_formatted']=str(info['time_last_edited'])

   #check if club name ends in s
   if info['club_name'][-1:]=='s':
        info['end_s']=True
   else:
        info['end_s']=False

   #Get club list, website stats, and admin info
   clubs = getClubs()
   stats = getStats()
   admin = getAdmin()

   #render club page
   return render_template("clubPage.html",info=info,events=events,clubs=clubs,stats=stats,admin=admin,message=message)


########################################################################################################################
##### Login/logout #####################################################################################################

#Login page (route when user clicks login on menu bar)
@app.route("/login")
def login_page(message=""):
   #Get club list, website stats, admin info
   clubs = getClubs()
   stats = getStats()
   admin = getAdmin()
   #render login page
   return render_template("login.html",clubs=clubs,message=message,stats=stats,admin=admin)


#Route when user clicks submit on login page
@app.route("/doLogin",methods=["POST"])
def do_login():
   cursor = mysql.connection.cursor()
   #get user and password
   user = request.form['Email']
   password = request.form['Password']

   #check if club email is associated with an account
   cursor.execute('''SELECT clubID, password, email_activated FROM %s WHERE club_email = %%s'''%(CLUB_TABLE,),(user,))
   result = cursor.fetchall()

   # If email has an account
   if len(result)==1:
       #get club ID, correct password, activation status
       result = result[0]
       clubID = result['clubID']
       correct_password = result['password']
       active = result['email_activated']
       #hash inputted password
       saltedPassword = password + salt
       password = hashlib.sha256(saltedPassword.encode()).hexdigest()

       # If inputted password is correct
       if password == correct_password:
           if active ==1:
               #if club activated, add clubID to session and reroute to homepage
               session['club_id']=clubID
               return index()
           else:
               #if club not active, reload login page
               return login_page(user+" not verified. Check your email for a verification link.")
       else:
           #if password incorrect, reload login page
           return login_page("Incorrect password.")

   # If email not associated with a club account
   else:
       #check if admin
       cursor.execute('''SELECT web_adminID, password, email_activated FROM %s WHERE web_admin_email = %%s'''%(ADMIN_TABLE,),(user,))
       result = cursor.fetchall()
       # If admin account
       if len(result)==1:
            #salt and hash their inputted password
            saltedPassword = password + salt
            password = hashlib.sha256(saltedPassword.encode()).hexdigest()
            #if password is correct
            if password == result[0]['password']:
                #if admin activated, login and render home page
                if result[0]['email_activated']==1:
                    session['admin_id']=result[0]['web_adminID']
                    return index()
                else:
                    #if admin not active, reload login page with error message
                    return login_page(user+" is not verified. Check your email for a verification link.")

            else:
                # If password incorrect, rerender login page with error message
                return login_page("Incorrect password.")

       #If email is neither a club nor an admin account
       else:
            # Rerender login page with error message
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

# Create account page (route when user clicks create account from login page)
@app.route("/createAccount")
def create_account(message=""):
   #Get club list, website stats, admin info
   clubs = getClubs()
   stats = getStats()
   admin = getAdmin()
   #Render create account page
   return render_template("create-account.html",clubs=clubs,message=message,stats=stats,admin=admin)


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

   #if email already associated with a club, rerender create account page with error message
   cursor.execute('''SELECT clubID FROM %s WHERE club_email=%%s'''%(CLUB_TABLE,),(club_email,))
   emailExists = len(cursor.fetchall())>0
   if emailExists:
        message = "There is already an account using "+club_email+"."
        return create_account(message)

   #hash password
   saltedPassword = password + salt
   password = hashlib.sha256(saltedPassword.encode()).hexdigest()

   #Create activation hash
   activation_hash = secrets.token_urlsafe()

   #get current time stamp
   cursor.execute('''SELECT NOW()''')
   time_last_edited = cursor.fetchall()[0]['NOW()']

   #Insert new account info into club table
   cursor.execute('''INSERT INTO %s(club_name,about_info,club_email,password,club_email_display,activation_hash,
       email_activated,time_last_edited) VALUES(%%s,%%s,%%s,%%s,%%s,%%s,0,%%s)'''%(CLUB_TABLE,),(club_name,about_info,club_email,password,
       club_email_display,activation_hash,time_last_edited))
   mysql.connection.commit()

   #send request for account to admin
   cursor.execute('''SELECT clubID FROM %s WHERE club_name=%%s AND club_email=%%s'''%(CLUB_TABLE,),(club_name,club_email))
   clubID=cursor.fetchall()[0]['clubID']
   requestApproval(clubID)

   #reroute to home page
   return index('''An email has been sent to the website admin to review your request for an account. Once you are
        approved, an email will be sent to '''+club_email+ " with a verification link.")


#Route when user clicks submit on edit club page
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
    club_email = request.form['club_email']
    old_club_email = request.form['old_club_email']

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


    #update time stamp
    cursor.execute('''SELECT NOW()''')
    time_last_edited = cursor.fetchall()[0]['NOW()']

    #Put new info in database
    cursor.execute('''UPDATE %s SET club_name=%%s,about_info=%%s,meet_time=%%s,meet_day=%%s,meet_location=%%s,
                    facebook_link=%%s,instagram_link=%%s,twitter_link=%%s,website_link=%%s,
                    club_email_display=%%s,time_last_edited=%%s WHERE
                    clubID = %%s'''%(CLUB_TABLE,),(club_name,about_info,meet_time,meet_day,meet_location,
                    facebook_link,instagram_link,twitter_link,website_link,club_email_display,time_last_edited,clubID))
    mysql.connection.commit()

    #Update club name on all of that club's events (in case club name changed)
    cursor.execute('''UPDATE %s SET club_name = %%s WHERE clubID = %%s'''%(EVENT_TABLE,),(club_name,clubID))
    mysql.connection.commit()

    #if email changed, send verification email
    if club_email != old_club_email:
        #change activation hash
        activation_hash = secrets.token_urlsafe()
        cursor.execute('''UPDATE %s SET activation_hash=%%s WHERE clubID=%%s'''%(CLUB_TABLE,),(activation_hash,clubID))
        mysql.connection.commit()
        #send verification email
        texts=verifyEmailText(clubID,activation_hash,0,club_email)
        sendEmail(club_email,texts['html'],texts['text'],"Verify your email")
        return index("An email has been sent to "+club_email+" with a verification link.")
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
    #Delete all of that club's events
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
    facebook_event_link = request.form['facebook_event_link']
    event_virtual = request.form.get('event_virtual') != None

    #if optional fields empty, set as none
    if event_type == '':
        event_type = None
    if facebook_event_link=='':
        facebook_event_link = None

    #instantiate cursor
    cursor = mysql.connection.cursor()
    #get club name
    cursor.execute('''SELECT club_name FROM %s where clubID = %%s'''%(CLUB_TABLE,),(clubID,))
    club_name=cursor.fetchall()[0]['club_name']
    #update time stamp
    cursor.execute('''SELECT NOW()''')
    time_last_edited = cursor.fetchall()[0]['NOW()']
    #put new event in table
    cursor.execute('''INSERT INTO %s(event_name,club_name,clubID,event_date,start_time,end_time,event_location,
            event_description,event_type,facebook_event_link,event_virtual) VALUES(%%s,%%s,%%s,%%s,%%s,
            %%s,%%s,%%s,%%s,%%s,%%s)'''%(EVENT_TABLE,),(event_name,club_name,clubID,event_date,start_time,end_time,
            event_location,event_description,event_type,facebook_event_link,event_virtual))
    mysql.connection.commit()
    #Update club time last active
    cursor.execute('''UPDATE %s SET time_last_edited=%%s WHERE clubID=%%s'''%(CLUB_TABLE,),(time_last_edited,clubID))
    mysql.connection.commit()

    #increment total events for tracking
    cursor.execute('''UPDATE %s SET total_events = total_events + 1 WHERE trackingID = 1'''%(TRACKING_TABLE,))
    mysql.connection.commit()


    #rerender club page
    return redirect(f"/clubPage?q={clubID}")


# Route when user clicks submit on edit event form
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
    facebook_event_link = request.form['facebook_event_link']
    event_virtual = request.form.get('event_virtual') != None

    #if optional fields empty, set as null
    if event_type == '':
        event_type = None
    if facebook_event_link=='':
        facebook_event_link = None

    #instantiate cursor
    cursor = mysql.connection.cursor()

    #Update event
    cursor.execute('''UPDATE %s SET event_name=%%s,event_date=%%s,start_time=%%s,end_time=%%s,event_location=%%s,
            event_description=%%s,event_type=%%s,facebook_event_link=%%s,event_virtual=%%s WHERE eventID=%%s'''%(EVENT_TABLE,),(event_name,
            event_date,start_time,end_time,event_location,event_description,event_type,facebook_event_link,event_virtual,eventID))
    mysql.connection.commit()

    #update time stamp
    cursor.execute('''SELECT NOW()''')
    time_last_edited = cursor.fetchall()[0]['NOW()']
    cursor.execute('''UPDATE %s SET time_last_edited=%%s WHERE clubID=%%s'''%(CLUB_TABLE,),(time_last_edited,clubID))
    mysql.connection.commit()

    #rerender club page
    return redirect(f"/clubPage?q={clubID}")


#Route when user clicks delete on event on club page and confirms
@app.route("/deleteEvent")
def deleteEvent():
    #Get which event
    eventID = request.args.get("q")
    #get which club
    clubID = session['club_id']
    #Delete event
    doDeleteEvent(eventID)
    #rerender club page
    return redirect(f"/clubPage?q={clubID}")


# Deletes the event with the specified ID
def doDeleteEvent(eventID):
    #instantiate cursor
    cursor = mysql.connection.cursor()

    #get a list of all cars associated with this event
    cursor.execute('''SELECT carID FROM %s where eventID = %%s'''%(CAR_TABLE,),(eventID,))
    results = cursor.fetchall()
    if len(results) > 0:
        #For each car, delete the car and all passengers
        for car in results:
            carID = car['carID']
            doDeleteCar(carID)

    #delete event from database
    cursor.execute('''DELETE FROM %s WHERE eventID = %%s'''%(EVENT_TABLE,),(eventID,))
    mysql.connection.commit()


#Route when admin clicks to delete all old events on club page
@app.route("/deleteOldEvents")
def deleteOldEvents():
    #instantiate cursor
    cursor = mysql.connection.cursor()
    #get a list of all past events
    cursor.execute('''SELECT * FROM %s WHERE event_date < NOW() '''%(EVENT_TABLE,))
    results = cursor.fetchall()
    if len(results) > 0:
        #Delete all events in list
        for event in results:
            eventID = event['eventID']
            doDeleteEvent(eventID)
    #Rerender home page
    return index()


########################################################################################################################
##### Ride Sharing #####################################################################################################

#route when user clicks submit on adding a car
@app.route("/addCar",methods=["POST"])
def addCar():
    #get form info
    eventID = request.form['eventID']
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

    #get carID
    cursor.execute('''SELECT last_insert_id()''')
    results = cursor.fetchall()[0]
    carID = results['last_insert_id()']

    #get event name and date using eventID
    cursor.execute('''SELECT event_name, event_date FROM %s WHERE eventID = %%s''' %(EVENT_TABLE,),(eventID,))
    results = cursor.fetchall()[0]
    event_name = results['event_name']
    date = results['event_date']

    #format date and time from SQL
    date = formatDateFromSql(date)
    depart_time = formatTimeFromSql(depart_time)
    return_time=formatTimeFromSql(return_time)

    #Notify driver that car has been added
    texts = addCarDriverText(event_name,date,depart_time,return_time,meeting_location)
    subject = 'Car Successfully Added!'
    sendEmail(driver_email,texts['html'],texts['text'],subject)

    #increment total overall cars for tracking
    cursor.execute('''UPDATE %s SET total_cars = total_cars + 1 WHERE trackingID = 1'''%(TRACKING_TABLE,))
    mysql.connection.commit()

    #If there are car requests for this event, add them to car
    cursor.execute('''SELECT * FROM %s WHERE eventID=%%s AND completed=%%s'''%(CAR_REQUEST_TABLE,),(eventID,False))
    carRequests = cursor.fetchall()
    while len(carRequests)>0:
        carRequest = carRequests[0]
        #Atomically check if request has already been added to a car
        cursor.execute('''UPDATE %s SET completed = IF(completed, completed, True) WHERE requestID=%%s'''%
            (CAR_REQUEST_TABLE,),(carRequest['requestID'],))
        mysql.connection.commit()
        if cursor.rowcount!=0:
            #Atomically check that their is an available seat and decrement available seats by 1
            cursor.execute('''UPDATE %s SET num_seats_available = IF(num_seats_available > 0, num_seats_available - 1,
                num_seats_available) WHERE carID = %%s'''%(CAR_TABLE,),(carID,))
            mysql.connection.commit()
            #If there was a seat available
            if cursor.rowcount!=0:
                #Delete from car request table
                cursor.execute('''DELETE FROM %s WHERE requestID=%%s'''%(CAR_REQUEST_TABLE,),(carRequest['requestID'],))
                mysql.connection.commit()
                #add passenger
                cursor.execute('''INSERT INTO %s(passenger_name,passenger_email,carID) VALUES (%%s,%%s,%%s)'''%(PASSENGER_TABLE,),
                    (carRequest['passenger_name'],carRequest['passenger_email'],carID))
                mysql.connection.commit()

                #increment total passengers for tracking
                cursor.execute('''UPDATE %s SET total_passengers = total_passengers + 1 WHERE trackingID = 1'''%(TRACKING_TABLE,))
                mysql.connection.commit()

                # Get eventID,depart_time,driver_email using carID
                cursor.execute('''SELECT eventID,depart_time,return_time,driver_email,meeting_location FROM %s WHERE carID = %%s''' %(CAR_TABLE,),(carID,))
                results = cursor.fetchall()[0]
                eventID = results['eventID']
                depart_time = results['depart_time']
                return_time = results['return_time']
                driver_email = results['driver_email']
                meeting_location=results['meeting_location']

                #get event_name and date using eventID
                cursor.execute('''SELECT event_name, event_date FROM %s WHERE eventID = %%s''' %(EVENT_TABLE,),(eventID,))
                results = cursor.fetchall()[0]
                event_name = results['event_name']
                date = results['event_date']

                #format date and time from SQL
                date = formatDateFromSql(date)
                depart_time = formatTimeFromSql(depart_time)
                return_time = formatTimeFromSql(return_time)

                #Notify passenger that they've been added to the car
                texts = addPassengerText(event_name,date,depart_time,return_time,meeting_location)
                subject = 'Successfully Added to a Car!'
                sendEmail(carRequest['passenger_email'],texts['html'],texts['text'],subject)
            else:
                cursor.execute('''UPDATE %s SET completed=False WHERE requestID=%%s'''%(CAR_REQUEST_TABLE,),(carRequest['requestID'],))
                mysql.connection.commit()
                break
        #Re-query to see if more requests
        cursor.execute('''SELECT * FROM %s WHERE eventID=%%s AND completed=%%s'''%(CAR_REQUEST_TABLE,),(eventID,False))
        carRequests = cursor.fetchall()

    #reroute to home page
    return index()


#route when user clicks delete on a car and confirms
@app.route("/deleteCar")
def deleteCar():
    #Get which car
    carID = request.args.get("id")
    #Delete car
    doDeleteCar(carID)
    #reroute to home page
    return index()


#Deletes car with the given ID
def doDeleteCar(carID):
    #instantiate cursor
    cursor = mysql.connection.cursor()

    # Get eventID and depart_time using carID
    cursor.execute('''SELECT eventID,depart_time,driver_email FROM %s WHERE carID = %%s''' % (CAR_TABLE,),(carID,))
    results = cursor.fetchall()[0]
    eventID = results['eventID']
    depart_time = results['depart_time']
    driver_email = results['driver_email']

    #get event name and date using eventID
    cursor.execute('''SELECT event_name, event_date FROM %s WHERE eventID = %%s''' %(EVENT_TABLE,),(eventID,))
    results = cursor.fetchall()[0]
    event_name = results['event_name']
    date = results['event_date']

    #format date and time from SQL
    date = formatDateFromSql(date)
    depart_time = formatTimeFromSql(depart_time)

    #notify driver
    texts = deleteCarDriverText(event_name,date,depart_time)
    subject = 'Your Car For '+event_name+' Has Been Deleted'
    sendEmail(driver_email,texts['html'],texts['text'],subject)

    #loop through all passengers in car and send cancellation email
    cursor.execute('''SELECT passenger_email FROM %s WHERE carID = %%s''' % (PASSENGER_TABLE,),(carID,))
    results = cursor.fetchall()
    subject = 'Car For '+event_name+' No Longer Available'
    texts = deleteCarPassText(event_name,depart_time,date)
    if len(results) > 0:
        for passenger in results:
            passenger_email = passenger['passenger_email']
            sendEmail(passenger_email,texts['html'],texts['text'],subject)
        #Delete passengers
        cursor.execute('''DELETE FROM %s where carID = %%s''' %(PASSENGER_TABLE,),(carID,))
        mysql.connection.commit()

    #delete car
    cursor.execute('''DELETE FROM %s where carID = %%s''' %(CAR_TABLE,),(carID,))
    mysql.connection.commit()


#Route when user clicks edit on a car
@app.route("/editCar",methods=["POST"])
def editCar():
    #get form info
    carID = request.form['carID']
    driver_name = request.form['driver_name']
    driver_email = request.form['driver_email']
    depart_time = request.form['depart_time']
    return_time = request.form['return_time']
    meeting_location = request.form['meeting_location']

    #instantiate cursor
    cursor = mysql.connection.cursor()

    #Update car
    cursor.execute('''UPDATE %s SET driver_name=%%s,driver_email=%%s,depart_time=%%s,return_time=%%s,
            meeting_location=%%s WHERE carID = %%s'''%(CAR_TABLE,),(driver_name,driver_email,depart_time,return_time,meeting_location,carID))
    mysql.connection.commit()

    #get eventID
    cursor.execute('''SELECT eventID FROM %s WHERE carID = %%s''' %(CAR_TABLE,),(carID,))
    eventID = cursor.fetchall()[0]['eventID']
    #get event name and date
    cursor.execute('''SELECT event_name, event_date FROM %s WHERE eventID = %%s''' %(EVENT_TABLE,),(eventID,))
    results = cursor.fetchall()[0]
    event_name = results['event_name']
    date = results['event_date']

    #format depart_time and return_time  from SQL
    date = formatDateFromSql(date)
    depart_time = formatTimeFromSql(depart_time)
    return_time = formatTimeFromSql(return_time)

    #Notify driver that car has been updated
    texts = editCarDriverText(event_name,date,depart_time,return_time,meeting_location)
    subject = 'Car For '+event_name+' Successfully Edited!'
    sendEmail(driver_email,texts['html'],texts['text'],subject)

    #loop through all passengers in car and send update email
    cursor.execute('''SELECT passenger_email FROM %s WHERE carID = %%s''' % (PASSENGER_TABLE,),(carID,))
    results = cursor.fetchall()
    subject = 'Car For '+event_name+' Has Been Edited'
    texts = editCarPassText(event_name,depart_time,return_time,meeting_location,date)
    for passenger in results:
        passenger_email = passenger['passenger_email']
        sendEmail(passenger_email,texts['html'],texts['text'],subject)

    #reroute to home page
    return index()


#Route when someone clicks submit on the request car form
#Adds the requester to a wait list
@app.route("/requestCar",methods=['POST'])
def requestCar():
    #Get which event
    eventID = request.form['eventID']

    #get form info
    passenger_name = request.form['passenger_name']
    passenger_email = request.form['passenger_email']

    #instantiate cursor
    cursor = mysql.connection.cursor()
    #Add car request to database
    cursor.execute('''INSERT INTO %s(passenger_name,passenger_email,eventID,completed) VALUES(%%s,%%s,%%s,%%s)'''
        %(CAR_REQUEST_TABLE,),(passenger_name,passenger_email,eventID,False))
    mysql.connection.commit()

    #reroute to home page
    return index("Request form submitted! When a new car is added, you will automatically be added as a passenger and receive a confirmation email.")



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

    #Atomically check that their is an available seat and decrement available seats by 1
    cursor.execute('''UPDATE %s SET num_seats_available = IF(num_seats_available > 0, num_seats_available - 1,
        num_seats_available) WHERE carID = %%s'''%(CAR_TABLE,),(carID,))
    mysql.connection.commit()
    #If there was a seat available
    if cursor.rowcount!=0:
        #add passenger
        cursor.execute('''INSERT INTO %s(passenger_name,passenger_email,carID) VALUES (%%s,%%s,%%s)'''%(PASSENGER_TABLE,),
            (passenger_name,passenger_email,carID))
        mysql.connection.commit()

        #increment total passengers for tracking
        cursor.execute('''UPDATE %s SET total_passengers = total_passengers + 1 WHERE trackingID = 1'''%(TRACKING_TABLE,))
        mysql.connection.commit()

        # Get eventID,depart_time,driver_email using carID
        cursor.execute('''SELECT eventID,depart_time,return_time,driver_email,meeting_location FROM %s WHERE carID = %%s''' %(CAR_TABLE,),(carID,))
        results = cursor.fetchall()[0]
        eventID = results['eventID']
        depart_time = results['depart_time']
        return_time = results['return_time']
        driver_email = results['driver_email']
        meeting_location=results['meeting_location']

        #get event_name and date using eventID
        cursor.execute('''SELECT event_name, event_date FROM %s WHERE eventID = %%s''' %(EVENT_TABLE,),(eventID,))
        results = cursor.fetchall()[0]
        event_name = results['event_name']
        date = results['event_date']

        #format date and time from SQL
        date = formatDateFromSql(date)
        depart_time = formatTimeFromSql(depart_time)
        return_time = formatTimeFromSql(return_time)

        #Notify passenger that they've been added to the car
        texts = addPassengerText(event_name,date,depart_time,return_time,meeting_location)
        subject = 'Successfully Added to a Car!'
        sendEmail(passenger_email,texts['html'],texts['text'],subject)

        #reroute to home page
        return index("You have been successfully added to a car! A confirmation email has been sent to the address you provided.")
    else:
        return index("Sorry! The car you have tried to reserve a seat in has no available seats.")


#route when user clicks to delete a single passenger
@app.route("/deletePassenger")
def deletePassenger():
    #Get passengerID
    passengerID = request.args.get("id")

    #instantiate cursor
    cursor = mysql.connection.cursor()

    #get carID using passengerID
    cursor.execute('''SELECT carID,passenger_email FROM %s WHERE passengerID = %%s''' % (PASSENGER_TABLE,),(passengerID,))
    results = cursor.fetchall()[0]
    carID = results['carID']
    passenger_email=results['passenger_email']

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
    subject = 'Passenger Successfully Deleted'
    texts = deletePassengerText(event_name,depart_time,date)
    sendEmail(passenger_email,texts['html'],texts['text'],subject)

    #delete passenger
    cursor.execute('''DELETE FROM %s where passengerID = %%s''' %(PASSENGER_TABLE,),(passengerID,))
    mysql.connection.commit()

    #increment number of available seats
    cursor.execute('''UPDATE %s SET num_seats_available = num_seats_available + 1 WHERE carId = %%s'''%(CAR_TABLE,),(carID,))
    mysql.connection.commit()

    #reroute to home page
    return index()


#returns a dict with the html and plain text versions of adding car email
def addCarDriverText(event_name,date,depart_time,return_time,meeting_location):
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               You have successfully added a car for {event_name} leaving on {date} at {depart_time}<br>
               from {meeting_location} and returning at {return_time}.<br>
               If this was a mistake or you no longer are able to drive, please modify or delete your car<br>
               on the ACTivism Hub homepage.<br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        You have successfully added a car for {event_name} leaving on {date} at {depart_time} from {meeting_location}
        and returning at {return_time}.
        If this was a mistake or you no longer are able to drive, please modify or delete your car
        on the ACTivism Hub homepage.

        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}


#returns a dict with the html and plain text version of confirmation email to added passenger
def addPassengerText(event_name,date,depart_time,return_time,meeting_location):
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               You have been successfully added to a car for {event_name} leaving on {date} at {time}<br>
               from {meeting_location} and returning at {return_time}.<br>
               If you no longer plan to attend, please remove yourself from this car on the ACTivism Hub homepage.<br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        You have been added to a car for {event_name} leaving on {date} at {time} from {meeting_location} and
        returning at {return_time}.
        If you no longer plan to attend, please remove yourself from this car on the ACTivism Hub homepage.

        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}


#returns a dict with the html and plain text versions of confirmation email for passenger in deleted car
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

        Your car for {event_name} leaving on {date} at {time} has been deleted.
        If this was a mistake, please return to ACTivism Hub and add your car again.

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
               Someone has requested a ride for {event_name} on {date}. <br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello {club_name},

        Someone has requested a ride for the {event_name} leaving on {date}.

        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}


#returns a dict with the html and plain text versions of confirmation email for deleted passenger
def deletePassengerText(event_name,date,time):
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               You have been successfully deleted from your car for {event_name} leaving on {date} at {time}.<br>
               If this was a mistake, please visit the ACTivism Hub homepage and add yourself to another car.<br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        You have been successfully deleted from your car for {event_name} leaving on {date} at {time}.
        If this was a mistake, please visit the ACTivism Hub homepage and add yourself to another car.

        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}


#returns a dict with the html and plain text versions of confirmation email to driver when car edited
def editCarDriverText(event_name,date,depart_time,return_time,meeting_location):
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               Your car for {event_name} has successfully been edited. It is scheduled to leave on {date} at {depart_time}
               from {meeting_location} and return at {return_time}.
               If this was a mistake, please return to ACTivism Hub and change your car details.<br><br>
               Best,<br>
               The ACTivism Hub Team<br><br>
             
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        Your car for {event_name} has successfully been edited. It is scheduled to leave on {date} at {depart_time} from
        {meeting_location} and return at {return_time}.
        If this was a mistake, please return to ACTivism Hub and change your car details.
               
        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}


#returns a dict with the html and plain text versions of update email for passengers when car edited
def editCarPassText(event_name,depart_time,return_time,meeting_location,date):
    html=f"""\
        <html>
          <body>
            <p>Hello,<br><br>
               A car you reserved for {event_name} has been edited and some details may have been changed.<br>
               It is now leaving on {date} at {depart_time} from {meeting_location} and returning at {return_time}.<br>
               Please visit ACTivism Hub and check that this still works with your schedule. <br><br>
               Best,<br>
               The ACTivism Hub Team
            </p>
          </body>
        </html>
        """
    text = f"""\
        Hello,

        A car you reserved for {event_name}has been edited and some details may have been changed.
        It is now leaving on {date} at {depart_time} from {meeting_location} and returning at {return_time}.
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

# Sends an email with the given html and plain text messages and subject to the given email
# from activismhub@pugetsound.edu
def sendEmail(receiver_email,html_text,plain_text,subject):
    smtp_server="webmail.pugetsound.edu"
    port = 587
    sender_email='activismhub@pugetsound.edu'
    password=EMAIL_PASSWORD

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
    mailserver = smtplib.SMTP(smtp_server,port)
    mailserver.starttls()
    mailserver.login(sender_email,password)
    mailserver.sendmail(sender_email,receiver_email,message.as_string())


########################################################################################################################
########## Verifying Emails ##############################################################################################

#Returns a dict with html and plain versions of a verify password email body
def verifyEmailText(clubID,hash,isAdmin,club_email):
    link=f"{SERVER_NAME}/verifyEmail?i={clubID}&h={hash}&a={isAdmin}&e={club_email}"
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


# Route when a user clicks the verification link in a "verify email" email
@app.route("/verifyEmail")
def verifyEmail():
    #get id, email, hash, and whether its an admin account from url
    clubID = request.args.get("i")
    hash = request.args.get("h")
    isAdmin = int(request.args.get("a"))
    club_email = request.args.get("e")
    #instantiate cursor
    cursor = mysql.connection.cursor()
    # If a club account
    if not isAdmin:
        #get hash from database
        cursor.execute('''SELECT activation_hash FROM %s WHERE clubID=%%s'''%(CLUB_TABLE,),(clubID,))
        r = cursor.fetchall()
        #if no club account with that email
        if len(r) == 0:
            return create_account("Unable to find account.")
        #If email associated with club account
        results = r[0]
        db_hash = results['activation_hash']
        #check if hash matches what we have stored for this email
        if db_hash != hash:
            return create_account("Email verification failed.")
        #activate club
        cursor.execute('''UPDATE %s SET email_activated=1, club_email=%%s WHERE clubID=%%s'''%(CLUB_TABLE,),(club_email,clubID))
        mysql.connection.commit()
        #reroute to login page
        return login_page("Email verification successful.")
    #If an admin account
    else:
        #get activation hash from database
        cursor.execute('''SELECT activation_hash, web_admin_email FROM %s WHERE web_adminID=%%s'''%(ADMIN_TABLE,),(clubID,))
        r2 = cursor.fetchall()
        #if not valid admin email
        if len(r2) == 0:
            return create_account("Unable to find account.")
        #if valid admin
        db_hash = r2[0]['activation_hash']
        old_admin_email = r2[0]['web_admin_email']
        #If hashes don't match, return error
        if db_hash != hash:
            return login_page("Email verification failed.")
        #If hashes match, activate admin account
        cursor.execute('''UPDATE %s SET email_activated=1, web_admin_email=%%s WHERE web_adminID=%%s'''%(ADMIN_TABLE,),(club_email,clubID))
        mysql.connection.commit()
        #email old admin with success message
        texts = adminChangeSuccessTexts(club_email)
        sendEmail(old_admin_email,texts['html'],texts['text'],"Admin change success")
        #reroute to login page
        return login_page("Email verification successful.")


########################################################################################################################
########## Resetting Passwords ###########################################################################################

#Route when user clicks forgot password on login page
@app.route("/forgotPassword")
def forgotPassword(message=""):
    clubs = getClubs()
    stats = getStats()
    admin = getAdmin()
    return render_template("forgotPassword.html",clubs=clubs,message=message,stats=stats,admin=admin)


#Route when user clicks reset password button in forgot password page
@app.route("/preparePasswordReset",methods=["POST"])
def preparePasswordReset():
   #get email from form
   club_email=request.form['club_email']
   #Get clubID for that email
   cursor = mysql.connection.cursor()
   cursor.execute('''SELECT clubID, activation_hash, club_approved FROM %s WHERE club_email=%%s'''%(CLUB_TABLE,),(club_email,))
   result = cursor.fetchall()

   #if that email isn't associated with a club
   if len(result) == 0:
        #check if admin
        cursor.execute('''SELECT activation_hash FROM %s WHERE web_admin_email=%%s'''%(ADMIN_TABLE,),(club_email,))
        result2 = cursor.fetchall()
        #if not an admin email either
        if len(result2) == 0:
            return forgotPassword(club_email+" is not associated with an account.")
        #if a real admin email
        else:
            activation_hash = result2[0]['activation_hash']
            texts = resetPasswordText(club_email,activation_hash)
            sendEmail(club_email,texts['html'],texts['text'],"Reset your password")
            return index("An email has been sent to "+club_email+" with a reset link.")

   #If email associated with a club, check if club approved
   clubID=result[0]['clubID']
   if result[0]['club_approved']:
       #Prepare text and send email
       activation_hash = result[0]['activation_hash']
       texts = resetPasswordText(club_email,activation_hash)
       sendEmail(club_email,texts['html'],texts['text'],"Reset your password")
       return index("An email has been sent to "+club_email+" with a password reset link.")
   #If club not approved
   else:
      return forgotPassword(club_email+" has not yet been approved to make an account.")


#route for link clicked in reset password email
@app.route("/resetPassword")
def resetPassword():
    #email and hash from url
    club_email = request.args.get("e")
    hash = request.args.get("h")
    #get clubID and hash associated with this email from database
    cursor = mysql.connection.cursor()
    cursor.execute('''SELECT clubID, activation_hash from %s WHERE club_email=%%s'''%(CLUB_TABLE,),(club_email,))
    results = cursor.fetchall()
    #if no account with that email
    if len(results)==0:
        #check if admin
        cursor.execute('''SELECT web_adminID, activation_hash from %s WHERE web_admin_email=%%s'''%(ADMIN_TABLE,),(club_email,))
        results2 = cursor.fetchall()
        #if not a valid admin email either
        if len(results2) == 0:
            return create_account(club_email+" is not associated with an account.")
        #if admin, check if hashes match
        else:
            activation_hash=results2[0]['activation_hash']
            adminID = results2[0]['web_adminID']
            if hash == activation_hash:
                clubs = getClubs()
                stats = getStats()
                admin = getAdmin()
                return render_template("resetPassword.html",clubs=clubs,clubID=adminID,stats=stats,admin=admin)
            else:
                return forgotPassword("Reset password via email failed")

    #If email associated with club account
    results=results[0]
    clubID=results['clubID']
    db_hash = results['activation_hash']
    #check if hash matches what we have stored for this email and account is active
    #if passes, render a reset password page, pass in clubID
    if db_hash == hash:
        clubs = getClubs()
        stats = getStats()
        admin = getAdmin()
        return render_template("resetPassword.html",clubs=clubs,clubID=clubID,stats=stats,admin=admin)
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
        #check if valid admin
        cursor.execute('''SELECT web_admin_email FROM %s WHERE web_adminID=%%s'''%(ADMIN_TABLE,),(clubID,))
        result2 = cursor.fetchall()
        #if not valid admin
        if len(result2)==0:
            return forgotPassword("This account does not exist.")
        #if valid admin
        saltedPassword = password + salt
        password = hashlib.sha256(saltedPassword.encode()).hexdigest()
        #update password in database, set club to active if not already (this counts as email verification)
        cursor.execute('''UPDATE %s SET password=%%s,email_activated=1 WHERE web_adminID=%%s'''%(ADMIN_TABLE,),(password,clubID))
        mysql.connection.commit()
        #render login page
        return login_page("Password successfully reset.")

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

# Called when a club requests to make an account
def requestApproval(clubID):
    #get admin email
    cursor=mysql.connection.cursor()
    cursor.execute('''SELECT web_admin_email FROM %s WHERE curr_admin=1'''%(ADMIN_TABLE))
    admin_email=cursor.fetchall()[0]['web_admin_email']
    #get club info
    cursor.execute('''SELECT * FROM %s WHERE clubID=%%s'''%(CLUB_TABLE,),(clubID,))
    club_info = cursor.fetchall()[0] #There will be an account, called right after insertion
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

        Club Name: {club_info['club_name']}
        Club Email: {club_info['club_email']}
        Club Description: {club_info['about_info']}

        If this club puts on activism related programming,please
        approve their request to make an account by clicking the first link: {approval_link}
        If not, please deny their request to make an account by clicking the second link: {denial_link}

        Best,
        The ACTivism Hub Team
        """
    return {'html':html,'text':text}


# Route if admin clicks approve in the email sent when a club requests an account
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
    texts = verifyEmailText(clubID,club_info['activation_hash'],0,club_info['club_email'])
    sendEmail(club_info['club_email'],texts['html'],texts['text'],"Verify your email")

    #increment total clubs for tracking
    cursor.execute('''UPDATE %s SET total_clubs = total_clubs + 1 WHERE trackingID = 1'''%(TRACKING_TABLE,))
    cursor.connection.commit()

    #load home page with message that club was approved
    return index(club_info['club_name']+" successfully approved. An email has been sent to the club to verify their email.")


# Route if admin clicks deny in email sent when club requests an account
@app.route("/denyClub")
def denyClub():
    #get clubID
    clubID=request.args.get('id')
    #get info for club
    cursor = mysql.connection.cursor()
    cursor.execute('''SELECT * FROM %s WHERE clubID=%%s'''%(CLUB_TABLE,),(clubID,))
    club_info = cursor.fetchall()[0]
    club_approved=club_info['club_approved']
    # If club not already approved
    if not club_approved:
        #get admin email
        cursor.execute('''SELECT web_admin_email FROM %s WHERE curr_admin=1'''%(ADMIN_TABLE))
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


########################################################################################################################
########## Admin #######################################################################################################

# Route when admin clicks change admin in the admin tab
@app.route("/changeAdmin",methods=["POST"])
def changeAdmin():
    # Get admin info
    admin_name=request.form['admin_name']
    admin_email = request.form['admin_email']
    old_admin_email = request.form['old_admin_email']
    adminID = request.form['adminID']
    # Change admin name
    cursor=mysql.connection.cursor()
    cursor.execute('''UPDATE %s SET web_admin_name=%%s WHERE web_adminID=%%s'''%(ADMIN_TABLE,),(admin_name,adminID))
    mysql.connection.commit()
    # If they changed the admin email, verify new email
    if admin_email != old_admin_email:
        cursor.execute('''SELECT activation_hash FROM %s WHERE web_adminID=%%s'''%(ADMIN_TABLE,),(adminID,))
        # Change activation hash??
        activation_hash=cursor.fetchall()[0]['activation_hash']
        texts = verifyAdminEmailText(adminID,admin_email,activation_hash)
        sendEmail(admin_email,texts['html'],texts['text'],"Verify new admin email")
        return index("An email has been sent to "+admin_email+" to verify the admin change.")
    return index("Admin name has been successfully changed.")


# Prepare text for email verifying new admin email
def verifyAdminEmailText(adminID,email,hash):
    link=f"{SERVER_NAME}/verifyEmail?i={adminID}&h={hash}&a=1&e={email}"
    html=f"""\
        <html>
            <body>
                <p>Hello,<br><br>
                    You have been set as the new admin for ACTivism Hub.<br>
                    If this has been done by mistake, please disregard this message.<br>
                    If not, please verify your email by clicking <a href={link}>here</a>.<br>
                    Once you have verified your email, you can login with your email and the<br>
                    previous administrator's password, or reset your password by clicking<br>
                    "forgot password" on the login page.<br><br>
                    Best,<br>
                    The ACTivism Hub Team
                </p>
            </body>
        </html>
        """
    text = f"""\
        Hello,

        You have been set as the new admin for ACTivism Hub.
        If this has been done by mistake, please disregard this message.
        If not, please verify your email by clicking the link below.
        Once you have verified your email, you can login with your email and the
        previous administrator's password, or reset your password by clicking
        "forgot password" on the login page.

        Best,
        The ACTivism Hub Team

        {link}
        """
    return {'html':html,'text':text}


# Prepares text for email informing old admin of successful admin change
def adminChangeSuccessTexts(new_admin):
    html=f'''\
        <html>
            <body>
                <p>Hello,<br><br>
                    The system administrator has been successfully changed to {new_admin}.<br><br>
                    Best,<br>
                    The ACTivism Hub Team
                </p>
            </body>
        </html>
        '''
    text = f'''\
        Hello,

        The system administrator has been successfully changed to {new_admin}.

        Best,
        The ACTivism Hub Team
        '''
    return {'html':html,'text':text}


def getAdmin():
    cursor = mysql.connection.cursor()
    #get current admin info
    cursor.execute('''SELECT * FROM %s WHERE curr_admin = 1''' %(ADMIN_TABLE,))
    admin = cursor.fetchall()
    if len(admin)>0:
        return admin[0]
    else:
        return {'web_adminID':0,'web_admin_name':'None','web_admin_email':'None',}


########################################################################################################################
########## Stats #######################################################################################################

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
    results = cursor.fetchall()
    if len(results)>0:
        results = results[0]
        total_overall_clubs = results['total_clubs']
        total_overall_events = results['total_events']
        total_overall_cars = results['total_cars']
        total_overall_passengers = results['total_passengers']
    else:
        total_overall_clubs = 0
        total_overall_events = 0
        total_overall_cars = 0
        total_overall_passengers = 0

    stats = {"total_current_clubs":total_current_clubs, "total_current_events":total_current_events,"total_current_cars":total_current_cars,
             "total_current_passengers":total_current_passengers,"total_overall_clubs":total_overall_clubs,"total_overall_events":total_overall_events,
             "total_overall_cars":total_overall_cars,"total_overall_passengers":total_overall_passengers}

    return stats

######## s3 functions ##################################################################################################

# @app.route('/sign_s3/')
# def sign_s3():
#   S3_BUCKET = os.environ.get('S3_BUCKET')
#
#   file_name = request.args.get('file_name')
#   file_type = request.args.get('file_type')
#
#   s3 = boto3.client('s3')
#
#   presigned_post = s3.generate_presigned_post(
#     Bucket = S3_BUCKET,
#     Key = file_name,
#     Fields = {"acl": "public-read", "Content-Type": file_type},
#     Conditions = [
#       {"acl": "public-read"},
#       {"Content-Type": file_type}
#     ],
#     ExpiresIn = 3600
#   )
#
#   return json.dumps({
#     'data': presigned_post,
#     'url': 'https://%s.s3.amazonaws.com/%s' % (S3_BUCKET, file_name)
#   })











