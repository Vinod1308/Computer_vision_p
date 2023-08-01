import os
import shutil
import csv
import cv2
from pathlib import Path
from retinaface import RetinaFace
from pprint import pprint
from deepface import DeepFace

import shutil


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
    image_path = str(Path(current_dir) / Path("test.jpg"))

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


def verify_face(img_path: str, db_path: str, ):
    resp = DeepFace.find(img_path, db_path, detector_backend="retinaface", model_name="VGG-Face", enforce_detection= False)
    cosine = resp[0].iloc[0]["VGG-Face_cosine"]
    if cosine > 0.2:
        return None
    else:
        identity = resp[0].iloc[0]["identity"]
        return extract_name_from_path(identity)

def get_attendance(img_path: str, db_path: str, save_as_csv, csv_file_path: str = None):
    all_students = []
    for i in os.listdir(db_path):
        if os.path.isdir(os.path.join(db_path, i)):
            all_students.append(i)

    current_dir = os.path.dirname(os.path.abspath(__file__))
    temp_path = Path(current_dir) / Path("temp")
    temp_path.mkdir(parents=True, exist_ok=True)


    resp = detect_faces(img_path, True)
    resp = extract_faces(img_path, resp["faces"], True, str(temp_path))
    output = {}
    present = []
    for file in os.listdir(temp_path):
        file_path = os.path.join(temp_path, file)
        resp = verify_face(file_path, db_path)
        if resp in all_students:
            present.append(resp)

    for student in all_students:
        if student in present:
            output[student] = "Present"
        else:
            output[student] = "Absent"
    shutil.rmtree(temp_path, ignore_errors=False)
    if save_as_csv:
        dict_to_csv(output, csv_file_path)
    return output


def dict_to_csv(output: dict, csv_file_path):
    with open(csv_file_path, 'w') as f:
        w = csv.writer(f)
        w.writerow(["Names", "Attendance"])
        for key in output.keys():
            w.writerow([key, output[key]])


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    database = str(Path(current_dir) / Path("Database"))












