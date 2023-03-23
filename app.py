from helpers import *
from app_helpers import *
from answer_parsing_helpers import *
from config import *

import pytesseract
from pytesseract import Output
from bs4 import BeautifulSoup

import streamlit as st
from datetime import datetime
import numpy as np
import pandas as pd
from ast import literal_eval

from traceback import print_exc

import json
import pickle
import requests
import certifi
from pymongo import MongoClient

import stqdm 

init_states()
st.set_page_config(page_title="APPAM Model :: Answer Digitisation", layout = "wide")

MATHPIX_API_ID = st.secrets["MATHPIX_API_ID"]
MATHPIX_API_KEY = st.secrets["MATHPIX_API_KEY"]

a1 = re.compile('((?:\d+(?:\s+|.)  \([a-z]\)))')  ## mcq
a2 = re.compile('((?:\\n\\d+\\.)(?:\\s+|<br>|</br>|<br/>))')

OUTPUT_DATA = {}
OUTPUT_DATA['page_wise_mathPix'] = []
OUTPUT_DATA['page_wise_mathPix_html'] = []
OUTPUT_DATA['page_wise_pytesseract'] = []
OUTPUT_DATA['answer_mathPix'] = ""



MONGO_URL_PROD = "mongodb+srv://mongo_jackett:fCmWGwxTJYiq3znL@cluster1.elr48.mongodb.net/mongoprod?retryWrites=true&w=majority"
MONGO_URL_DEV = "mongodb+srv://mongo_jackett:fCmWGwxTJYiq3znL@cluster0.elr48.mongodb.net/test?retryWrites=true&w=majority"
client = MongoClient(MONGO_URL_DEV, tlsCAFile=certifi.where())
dbToUse = client.test
questionsCollection = dbToUse.questions


#questions = split(q3_t, html_q_data)
#print("Number of questions :: " + str(len(questions)))
#TOKEN, _  = connect_DB(st.session_state['Username'], st.session_state['Password'])


st.markdown("""#### Upload <span style="color:red">Single PDF File</span>""", 
            unsafe_allow_html=True)
st.file_uploader("Upload pdf File", type = ["pdf", "zip"], label_visibility="hidden", key = 'uploaded_pdf')

if st.session_state['uploaded_pdf'] is not None:
    if st.session_state['uploaded_pdf'].name.endswith(".pdf") or st.session_state['uploaded_pdf'].name.endswith(".zip"):
        st.markdown("""#### Upload the json file generated when question pipeline was run""", 
                unsafe_allow_html=True)
        st.file_uploader("Upload json File", type = ["json"], label_visibility="hidden", key = 'uploaded_json')

        if st.session_state['uploaded_json'] is not None:
            print("json uploaded")
            create_sidebar()
            if st.session_state['uploaded_pdf'].name.endswith(".zip"):
                print("processing zip")
                process_zip(st.session_state['uploaded_pdf'])
                print("zip to image complete")
            else:
                print("processing pdf")
                process_pdf()
                print("pdf to image complete")

            json_file = st.session_state['uploaded_json']
            json_bytes = json_file.read()
            jsonsised_data = json.loads(json_bytes)


            QUESTIONTEXT_EXTRACTED = [i['questionText'] for i in jsonsised_data['questions']]
            QUESTIONID_EXTRACTED = [i['questionId'] for i in jsonsised_data['questions']]
            dfQuestions = pd.DataFrame({'questionText':QUESTIONTEXT_EXTRACTED,'questionId':QUESTIONID_EXTRACTED})
            dfQuestions['strip_num'] = [strip_num(i) for i in list(dfQuestions['questionText'].values)]
            dfQuestions.dropna(subset=['strip_num'], inplace=True)
            dfQuestions['strip_num'] = dfQuestions['strip_num'].astype('int32')

            if dfQuestions.shape[0] == 0:
                st.error(f"PDF identified with regex with no numbering(questions), CD method to be used", icon="❌")
                st.stop()

            if jsonsised_data['answer_page_start_fromStreamlitInput'] != -1:
                ANSWER_START = jsonsised_data['answer_page_start_fromStreamlitInput']  #st.session_state['answer_page_start']#
                ANSWER_IMAGES = list(sorted(st.session_state['image_file_paths'], key = image_name_sorting))[ANSWER_START-1:]
                print(ANSWER_IMAGES)

            else:
                ANSWER_IMAGES = list(sorted(st.session_state['image_file_paths'], key = image_name_sorting))
                print(ANSWER_IMAGES)
            
            st.markdown(f"""<h5 style="color:yellow">Click on the button below to start parsing answers and mapping to questions</h5>""", unsafe_allow_html=True)

            if st.button("Run Pipeline"):
                
                try:
                    TOKEN, _  = connect_DB(st.session_state['Username'], st.session_state['Password'])
                    #TOKEN, _  = connect_DB("mahesh@tryjackett.com", "mahesh_test")
                    
                except Exception as e:
                    st.error("Authentication Error: Enter correct Username and Password")
                    st.stop()

                html_ans_data = ""
                pytesseract_ans_data = ""
                for page_num, image_path in enumerate(ANSWER_IMAGES):
                    
                    print("Starting to call mathPix")
                    print(image_path)
                    ocr_returned = True
                    original_image_name = image_path
                    error_pages = {"page":[],"cause":[]}
                    try:
                        mathpix_response = get_mathPix_OCR(image_path, MATHPIX_API_ID, MATHPIX_API_KEY)
                    except Exception as e:
                        error_pages["page"].append(original_image_name)
                        error_pages["cause"].append("MathPix didn't return Any Data")
                        print_exc()
                        continue

                    if "error" in mathpix_response:
                        st.warning(f"Error | {mathpix_response['error']} | returned by MathPix instead of OCR for image: {image_path}")
                        error_pages["page"].append(original_image_name)
                        error_pages["cause"].append(mathpix_response['error'])
                        continue
                    
                    if "html" in mathpix_response:
                        page_text = mathpix_response['html']
                    else:
                        ocr_returned = False
                        for res in [1280, 720, 480, 224]:
                            resize(image_path, res).save(image_path)
                            mathpix_response = get_mathPix_OCR(image_path, MATHPIX_API_ID, MATHPIX_API_KEY)
                            if "html" in mathpix_response:
                                page_text = mathpix_response['html']
                                ocr_returned = True
                                break

                    pytesseract_text = get_pytesseract_text(image_path)
                    pytesseract_text = pytesseract_text.replace("\n", " ").strip()

                    OUTPUT_DATA['page_wise_mathPix'].append({image_path:mathpix_response})
                    OUTPUT_DATA['page_wise_mathPix_html'].append({image_path:page_text})

                    OUTPUT_DATA['page_wise_pytesseract'].append({image_path:pytesseract_text})


                    try:
                        html_ans_data += preprocess_text(page_text, "q3")
                        html_ans_data += "\n"
                    except Exception as e:
                        st.warning(f"Error | {e} | while appending html data : {image_path}")
                        html_ans_data += "\n"

                    pytesseract_ans_data += pytesseract_text
                    pytesseract_ans_data += "\n"

                print("MathPix extraction done")

                OUTPUT_DATA['answer_mathPix'] = html_ans_data
                OUTPUT_DATA['answer_tesseract'] = pytesseract_ans_data

                a1_regex_matches_mathPix = re.findall(a1, html_ans_data)
                a2_regex_matches_mathPix = re.findall(a2, html_ans_data)

                a1_regex_matches_pyt = re.findall(a1, pytesseract_ans_data)
                print('Regex mathces from pyta1 :: ' + str(len(a1_regex_matches_pyt)))
                print('Regex mathces from mathPix a1 :: ' + str(len(a1_regex_matches_mathPix)))
                print('Regex mathces from mathPix a2 :: ' + str(len(a2_regex_matches_mathPix)))
                if a1_regex_matches_pyt > a1_regex_matches_mathPix and a1_regex_matches_pyt> a2_regex_matches_mathPix:
                    print("pytesseract OCR engine to be used")
                    answer_data_to_parse = pytesseract_ans_data
                    selected_answer_regex = a1

                else:
                    print("mathPix OCR engine to be used")
                    answer_data_to_parse = html_ans_data
                    if len(a2_regex_matches_mathPix)==0 and len(a1_regex_matches_mathPix)==0:
                        st.error(f"Send PDF to DS team to identify answer regex, none identified.", icon="❌")

                        appam_json = json.dumps(OUTPUT_DATA)
                        st.download_button(label="Download APPAM JSON", file_name="answer_data.json", mime="application/json", data=appam_json)
        
                        st.stop()
                    elif len(a2_regex_matches_mathPix) > len(a1_regex_matches_mathPix):
                        print('Using a2 regex')
                        selected_answer_regex = a2
                    else:
                        print('Using a1 regex')
                        selected_answer_regex = a1
                print("selected_answer_regex is :: ", str(selected_answer_regex))

                answers_identified = split(selected_answer_regex, answer_data_to_parse)
                print("Number of answers identified :: ", str(len(answers_identified)))

                ### Mapping question answer
                dfAnswers = pd.DataFrame(answers_identified, columns=['questionText'])
                dfAnswers['strip_num'] = [strip_num(i) for i in list(dfAnswers['questionText'].values)]
                dfAnswers.dropna(subset=['strip_num'], inplace=True)
                print("dfAnswers shape is ::" + str(dfAnswers.shape))

                dfAnswers['strip_num'] = dfAnswers['strip_num'].astype('int32')
                if dfAnswers.shape[0] == 0:
                    st.error(f"PDF identified with regex with no numbering(answers), CD method to be used", icon="❌")
                    st.stop()


                dfQuestions = mark_section(dfQuestions)
                dfAnswers = mark_section(dfAnswers)

                dfQuestions['section_number'] = 0
                dfAnswers['section_number'] = 0
                number_of_sections_que = dfQuestions['section_number'].nunique()
                number_of_sections_ans = dfAnswers['section_number'].nunique()
                print("Starting Mapping ")

                if number_of_sections_ans==number_of_sections_que:
                    for section in dfQuestions['section_number'].unique():
                        questions_test = list(dfQuestions[dfQuestions['section_number'] == section]['questionText'].values)
                        answers_test = list(dfAnswers[dfAnswers['section_number'] == section]['questionText'].values)

                        auto_map_question_answer(questions_test, answers_test)

                        print(f"\n{round((sum([True for i in questions_test if i[1] != ''])/len(questions_test)), 3)*100}% of the Found Questions have been mapped automatically for section :: {section}")
                        st.info(f"\n{round((sum([True for i in questions_test if i[1] != ''])/len(questions_test)), 3)*100}% of the Found Questions have been mapped automatically")

                        for idx, row in dfQuestions.head(20).iterrows():
                            
                            temp_answer_df = dfAnswers[(dfAnswers['section_number']==row['section_number']) & (dfAnswers['strip_num']==row['strip_num'])]
                            if temp_answer_df.shape[0] != 0:
                                temp_answer = temp_answer_df['questionText'].values[0]
                                #callUpdateQuestionAPI(questionsCollection, TOKEN, "f0593d17-2bee-4272-890e-92f0fa87c792", row['questionText'], temp_answer)
                                callUpdateQuestionAPI(questionsCollection, TOKEN, row['questionId'], row['questionText'], temp_answer)
                                print("updated in db")
                            else:
                                print("Answer not present")
                                pass
                            #callUpdateQuestionAPI(questionCollection, row['questionId'], row['questionText'], temp_answer)
                            print("#########\n")

                    appam_json = json.dumps(OUTPUT_DATA)
                    st.download_button(label="Download APPAM JSON", file_name="answer_data.json", mime="application/json", data=appam_json)

                else:
                    st.error(f"Send PDF to DS team as number of sections in question and answers are different and mapping could go wrong.", icon="❌")

                    appam_json = json.dumps(OUTPUT_DATA)
                    st.download_button(label="Download APPAM JSON", file_name="answer_data.json", mime="application/json", data=appam_json)
                    st.stop()
