import os
import re
import shutil
import multiprocessing 
import zipfile

import json
import requests
import imagesize
from PIL import Image
import cv2
import streamlit as st

import numpy as np
from pdf2image import convert_from_bytes


def _detect_columns(path, k, block_width_thresh = 0.20):

    img = cv2.imread(path, 0)
    h, w = img.shape
    img = img[int(h*0.3):(h - int(h*0.3)), :] # Keep 40% Horizontal middle part only and 90% Vertical

    blur = cv2.GaussianBlur(img,(7,7),0)

    ret,mask = cv2.threshold(blur,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1,k))  # to manipulate the orientation of dilution , large X means horizonatally effect more, large Y means vertically dilating more
    mask = cv2.erode(mask, kernel, iterations=10)  # erode -> Increase size of black , more the iteration more erosion

    mask_col_means =  mask.mean(axis = 0).astype(int) # mean of each pixel column
    prev = mask_col_means[0] # Last accessed Pixel column

    result = {} # stores [start_index, end_index, length_of block] for each White (background) and black (words) found

    if prev not in result:
        result[prev] = []

    result[prev].append([0]) # first column could be Black or White. Mean is other than 0 or 255 when there are mixed pixels

    first_word_pixel_index = None # When does first column comes which is not white, it is the place where ANY of the word came
    for ind, curr_col_mean in enumerate(mask_col_means[1:]): # index starts from 0 but it'll already be at Col Num 1 so add +1 to evert index number
        if curr_col_mean not in result: result[curr_col_mean] = []
        
        index = ind + 1

        if first_word_pixel_index is None and curr_col_mean != 255: first_word_pixel_index = index
        if first_word_pixel_index and curr_col_mean != 255: last_word_pixel_index = index # what is the last place where ANY Non, white column occured

        if prev != curr_col_mean: # if different block starts

            block_length = index-1  - result[prev][-1][0] # length of the block that just ended at last index

            result[prev][-1].extend([index-1, block_length]) # last block was the ending index of last block
            result[curr_col_mean].append([index]) # current index is the starting point of this block

        prev = curr_col_mean

    block_length = index-1  - result[prev][-1][0]
    result[prev][-1].extend([index-1, block_length])

    width_text_area = last_word_pixel_index - first_word_pixel_index

    num_cols = 0
    for black_col in result[0]:
        if black_col[-1] >= (block_width_thresh * width_text_area): num_cols += 1

    return num_cols


def get_cols_data(image_paths):
    col_data = {1:0, 2:0, 3:0, "Error": 0}

    for index, image in enumerate(image_paths):
        try:
            num_cols = _detect_columns(image, k = 91, block_width_thresh = 0.23)
            col_data[num_cols] += 1

        except:
            col_data["Error"] += 1
    
    return col_data

def is_image(image_path):
    return image_path.split('.')[-1] in ["jpg","JPG", "PNG", "png", 'JPEG', "jpeg"]


def image_name_sorting(image_name):
    '''
    Criteria for sorting the images name based on some number. Used as a `key` argument in sorted()
    '''
    split_num = None

    if "-<SPLIT-" in image_name:
        image_name, split_num = image_name.split("-<SPLIT-")

    found = re.findall("\d+",image_name)
    if not found : raise Exception("No number found for sorting criteria. Rename you images on some numbering basis like page or so")

    return int(found[-1] + split_num[0]) if split_num else int(found[-1])

MAX_THREADS = min(4, multiprocessing.cpu_count())
basewidth = 1100 # image resizing 

def override_print_with_date():
    '''
    Override Print statement to include the Time for the logging by default
    '''
    import pytz

    IST = pytz.timezone('Asia/Kolkata')

    _print = print # keep a local copy of the original print
    return lambda *args, **kwargs: _print(datetime.now(IST).strftime("%D %H:%M:%S"), *args, **kwargs)

print_with_date = override_print_with_date()

def resize(image, new_width_height = 1920):
    '''
    Resize and return Given Image
    args:
    path: Image Path
    new_width_height = Reshaped image's width and height. If integer is given, it'll keep the aspect ratio as it is by shrinking the Bigger dimension (width or height) to the max of new_width_height  and then shring the smaller dimension accordingly 
    '''
    if isinstance(image, np.ndarray):
        image = Image.fromarray(image)
    elif isinstance(image, str):
        image = Image.open(image)

    w, h = image.size

    if (w > new_width_height) or (h > new_width_height):

        fixed_size = new_width_height if isinstance(new_width_height, int) else False

        if fixed_size:
            if h > w:
                fixed_height = fixed_size
                height_percent = (fixed_height / float(h))
                width_size = int((float(w) * float(height_percent)))
                image = image.resize((width_size, fixed_height), Image.Resampling.NEAREST)

            else:
                fixed_width = fixed_size
                width_percent = (fixed_width / float(w))
                height_size = int((float(h) * float(width_percent)))
                image = image.resize((fixed_width, height_size), Image.Resampling.NEAREST) 

        else:
            image = image.resize(new_width_height)

    return image

def resize_all_images(input_images):
    '''
    Resize all images as bigger size images are not supported in the backend as well as Mathpix also
    '''
    for image_path in input_images:

        width, height = imagesize.get(image_path)
        if (width < 1920) and (height < 1920): continue
        
        if image_path.lower().endswith(".png"):
            resize(image_path).save(image_path)
        else:
            resize(image_path).save(image_path, quality=100, subsampling=0) # to preserve the quality


def extract_images_from_pdf(PDF_FILE, destination_path, first_page = None, last_page = None):
    
    try:
        os.mkdir(destination_path)
    except:
        shutil.rmtree(destination_path)
        os.mkdir(destination_path)


    images = convert_from_bytes(PDF_FILE, 250, destination_path, fmt = "jpeg", output_file = "thread",
        first_page = first_page, last_page = last_page, paths_only = True, thread_count = MAX_THREADS)

    return images


def process_zip(zip_file): # part of second flow
    '''
    Extract the zip file uploaded
    '''
    print("zip_file is :: "+ str(zip_file))
    st.session_state['file_dir'] = zip_file.name.split(".zip")[0]

    if os.path.exists(st.session_state['file_dir']): # if the directory exists, clean the directory
        shutil.rmtree(st.session_state['file_dir'])

    with zipfile.ZipFile(zip_file, "r") as z:
        z.extractall(st.session_state['file_dir'])

    st.session_state['image_file_paths'] = sorted([os.path.join(st.session_state['file_dir'],i ) for i in os.listdir(st.session_state['file_dir']) if is_image(i)], 
                                            key = image_name_sorting)
    
    
    resize_all_images(st.session_state['image_file_paths']) # resize images which are bigger than Full HD 1920
   
    image = Image.open(st.session_state['image_file_paths'][st.session_state['image_counter']])
    if image.mode == "RGBA": image = image.convert("RGB")
    st.session_state['display_image'] = np.array(image)


def process_pdf(): # part of First Flow
    '''
    Givne a PDf, extract images from it
    '''
    pdf = st.session_state['uploaded_pdf']
    
    in_pdf = pdf.read()
    dir_path = pdf.name.split(".pdf")[0]

    if os.path.exists(dir_path): # remove directory if exists
        shutil.rmtree(dir_path)
    

    _ = extract_images_from_pdf(in_pdf, dir_path)


    st.session_state['file_dir'] = dir_path
    st.session_state['image_file_paths'] = sorted([os.path.join(st.session_state['file_dir'],i ) for i in os.listdir(st.session_state['file_dir']) if is_image(i)], 
                                            key = image_name_sorting)
    
    resize_all_images(st.session_state['image_file_paths']) # resize images to full HD
    image = Image.open(st.session_state['image_file_paths'][st.session_state['image_counter']])
    if image.mode == "RGBA": image = image.convert("RGB")
    st.session_state['display_image'] = np.array(image)

    st.session_state['zipped_path'] = shutil.make_archive(dir_path, 'zip', dir_path)


def fix_html(in_string:str)->str:
        '''
        Given a HTML string, fix it's tags tree and clean tags in such a way that it can be rendered properly on mobile, webapp
        '''
        in_string = BeautifulSoup(in_string, "html.parser").prettify().strip() # fix html tree if missing

        out_string = re.compile(r"<\/?span[^>]*>").sub("", in_string)
        out_string = re.compile(r"<\/?mathml[^>]*>").sub("", out_string)
        out_string = re.compile(r"<div>").sub("", out_string)
        out_string = re.compile(r"</div>").sub("", out_string)
        out_string = re.sub("\s+", " ", out_string)
        return out_string

def get_mathPix_OCR(image_path:str, MATHPIX_API_ID:str, MATHPIX_API_KEY:str):

    mathPix_raw_out = requests.post("https://api.mathpix.com/v3/text",
                            files={"file": open(image_path,"rb")},
                            data={
                                    "options_json":json.dumps({
                                        "formats":['html'],  # data , need "text" ?
                                        "include_line_data": True,
                                        "enable_spell_check": True,
                                        "include_smiles": True,
                                        
                                        "data_options": {"include_mathml": True, 'include_table_html':True}, # include_latex and others

                                    })
                                },
                            headers={
                                    "app_id": MATHPIX_API_ID,
                                    "app_key": MATHPIX_API_KEY
                                }
                             )

    mathPix_json_out = mathPix_raw_out.json()     
    return mathPix_json_out



loginUrl = "http://jackett-development-v1.ap-southeast-1.elasticbeanstalk.com/api/v1/auth/login"
def connect_DB(USERNAME, PASSWORD):

    login_headers = {"accept": "application/json",
                    "content-type": "application/json"
                    }

    login_data = {"username":USERNAME,
            "password":PASSWORD}
        
    respLogin = requests.post(url=loginUrl, headers=(login_headers), data=json.dumps(login_data))

    respLoginJson = respLogin.json()


    TOKEN = respLoginJson['data']['token']
    USERNAME = respLoginJson['data']['username']

    return TOKEN, USERNAME