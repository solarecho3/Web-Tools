import streamlit as st
import web_tools
import glob
import re
import pandas as pd
import numpy as np

### Initialize a Twitter session
t = web_tools.Twitter_Session()
t.get_token_local("keys.json")

### Initialiaze the Streamlit GUI
s = web_tools.Streamlit_Functions()

### Get a line from the bard
l = web_tools.random_line()

### Get boilerplate with metrics
s.set_boilerplate(page_title="solarecho3/Web Tools", metrics=False)

### Show the Web Tools tutorial on your Streamlit page.
# web_tools.tutorial()

### Snapshot a user.
# t1.get_user_snapshot('elonmusk')

selected_db = st.selectbox(label="Select DB", options=glob.glob("data/*.db"))

if selected_db:

    t1 = web_tools.Database_Functions().list_db_tables(selected_db)

    # st.write(list(t1))

    count = 0

    for i in list(t1):

        df = pd.read_sql_table(table_name=i, con=f"sqlite+pysqlite:///{selected_db}")

        st.write(
            f"""

        Schema: {(str(i).capitalize())}

        Length: {len(df)}

        Count: {count}
        """
        )

        st.dataframe(data=df, use_container_width=True)

        count += 1
