from flask import Blueprint, render_template, request, flash, jsonify, redirect, send_file
from flask_login import login_required, current_user
from .models import Database
from . import db
import json
import os
import zipfile
from pathlib import Path
from website.utils2 import get_attendance1

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
            new_note = Database(data=note, user_id=current_user.id)  #providing the schema for the note 
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
        # Check that the file is a zip file
        if ext != '.zip':
            flash('Please upload .zip files', category='error')
            return render_template('upload.html', user=current_user)

        new_folder_path = database_path / Path(folder_name)
        new_folder_path.mkdir(parents=True, exist_ok=True)

        zip_file.save(new_folder_path / f'{filename}.zip')

        # extract and remove the first folder in the zip file
        with zipfile.ZipFile(new_folder_path / f'{filename}.zip', 'r') as zip_ref:
            zip_ref.extractall(new_folder_path, members=zip_ref.namelist()[1:] )

        os.remove(new_folder_path / f'{filename}.zip')


        new_database = Database(class_name=folder_name, class_database_path=str(new_folder_path), user_id=current_user.id)  #providing the schema for the note 
        db.session.add(new_database) #adding the note to the database 
        db.session.commit()
        
        flash("Database uploaded successfully", category='success')
        return render_template('upload.html', user=current_user)
              
    return render_template('upload.html', user=current_user)


@views.route('/attendance', methods=['POST', 'GET'])
@login_required
def attendance():
    if request.method == 'POST':
        # get the name of the folder and the zip file
        class_name = request.form['class_name']
        image = request.files['class_image']

        file_name, ext = os.path.splitext(image.filename)
        print(ext)
        # Check if the class_name is empty
        if class_name == '':
            flash('Please enter a name for the folder', category='error')
            return render_template('attendance.html', user=current_user)
        
        # Check that the file is a zip file
        # if ext != '.jpg':
        #     flash('Please upload .jpg / .jpeg / .png files', category='error')
        #     return render_template('attendance.html', user=current_user)

        image_save_path = buffer_path / f'{file_name}{ext}'
        image.save(image_save_path)
        row = Database.query.filter_by(class_name=class_name).first()
        if row:
            if row.user_id == current_user.id:
                database_path = row.class_database_path
            else:
                flash('No {class_name} database available', category='error')
                return render_template('attendance.html', user=current_user)
        else:
            flash('No {class_name} database available', category='error')
            return render_template('attendance.html', user=current_user)
        
        output = get_attendance1(str(image_save_path), database_path, True, csv_path)
        try:
            return redirect("/download_csv")
        except:
            flash('Something went wrong', category='error')
            return render_template('attendance.html', user=current_user)
    return render_template('attendance.html', user=current_user)


@views.route('/download_csv')
@login_required
def download_csv():
    return send_file(csv_path, as_attachment=True)


