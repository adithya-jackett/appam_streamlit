import streamlit as st


def init_states():
    '''
    Init new states
    '''
    if "zipped_path" not in st.session_state:
        st.session_state['zipped_path'] = None

    if "display_image" not in st.session_state:
        st.session_state['display_image'] = None

    if "image_points" not in st.session_state: # Points to plot on image [header margin ,footer margin , vert_line-1, vert_line-1]
        st.session_state['image_points'] = [30,30,None,None]

    if 'image_file_paths' not in st.session_state:
        st.session_state['image_file_paths'] = None
    
    if 'image_splits_mapping' not in st.session_state:
        st.session_state['image_splits_mapping'] = {}

    if "file_dir" not in st.session_state:
        st.session_state['file_dir'] = None
    
    if "image_counter" not in st.session_state:
        st.session_state['image_counter'] = 0

    if "Line 1" not in st.session_state:
        st.session_state["Line 1"] = 0

    if "Line 2" not in st.session_state:
        st.session_state["Line 2"] = 0
    
    if "col_detection" not in st.session_state:
        st.session_state["col_detection"] = None


def create_sidebar():
    '''
    Render these parts when Zip File is uploaded. 
    1. Upload Zip File
    2. Unzip and process Zip file
    '''
    with st.sidebar:
        st.markdown("#### Enter Username & Password")

        col1, col2 = st.columns(2)
        with col1:
            _ = st.text_input("Username", key = "Username", help = "Enter username for which you want to run the pipeline")
        
        with col2:
            _ = st.text_input("Password", key = "Password", help = "Password for the above username",)


        #st.markdown("#### Enter no of columns")
        #st.number_input("No of columns", min_value= 1, max_value = 3, key="num_columns", label_visibility="collapsed", on_change = reset_vertical_lines_callback) # Numbers of columns in image

        st.markdown("#### Enter answer page start")
        st.number_input("Answer page start", key="answer_page_start", step=1, label_visibility="collapsed")


        #st.markdown("_"*10)
        #if st.button(label = "Click to use the most recently used tags", key = "recent_tags", disabled = False if st.session_state["Username"] else True):
        #    get_set_recent_tags()

        #with st.expander("Click & expand to enter the values of tags you already know", expanded=False):
        #    for tag_name in MAPPING.keys():
        #        _ = st.text_input(tag_name, key = MAPPING[tag_name], placeholder = "")

        #try:
            #st.markdown("_"*10)
            #st.write("Please fill the following details: ([Source]({}))".format(get_teacher_name_worksheet_url()))
            #st.session_state["DIGITISING_FOR_TEACHER"] = st.selectbox("""Who are you digitising for?""", get_teacher_name_tuple())
            #st.session_state["DIGITISED_BY"] = st.selectbox("""Who are you?""", get_digitiser_name_tuple())
            #st.session_state["EXPORT_DATA_SHEET"] = st.selectbox("""What sheet would you like to see the metadata in?""", get_export_worksheet_names())
            #update_export_sheet(st.session_state["EXPORT_DATA_SHEET"])
            # Somehow, updating the selectbox runs this piece of code again.
            #st.session_state["WRITE_MAPPING_DATA"] = st.checkbox("Create Mapping Data?", value=True)
            #if not st.session_state["WRITE_MAPPING_DATA"]:
            #    st.markdown("""Mapping Data will <span style="color:red"><b><i>not</i></b></span> be created""", unsafe_allow_html=True)

        #except Exception as e:
        #    st.warning("Something went wrong while loading the legends list: " + str(e))
        #    print_with_date(e)
        
        #st.markdown("_"*10)
        #st.markdown("#### Upload Chapter Sheet")
        #st.session_state["chapter_sheet"] = st.file_uploader("Chapter Sheet", type = ["csv", "xls", "xlsx"], label_visibility="hidden")

