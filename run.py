import os
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import requests
import PyPDF2
import json

app = Flask(__name__)
app.secret_key = 'your_secret_key'

app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:Shanky4829@localhost/flaskdrive'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)

class UploadedFile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    original_name = db.Column(db.String(255), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    content_type = db.Column(db.String(100))
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))


with app.app_context():
    db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        if User.query.filter((User.username == username) | (User.email == email)).first():
            return render_template('signup.html', message="User already exists. Try logging in.")

        new_user = User(username=username, email=email, password_hash=password)
        db.session.add(new_user)
        db.session.commit()
        return render_template('index.html', message="Signup successful!")

    return render_template('signup.html')



@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password_hash, request.form['password']):
            login_user(user)
            return render_template('main.html', message="Login successful!")
        return render_template('index.html', message="Invalid credentials. Try again.")

    return render_template('index.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('index.html')

@app.route('/main')
def main():
    return render_template('main.html')

@app.route('/upload', methods=['GET', 'POST'])
@login_required
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)

            upload = UploadedFile(
                original_name=file.filename,
                filename=filename,
                content_type=file.content_type,
                user_id=current_user.id
            )
            db.session.add(upload)
            db.session.commit()
            return render_template('main.html')

    files = UploadedFile.query.filter_by(user_id=current_user.id).order_by(UploadedFile.upload_time.desc()).all()
    return render_template('main.html', files=files)

@app.route('/uploads/<filename>')
@login_required
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/api/files', methods=['GET'])
@login_required
def api_files():
    files = UploadedFile.query.filter_by(user_id=current_user.id).order_by(UploadedFile.upload_time.desc()).all()
    return jsonify([
        {
            'filename': f.original_name,
            'stored_as': f.filename,
            'uploaded_at': f.upload_time.isoformat(),
            'content_type': f.content_type
        } for f in files
    ])

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads') 
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/summarize', methods=['GET'])
def summarize_file():
    filename = request.args.get("file")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    if not os.path.exists(filepath):
        return "File not found", 404

    
    if filename.lower().endswith('.pdf'):
        text = extract_text_from_pdf(filepath)
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

    if not text.strip():
        return "No content to summarize.", 400

    
    try:
        res = requests.post("http://localhost:11434/api/generate", 
         json={
              "model": "llama3.2",  
             "prompt": f"Summarize this file in short in two to three sentences:\n\n{text[:3000]}"
             }, 
         stream=False)

        if res.status_code == 200:
            summary = ""
            for line in res.iter_lines():
                if line:
                    data = json.loads(line.decode("utf-8"))
                    if "response" in data:
                        summary += data["response"]
            return summary.strip()
        else:
            return f"Request failed with status {res.status_code}: {res.text}", 500

    except Exception as e:
        return f"Ollama error: {str(e)}", 500


def extract_text_from_pdf(pdf_path):
    text = ""
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            text += page.extract_text() or ""
    return text

if __name__ == '__main__':
    app.run(debug=True)