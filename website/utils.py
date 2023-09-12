import os
import shutil
import csv
import cv2
from pathlib import Path
from retinaface import RetinaFace
from pprint import pprint
from deepface import DeepFace
import pandas as pd 
import shutil
from moviepy.editor import VideoFileClip

def detect_faces(img_path: str, bounding_box: bool = False):
    resp = {}
    obj = RetinaFace.detect_faces(img_path)
    resp["faces"] = obj

    if bounding_box:
        img = cv2.imread(img_path)
        for key in obj.keys():
            identity = obj[key]
            facial_area = identity["facial_area"]
            cv2.rectangle(img, (facial_area[2], facial_area[3]), (facial_area[0], facial_area[1]), (255, 255, 255), 1)
        resp["image"] = img

    return resp


def extract_faces(image_path: str, obj: dict, save_images: bool = False, save_path: str = None):
    resp = {}
    img = cv2.imread(image_path)
    if save_path[-4:] == ".jpg":
        save_path = save_path[:-4]
    for key in obj.keys():
        identity = obj[key]
        facial_area = identity["facial_area"]
        cropped_img = img[facial_area[1]: facial_area[3], facial_area[0]: facial_area[2]]
        resp[key] = cropped_img
        if save_images:
            cv2.imwrite(f'{save_path}/{key}.jpg', cropped_img)
    return resp


def main():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    image_path = str(Path(current_dir) / Path("SSP.mp4"))

    a = detect_faces(image_path, bounding_box=True)
    cv2.imwrite("output.jpg", a["image"])

    b = extract_faces(image_path, a["faces"], save_images=True, save_path=current_dir)


def create_dirtree_without_files(src_dir_path, dst_dir_path, dest_dir_name: str = None):
    src = os.path.abspath(src_dir_path)
    dst = os.path.join(os.path.abspath(dst_dir_path), dest_dir_name)
    src_prefix = len(src) + len(os.path.sep)
    os.makedirs(os.path.join(dst_dir_path, dest_dir_name), exist_ok=True)

    for root, dirs, files in os.walk(src):
        for dirname in dirs:
            dirpath = os.path.join(dst, root[src_prefix:], dirname)
            os.makedirs(dirpath, exist_ok=True)
    return dst


def crop_database(database_path: str, crop_database_base_path: str, crop_database_dir_name: str):
    dst = create_dirtree_without_files(database_path, crop_database_base_path, crop_database_dir_name)
    for directory in os.listdir(database_path):
        for file in os.listdir(os.path.join(database_path, directory)):
            if file.endswith(".jpg"):
                file_path = os.path.join(database_path, directory, file)
                crop_file_path = os.path.join(dst, directory, file)
                resp = detect_faces(file_path)
                extract_faces(file_path, resp["faces"], save_images=True, save_path=crop_file_path)

def extract_name_from_path(path: str):
    reverse = path[::-1]
    for i in range(0, 2):
        slash = reverse.find("/")
        if slash == -1:
            slash = reverse.find("\\")
        if i == 0:
            reverse = reverse[slash + 1:]
        else:
            reverse = reverse[:slash]
    name = reverse[::-1]
    return name

def separate_name_roll(input_str):
   roll_number = input_str[:9]
   name = input_str[9:].strip()
    
   return roll_number, name

def verify_face(img_path: str, db_path: str, ):
    resp = DeepFace.find(img_path, db_path, detector_backend="retinaface", model_name="VGG-Face", enforce_detection= False)
    
    if not resp[0].empty:
        cosine = resp[0].iloc[0]["VGG-Face_cosine"]
        if cosine > 0.2:
            return None
        else:
            identity = resp[0].iloc[0]["identity"]
            return extract_name_from_path(identity)
    return

    
def reduce_frame_rate(input_path, output_path, target_frame_rate):
    video_clip = VideoFileClip(input_path)
    new_video_clip = video_clip.set_fps(target_frame_rate)
    new_video_clip.write_videofile(output_path)

def get_attendance(img_path: str, db_path: str, save_as_csv, csv_file_path: str = None,attendance_date: str = None):
    reduced_video_path = 'SSP.mp4'  # Define the path for the reduced frame rate video
    target_frame_rate = 1  # Desired frame rate

    reduce_frame_rate(img_path, reduced_video_path, target_frame_rate)
    cap = cv2.VideoCapture(reduced_video_path)

    # Get the frames per second (fps) of the video
    fps = cap.get(cv2.CAP_PROP_FPS)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    print(total_frames)
    current_frame = 0
    output = {}
    attendance_data = {}
    all_students = []
    for i in os.listdir(db_path):
        if os.path.isdir(os.path.join(db_path, i)):
            all_students.append(i)

    already_marked_present = set()

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_dir = os.path.dirname(os.path.abspath(__file__))
        temp_path = Path(current_dir) / Path("temp")
        temp_path.mkdir(parents=True, exist_ok=True)
        temp_file_path = str(temp_path / f"frame_{current_frame}.jpg")

        cv2.imwrite(temp_file_path, frame)

        resp = detect_faces(temp_file_path)
        print(resp)
        resp = extract_faces(temp_file_path, resp["faces"], True, str(temp_path))

        present = []
        for file in os.listdir(temp_path):
            file_path = os.path.join(temp_path, file)
            resp = verify_face(file_path, db_path)
            if resp is not None:
                present.append(resp)

        frame_time = current_frame / fps

        # Mark students as "Present" only if they are new (not already marked as present)
        for student in all_students:
            if student in present and student not in already_marked_present:
                output.setdefault(frame_time, {})[student] = "Present"
                already_marked_present.add(student)
            else:
                output.setdefault(frame_time, {})[student] = "Absent"

        for frame_time, frame_attendance in output.items():
            for student, status in frame_attendance.items():
               attendance_data.setdefault(student, {}).setdefault(attendance_date, {})[frame_time] = status

        current_frame += 1
        shutil.rmtree(temp_path, ignore_errors=False)
    cap.release()

    if save_as_csv:
        dict_to_csv(output, csv_file_path,attendance_date)
    return output



def dict_to_csv(output: dict, csv_file_path, attendance_date):
    # Create a mapping of roll numbers to names
    roll_number_to_name = {}
    
    # Iterate through the output dictionary to collect roll numbers and names
    for frame_time, frame_attendance in output.items():
        for student in frame_attendance.keys():
            roll_number, name = separate_name_roll(student)
            roll_number_to_name[roll_number] = name

    # Check if the CSV file already exists
    existing_dates = []
    existing_data = {}
    if os.path.exists(csv_file_path):
        with open(csv_file_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                roll_number = row['Roll Number']
                name = row['Name']
                for date in reader.fieldnames[2:]:
                    if date not in existing_dates:
                        existing_dates.append(date)
                    attendance_status = row[date]
                    existing_data.setdefault(roll_number, {}).setdefault(date, attendance_status)

    # Add the new date to the list of existing dates
    if attendance_date not in existing_dates:
        existing_dates.append(attendance_date)

    with open(csv_file_path, 'w', newline='') as f:
        fieldnames = ['Roll Number', 'Name'] + existing_dates  # Include all existing dates
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for frame_time, frame_attendance in output.items():
            for student, status in frame_attendance.items():
                roll_number, _ = separate_name_roll(student)  # Use the roll number to get the name
                name = roll_number_to_name.get(roll_number, '')
                row = {'Roll Number': roll_number, 'Name': name}
                for date in existing_dates:
                    attendance_status = existing_data.get(roll_number, {}).get(date, 'Absent')
                    new_attendance = frame_attendance.get(student, 'Absent')
                    row[date] = new_attendance if new_attendance != 'Absent' else attendance_status
                writer.writerow(row)




def clean_duplicate_attendance(csv_file_path, attendance_date):
    cleaned_data = []

    existing_dates = []
    existing_data = {}
    
    roll_number_to_name = {}  # Create a mapping of roll numbers to names

    # Check if the CSV file already exists
    if os.path.exists(csv_file_path):
        with open(csv_file_path, 'r') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            for row in reader:
                roll_number = row['Roll Number']
                name = row['Name']
                for date in fieldnames[2:]:
                    if date not in existing_dates:
                        existing_dates.append(date)
                    attendance_status = row[date]
                    existing_data.setdefault(roll_number, {}).setdefault(date, attendance_status)
                    
                # Populate the roll_number_to_name mapping
                roll_number_to_name[roll_number] = name

    # Add the new date to the list of existing dates
    if attendance_date not in existing_dates:
        existing_dates.append(attendance_date)

    # Update the existing data with the new date's attendance
    for roll_number, date_data in existing_data.items():
        new_attendance = 'Absent'
        if roll_number in existing_data and attendance_date in existing_data[roll_number]:
            new_attendance = existing_data[roll_number][attendance_date]

        # Ensure that the new attendance status is not 'Absent' if there's data for that date
        for date in existing_dates:
            if date != attendance_date and date in existing_data[roll_number]:
                if new_attendance == 'Absent':
                    new_attendance = existing_data[roll_number][date]
                else:
                    new_attendance += f', {existing_data[roll_number][date]}'

        # Retrieve the name using the roll_number_to_name mapping
        name = roll_number_to_name.get(roll_number, '')

        cleaned_data.append({
            'Roll Number': roll_number,
            'Name': name,
            **{date: new_attendance for date in existing_dates}
        })

    # Write the cleaned data back to the CSV file
    with open(csv_file_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(cleaned_data)





if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    database = str(Path(current_dir) / Path("Database"))