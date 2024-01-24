from flask import Flask, render_template, redirect, url_for, session, request, flash, get_flashed_messages
from flask import Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired
from flask_bcrypt import Bcrypt
import cv2, sys, numpy as np, os, base64, joblib, face_recognition
from io import BytesIO
from PIL import Image,UnidentifiedImageError
haar_file = 'haarcascade_frontalface_default.xml'
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

app = Flask(__name__)
@app.after_request
def add_header(response):
    response.cache_control.no_store = True
    return response

# Use SQLite database file named 'users.db' located in the project directory
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SECRET_KEY'] = '\xfd{H\xe5<\x95\xf9\xe3\x96.5\xd1\x01O<!\xd5\xa2\xa0\x9fR"\xa1\xa8'
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
db = SQLAlchemy(app)

class Authenticate(db.Model, UserMixin):
    sno = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(200), nullable=False, unique=True)
    password = db.Column(db.String(200), nullable=False)

    def __repr__(self) -> str:
        return f"{self.sno} - {self.username} - {self.password}"
    def get_id(self):
        return str(self.sno)

@login_manager.user_loader
def load_user(user_id):
    return Authenticate.query.get(int(user_id))

@app.route("/", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        uname = request.form['uname']
        pwd = request.form['pwd']

        user = Authenticate.query.filter_by(username=uname).first()
        if user and bcrypt.check_password_hash(user.password, pwd):
            login_user(user)
            if current_user.is_authenticated:
                flash('Login Successful!','info')
            return redirect(url_for('home'))
        else:
            return render_template('login.html', error="Invalid credentials")

    return render_template("login.html")

@app.route("/home")
@login_required
def home():
    return render_template("home.html") 

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out", "info")
    return redirect(url_for('login'))

@app.route('/addstudent')
def to_addStudent():
    return render_template('addStudent.html')

@app.route('/markattendance')
def to_markAttendance():
    return render_template('markAttendance.html')


def recognize():
    size = 4
    datasets='trained_faces'
    (images, labels) = ([], [])
    id_to_name = {}
    model = cv2.face.LBPHFaceRecognizer_create()

    for (subdirs, dirs, files) in os.walk(datasets):
        for subdir in dirs:
            subject_path = os.path.join(datasets, subdir)
            id_to_name[len(id_to_name)] = subdir
            for filename in os.listdir(subject_path):
                path = os.path.join(subject_path, filename)
                label = len(id_to_name) - 1
                image = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
                if image is not None:
                    images.append(image)
                    labels.append(label)

    model.train(images, np.array(labels))

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    webcam = cv2.VideoCapture(1,)
    width = 100
    height = 100

    for frame in generate_frames():
        ret, im = webcam.read()
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        for (x, y, w, h) in faces:
            cv2.rectangle(im, (x, y), (x + w, y + h), (255, 0, 0), 2)
            face = gray[y:y + h, x:x + w]
            face_resize = cv2.resize(face, (width, height))
            
            label, confidence = model.predict(face_resize)
            if confidence < 90:
                recognized_name = id_to_name[label]
                cv2.putText(im, recognized_name, (x, y), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0))
            else:
                cv2.putText(im, 'Not Recognized', (x, y), cv2.FONT_HERSHEY_PLAIN, 1, (0, 255, 0))

        _, jpeg = cv2.imencode('.jpg', im)
        frame = jpeg.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
        key = cv2.waitKey(1)
    webcam.release()
    cv2.destroyAllWindows()

@app.route('/video_recog')
def video_recog():
    return Response(recognize(), mimetype='multipart/x-mixed-replace; boundary=frame')

#This route calls the generate_frames function continuously, for capturing 50 images
@app.route('/video_get')
def video_get():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

def generate_frames():
    datasets = 'trained_faces'  
    sub_data = 'Shreyash Chilip'     
    path = os.path.join(datasets, sub_data)
    if not os.path.isdir(path):
        os.mkdir(path)
    (width, height) = (130, 100)    
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    webcam = cv2.VideoCapture(1, cv2.CAP_DSHOW)  # Use the default camera
    count = 1

    while count <= 50:  # Adjust the number of frames as needed
        _, im = webcam.read()
        gray = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 4)

        for (x, y, w, h) in faces:
            cv2.rectangle(im, (x, y), (x + w, y + h), (255, 0, 0), 2)
            face = gray[y:y + h, x:x + w]
            face_resize = cv2.resize(face, (width, height))
            cv2.imwrite(os.path.join(path, f'{count}.png'), face_resize)

        _, jpeg = cv2.imencode('.jpg', im)
        frame = jpeg.tobytes()

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

        count += 1

    webcam.release()
    cv2.destroyAllWindows()


@app.route('/process_video_frames', methods=['POST'])
def process_video_frames():
    try:
        image_data_bytes = request.data

        # Convert bytes to numpy array
        nparr = np.frombuffer(image_data_bytes, np.uint8)

        # Decode numpy array into an image
        image_cv2 = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Check if the image is empty
        if image_cv2 is not None and not np.all(image_cv2 == 0):
            # Convert cv2 image to RGB
            image_pil = Image.fromarray(cv2.cvtColor(image_cv2, cv2.COLOR_BGR2RGB))
            # Continue with face recognition or other processing
            image_pil.save('image.jpeg')
            recognize_face(process_image(image_pil))
            return 'Success'
        else:
            print("Error: Unable to decode the image.")
            return 'Error: Unable to decode the image.'

    except Exception as e:
        print(f"Unexpected error: {e}")
        return 'Unexpected error occurred.'

def process_image(image):
    # Resize the image to a smaller size (150x150) for faster face detection
    image = image.resize((1366, 1024))
    # Convert the image to RGB format
    image = image.convert("RGB")
    image.save('image1024.jpeg')
    return image

def recognize_face(image):
    known_face_encodings = joblib.load('known_face_encodings.joblib')
    try:
        known_face_names = joblib.load('known_face_names.joblib')
    except (Exception) as e:
        print(f"Exception!: {e}")
        known_face_names=[]

    image = process_image(image)
    image_np = np.array(image)

    # Find faces in the frame
    face_locations = face_recognition.face_locations(image_np)
    face_encodings = face_recognition.face_encodings(image_np, face_locations)

    if not face_encodings:
        print("No faces found in the image.")
        return

    for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
        # Compare the face with known faces
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding)

        name = "Unknown"

        # Use the first match found
        if True in matches:
            first_match_index = matches.index(True)
            name = known_face_names[first_match_index]
            print("Found : " + name)
        else:
            print(name)


if __name__ == "__main__":
    app.run(debug=False, port=int(os.environ.get('PORT', 5000)))
