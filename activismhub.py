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
import os, datetime, secrets, json
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
# CLUB_TABLE='club'
# EVENT_TABLE='club_event'
# ADMIN_TABLE='club_admin'
#for testing
CLUB_TABLE ='testClub'
EVENT_TABLE ='testClub_event'
ADMIN_TABLE ='testClub_admin'
CAR_TABLE = 'testRideShare_car'
PASSENGER_TABLE = 'testRideShare_passenger'

#salt for password hashing
salt = '1kn0wy0ulov3m3'



def activeType():
    cursor = mysql.connection.cursor()
    cursor.execute('''SELECT club_email, email_activated FROM %s'''%(CLUB_TABLE,))
    results = cursor.fetchall()
    for result in results:
        print(result['club_email'])
        print(result['email_activated'])
    cursor.execute('''SELECT clubID FROM %s WHERE club_email="manyam686@gmail.com"'''%(CLUB_TABLE,))
    me = len(cursor.fetchall())
    print("Num my email: ",me)


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
        for car in cars:
            print("in loop")
            cursor.execute('''SELECT * FROM %s WHERE carID=%%s'''%(PASSENGER_TABLE,),(car['carID'],))
            car['passengers'] = cursor.fetchall()
            car = json.dumps(car, default=str)
            event['cars1']=car
        #add JSON string of cars to event
        event['cars'] = json.dumps(cars,default=str)
        print(event['cars'])
        print(type(event['cars']))
        #add formatted date and times
        event['event_date_formatted']=formatDateFromSql(event['event_date'])
        event['start_time_formatted']=formatTimeFromSql(event['start_time'])
        event['end_time_formatted']=formatTimeFromSql(event['end_time'])
#    #Get cars
#    cursor.execute('''SELECT * FROM %s'''%(CAR_TABLE,))
#    cars = cursor.fetchall()
#    #get passengers for each car
#    for car in cars:
#        cursor.execute('''SELECT * FROM %s WHERE carID=%%s'''%(PASSENGER_TABLE,),(car['carID']))
#        car['passengers'] = cursor.fetchall()
   #render homepage
   return render_template("homePage.html",events=events,clubs=clubs,message=message)


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
               return login_page("Email not verified. Check your email for a verification link.")
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
def create_account(message=""):
   #sample list of dicts of clubs
   clubs = getClubs()
   return render_template("create-account.html",clubs=clubs,message=message)


#Route when user clicks submit on the create account page
@app.route("/enterAccount",methods=["POST"])
def enter_account():
   #instantiate cursor
   cursor = mysql.connection.cursor()
   #get form info
   club_email = request.form['clubEmail']
   club_name = request.form['club-name']
#    admin_name = request.form['admin-name']
   about_info = request.form['club-description']
#    admin_email = request.form['admin-email']
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
   #Insert new account info into club table
   cursor.execute('''INSERT INTO %s(club_name,about_info,club_email,password,club_email_display,activation_hash,
       email_activated) VALUES(%%s,%%s,%%s,%%s,%%s,%%s,0)'''%(CLUB_TABLE,),(club_name,about_info,club_email,password,
       club_email_display,activation_hash))
   mysql.connection.commit()
#    #get club new club id
#    cursor.execute('''SELECT clubID FROM %s where club_name = %%s'''%(CLUB_TABLE,),(club_name,))
#    clubID=cursor.fetchall()[0]['clubID']
#    #Insert new account info into admin table
#    cursor.execute('''INSERT INTO %s(clubID,admin_name,admin_email) VALUES(%%s,%%s,%%s)'''%(ADMIN_TABLE,),
#         (clubID,admin_name,admin_email))
#    mysql.connection.commit()
   #Create text for email verification and send email
   texts = verifyEmailText(club_email,activation_hash)
   sendEmail(club_email,texts['html'],texts['text'],"Verify your email")
   #TODO - render page with message about sent email
   #reroute to home page
   return index("An email has been sent to "+club_email+" with an verification link.")


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
##### Ride Sharing #####################################################################################################

#route when user clicks submit on adding a car
@app.route("/addCar",methods=["POST"])
def addCar():
    #Get which event // TODO
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
    #reroute to home page
    # -- I DON'T THINK THIS IS WHAT WE WANT THO, GO BACK TO SPLIT SCREEN OF RIDES AND DESCRIPTION --
    return index()


#route when user clicks submit on reserving a seat
@app.route("/addPassenger",methods=["POST"])
def addPassenger():
    #Get which car -- NOT SURE HOW TO DO THIS
    carID = 1
    #eventID = request.args.get("q")

    #get form info
    passenger_name = request.form['passenger_name']
    passenger_email = request.form['passenger_email']

    #instantiate cursor
    cursor = mysql.connection.cursor()
    #Add passenger
    cursor.execute('''INSERT INTO %s(passenger_name,passenger_email,carID) VALUES (%%s,%%s)'''
                   %(PASSENGER_TABLE,),(passenger_name,passenger_email,carID))

    #decrement number of available seats for specific car
    cursor.execute('''UPDATE %s SET num_seats_available = num_seats_available - 1 WHERE carId = %%s'''%(CAR_TABLE,),(carID))
    #increment number of seats taken or specific car
    cursor.execute('''UPDATE %s SET num_seats_taken = num_seats_taken + 1 WHERE carId = %%s'''%(CAR_TABLE,),(carID))

    mysql.connection.commit()
    #reroute to home page
    # -- I DON'T THINK THIS IS WHAT WE WANT THO, GO BACK TO SPLIT SCREEN OF RIDES AND DESCRIPTION --
    return index()


########################################################################################################################
##### Helper functions #################################################################################################

#Gets list of club names and IDs
def getClubs():
   cursor = mysql.connection.cursor()
   cursor.execute('''SELECT club_name, clubID FROM %s WHERE email_activated=1''' % (CLUB_TABLE,))
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
##########Verifying Emails##############################################################################################

#Returns a dict with html and plain versions of a verify password email body
def verifyEmailText(email,hash):
    link=f"http://localhost:5000/verifyEmail?e={email}&h={hash}"
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
    print(len(r))
    print(club_email)
    print(type(club_email))
    results = r[0]
    clubID=results['clubID']
    db_hash = results['activation_hash']
    active = results['email_activated']
    #check if hash matches what we have stored for this email and account isn't active
    if active == 1:
        return login_page("Club has already been activated.")
    if db_hash != hash:
        message="Email verification failed."
        #how to reroute here?? With popup
    #activate club
    cursor.execute('''UPDATE %s SET email_activated=1 WHERE clubID=%%s'''%(CLUB_TABLE,),(clubID,))
    mysql.connection.commit()
    #reroute to login page
    return login_page("Email verification successful.")


########################################################################################################################
##########Resetting Passwords###########################################################################################

#When click forgot password on login page
@app.route("/forgotPassword")
def forgotPassword(message=""):
    clubs = getClubs()
    return render_template("forgotPassword.html",clubs=clubs,message=message)


#When click reset password button in forgot password page
@app.route("/preparePasswordReset",methods=["POST"])
def preparePasswordReset():
   #get email from form
   club_email=request.form['club_email']
   #Get clubID for that email
   cursor = mysql.connection.cursor()
   cursor.execute('''SELECT clubID, activation_hash FROM %s WHERE club_email=%%s'''%(CLUB_TABLE,),(club_email,))
   result = cursor.fetchall()
   #if that email isn't in the database
   #TODO - add message saying email not in database
   if len(result) == 0:
        return forgotPassword(club_email+" is not associated with an account.")
   #Prepare text and send email
   clubID=result[0]['clubID']
   activation_hash = result[0]['activation_hash']
   texts = resetPasswordText(club_email,activation_hash)
   sendEmail(club_email,texts['html'],texts['text'],"Reset your password")
   #TODO - where to return when email sent? Add pop up
   return index("An email has been sent to "+club_email+" with a reset link.")


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
    results = cursor.fetchall()[0]
    clubID=results['clubID']
    db_hash = results['activation_hash']
    #check if hash matches what we have stored for this email and account is active
    #if passes, render a reset password page, pass in clubID
    if db_hash == hash:
        clubs = getClubs()
        return render_template("resetPassword.html",clubs=clubs,clubID=clubID)
    else:
        return login_page("Reset password via email failed")


#When click submit on reset password form
@app.route("/doPasswordReset",methods=["POST"])
def doPasswordReset():
    #get info from form
    password = request.form['password']
    clubID = request.form['clubID']
    #hash password
    saltedPassword = password + salt
    password = hashlib.sha256(saltedPassword.encode()).hexdigest()
    #update password in database
    cursor = mysql.connection.cursor()
    cursor.execute('''UPDATE %s SET password=%%s WHERE clubID=%%s'''%(CLUB_TABLE,),(password,clubID))
    mysql.connection.commit()
    #render login page
    return login_page("Password successfully reset.")


#returns a dict with the html and plain text versions of a reset password email
def resetPasswordText(email,hash):
    link=f"http://localhost:5000/resetPassword?e={email}&h={hash}"
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





