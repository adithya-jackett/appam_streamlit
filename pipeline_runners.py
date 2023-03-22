import re



def run_answer_pipeline():

    #if st.session_state["col_detection"] is None:
    #    st.session_state["col_detection"] = get_cols_data(st.session_state['image_file_paths'])
    
    #st.warning(f"Single / Multi Column stats:  {st.session_state['col_detection']}", icon="🚩")


        process_second_part(st.session_state['file_dir']) # digitise questions from images

        #Q_GEN = QuestionGeneration()

        with st.spinner("Trying to find if there's any pattern in the data for Ans"):
        total_images = len(st.session_state['image_file_paths'])
        regex_test_data = []
        
        print(st.session_state['image_file_paths'])
        
        for i in np.random.choice(st.session_state['image_file_paths'], min(4,total_images), replace = False):
            print(i)
            print(cv2.imread(i).shape)
            try:
                ocr = get_mathPix_OCR(i, MATHPIX_API_ID, MATHPIX_API_KEY)['html']
                regex_test_data.append(ocr)
            except Exception as e:
                print_with_date(f"MathPix data return error for {i} during regex testing : {e}")
                print_exc()
                continue

        #QUESTION_REGEX, statement, selected_regex = Q_GEN.select_priority_regex(regex_test_data)
        ## code to select regex
        


        if statement:
            st.info(statement,icon="ℹ️")
            del i, regex_test_data
        else:
            st.error("Unable to find any Ques - Ans pattern in the data, might be a new pattern. Send PDF along with the screenshot to DS Team and use MCQ or CD Pipeline for now",icon="❌")
            st.stop()