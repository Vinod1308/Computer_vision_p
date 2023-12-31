from flask import Blueprint, render_template, request, flash, jsonify, redirect, send_file
from flask_login import login_required, current_user
from .models import Database
from . import db
import json
import os
import zipfile
from pathlib import Path
import time
from website.utils import get_attendance,clean_duplicate_attendance

views = Blueprint('views', __name__)

current_dir = os.path.dirname(os.path.abspath(__file__))
database_path = Path(current_dir) / Path("database")
buffer_path = Path(current_dir) / Path("buffer")
csv_path = Path(buffer_path) / Path("attendance.csv")

@views.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST': 
        note = request.form.get('note')#Gets the note from the HTML 

        if len(note) < 1:
            flash('Note is too short!', category='error') 
        else:
            new_note = Note(data=note, user_id=current_user.id)  #providing the schema for the note 
            db.session.add(new_note) #adding the note to the database 
            db.session.commit()
            flash('Note added!', category='success')

    return render_template("home.html", user=current_user)

@views.route('/upload', methods=['POST', 'GET'])
@login_required
def upload_database():
    if request.method == 'POST':

        # get the name of the folder and the zip file
        folder_name = request.form['folder_name']
        zip_file = request.files['zip_file']
        
        filename, ext = os.path.splitext(zip_file.filename)
        # Check if the folder_name is empty
        if folder_name == '':
            flash('Please enter a name for the folder', category='error')
            return render_template('upload.html', user=current_user)
        
        class_in_db = Database.query.filter_by(class_name=folder_name).first()
        if not class_in_db:
            flash(f'Class "{folder_name}" does not exist.', category='error')
            return render_template('upload.html', user=current_user)
        # Check that the file is a zip file
        if ext != '.zip':
            flash('Please upload .zip files', category='error')
            return render_template('upload.html', user=current_user)
        
        new_folder_path = os.path.join(database_path, folder_name)
        os.makedirs(new_folder_path, exist_ok=True)

        zip_file.save(os.path.join(new_folder_path, f'{filename}.zip'))

        # extract and remove the first folder in the zip file
        with zipfile.ZipFile(os.path.join(new_folder_path, f'{filename}.zip'), 'r') as zip_ref:

            zip_ref.extractall(new_folder_path)


        os.remove(os.path.join(new_folder_path, f'{filename}.zip'))

      
            
        new_database = Database(class_name=folder_name, class_database_path=str(new_folder_path), user_id=current_user.id)
        db.session.add(new_database)
        db.session.commit()
        
        flash("file uploaded in class successfully", category='success')
        return render_template('upload.html', user=current_user)
              
    return render_template('upload.html', user=current_user)

@views.route('/create_new_class', methods=['GET', 'POST'])
@login_required
def create_new_class():
    if request.method == 'POST':
        class_name = request.form.get('class_name')

        folder_path = database_path / Path(class_name)
        folder_path.mkdir(parents=True, exist_ok=True)
    
        if class_name == " ":
            flash('Please enter a class name.', category='error')
            return render_template("create_new_class.html", user=current_user)
        else:
            # Assuming 'current_user' is the faculty creating the class
            new_class = Database(class_name=class_name, class_database_path=str(folder_path),user_id=current_user.id)
            db.session.add(new_class)
            db.session.commit()
            flash('Class created successfully!', category='success')
            return render_template("create_new_class.html", user=current_user)

    return render_template("create_new_class.html",user=current_user)


@views.route('/edit_class', methods=['POST', 'GET'])
@login_required
def edit_class():
    if request.method == 'POST':
        class_name = request.form['class_name']

        if not class_name:
            flash('Please enter a class name.', category='error')
            return render_template('edit_class.html', user=current_user, class_data=None)

        class_to_edit = Database.query.filter_by(class_name=class_name, user_id=current_user.id).first()

        print("class to edit :",class_to_edit)
        if not class_to_edit:
            flash(f'Class "{class_name}" does not exist.', category='error')
            return render_template('edit_class.html', user=current_user, class_data=None)

        print("Class To Edit:", type(class_to_edit))  # Debugging message

        class_data = {
            'class_name': class_to_edit.class_name,
            'class_database_path': class_to_edit.class_database_path,
        }

        print("Class Data:", class_data)  # Debugging message

        class_files = []
        if class_to_edit.class_database_path:
            class_directory_path = os.path.join(class_to_edit.class_database_path, class_name)
            if os.path.exists(class_directory_path) and os.path.isdir(class_directory_path):
                class_files = [filename for filename in os.listdir(class_directory_path) if filename.endswith('.jpg')]
                print("Class Files:", class_files)  # Debugging message
            else:
                print("Class directory not found")  # Debugging message

        class_data['class_files'] = class_files

        return render_template('edit_class.html', user=current_user, class_data=class_data)

    return render_template('edit_class.html', user=current_user, class_data=None)


@views.route('/attendance', methods=['POST', 'GET'])
@login_required
def attendance():
    if request.method == 'POST':
        start_time = time.time()
        # get the name of the folder and the zip file
        class_name = request.form['class_name']
        image = request.files['class_image']
        attendance_date = request.form['attendance_date']  # Get the selected attendance date
        csv_path = Path(buffer_path) / Path(class_name+"attendance.csv")

        
        file_name, ext = os.path.splitext(image.filename)
        print(ext)
        # Check if the class_name is empty
        if class_name == '':
            flash('Please enter a name for the folder', category='error')
            return render_template('attendance.html', user=current_user)
        
        #Check that the file is a zip file
        # if ext != '.jpg':
        #     flash('Please upload .jpg / .jpeg / .png files', category='error')
        #     return render_template('attendance.html', user=current_user)

        image_save_path = os.path.join(buffer_path, f'{file_name}{ext}')  # Use os.path.join
        image.save(image_save_path)
        row = Database.query.filter_by(class_name=class_name).first()

        if row:
            if row.user_id == current_user.id:
                database_path = row.class_database_path
                # print("Database Path:", database_path)  # Add this line for debugging
            else:
                flash('No {class_name} database available', category='error')
                return render_template('attendance.html', user=current_user)
        else:
            flash('No {class_name} database available', category='error')
            return render_template('attendance.html', user=current_user)
        print("Image_save:",image_save_path)
        
        output = get_attendance(image_save_path, database_path, True, csv_path,attendance_date)
        clean_duplicate_attendance(csv_path,attendance_date)
        end_time = time.time()
        execution_time = (end_time-start_time)/60
        print(f"Execution Time: {execution_time:.2f} minutes")
        try:
            return redirect(f"/download_csv/{class_name}")
        except:
            flash('Something went wrong', category='error')
            return render_template('attendance.html', user=current_user)
    return render_template('attendance.html', user=current_user)

@views.route('/download_csv/<class_name>')
@login_required
def download_csv(class_name):
    csv_file_path = os.path.join(buffer_path, f"{class_name}attendance.csv")
    return send_file(csv_file_path, as_attachment=True, download_name=f"{class_name}attendance.csv")

# def download_csv(class_name):
#     return send_file(csv_path, as_attachment=True)



