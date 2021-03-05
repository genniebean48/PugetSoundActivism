# INITIAL BARE BONES FOR APPLICATION LAYER
# 2/14/21
# This file runs the application, SQL queries and route direction will be in here
# Both flask and flask-mysqldb must be installed (on CL: pip install flask--mysqldb)

#IMPORT
#request is for get/post data, render_template is to render html pages
from flask import Flask, request, render_template, session
#from flask_mysqldb import MySQL

#INSTANTIATE
app = Flask(__name__) #what does the parameter here mean? look up
app.secret_key = b'1234567'

#Configure MySQL
#Not sure if we need to include one's where default is fine -- there are more in docs
# app.config['MYSQL_HOST'] = 'localhost' #I assume we change this once we have a server
# app.config['MYSQL_USER'] = #Emma will know
# app.config['MYSQL_PASSWORD'] = #Emma will know
# app.config['MYSQL_DB'] = #Emma will know
# app.config['MYSQL_CURSORCLASS'] = 'DictCursor' #returns queries as dicts instead of default tuples

#Instantiate
# mysql = MySQL(app)
# #connect to the MySQL server and establishes cursor -- does this need to be in functions or ok here?
# cursor = mysql.connection.cursor()


#Route with nothing appended (in our local machine, localhost:5000)
@app.route("/")
def index():
    #TODO w/ database
        #Execute SQL query to get all events -- have today or after code here?
            #cursor.execute(query text)
            #results = cursor.fetchall()
        #Do ordering by date here or in html file? Can SQL do that?
        #Pass to html file as a list of dicts
            #return render_template("homePage.html",events=results)

    #sample list of event dicts
    event1 = {'event_name': "Event 1",'event_date':"January 12, 2021",
                'event_time':"1:00 PM", 'event_type':"Protest",
                'event_description':"Description for event 1"}
    event2 = {'event_name': "Event 2",'event_date':"February 3, 2021",
                    'event_time':"6:00 PM", 'event_type':"City Council Meeting",
                    'event_description':"Description for event 2"}
    event3 = {'event_name': "Event 3",'event_date':"June 27, 2021",
                    'event_time':"9:00 AM", 'event_type':"Sit In",
                    'event_description':"Description for event 3"}
    events = [event1, event2, event3]
    #sample list of dicts of clubs
    clubs = [{'club_name':'Advocates for Detained Voices', 'club_id':"1"},{'club_name':'BSU', 'club_id':"2"},{'club_name':'MIBU', 'club_id':"3"}]
    return render_template("homePage.html",events=events,clubs=clubs)



#Route when a club page is clicked
@app.route("/clubPage")
def club_page():
    #TODO w/ database
        #Use request to figure out which club
            #club_name = request.args.get("club_name") #if using GET, club_name is var that value of club name is set to in html file
            #club_name = request.form.get("q") #if using POST , ''
        #Execute SQL query to get club info
            #cursor.execute(query text)
            #results = cursor.fetchall()
        #Pass to html file as a dict
            # return render_template("clubPage.html",fields=results[0])

    #try getting get data
    club_name = request.args.get("club")

    #sample dict of club info
    info = {'club_name' : "Advocates for Detained Voices",
            'about_info' : '''Our purpose is to donate our time toward empowering detainees and their families and
                raise awareness about families struggling with undocumented status. Advocates for Detained Voices (ADV)
                plan is to set up continued monthly volunteer opportunities through the Seattle based group Latino
                Advocacy. This group works throughout Washington State providing workshops and counseling for families
                that are undocumented.''',
            'facebook_link' : "https://www.facebook.com/ADVUnivofPugetSound"}
    #sample list of event dicts
    event1 = {'event_name': "Event 1",'event_date':"January 12, 2021",
                'event_time':"1:00 PM", 'event_type':"Protest",
                'event_description':"Description for event 1"}
    event2 = {'event_name': "Event 2",'event_date':"February 3, 2021",
                    'event_time':"6:00 PM", 'event_type':"City Council Meeting",
                    'event_description':"Description for event 2"}
    event3 = {'event_name': "Event 3",'event_date':"June 27, 2021",
                    'event_time':"9:00 AM", 'event_type':"Sit In",
                    'event_description':"Description for event 3"}
    events = [event1, event2, event3]
    #sample list of dicts of clubs
    clubs = [{'club_name':'Advocates for Detained Voices', 'club_id':"1"},{'club_name':'BSU', 'club_id':"2"},{'club_name':'MIBU', 'club_id':"3"}]
    return render_template("clubPage.html",info=info,events=events,clubs=clubs)

@app.route("/login")
def login_page():
    #sample list of dicts of clubs
    clubs = [{'club_name':'Advocates for Detained Voices', 'club_id':"1"},{'club_name':'BSU', 'club_id':"2"},{'club_name':'MIBU', 'club_id':"3"}]
    return render_template("login.html",clubs=clubs)

@app.route("/createAccount")
def create_account():
    #sample list of dicts of clubs
    clubs = [{'club_name':'Advocates for Detained Voices', 'club_id':"1"},{'club_name':'BSU', 'club_id':"2"},{'club_name':'MIBU', 'club_id':"3"}]
    return render_template("create-account.html",clubs=clubs)

@app.route("/doLogin",methods=["POST"])
def do_login():
    logins = {'admin_email':'email1@gmail.com','password':'password1','club_id':'1'}
    user = request.form['Email']
    password = request.form['Password']
    if password == logins['password']:
        session['club_id']=logins['club_id']
        return index()
    else:
        return login()

@app.route("/logout")
def logout():
    session.pop('club_id',None)
    return index()

@app.route("/editClub")
def editClub():
    return render_template("editClub.html")

