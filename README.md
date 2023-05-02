🇺🇲 Web Tools <[Research Utilities]>

= Tools to request data via APIs, perform database functions, and produce analytics.

- 🍳 This is the boilerplate text. Call set_boilerplate(scroll_text='YOUR TEXT to change this...')

+ 🍼 Show example script (the code below) - web_tools.tutorial()

+ 🍗 Documentation: https://github.com/solarecho3/web-tools  >  documentation  >  web_tools.htm

++ web_tools.py - The main module.

++ how_to.ipynb - How to use web_tools.py.

++ keyword_snapshot.py - Command-line module to capture Twitter samples.

- ⚔️ A line from the bard? "Therefore no more turn me to him, sweet Nan." 🤺

    ### Example
    ```python
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
        )```
