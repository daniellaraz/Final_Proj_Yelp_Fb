import requests
import facebook
import json
import urllib
import sqlite3
import fb_token_info
import weatherAPI_token_info
#from datetime import datetime as dt
import dateutil.parser
from darksky import forecast
import webbrowser
import datetime
import yelp_token_info
import plotly
import plotly_token_info
import plotly.plotly as py
import plotly.graph_objs as go


### PLOTLY SETUP
plotly_username = plotly_token_info.username
plotly_key = plotly_token_info.api_key
plotly.tools.set_credentials_file(username = "daniellaraz", api_key = plotly_key)


### FACEBOOK SETUP
token = fb_token_info.access_token
graph = facebook.GraphAPI(token)

### WEATHER SETUP
weather_token = weatherAPI_token_info.token

### YELP SETUP
client_id = yelp_token_info.my_id
yelp_API_key = yelp_token_info.API_Key
bearer_token = 'Bearer ' + yelp_API_key


### CACHING SETUP FOR FACEBOOK
CACHE_FNAME = "my_facebook_testing.json"
try:
    cache_file = open(CACHE_FNAME, 'r')
    cache_contents = cache_file.read()
    CACHED_POSTS = json.loads(cache_contents)
    cache_file.close()
except:
    CACHED_POSTS = {}

### CACHING SETUP FOR YELP

CACHE_FNAME2 = "yelp_TESTING.json"
try:
    cache_file2 = open(CACHE_FNAME2, 'r')
    cache_contents2 = cache_file2.read()
    CACHED_POSTS2 = json.loads(cache_contents2)
    cache_file2.close()
except:
    CACHED_POSTS2 = {}

### FACEBOOK API: GETS ALL OF MY POSTS FROM FACEBOOK
def get_posts(CACHED_POSTS):
    if CACHED_POSTS:
        print('using cached data')
        list_of_pages = CACHED_POSTS
    else:
        print("Retrieving data from internet")
        all_fields = ['message', 'created_time', 'description', 'caption', 'link', 'place', 'status_type']
        all_fields = ','.join(all_fields)
        posts = graph.get_connections('me','posts', fields = all_fields)

        posts_to_write = []
        list_of_pages = []

        while True:
            try:
                for post in posts['data']:
                    posts_to_write.append(post)
                requests_data = requests.get(posts['paging']['next'])
                posts = requests_data.json()
                list_of_pages.append(posts)
            except KeyError:
                #ran out of posts
                break
        with open('my_facebook_testing.json','a') as f:
            json_encoded_posts = json.dumps(posts_to_write)
            f.write(json_encoded_posts)
    return list_of_pages

### DARKSKYAPI: REQUESTS AND USES DARKSKY API TO GET THE TEMPERATURE AT THE PLACE AND TIME
### WHERE AND WHEN I MADE A POST
def get_weather(latitude, longitude, time):

    latitude = str(latitude)
    longitude = str(longitude)
    baseURL = 'https://api.darksky.net/forecast/'
    newURL = baseURL + weather_token + '/' + latitude + ',' + longitude + ',' + time
    response = requests.get(newURL)
    data = response.json()
    return(data)

### USING YELP API TO GET RESTAURANTS IN ANN ARBOR
def get_yelp(latitude, longitude):
    headers = {'authorization': bearer_token}
    if CACHED_POSTS2:
        print('using cached data')
        yelp_data = CACHED_POSTS2
    else:
        print("Retrieving data from internet")
        latitude = str(latitude)
        longitude = str(longitude)
        baseURL2 = 'https://api.yelp.com/v3/businesses/search'
        newURL2 = baseURL2 + '?latitude=' +  latitude + '&longitude=' + longitude
        response2 = requests.get(newURL2, headers = headers)
        yelp_data = response2.json()

        with open('yelp_TESTING.json','a') as f:
            json_yelp_encoded_posts2 = json.dumps(yelp_data)
            f.write(json_yelp_encoded_posts2)
    return yelp_data

my_facebook = get_posts(CACHED_POSTS)
top_hundred = my_facebook[0:100]

### CREATING DATABASE CONNECTION
conn = sqlite3.connect('Final_Project.sqlite')
cur = conn.cursor()

### CREATING TABLE NAMED Facebook WITH THESE COLUMNS
cur.execute('DROP TABLE IF EXISTS Facebook')
cur.execute('CREATE TABLE Facebook (id TEXT, status_type TEXT, message TEXT, created_time TIMESTAMP, day TEXT, time_bracket TEXT, link TEXT, longitude REAL, latitude REAL)')

### CREATING TABLE NAMED Weather WITH THESE COLUMNS
cur.execute('DROP TABLE IF EXISTS Weather')
cur.execute('CREATE TABLE Weather (id TEXT, status_type TEXT, longitude REAL, latitude REAL, temperature REAL)')

### CREATING TABLE NAMED Yelp WITH THESE COLUMNS
### TAKING ALL THE POSTS THAT HAVE A LATITUDE AND LONGITUDE ASSOCIATED WITH THEM
### AND FINDING THE TOP RESTAURANTS NEARBY
### filtered by price range, distance from latlong where post was made, rating
cur.execute('DROP TABLE IF EXISTS Restaurant_Nearby')
cur.execute('CREATE TABLE Restaurant_Nearby (id TEXT, name TEXT, location TEXT, price_range TEXT, rating REAL)')

### ITERATING THROUGH DATA AND INSERTING INTO FACEBOOK TABLE, THEN WEATHER TABLE
for index, my_posts in enumerate(top_hundred):

    ### GETTING THE LATITUDES AND LONGITUDES OF POSTS (SETTING TO 'NONE' IF THE
    ### LOCATION IS NOT AVAILABLE) BY ITERATING THROUGH NESTED DICTIONARIES
    dict_of_places = my_posts.get("place", {})
    new_dict = dict_of_places.get("location", {})
    latitude = new_dict.get("latitude", None)
    longitude = new_dict.get("longitude", None)
    time = my_posts["created_time"]

    ### SPLITTING UP TIME TO YEAR, MONTH, DAY ELEMENTS, GETTING THE DAY OF WEEK
    split_date = time.split("T")
    just_date = split_date[0]
    just_date_split = just_date.split("-")
    year = just_date_split[0]
    month = just_date_split[1]
    day = just_date_split[2]
    facebook_day = datetime.date(int(year), int(month), int(day)).weekday()

    ### CONVERTING DIGIT TO THE CORRESPONDING NAME OF THE DAY OF THE WEEK
    if facebook_day == 0:
        facebook_day = "Monday"
    elif facebook_day == 1:
        facebook_day = "Tuesday"
    elif facebook_day == 2:
        facebook_day = "Wednesday"
    elif facebook_day == 3:
        facebook_day = "Thursday"
    elif facebook_day == 4:
        facebook_day = "Friday"
    elif facebook_day == 5:
        facebook_day = "Saturday"
    else:
        facebook_day = "Sunday"

    ### BREAKING DOWN TIME INTO ADDITIONAL DATA POINTS
    ### USING: 12:00am - 5:59am, 6:00am - 11:59pm, 12pm - 5:59 pm, and 6:00pm - 11:59pm
    just_time = split_date[1].split('+')
    just_time2 = just_time[0]
    split_time = just_time2.split(':')

    hour = int(split_time[0])
    minutes = int(split_time[1])
    seconds = int(split_time[2])

    if (hour <= 5):
        time_bracket = "12:00am - 5:59am"
    elif (hour <= 11):
        time_bracket = "6:00am - 11:59am"
    elif (hour <= 17):
        time_bracket = "12:00pm - 5:59 pm"
    else:
        time_bracket = "6:00pm - 11:59pm"

    ### CREATING AND INSERTING TUPLE W/ THE INFO I WANT IN THE FACEBOOK TABLE
    tuple1 = my_posts["id"], my_posts["status_type"], my_posts.get("message", ""), time, facebook_day, time_bracket, my_posts.get("link", ""), latitude, longitude
    cur.execute('INSERT INTO Facebook (id, status_type, message, created_time, day, time_bracket, link, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', tuple1)

    ### CHECKING IF THERE IS A "PLACE" LISTED FOR THE POST
    if(type(latitude) == float):

        ### CALLING GET WEATHER FUNCTION AND PASSING THROUGH IT THE INFORMATION
        ### RETRIEVED FROM MY POSTS
        temp_at_time = get_weather(latitude, longitude, time)
        tuple2 = my_posts["id"], my_posts["status_type"], longitude, latitude, temp_at_time["currently"]["temperature"]
        cur.execute('INSERT INTO Weather (id, status_type, longitude, latitude, temperature) VALUES (?, ?, ?, ?, ?)', tuple2)

        if index < 30:
            restaurants = get_yelp(latitude, longitude) #this is a dictionary
            y = restaurants["businesses"]

            for elements in y:  # for the elements in the list (dictionaries)
                names = elements.get("name", None)
                ratings = elements.get("rating", None)
                price = elements.get("price", None)
                general_location = elements.get("location", None)
                city_within_location = general_location.get("city", None)

                tuple4 = my_posts["id"], names, city_within_location, price, ratings
                cur.execute('INSERT INTO Restaurant_Nearby (id, name, location, price_range, rating) VALUES (?, ?, ?, ?, ?)', tuple4)


conn.commit()

### PLOTLY WORK


### SELECTINGING ALL DAYS OF POSTS
days_info = cur.execute('SELECT day FROM Facebook')
days_info = days_info.fetchall() #fetchall() returns a list of tuples

list_of_frequencies = [0] * 7

days_of_week = ['Sundays', 'Mondays', 'Tuesdays', 'Wednesdays', 'Thursdays', 'Fridays', 'Saturdays']
dict_of_indices = {}

### ITERATING THROUGH TO FIND THE FREQUENCIES, GETTING A LIST OF FREQUENCIES, AND
### A DICTIONARY THAT HAS INDICES ASSOCIATED WITH DAYS OF THE WEEK
### (I.E. SUNDAY = 0, MONDAY = 1, AND SO FORTH)
for i, day in enumerate(days_of_week):
    dict_of_indices[day[0:-1]] = i
for tuples_of_days in days_info:
    x = tuples_of_days[0]
    index = dict_of_indices[x]
    list_of_frequencies[index] += 1

### MAKING A PLOTLY BAR GRAPH WITH DAYS I AM MOST ACTIVE ON FACEBOOK
data = [go.Bar(
        x = days_of_week,
        y = list_of_frequencies
        )]

layout = go.Layout(title = 'Activity Level for Each Day of the Week', xaxis = dict(title = 'Day of the Week', titlefont = dict(family = 'Courier New, monospace', size = 18,
color = '7f7f7f')), yaxis = dict(title = 'Number of Posts on Facebook', titlefont = dict(family = 'Courier New, monospace', size = 18, color = '7f7f7f')))
fig = go.Figure(data = data, layout = layout)
py.iplot(fig, filename = 'Most-Active-Days-On-Facebook')

### report_dictionary fulfills the requirement from Part 1 - Basic Work where we
### have to "create a 'report' - (screen display, file output, or other
### easy-to-read format) that shows how active you are on each day on the site.
### ZIPPING TWO LISTS INTO A DICTIONARY OF KEY AND VALUE
report_dictionary = dict(zip(days_of_week, list_of_frequencies))
print("This is a 'report' of how active I am on each day on the site (number of posts per day): ")
print(report_dictionary)

### SELECTINGING ALL DAYS OF POSTS
time_bracket_info = cur.execute('SELECT time_bracket FROM Facebook')
time_bracket_info = time_bracket_info.fetchall() #fetchall() returns a list of tuples

### ITERATING THROUGH TO FIND THE FREQUENCIES, GETTING A LIST OF FREQUENCIES, AND
### A DICTIONARY THAT HAS INDICES ASSOCIATED WITH TIMES OF DAY
### (I.E. 12:00am - 5:59am = 0, 6:00am - 11:59am = 1, AND SO FORTH)
time_bracket_list = ['12:00am - 5:59am', '6:00am - 11:59am', '12:00pm - 5:59 pm', '6:00pm - 11:59pm']
list_of_time_frequencies = [0] * 4
dict_of_time_indices = {}
for i, time in enumerate(time_bracket_list):
    dict_of_time_indices[time] = i
for tuples_of_times in time_bracket_info:
    x = tuples_of_times[0]
    index_for_time = dict_of_time_indices[x]
    list_of_time_frequencies[index_for_time] += 1

### MAKING A PLOTLY BAR GRAPH WITH TIMES I AM MOST ACTIVE ON FACEBOOK
data2 = [go.Bar(
        x = time_bracket_list,
        y = list_of_time_frequencies
        )]

layout2 = go.Layout(title = 'Activity Level for Each Time Bracket', xaxis = dict(title = 'Time of Day', titlefont = dict(family = 'Courier New, monospace', size = 18,
color = '7f7f7f')), yaxis = dict(title = 'Number of Posts on Facebook', titlefont = dict(family = 'Courier New, monospace', size = 18, color = '7f7f7f')))
fig2 = go.Figure(data = data2, layout = layout2)
py.iplot(fig2, filename = 'Most-Active-Time-Brackets-On-Facebook')

### ZIPPING TWO LISTS INTO A DICTIONARY OF KEY AND VALUE
report_time_dictionary = dict(zip(time_bracket_list, list_of_time_frequencies))
print("This is a 'report' of how active I am during each time frame on the site (number of posts per time frame): ")
print(report_time_dictionary)



### SELECTINGING ALL TEMPERATURES OF POSTS
temperature_info = cur.execute('SELECT temperature FROM Weather')
temperature_info = temperature_info.fetchall() #fetchall() returns a list of tuples

### ITERATING THROUGH TO FIND FREQUENCIES OF HOW MANY POSTS IN EACH CATEGORY OF
### TEMPERATURE
temperature_list = ['Frigid', 'Cold', 'Mild', 'Warm', 'Hot']
list_of_temp_frequencies = [0] * 5
dict_of_temp_indices = {}

for i, temp in enumerate(temperature_list):
    dict_of_temp_indices[temp] = i
for tuples_of_temps in temperature_info:
    x = tuples_of_temps[0]
    if x <= 32:
        temp_category = 'Frigid'
    elif(x > 32 and x <= 45):
        temp_category = 'Cold'
    elif(x > 45 and x <= 55):
        temp_category = 'Mild'
    elif(x > 55 and x <= 65):
        temp_category = 'Warm'
    else:
        temp_category = 'Hot'
    index_for_temp = dict_of_temp_indices[temp_category]
    list_of_temp_frequencies[index_for_temp] += 1

### MAKING A PLOTLY BAR GRAPH WITH TIMES I AM MOST ACTIVE ON FACEBOOK
data3 = [go.Bar(
        x = temperature_list,
        y = list_of_temp_frequencies
        )]

layout3 = go.Layout(title = 'Activity Level During Temperature Ranges', xaxis = dict(title = 'Weather', titlefont = dict(family = 'Courier New, monospace', size = 18,
color = '7f7f7f')), yaxis = dict(title = 'Number of Posts on Facebook', titlefont = dict(family = 'Courier New, monospace', size = 18, color = '7f7f7f')))
fig3 = go.Figure(data = data3, layout = layout3)
py.iplot(fig3, filename = 'Most-Active-Weather-Range-On-Facebook')

### ZIPPING TWO LISTS INTO A DICTIONARY OF KEY AND VALUE
report_temp_dictionary = dict(zip(temperature_list, list_of_temp_frequencies))
print("This is a 'report' of how active I am during each temperature category (number of posts per temperature category): ")
print(report_temp_dictionary)


### SELECTINGING ALL TEMPERATURES OF POSTS
pricing_rating_info = cur.execute('SELECT price_range, rating FROM Restaurant_Nearby')
pricing_rating_info = pricing_rating_info.fetchall() #fetchall() returns a list of tuples

price_bracket_list = ['$', '$$', '$$$', '$$$$']
list_of_averages = []
num_prices = len(price_bracket_list)
list_of_price_frequencies = [0] * num_prices
dict_of_price_indices = {}
list_of_rating_sum = [0] * num_prices
list_of_average_rating_per_price = []
for i, price in enumerate(price_bracket_list):
    dict_of_price_indices[price] = i
for tuples_of_pricing_and_rating in pricing_rating_info:
    price, rating = tuples_of_pricing_and_rating
    ### GETTING RID OF EUROS AND WHERE PRICING IS NONE
    if price != None and price != '€' and price != '€€' and price != '€€€' and price != '€€€€':
        index_for_price = dict_of_price_indices[price]
        list_of_price_frequencies[index_for_price] += 1
        list_of_rating_sum[index_for_price] += rating
### FINDING AVERAGE BY DIVIDING SUM BY THE NUMBER OF NUMBERS
for i in range(num_prices):
    if(list_of_price_frequencies[i]!= 0):
        list_of_averages.append(list_of_rating_sum[i]/list_of_price_frequencies[i])
    else:
        list_of_averages.append(0)

### MAKING A PLOTLY BAR GRAPH w/ COMPARISON OF PRICING AND RATINGS
### DO PRICIER RESTAURANTS HAVE HIGHER RATINGS?
data4 = [go.Bar(
        x = price_bracket_list,
        y = list_of_averages
        )]
py.iplot(data4, filename = 'Rating-Pricing-Comparison')

### ZIPPING TWO LISTS INTO A DICTIONARY OF KEY AND VALUE
report_price_rating_dictionary = dict(zip(price_bracket_list, list_of_averages))
print("This is a 'report' of how the average ratings of a restaurant compare to its average priciness. Are more expensive restaurants rated higher on average?: ")
print(report_price_rating_dictionary)
