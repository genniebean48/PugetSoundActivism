# INITIAL BARE BONES FOR APPLICATION LAYER
# 2/14/21
# This file runs the application, SQL queries and route direction will be in here
# Both flask and flask-mysqldb must be installed (on CL: pip install flask--mysqldb)

#IMPORT
#request is for get/post data, render_template is to render html pages
from flask import Flask, request, render_template, session
from flask_mysqldb import MySQL

#INSTANTIATE
app = Flask(__name__) #what does the parameter here mean? look up
app.secret_key = b'1234567'

#Instantiate
mysql = MySQL(app)

#Configure MySQL
# app.config['MYSQL_HOST'] = 'activism-hub'
# app.config['MYSQL_USER'] = 'dba'
# app.config['MYSQL_PASSWORD'] = 'Password321$'
# app.config['MYSQL_DB'] = 'remote_activismHub'
# app.config['MYSQL_CURSORCLASS'] = 'DictCursor' #returns queries as dicts instead of default tuples


#Route with nothing appended (in our local machine, localhost:5000)
@app.route("/")
def index():
#     #HARD CODING FOR TESTING--Delete later
#     #sample add new club to database
#     newClub = {'club_name':'ADV','admin_name':'Manya','about_info':'About about about about','club_email':
#                'adv@gmail.com'}
#     cursor.execute('''INSERT INTO testClub(club_name,admin_name,about_info,club_email)
#                       VALUES(%s,%s,%s,%s)''',(newClub['club_name'],newClub['admin_name'],newClub['about_info'],newClub['club_email']))
#     mysql.connection.commit()
#     #sample add new event for club with ID 13
#     cursor.execute('''SELECT club_name FROM testClub where clubID = 13''')
#     clubName = cursor.fetchall()[0]['club_name']
#     newEvent={'event_name':'Another Event','clubID':'13','event_date':'2021-05-3','event_time':'12:00:00','event_location':'Campus',
#                 'event_description':'its an event whoop whoop event','club_name':clubName}
#     cursor.execute('''INSERT INTO testClub_event(event_name, club_name, clubID, event_date, event_time, event_location, event_description)
#             VALUES(%s,%s,%s,%s,%s,%s,%s)''',(newEvent['event_name'],newEvent['club_name'],newEvent['clubID'],newEvent['event_date'],
#             newEvent['event_time'],newEvent['event_location'],newEvent['event_description']))
#     mysql.connection.commit()
    #sample list of event dicts
#     event1 = {'event_name': "Event 1",'event_date':"January 12, 2021",
#                 'event_time':"1:00 PM", 'event_type':"Protest",
#                 'event_description':"Description for event 1"}
#     event2 = {'event_name': "Event 2",'event_date':"February 3, 2021",
#                     'event_time':"6:00 PM", 'event_type':"City Council Meeting",
#                     'event_description':"Description for event 2"}
#     event3 = {'event_name': "Event 3",'event_date':"June 27, 2021",
#                     'event_time':"9:00 AM", 'event_type':"Sit In",
#                     'event_description':"Description for event 3"}
#     events = [event1, event2, event3]
    #sample list of dicts of clubs
    #clubs = [{'club_name':'Advocates for Detained Voices', 'club_id':"1"},{'club_name':'BSU', 'club_id':"2"},{'club_name':'MIBU', 'club_id':"3"}]

    #Establish connection
    cursor = mysql.connection.cursor()
    #Get list of clubs and IDs
    clubs = getClubs()
    #Get events
    cursor.execute('''SELECT * FROM testClub_event ORDER BY event_date ASC''')
    events = cursor.fetchall()
    return render_template("homePage.html",events=events,clubs=clubs)



#Route when a club page is clicked
@app.route("/clubPage")
def club_page():
#     #HARD CODING FOR TESTING--Delete later
#     #sample dict of club info
#     info = {'club_name' : "Advocates for Detained Voices",
#             'about_info' : '''Our purpose is to donate our time toward empowering detainees and their families and
#                 raise awareness about families struggling with undocumented status. Advocates for Detained Voices (ADV)
#                 plan is to set up continued monthly volunteer opportunities through the Seattle based group Latino
#                 Advocacy. This group works throughout Washington State providing workshops and counseling for families
#                 that are undocumented.''',
#             'facebook_link' : "https://www.facebook.com/ADVUnivofPugetSound"}
#     #sample list of event dicts
#     event1 = {'event_name': "Event 1",'event_date':"January 12, 2021",
#                 'event_time':"1:00 PM", 'event_type':"Protest",
#                 'event_description':"Description for event 1"}
#     event2 = {'event_name': "Event 2",'event_date':"February 3, 2021",
#                     'event_time':"6:00 PM", 'event_type':"City Council Meeting",
#                     'event_description':"Description for event 2"}
#     event3 = {'event_name': "Event 3",'event_date':"June 27, 2021",
#                     'event_time':"9:00 AM", 'event_type':"Sit In",
#                     'event_description':"Description for event 3"}
#     events = [event1, event2, event3]

    #Establish connection
    cursor = mysql.connection.cursor()
    #Get which club
    clubID = request.args.get("q")
    #Get club info
    cursor.execute('''SELECT * FROM testClub WHERE clubID = %s''',(clubID,))
    info = cursor.fetchall()[0]
    #Get events
    cursor.execute('''SELECT * FROM testClub_event ORDER BY event_date ASC''')
    events = cursor.fetchall()
    #Get list of dicts of clubs
    clubs = getClubs()
    return render_template("clubPage.html",info=info,events=events,clubs=clubs)


#Route when user clicks login
@app.route("/login")
def login_page():
    #sample list of dicts of clubs
    clubs = getClubs()
    return render_template("login.html",clubs=clubs)


#Route when user clicks create account from login page
@app.route("/createAccount")
def create_account():
    #sample list of dicts of clubs
    clubs = getClubs()
    return render_template("create-account.html",clubs=clubs)


#Route when user clicks submit on login page
@app.route("/doLogin",methods=["POST"])
def do_login():
    cursor = mysql.connection.cursor()
    #get user and password
    user = request.form['Email']
    password = request.form['Password']
    #get club ID
    cursor.execute('''SELECT clubID FROM testClub where club_email = %s''',(user,))
    clubID=cursor.fetchall()[0]['clubID']
    #get correct password for that ID
    cursor.execute('''SELECT password FROM testClub_admin where clubID = %s''',(clubID,))
    correct_password = cursor.fetchall()[0]['password']
    #simple authentication
    if password == correct_password:
        #add clubID to session and reroute to homepage
        session['club_id']=clubID
        return index()
    else:
        #if password incorrect, reload login page
        return login()


#Route when user clicks logout
@app.route("/logout")
def logout():
    #remove session variable for clubID
    session.pop('club_id',None)
    #reroute to home page
    return index()

@app.route("/editClub")
def editClub():
    return render_template("editClub.html")

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
    #Insert new account info into club table
    cursor.execute('''INSERT INTO testClub(club_name,admin_name,about_info,club_email)
        VALUES(%s,%s,%s,%s)''',(clubName,adminName,description,email))
    mysql.connection.commit()
    #get club new club id
    cursor.execute('''SELECT clubID FROM testClub where club_name = %s''',(clubName,))
    clubID=cursor.fetchall()[0]['clubID']
    #Insert new account info into admin table
    cursor.execute('''INSERT INTO testClub_admin(club_name,clubID, admin_name,admin_email,password)
        VALUES(%s,%s,%s,%s,%s)''',(clubName,clubID,adminName,adminEmail,password))
    mysql.connection.commit()
    #reroute to home page
    return index()


#Gets list of club names and IDs
def getClubs():
    cursor = mysql.connection.cursor()
    cursor.execute('''SELECT club_name, clubID FROM testClub''')
    return cursor.fetchall()

