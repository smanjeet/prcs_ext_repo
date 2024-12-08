import streamlit as st
import pandas as pd
import json

#from langchain import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain_openai import OpenAI
from langchain_openai import ChatOpenAI

import os
from datetime import datetime
import re
from datetime import UTC

from pathlib import Path


def grep_file(file_path, pattern):
    compiled_pattern = re.compile(pattern)
    grep_result = ''
    with open(file_path, 'r') as file:
        for line in file:
            if compiled_pattern.search(line):
                grep_result += line
                grep_result += '\n'
    return grep_result

@st.cache_data
def pull_logs(id):
    if 'component' in st.session_state:
        st.write("Search in logs for given Id : " + id)
        st.write("Searching logs for Component : [" + st.session_state['component'] + "]")
        logfile = logs[st.session_state['component']]
        component_logs = grep_file(logfile, id)
        return component_logs
    else:
        st.write("No component found!")


def load_config_data():
    if not st.session_state['templates_loaded']:
        with open(config_file, 'r') as json_file:
            #json.dump(config_data, json_file)
            config_data = json.load(json_file)
            template_file = config_data['template_store']
            print('templates are stored in : ' + template_file)
            st.session_state['templates_loaded'] = True


################ Main App Start ################
#Page title and header
st.title('PT-ProcessTracker')
st.subheader("Identify and Track process flow through logs", divider="blue")

st.session_state['component'] = None
st.session_state['templates_loaded'] = False
config_file=r'prcs_ext_config.json'
config_data = None

COMPONENTS = ["Choose a component", "Orders", "OrderPersistor", "Blotter", "Pricing", "Booking"]

component = st.selectbox("Choose component to investigate", COMPONENTS)
st.session_state['component'] = component


################ Load data Start ################
load_config_data()


################ Pull Logs Start ################
st.header('PT - Pull logs', divider="blue")
logs = {}
logs['Orders'] = r'data\server1\orders.log'


input_id = st.text_area(label="Text", label_visibility='collapsed', placeholder="ID to search...", key="input_id")

matching_logs = ""

if st.button("GetLogs"):
    st.text("PT - Matching logs:")
    matching_logs = pull_logs(input_id)
    st.write("############################# Following logs have been pulled:")
    st.write(matching_logs)

################ Pull Logs End ################


################ Load Templates Start ################

st.subheader('PT - Load Template', divider="blue")

template_store = r'C:\Users\User\projects\prcs_ext_demo\prcs_ext_demo\data\template_store'

### Crete empty dataframe if no template store found
df = None

my_file = Path(template_store)
if my_file.is_file():
    if os.path.getsize(template_store) > 0:
        df = pd.read_csv(template_store)
        st.write("--> Loaded templates")
    else:
        df = pd.DataFrame(columns=["Key", "TemplateText", "Added"])


#Replace any numerical or alphanumeric word with "<*>".
#Remove log indicator as INFO or DEBUG.
#Remove module and other details in "[" and "]"
#Return back the remaining LogSnippet as is.
#Replace any numerical or alphanumeric word with "<*>".
# First of all, remove date or time in any format.
# On the remaining LogSnippet:
# For any Key:Value pairs, where Key is alphabetic, replace Value with "<*>".
# Remove log level indicators as INFO or DEBUG.
#Remove module and other details within "[" and "]".
#Replace any numerical or alpha-numeric word with "<*>".

process_template_creation = """
Do the following steps on given LogSnippet:
Remove date or time in any format.
For all Key:Value pairs, where Key is alphabetic, replace Value with "<*>"
For all Key=Value pairs, where Key is alphanumeric, replace Value with "<*>"
Return back the remaining LogSnippet as is.

LogSnippet = {log}
"""

#PromptTemplate variables definition
prompt = PromptTemplate(
    input_variables=["log"],
    template=process_template_creation,
)


################ Function to load LLM and Keys ################
def load_LLM():
    """Logic for loading the chain you want to use should go here."""
    # Make sure your openai_api_key is set as an environment variable
    #llm = OpenAI(temperature=0, openai_api_key=openai_api_key)
    llm = ChatOpenAI(model="gpt-4o", temperature=0) #="gpt-3.5-turbo")
    return llm

################ Load LLM ################
openai_api_key = os.getenv('OPENAI_API_KEY')
llm = load_LLM()


@st.cache_data
def invoke_llm(prompt):
    draft_template = llm.invoke(prompt)
    return draft_template



if st.button("Create Template from logs"):
    pulled_logs = pull_logs(input_id)
    formatted_prompt = prompt.format(
        log=pulled_logs
    )
    # st.write("############################# Following prompt will be sent to LLM:")
    # st.write(formatted_prompt)
    st.write("############################# Following template has been created by LLM:")
    prcs_template = invoke_llm(formatted_prompt)
    st.write(prcs_template)


# Version = 1
# if st.button("Save Template to store"):
#     pulled_logs = pull_logs(input_id)
#     formatted_prompt = prompt.format(
#         log=pulled_logs
#     )
#     prcs_template = invoke_llm(formatted_prompt)
#     st.write(prcs_template)
#     if prcs_template and len(prcs_template.content) > 0:
#         df.loc[len(df)] = [st.session_state["component"],"ORDERTYPE", prcs_template, datetime.now(UTC).strftime("%Y%m%d"), Version]
#         df.to_csv(template_store, sep=',', index=False, encoding='utf-8')

################ Load Templates End ################

process_template = """
Given the process steps in a ProcessTemplate, compare these with the LogSnippet and provide the first line of ProcessTemplate that is not matched in LogSnippet.
Also provide the first line of LogSnippet that is not matched with ProcessTemplate.
If all lines in ProcessTemplate match LogSnippet, report "All Matched!"

ProcessTemplate = {process_template}

LogSnippet = {log}
"""

match_prompt = PromptTemplate(
    input_variables=["process_template", "log"],
    template=process_template,
)

logs_to_match = ""

search_id = st.text_area(label="Text", label_visibility='collapsed', placeholder="ID to search...", key="search_id")

if st.button("Match logs to ProcessTemplate"):
    pulled_logs = pull_logs(input_id)
    formatted_prompt = prompt.format(
        log=pulled_logs
    )
    st.markdown("##### Following template has been generated by LLM from ExecId: " + input_id)
    prcs_template = llm.invoke(formatted_prompt)
    st.write(prcs_template)

    logs_to_match = pull_logs(search_id)
    formatted_match_prompt = match_prompt.format(
        process_template=prcs_template,
        log=logs_to_match
    )
    #st.markdown("#### Following prompt will be sent to LLM:")
    #st.write(formatted_match_prompt)
    st.markdown("#### Result of matching Process Template to logs for ExecId: " + search_id)
    llm_response = llm.invoke(formatted_match_prompt)
    st.write(llm_response.content)