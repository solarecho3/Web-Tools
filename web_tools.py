import datetime
import glob
import json
import pickle
import random
import re
import sys
import time
import urllib.parse
from dataclasses import dataclass

import pandas
import requests
import sqlalchemy

"""
I'm using pdoc to write the API documentation.
$: pdoc ./web_tools.py -o ./documentation/
"""


@dataclass
class Twitter_Session:

    """
    A Twitter session object.

    #### Parameters

        token : str - The bearer token for public metrics. Acquired via a Twitter developer account. Use the get_token_local() method to set.

    #### Attributes

        token : str - The bearer token for this instance.

        session : object - The requests.Session object for this instance.

        history : list - History of URL calls made by this instance.

        limit_log : dict - Metrics parsed from Twitter response headers. Used to set metrics trackers by the application.

        query_log : dict - Log of queries made. Primarily used to find session query terms.
    """

    twitter_enrollment_period = "29 October"

    def __init__(self):

        """
        Instantiate the session object. Requires no parameters.
        """

        self.session = requests.Session()
        """Creates a request.session object unique to the instance."""

        self.response = ""
        """The last requests.response object received."""

        self.limit_log = {}
        """The log of Twitter server rates and limits. Appended as the endpoint is accessed. Refer: https://developer.twitter.com/en/docs/twitter-api/rate-limits"""

        self.query_log = {}
        """The log of Twitter queries and responses. Use to reference the transaction id, search term, etc."""

    def get_token_local(self, path: str) -> None:

        """
        Retreive a Twitter bearer token from a JSON with the following schema:

            {'keys':

                'Bearer Token': 'token'

                }

        #### Parameters

            path : str - File path to the JSON. Must be accessible with open(), and readable by read().

        #### Attributes

            self.token : str - The bearer token string.
        """

        with open(file=path, mode="r") as file:

            temp = json.loads(file.read())

            self.token = temp["keys"]["Bearer Token"]
            """This session's bearer token. Acquired from a Twitter developer account. Refer: https://developer.twitter.com/en/docs/twitter-api/getting-started/getting-access-to-the-twitter-api"""

    def get_url(self, url: str) -> None:

        """
        Simple HTTP GET request.

        #### Parameters

            url : str - The complete URL, with or without a scheme. If no scheme is specified, defaults to 'https://'.

        #### Attributes

            self.response : Response - The complete requests.response object, set to the class variable response.
        """

        try:  # try the call

            self.response = self.session.get(
                url, headers={"Authorization": f"Bearer {self.token}"}, stream=False
            )

        except requests.exceptions.MissingSchema:

            # print(sys.exc_info())

            self.response = self.session.get(
                url=f"https://{url}",
                headers={"Authorization": f"Bearer {self.token}"},
                stream=False,
            )

    def get_user_profile(self, username: str, **kwargs) -> pandas.DataFrame:

        """
        Request Twitter's users by username endpoint. Resets index.

        #### Parameters

            username : str - The @username. Can be passed with or without '@'.

            timer : bool

        #### Returns

            pandas.DataFrame - A parsed DataFrame generated from the response JSON.
        """

        if "timer" in kwargs.keys():

            timer = kwargs["timer"]

        else:

            timer = False

        if timer is True:

            print("sleeping...-_-...")

            time.sleep(59)

        if username[0] == "@":

            username = username[1:]

        self.get_url(
            url=f"https://api.twitter.com/2/users/by/username/{username}?user.fields=description,public_metrics,profile_image_url"
        )

        try:

            self.limit_log["user_profile"] = self.return_server_limits()

            self.limit_log["user_profile"]["checked_at"] = datetime.datetime.now()

            df = pandas.DataFrame(data=self.response.json()["data"])

            df = df.reset_index()

            df = df.rename(columns={"index": "metric"})

            return df

        except KeyError:

            self.limit_log["user_profile"] = self.return_server_limits()

            self.limit_log["user_profile"]["checked_at"] = datetime.datetime.now()

            return pandas.DataFrame(self.response.json()["errors"])

    def get_user_tweets(self, user_id: str, **kwargs):

        """
        Get all a user's tweets. This is a costly operation in that Twitter paginates tweets

        100 at a time. Due to rate limits, and depending on how many tweets a user has, this

        may take a while. Twitter rate epochs reset 15 minutes after the first call has been

        made. The rate limits vary. Refer to the rate limits returned in the headers of this

        class.

        #### Parameters

            user_id : str - The Twitter user's id. This is typically a 64-bit unsigned integer. Passed back to the server as a string to avoid accuracy loss. Read more: https://developer.twitter.com/en/docs/twitter-ids

            pages : int - Number of pages to request. Pages are 100 tweets. To get a user's entire profile, check their tweet count, divide by 100, and round up. If pages is not specified, the function will run recursively until all available pages have been retrieved or the rate limit has been reached.

            timer : bool

        #### Returns

            pandas.DataFrame - The DataFrame with a user's tweets.

        #### Example

            Getting all available user tweets

            `df = t1.get_user_profile('elonmusk')`
            `df = t1.get_user_tweets(df['id'][0], round(df['tweet_count'][0] / 100))`
        """

        df = pandas.DataFrame()

        if "pages" in kwargs.keys():

            pages = kwargs["pages"]

        else:

            pages = 1500

        for i in range(pages):

            if i == 0:

                self.get_url(
                    f"https://api.twitter.com/2/users/{user_id}/tweets?tweet.fields=created_at,text,public_metrics&max_results=100"
                )

                if self.response.json().get("title"):

                    if self.response.json()["title"] == "UsageCapExceeded":

                        raise Exception("Usage cap exceeded for Tweets.")

                        break

                if self.response.json().get("data"):

                    df = pandas.DataFrame(self.response.json()["data"])

            else:

                try:

                    next_token = self.response.json()["meta"]["next_token"]

                    self.get_url(
                        f"https://api.twitter.com/2/users/{user_id}/tweets?tweet.fields=created_at,text,public_metrics&max_results=100&pagination_token={next_token}"
                    )

                    df2 = pandas.DataFrame(self.response.json()["data"])

                    df = pandas.concat([df, df2], axis=0)

                except KeyError:

                    break

            if kwargs.get("timer", False):

                if kwargs["timer"] is True:

                    print("sleeping...-_-...")

                    time.sleep(59)

        try:

            df = df.reset_index()

            df2 = pandas.DataFrame.from_records(df["public_metrics"])

            self.limit_log["user_tweets"] = self.return_server_limits()

            self.limit_log["user_tweets"]["checked_at"] = datetime.datetime.now()

            return pandas.concat([df, df2], axis=1).drop(
                labels=["index", "public_metrics"], axis=1
            )

        except KeyError:

            self.limit_log["user_tweets"] = self.return_server_limits()

            self.limit_log["user_tweets"]["checked_at"] = datetime.datetime.now()

            if self.response.json().get("errors"):

                return pandas.DataFrame(self.response.json()["errors"])

            else:

                return pandas.DataFrame([self.response.json()])

    def get_user_following(self, user_id: str, **kwargs):

        """
        Get all the users the requested account follows. If `pages` is not specified the function will run recursively.

        Endpoint: Users > Follows lookup > Limit: 15

        #### Parameters

            user_id : str - The Twitter user's id. This is typically a 64-bit unsigned integer. Passed back to the server as a string to avoid accuracy loss. Read more: https://developer.twitter.com/en/docs/twitter-ids

            pages : int - Number of pages to request. Pages are 100 tweets. To get a user's entire profile, check their tweet count, divide by 100, and round up. If pages is not specified, the function will run recursively until all available pages have been retrieved or the rate limit has been reached.

            timer : bool - Default `False`. If `True`, the script will use a sleep timer to prevent running over the rate limit. This means one page is collected per minute, until the end of pagination.

        #### Returns

            pandas.DataFrame - The DataFrame with a user's tweets.
        """

        df = pandas.DataFrame()

        if "pages" in kwargs.keys():

            pages = kwargs["pages"]

        else:

            pages = 15

        for i in range(pages):

            if i == 0:

                self.get_url(
                    f"https://api.twitter.com/2/users/{user_id}/following?user.fields=id,name,username,public_metrics&max_results=1000"
                )

                df = pandas.DataFrame(self.response.json()["data"])

            else:

                try:

                    next_token = self.response.json()["meta"]["next_token"]

                    self.get_url(
                        f"https://api.twitter.com/2/users/{user_id}/following?user.fields=id,name,username,public_metrics&max_results=1000&pagination_token={next_token}"
                    )

                    df2 = pandas.DataFrame(self.response.json()["data"])

                    df = pandas.concat([df, df2], axis=0)

                except KeyError:

                    break

            if "timer" in kwargs.keys():

                timer = kwargs["timer"]

            else:

                timer = False

            if timer is True:

                print("sleeping...-_-...")

                time.sleep(59)

        self.limit_log["user_following"] = self.return_server_limits()

        self.limit_log["user_following"]["checked_at"] = datetime.datetime.now()

        return df

    def get_user_followers(self, user_id: str, **kwargs):

        """
        Get a user's followers.

        Attributes

            pages : int

            timer : bool
        """

        df = pandas.DataFrame()

        if "pages" in kwargs.keys():

            pages = kwargs["pages"]

        else:

            pages = 15

        for i in range(pages):

            if i == 0:

                self.get_url(
                    f"https://api.twitter.com/2/users/{user_id}/followers?user.fields=id,name,username,public_metrics&max_results=1000"
                )

                df = pandas.DataFrame(self.response.json()["data"])

            else:

                try:

                    next_token = self.response.json()["meta"]["next_token"]

                    self.get_url(
                        f"https://api.twitter.com/2/users/{user_id}/followers?user.fields=id,name,username,public_metrics&max_results=1000&pagination_token={next_token}"
                    )

                    df2 = pandas.DataFrame(self.response.json()["data"])

                    df = pandas.concat([df, df2], axis=0)

                except KeyError:

                    break

            if kwargs.get("timer", False):

                if kwargs["timer"] is True:

                    print("sleeping...-_-...")

                    time.sleep(59)

        self.limit_log["user_followers"] = self.return_server_limits()

        self.limit_log["user_followers"]["checked_at"] = datetime.datetime.now()

        return df

    def get_user_snapshot(self, username: str, **kwargs):

        """
        Get profile, tweets, following, and followers of user
        with no page limits, and write to db.

        Must already have instantiated a Twitter_Session class
        object, and passed it a bearer token using get_token_local().

        Parameters

            username : str - The @username. Can be passed with or without '@'.

            followers : bool - Gather followers. Default == `False`.

            following : bool - Gather following. Default == `False`.
        """

        df = self.get_user_profile(username)
        self.df_to_db(df["id"][0], df, "profile")

        df2 = self.get_user_tweets(df["id"][0])
        self.df_to_db(df["id"][0], df2, "tweets")

        if kwargs.get("followers", False):

            df3 = self.get_user_following(df["id"][0])
            self.df_to_db(df["id"][0], df3, "following")

        elif kwargs.get("following", False):

            df4 = self.get_user_followers(df["id"][0])
            self.df_to_db(df["id"][0], df4, "followers")

    def get_string_query(self, query: str, **kwargs):

        """
        Query Twitter. Returns the last n pages of tweets containing the query string.

        #### Parameters

            query : str - The string to be searched for. Can include hashtags.

            pages : int - The number of pages to return. A page is 100 tweets. Default = 0.
        """

        if "pages" in kwargs.keys():

            pages = kwargs["pages"]

        else:

            pages = 1

        df = pandas.DataFrame()

        for i in range(pages):

            if i == 0:

                self.get_url(
                    f"https://api.twitter.com/2/tweets/search/recent?query={urllib.parse.quote(query)}&max_results=100"
                )

                self.limit_log["query"] = self.return_server_limits()

                self.limit_log["query"]["checked_at"] = datetime.datetime.now()

                df = pandas.DataFrame(self.response.json()["data"])

            else:

                next_token = self.response.json()["meta"]["next_token"]

                self.get_url(
                    f"https://api.twitter.com/2/tweets/search/recent?query={urllib.parse.quote(query)}&max_results=100&pagination_token={next_token}"
                )

                self.limit_log["query"] = self.return_server_limits()

                self.limit_log["query"]["checked_at"] = datetime.datetime.now()

                df2 = pandas.DataFrame(self.response.json()["data"])

                df = pandas.concat([df, df2], axis=0)

        self.query_log[len(self.query_log)] = {
            "timestamp": datetime.datetime.now(),
            "x-transaction-id": self.response.headers["x-transaction-id"],
            "query_term": query,
            "parsed_query_term": urllib.parse.quote(query),
        }

        return df.reset_index()

    def return_server_limits(self) -> tuple[float, float, str, int, str]:

        """
        Return Twitter server rate limits and timers from the response in memory. Used to update the limit log internally.

        #### Returns

            A dictionary with the following schema:

                {
                    'remaining': float,
                    'limit': float,
                    'limit_reset': str,
                    'percent_remaining': int,
                    'limit_delta': str
                    }

            ##### Attributes

                remaining : float - Transmission-rate limit remaining in epoch for this endpoint.

                limit : float - Total call limit for the endpoint, per epoch.

                limit_reset : str - The time when the limit epoch resets. Converted from unix time stamp to a string with `%H:%M:%S` format.

                percent_remaining : int - Percentage remaining in the call limit, for this epoch.

                limit_delta : str - Difference between when the limit resets and now, in `%H:%M:%S` format.
        """

        return_headers = self.response.headers

        remaining = float(return_headers["x-rate-limit-remaining"])

        limit = float(return_headers["x-rate-limit-limit"])

        percent_remaining = int(float(remaining) / float(limit) * 100)

        # TODO rename this variable
        # NOTE this is used as the delta in a streamlit.metric object
        remaining_math = (100 - percent_remaining) * -1

        # TODO there has to be a better way than the following:
        limit_reset = time.strftime(
            "%H:%M:%S", time.localtime(int(return_headers["x-rate-limit-reset"]))
        )

        limit_reset = datetime.datetime.strptime(limit_reset, "%H:%M:%S")

        limit_reset = limit_reset.time()

        time_now = datetime.datetime.now()

        time_now = datetime.datetime.strptime(
            f"{time_now.hour}:{time_now.minute}:{time_now.second}", "%H:%M:%S"
        )

        time_now = time_now.time()

        limit_reset = datetime.datetime.combine(datetime.date.today(), limit_reset)

        time_now = datetime.datetime.combine(datetime.date.today(), time_now)

        limit_delta = str(limit_reset - time_now)

        limit_reset = datetime.datetime.strftime(limit_reset, "%H:%M:%S")

        dict = {
            "remaining": remaining,
            "limit": limit,
            "limit_reset": limit_reset,
            "percent_remaining": percent_remaining,
            "limit_delta": limit_delta,
        }

        return dict

    def df_to_db(self, id: str, data: pandas.DataFrame, type: str, **kwargs):

        """
        Write user's twitter data to a SQLite3 database using an SQLAlchemy engine.

        #### Parameters

            data : pandas.DataFrame - The DataFrame with user profile data, as formatted by get_user_profile().

            type : str - profile, tweets, following, query

            query_term : str - The term used in a get_string_query().

        #### Attributes

            id : str - The table id to be stored under. If type is profile, tweets, or following the id will be the user id of the profile. If a query, use 'x-transaction-id' from the query response header.

        #### Example

            `t1 = Twitter_Session()`
            `t1.get_token_local('/home/user/keys.json')`
            `df = t1.get_user_profile('elonmusk')`
            `t1.df_to_db(user_id = df['id'][0], data = df, type='profile')`
            `df2 = t1.get_user_tweets(user_id = df['id'][0])`
            `t1.df_to_db(user_id = df['id'][0], data = df2, type='tweets')`
        """

        try:

            query_term = kwargs["query_term"]

        except KeyError:

            query_term = ""

        if type == "profile":

            engine = sqlalchemy.create_engine(f"sqlite:///data/{id}.db")

            table_name = "profile"

        elif type == "tweets":

            engine = sqlalchemy.create_engine(f"sqlite:///data/{id}.db")

            table_name = "tweets"

        elif type == "following":

            engine = sqlalchemy.create_engine(f"sqlite:///data/{id}.db")

            table_name = "following"

        elif type == "followers":

            engine = sqlalchemy.create_engine(f"sqlite:///data/{id}.db")

            table_name = "followers"

        elif type == "query":

            engine = sqlalchemy.create_engine("sqlite:///data/twitter_queries.db")

            table_name = id
            """For queries, use self.response.headers['x-transaction-id']"""

            data.insert(0, "query_term", [query_term for i in range(len(data))])

        else:

            raise ValueError("type must be one of: profile, tweets, following, query")

        try:

            data.insert(
                0,
                "capture_timestamp",
                [datetime.datetime.now() for i in range(len(data))],
            )

        except ValueError:  # work-around to avoid producing a Nonetype DataFrame

            data.drop(labels="capture_timestamp", axis=1, inplace=True)

            data.insert(
                0,
                "capture_timestamp",
                [datetime.datetime.now() for i in range(len(data))],
            )

        data = data.astype("str")

        data = data.sort_index()

        data.to_sql(name=str(table_name), con=engine, if_exists="append", index=False)

        engine.dispose()

    def db_to_df(self, id: str, type: str) -> pandas.DataFrame:

        """
        Read a user's data from a specified database into a pandas DataFrame.

        #### Paramters

            id : str - The user id of the profile. Can be referenced from the dataframe, or passed as string.

            type : str - profile, tweets, following
        """

        if type == "profile":

            engine = sqlalchemy.create_engine(f"sqlite:///data/{id}.db")

            table_name = "profile"

        elif type == "tweets":

            engine = sqlalchemy.create_engine(f"sqlite:///data/{id}.db")

            table_name = "tweets"

        elif type == "following":

            engine = sqlalchemy.create_engine(f"sqlite:///data/{id}.db")

            table_name = "following"

        elif type == "followers":

            engine = sqlalchemy.create_engine(f"sqlite:///data/{id}.db")

            table_name = "followers"

        elif type == "query":

            engine = sqlalchemy.create_engine("sqlite:///data/twitter_queries.db")

            table_name = id
            """For queries, use self.response.headers['x-transaction-id']"""

        else:

            raise ValueError("type must be one of: profile, tweets, following, query")

        df = pandas.read_sql_table(table_name=table_name, con=engine)

        engine.dispose()

        return df

    def get_dbs(self):

        """
        Retrieve Twitter databases. Uses regex to check file names for an expected convention.

        This will be deprecated by class Database_Functions.

        Returns

            A list of database files by user id.
        """

        files = glob.glob("data/*.db")

        l = [
            re.search(r"(\d+.db)", i) for i in files
        ]  # regex for any files consisting of [0-9].db

        processed_list = [x for x in l if x is not None]

        return processed_list


@dataclass
class Database_Functions:
    def __init__(self):

        """Database functions."""

    def list_db_keys(self):

        files = glob.glob("data/*.db")

        list_keys = []

        for i in files:

            engine = sqlalchemy.create_engine(
                f"sqlite+pysqlite:///{i}", echo=True, future=True
            )

            s = sqlalchemy.schema.MetaData(bind=engine)

            s.reflect()

            list_keys.append((s.tables.keys(), i))

        return list_keys

    def list_db_tables(self, db):

        engine = sqlalchemy.create_engine(
            f"sqlite+pysqlite:///{db}", echo=True, future=True
        )

        s = sqlalchemy.schema.MetaData(bind=engine)

        s.reflect()

        return s.tables


class Streamlit_Functions:
    def __init__(self):
        """
        A class for Streamlit utilities.
        """

    def set_boilerplate(self, **kwargs):
        """
        Boilerplate setup for a Streamlit page.

        Parameters

            page_title : str - The title bar page name.

            scroll_text : str - The text to scroll when the page loads.

            metrics : bool - Show the metrics during operations, in expanders.
        """

        if "page_title" in kwargs.keys():

            page_title = str(kwargs["page_title"])

        else:

            page_title = "solarcho3/Web Tools"

        scroll_text = ""

        if kwargs.get("scroll_text"):

            scroll_text = str(kwargs["scroll_text"])

        import streamlit as st

        st.set_page_config(page_title=page_title, page_icon=":wrench:", layout="wide")

        if kwargs.get("metrics", False):

            with st.expander("🌡️ Twitter API-server rate limit metrics"):

                self.metrics_col1, self.metrics_col2, self.metrics_col3 = st.columns(3)

            with st.expander("📻 Traffic log"):

                traffic = st.columns(1)

        scroll_container = st.empty()

        store = ""

        for char in scroll_text:

            store = store + char

            scroll_container.text(store)

            time.sleep(0.005)

    def update_metrics(self, data):
        """
        Update the boilerplate metrics.
        """

        keys_list = list(data.keys())

        self.metrics_col1.metric(
            f"{keys_list[0]} % remaining",
            data[keys_list[0]]["percent_remaining"],
            round((1000 / data[keys_list[0]]["remaining"]) * -1, 2),
        )

        self.metrics_col2.metric(
            keys_list[0], data[keys_list[0]]["limit"], data[keys_list[0]]["remaining"]
        )


def random_line():

    """
    Get a random line of Shakespeare

    Returns

        line : str - A single line of Shakespeare.
    """

    with open("data/alllines.txt") as f:

        f1 = f.read().splitlines()

    return random.choice(f1)


def tutorial():

    import streamlit as st

    l1 = random_line()

    st.code(
        f"""
    🇺🇲 Web Tools <[Research Utilities]>

    = Tools to request data via APIs, perform database functions, and produce analytics.

    - 🍳 This is the boilerplate text. Call set_boilerplate(scroll_text='YOUR TEXT to change this...')

    + 🍼 Show example script (the code below) - web_tools.tutorial()

    + 🍗 Documentation: https://github.com/solarecho3/web-tools  >  documentation  >  web_tools.htm

    - ⚔️ A line from the bard?  {l1}  🤺

    # Example

        import web_tools

        t1 = web_tools.Twitter_Session()
        t1.get_token_local('/home/docs/keys.json')

        df = t1.get_user_profile('elonmusk')
        df2 = t1.get_user_tweets(df['id'][0])
        df3 = t1.get_user_following(df['id'][0])

        t1.df_to_db(df['id'][0], df, 'profile')
        t1.df_to_db(df['id'][0], df2, 'tweets')
        t1.df_to_db(df['id'][0], df3, 'following')

        df4 = t1.get_string_query('taiwan', pages=2)
        t1.df_to_db(
            id = t1.response.headers['x-transaction-id'],
            data = df4,
            type = 'query',
            query_term = t1.query_log[len(t1.query_log)-1]['parsed_query_term']
            )

        df4 = t1.get_string_query('musk', pages=2)
        t1.df_to_db(
            id = t1.response.headers['x-transaction-id'],
            data = df4,
            type = 'query',
            query_term = t1.query_log[len(t1.query_log)-1]['parsed_query_term']
            )

        df4 = t1.get_string_query('russia', pages=2)
        t1.df_to_db(
            id = t1.response.headers['x-transaction-id'],
            data = df4,
            type = 'query',
            query_term = t1.query_log[len(t1.query_log)-1]['parsed_query_term']
            )
    """
    )
