import re
import requests
from bs4 import BeautifulSoup

import cv2
import pytesseract
from pytesseract import Output


def get_pytesseract_text(image_path):
    """
        Function to return the pytesseract output
        Input ::  
        image_path : path to where image is stored
        
        Output
        str : pyteseeract outpout string
    """
    image = cv2.imread(image_path)
    
    custom_oem_psm_config = r'--oem 1 --psm 12'
    #results = pytesseract.image_to_data(image, output_type=Output.DICT, config=custom_oem_psm_config)
    pyt_text = pytesseract.image_to_string(image, config=custom_oem_psm_config)

    return pyt_text

def split(REGEX, data):
    result = []
    start = 0
    for pat in re.finditer(REGEX, data):
        pat_start = pat.span()[0]
        result.append(data[start: pat_start])
        start = pat_start
    
    result.append(data[start:])
    return result

def preprocess_text(html:str, selected_regex:str = None) ->str:
    '''
    Change Every NESTED <li> tag (whose ANY parent is <li>)  OR  any <li> tag whose parent is not <ol>
    AND
    `<ol start = "NUM"> <li> some data </li>` to -> 'NUM.  some data'  if selected_regex == 'q3'
    '''
    soup = BeautifulSoup(html, 'html.parser')

    for tag in soup.find_all('li', recursive=True): # change child <li> to <REPLACEli>
        if (tag.find_parents("li") or (not tag.find_parents("ol"))): tag.name = 'REPLACEli'
    
    if selected_regex == 'q3': # if selected_regex == q3, try to force change every <li> elemment in a number format
        for ol in soup.find_all("ol", start = True):
            start = int(ol["start"])
            for li in ol.find_all("li"):
                li.insert_before("\n"+str(start)+".\n")
                li.unwrap()
                start += 1
            ol.unwrap()
    
    return str(soup).replace("<br/>","<br>") # because MCQ won't be selected or we'll have to change MCQ finder Regex


def strip_num(string):
    num = ''
    for i in string.lstrip("\n .:"): # strip the SPACE, DOT, SEMI Column from left just to be sure
        #print(i)
        if i.isdigit(): num +=i
        else:
            try:
                return int(num)
            except ValueError: return None


def auto_map_question_answer(questions:list, answers:list):
    '''
    Given list of Questions and Answers, map each Question to it's respective Answer

    1. Traverse the Question and Answer Array
    2. If Question is more than answer, Pop the Question. If Answer is More than Question, Pop the answer.
    3. If Number of Question == Num of answer -> Save (question,answer)
    '''
    i = 0
    j = 0 # Index of answer array
    while True: # because we have to Map every Question to every answer
        try:
            que = questions[i]
            ans = answers[j]

            q_num = strip_num(que)
            a_num = strip_num(ans)


            if (q_num is None) or (a_num is None):
                if q_num is None:i += 1
                if a_num is None:j += 1
                continue

            if q_num == a_num:
                questions[i] = (que, ans)
                # print(f"Mapped Que: {q_num} to Ans: {a_num}")
                i += 1
                j += 1

            elif q_num > a_num:
                j += 1 # If answer is smaller, skip to next answer
            
            else: # skip to next question
                i += 1

        except IndexError:
            break
    
    for i, que in enumerate(questions):
        if isinstance(que, str): # means no answer was matched
            questions[i] = (que, "")


#a = [1,2,3,4,5,6,7, 9, 10,11,1,2, 5, 7,10,11,12,14,15,3,4,6,7,8, 9, 15]
#a = [2,3,4,5,6,7, 9, 10,11,2, 5, 7,10,11,1,2,3,4,1,3,4,6,7,8, 9, 15, 4,5,7,8,9,12,13,15]

def mark_section(question_df):

    least_number_in_each_section = int(question_df['strip_num'].value_counts().index[0])
    number_of_sections = int(list(question_df['strip_num'].value_counts().values)[0])

    #print("number_of_sections :: " + str(number_of_sections))
    #print("least_number_in_each_section :: " + str(least_number_in_each_section))

    start_indices = list(question_df[question_df['strip_num']==least_number_in_each_section].index)
    #print(start_indices)

    start = 0
    question_df['section_number'] = 0

    initial_sections_split = []

    for i in range(0,(number_of_sections)):
        temp_section = []
        #print(i)
        if i == number_of_sections-1:
            end = question_df.shape[0]
        else:
            end = start_indices[i+1]
        #print(start, end)
        #print("section value is :: " + str(i))
        question_df[start:end]['section_number'] = i
        temp_section = list(question_df[start:end]['strip_num'].values)
        initial_sections_split.append(temp_section)
        start=end


    final_out_section = []

    temp_section_final_split = []
    temp_section_final_split_next_section = []
    for section_idx, section_in_spl in enumerate(initial_sections_split):    
        #print( "\nList value" , section_in_spl)
        #print("\n",temp_section_final_split_next_section)
        #print("Initial list value :: ", section_in_spl)
        section_in_spl = temp_section_final_split_next_section+section_in_spl
        temp_section_final_split_next_section = []
        #print( "Appended List value :: " , section_in_spl)
        for idx, row in enumerate(section_in_spl):
            if idx!=0:
                if row<prev_value:
                    temp_section_final_split_next_section = temp_section_final_split_next_section + section_in_spl[idx:]
                    break
                else:
                    temp_section_final_split.append(row)
                    prev_value = row
            else:
                prev_value = row
                temp_section_final_split.append(row)
        #print("FInal output val :: " , temp_section_final_split)
        #print(temp_section_final_split_next_section)
        #print("\n")
        final_out_section.append(temp_section_final_split)
        temp_section_final_split = []

    final_out_section.append(temp_section_final_split_next_section)
    
    question_df['section_number'] = 0
    start = 0
    for idx, row in enumerate(final_out_section):
        #print(idx)
        end = start + len(row)
        #print(start, end)
        question_df[start:end]['section_number'] = idx

        start = end
    
    return question_df


def get_question_data_from_mongo(questionsCollection, questionId):
    question_mongo = list(questionsCollection.find({'questionId':questionId}, 
                         {'options':1, 'questionType':1, 'questionId':1, 
                          'questionText':1, 'answers':1}))
    print(question_mongo[0]['questionId'])
    return question_mongo[0]

def mark_answer(answer:str):
    '''
    Mark the Answer
    '''
    ans = 10
    if '(a)' in answer: ans = 0
    elif '(b)' in answer: ans = 1
    elif '(c)' in answer: ans = 2
    elif '(d)' in answer: ans = 3
    
    return ans

def callUpdateQuestionAPI(questionsCollection, TOKEN, UPDATE_QUESTION_ID, UPDATE_QUESTION_TEXT, in_answer_text):

    UPDATE_QUESTION_URL = "http://jackett-development-v1.ap-southeast-1.elasticbeanstalk.com/api/v3/questions/"
    UPDATE_QUESTION_URL = UPDATE_QUESTION_URL + UPDATE_QUESTION_ID
    
    QUESTION_NUMBER = strip_num(UPDATE_QUESTION_TEXT)
    print("number stripped from question text")
    
    answer = "NOT MAPPED"
    #for i in answers:
    if strip_num(in_answer_text) == QUESTION_NUMBER:
        answer = in_answer_text
            
    if answer == "NOT MAPPED":
        return 
    
    update_answer_data = {}
    update_answer_data['options'] = []
    update_answer_data['answers'] = []

    mongo_question_data = get_question_data_from_mongo(questionsCollection, UPDATE_QUESTION_ID)
    print("question data exttracted from db")

    answerOptionListId = mark_answer(answer)
    update_answer_data['options'] = mongo_question_data['options']
    update_answer_data['answers'] = mongo_question_data['answers']
    print("answerOptionListId is :: " + str(answerOptionListId))
    if answerOptionListId!=10:
        update_answer_data['options'][answerOptionListId]['isAnswer'] = True
    #try:
    #    update_answer_data['options'][answerOptionListId]['isAnswer'] = True
    #except:
    #    print("not mcq type")
    update_answer_data['answers'][0]['answerText'] = answer

    update_question_header = { "accept": "application/json",
                "content-type": "application/json",
                'authorization': "Bearer " + str(TOKEN)
              }
    
    print("adding to db, print inside the function")
    update_answer_resp = requests.put(UPDATE_QUESTION_URL, json=update_answer_data, headers=update_question_header)
    print("Updated in DB")
    print(update_answer_resp)
    print(update_answer_resp.text)


    return 