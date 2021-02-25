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
#app.secret_key = b'1234567'

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


    return render_template("homePage.html")



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

    #hardcode a dict as if it came from a SQL query, pass info to html
    info = {'club_name' : "Advocates for Detained Voices",
            'about_info' : '''Our purpose is to donate our time toward empowering detainees and their families and
                raise awareness about families struggling with undocumented status. Advocates for Detained Voices (ADV)
                plan is to set up continued monthly volunteer opportunities through the Seattle based group Latino
                Advocacy. This group works throughout Washington State providing workshops and counseling for families
                that are undocumented.''',
            'facebook_link' : "https://www.facebook.com/ADVUnivofPugetSound"}

    return render_template("clubPage.html",info=info)

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/createAccount")
def create_account():
    return render_template("create-account.html")

