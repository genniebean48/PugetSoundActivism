# ACTivism Hub
Web app serving as a central hub for student ACTivism on University of Puget Sound campus. [Linked here](https://pugetsoundactivism.com)

## Table of Contents
* [General Info](#general-info)
* [Technologies](#technologies)
* [Directory Layout](#directory-layout)
* [Functionality](#functionality)
* [Credits](#credits)

## General Info
This python web app was created to serve as a central hub for student activism on University of Puget Sound campus. Its seeks to increase accessibility for students engaging with local activism, increase visibility for student activist leaders, and enable resource sharing between activist clubs. Features include a central homepage with upcoming activism events, club profile pages, a rideshare feature, event and club creation/edit/deletion for club owners, password recovery, and email verification and notification systems. Created in collaboration with student activists and club leaders on the University of Puget Sound campus.

## Technologies
* Python: 3.10.5
* Flask: 1.1.2
* Flask-MySQLdb: 0.2.0
* gunicorn: 20.1.0
* JavaScript: ES9
* HTML: 5
* LESS
* CSS
* itsdangerous==1.1.0
* Jinja2==2.11.2
* MarkupSafe==1.1.1
* mysqlclient==2.0.3
* Werkzeug==1.0.1
* click==7.1.2

## Directory Layout
|-Project folder/
| |--activismhub.py
| |--README
| |--templates/
| |  |--all html files
| |--static/
| |  |--all less files
| |  |--all css files
| |  |--all js files
| |  |--images/
| |  |  |--all images
| |  |--font styling

## Functionality

## For students:
* Students can view upcoming events from all clubs on the homepage:
![image](/readme_images/homepage.PNG)
* For in person events, students who are driving can add cars, and students who need rides can sign up for seats or request a spot in a future car:
![image](/readme_images/rideshare.PNG)
![image](/readme_images/add_car.PNG)
![image](/readme_images/reserve_seat.PNG)
* If rideshare info is changed, all passengers get an email notification.
* Students can also view club profiles, including contact info and social media:
![image](/readme_images/club_page.PNG)

### For club leaders:
* Club leaders can create and (once they've been approved by the site administrator and verified their email) login to the site, as well as using password recovery throug their email
* Once logged in, club leaders can customize their club profile, and add/edit/delete events:
![image](/readme_images/edit_club_profile.PNG)
![image](/readme_images/add_event.PNG)
![image](/readme_images/edit_event.PNG)

## Credits:
Created by [Manya Mutschler-Aldine](https://github.com/manyam686), [Emma Kauzmann](https://github.com/EmmaKau), and [Gennie Cheatham](https://github.com/genniebean48) in collaboration with student activists on University of Puget Sound Campus in 2021. 
