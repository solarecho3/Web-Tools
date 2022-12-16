import streamlit as st
import hashlib as hl

def signup(email, pwd, confpwd):
    if confpwd == pwd:
        encoded_pwd = confpwd['']

# https://medium.com/@moinahmedbgbn/a-basic-login-system-with-python-746a64dc88d6
# https://www.section.io/engineering-education/user-login-web-system/
# https://gist.github.com/ib-lundgren/6507798
# https://falconframework.org/