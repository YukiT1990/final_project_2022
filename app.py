from flask import Flask, render_template, Response, request
import cv2
import time
import datetime
import csv
import os
from email.mime.text import MIMEText
import smtplib
import gmail_password
import ffmpeg
import sys
from pprint import pprint
import json

app = Flask(__name__, static_folder='./static')
data = []
cap = cv2.VideoCapture(0)
video_height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
video_width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
translation = {
  "human_face": "Human Face", 
  "human_full_body": "Human Full Body", 
  "human_upper_body": "Human Upper Body", 
  "human_lower_body": "Human Lower Body", 
  "cat_face": "Cat", 
  "dog_face": "Dog", 
  "bird_body": "Bird"
  }
user_name = "Anonymous"
user_email = ""

# for sending alert email
account = gmail_password.email_address
password = gmail_password.email_password


def gen_frames():  
    # https://github.com/opencv/opencv/tree/master/data/haarcascades
    # face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    # full body detection
    full_body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_fullbody.xml")
    # upper body detection
    upper_body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_upperbody.xml")
    # lower body detection
    lower_body_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_lowerbody.xml")
    # cat face detection
    cat_face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalcatface_extended.xml")

    # https://github.com/udacity/dog-project/blob/master/haarcascades/haarcascade_frontalface_alt.xml
    # dog face detection
    dog_face_cascade = cv2.CascadeClassifier("Haarcascades/haarcascade_frontaldogface_alt.xml")

    # https://github.com/TheLongRunSmoke/bird-haar
    # bird detection
    bird_cascade = cv2.CascadeClassifier("Haarcascades/haarcascade_bird.xml")


    detection = False
    detection_stopped_time = None
    timer_started = False
    SECONDS_TO_RECORD_DETECTION = 5

    # get the sizes of the width and the height of the frame
    frame_size = (int(cap.get(3)), int(cap.get(4)))
    # as flask does not play MPEG4 mp4 file, it must be H246
    fourcc = cv2.VideoWriter_fourcc(*"H264")

    while True:
        success, frame = cap.read()  # read the camera frame
        if not success:
            break
        else:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_cascade.detectMultiScale(gray, 1.3, 5)
            full_bodies = full_body_cascade.detectMultiScale(gray, 1.3, 5)
            upper_bodies = upper_body_cascade.detectMultiScale(gray, 1.3, 5)
            lower_bodies = lower_body_cascade.detectMultiScale(gray, 1.3, 5)
            cats = cat_face_cascade.detectMultiScale(gray, 1.3, 5)
            dogs = dog_face_cascade.detectMultiScale(gray, 1.3, 5)
            birds = bird_cascade.detectMultiScale(gray, 1.3, 5)

            # face detection
            for (x, y, width, height) in faces:  # BGR, blue
                cv2.rectangle(frame, (x, y), (x + width, y + height), (255, 0, 0), 3)

            # full body detection
            for (x, y, width, height) in full_bodies:  # BGR, green
                cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 0), 3)

            # upper body detection
            for (x, y, width, height) in upper_bodies:  # BGR, yellow
                cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 255), 3)

            # lower body detection
            for (x, y, width, height) in lower_bodies:  # BGR, pink
                cv2.rectangle(frame, (x, y), (x + width, y + height), (255, 0, 255), 3)

            # cat face detection
            for (x, y, width, height) in cats:  # BGR, purple
                cv2.rectangle(frame, (x, y), (x + width, y + height), (255, 0, 127), 3)

            # dog face detection
            for (x, y, width, height) in dogs:  # BGR, white
                cv2.rectangle(frame, (x, y), (x + width, y + height), (255, 255, 255), 3)

            # bird detection
            for (x, y, width, height) in birds:  # BGR, sky blue
                cv2.rectangle(frame, (x, y), (x + width, y + height), (255, 255, 153), 3)


            # detect someone
            if len(faces) + len(full_bodies) + len(upper_bodies) + len(lower_bodies) + len(cats) + len(dogs) + len(birds) > 0:
                cv2.putText(frame,
                    text='Intruder!!!',
                    org=(500, 100),
                    fontFace=cv2.FONT_HERSHEY_SIMPLEX,
                    fontScale=2.0,
                    color=(0, 0, 255),
                    thickness=4,
                    lineType=cv2.LINE_4)
                
                if detection:
                    timer_started = False

                else:
                    intruder_types = "";
                    if len(faces) > 0:
                      intruder_types += "human_face "
                    if len(full_bodies) > 0:
                      intruder_types += "human_full_body "
                    if len(upper_bodies) > 0:
                      intruder_types += "human_upper_body "
                    if len(lower_bodies) > 0:
                      intruder_types += "human_lower_body "
                    if len(cats) > 0:
                      intruder_types += "cat_face "
                    if len(dogs) > 0:
                      intruder_types += "dog_face "
                    if len(birds) > 0:
                      intruder_types += "bird_body "

                    detection = True
                    current_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
                    current_time_for_log = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                    # store inside static directry to play later on flask
                    out = cv2.VideoWriter(f"static/recordings/{current_time}.mp4", fourcc, 20, frame_size)
                    print("Started Recording!")
                    # record log
                    with open("log/intruder_log.csv","a") as o:
                      print(current_time_for_log, intruder_types, sep=", ", file=o) 
                    # send alert email
                    send_alert(current_time_for_log, intruder_types)

            elif detection:  # already detected sb but not anymore
                if timer_started:
                    if time.time() - detection_stopped_time >= SECONDS_TO_RECORD_DETECTION:
                        detection = False
                        timer_started = False
                        out.release()
                        print('Stop Recording!')

                else:
                    timer_started = True
                    detection_stopped_time = time.time()

            
            if detection:
                out.write(frame)

            # if pressing stop button 
            # break

            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
    
    # after finishing while loop
    # such as pressing stop button
    out.release()
    cap.release()
    cv2.destroyAllWindows()

def send_alert(date_time, intruder_content):
  csv_user = read_csv("./user_data/user")
  for row in csv_user:
    user_name = row[0]
    user_email = row[1]
    break
  if user_email == "":
    return
  date_and_time = date_time.split()
  date = date_and_time[0]
  time = date_and_time[1]
  intruders = intruder_content.split()
  pre_message = ""
  for i in range(len(intruders)):
    pre_message += translation[intruders[i]]
    if i < len(intruders) - 1:
      pre_message += ", "
  pre_message += " is/are detected at "

  # addresses
  to_email = user_email
  from_email = account

  # email content
  subject = "Intruder Alert for {} at {}".format(user_name, time)
  message = pre_message + time + " on " + date
  msg = MIMEText(message, "html")
  msg["Subject"] = subject
  msg["To"] = to_email
  msg["From"] = from_email

  # send email
  server = smtplib.SMTP("smtp.gmail.com", 587)
  server.starttls()
  server.login(account, password)
  server.send_message(msg)
  server.quit()
  


# top page
@app.route('/')
def index():
    csv_content = read_csv("./log/intruder_log")
    for row in csv_content:
        types = row[1].split()
        type_list = []
        for i in range(len(types)):
            type_list.append(translation[types[i]])
        line = {"date": row[0], "type": type_list}
        data.append(line)
        # print(data)
    today = datetime.datetime.now().strftime("%d/%m/%Y")
    now = datetime.datetime.now().strftime("%H:%M")

    csv_user = read_csv("./user_data/user")
    for row in csv_user:
      user_name = row[0]
      break
    
    
    return render_template('index.html',input_from_python= data, date=today, time=now, name=user_name, height=video_height, width=video_width)
def read_csv(filename):
    csv_file = open(str(filename) + ".csv", "r", encoding="ms932", errors="", newline="" )
    f = csv.reader(csv_file, delimiter=",", doublequote=True, lineterminator="\r\n", quotechar='"', skipinitialspace=True)
    return f
@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# recording list page
@app.route('/recordings', methods=['GET'])
def recordings_get():
  directry = './static/recordings' # inside static directry to play on flask
  files = os.listdir(directry)
  filtered_files = []
  for i in range(len(files)):
    if os.path.splitext(files[i])[1] == ".mp4": # os.path.splitext()[1] stores file extension
        filtered_files.append(files[i])
  filtered_files.sort()
  
  chosen_video = ""
  title = "Not Selected"
  duration = "_"
  codec = "_"
  v_height = "_"
  v_width = "_"
  ratio = "_"

  return render_template(
    'recordings.html', 
    file_paths=filtered_files, 
    video_name=chosen_video, 
    title=title,
    duration=duration,
    codec=codec,
    v_height=v_height,
    v_width=v_width,
    ratio=ratio
  )

@app.route('/recordings', methods=['POST'])
def recordings_post():
  directry = './static/recordings' # inside static directry to play on flask
  files = os.listdir(directry)
  filtered_files = []
  for i in range(len(files)):
    if os.path.splitext(files[i])[1] == ".mp4": # os.path.splitext()[1] stores file extension
        filtered_files.append(files[i])
  filtered_files.sort()
  
  if request.form['video'][0] != "D":
    chosen_video = request.form['video']

    video_meta_data = ffmpeg.probe('./static/recordings/' + chosen_video)["streams"]
    video_meta_data = video_meta_data[0]
    
    title = chosen_video
    duration = video_meta_data['duration']
    codec = video_meta_data['codec_long_name']
    v_height = video_meta_data['coded_height']
    v_width = video_meta_data['coded_width']
    ratio = video_meta_data['display_aspect_ratio']
  else:
    chosen_video = request.form['video'][1:]
    os.remove('./static/recordings/' + chosen_video)

    files = os.listdir(directry)
    filtered_files = []
    for i in range(len(files)):
      if os.path.splitext(files[i])[1] == ".mp4": # os.path.splitext()[1] stores file extension
          filtered_files.append(files[i])
    filtered_files.sort()

    title = "Video Name " + chosen_video + " is deleted."
    duration = "_"
    codec = "_"
    v_height = "_"
    v_width = "_"
    ratio = "_"
    chosen_video = ""
    
  return render_template(
    'recordings.html', 
    file_paths=filtered_files, 
    video_name=chosen_video, 
    title=title,
    duration=duration,
    codec=codec,
    v_height=v_height,
    v_width=v_width,
    ratio=ratio
  )

# settings page
@app.route('/settings', methods=['GET'])
def settings_get():
  title = "Registration and Settings"
  message = "Register or update your name and email address."
  return render_template('settings.html', title=title, message=message)

@app.route('/settings', methods=['POST'])
def settings_post():
  user_name = request.form['name']
  user_email = request.form['email']
  title = "Hi, {}!".format(user_name)
  message = "Your email address is {}.".format(user_email)
  with open("user_data/user.csv","w") as o:
    print(user_name, user_email, sep=", ", file=o)
  return render_template('settings.html', title=title, message=message)

# manage logs page
@app.route('/logs', methods=['GET'])
def logs_get():
  return render_template('logs.html')

if __name__=='__main__':
    app.run(debug=True)



"""
References
https://www.youtube.com/watch?v=mzX5oqd3pKA
https://github.com/krishnaik06/Flask-Web-Framework
"""