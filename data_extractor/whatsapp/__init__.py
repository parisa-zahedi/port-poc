__version__ = '0.2.0'

import zipfile
# coding=utf-8
"""Parser utils.
   The main part is extracted from https://github.com/lucasrodes/whatstk.git
"""
import os
import re
from datetime import datetime
import pandas as pd
#import advertools as adv
#import hashlib

URL_PATTERN = r'(https?://\S+)'
LOCATION_PATTERN = r'(Location: https?://\S+)'
FILE_PATTERN = r'(<attached: \S+>)'

class RegexError(Exception):
    """Raised when regex match is not possible."""
    pass

class ColnamesDf:
    """Access class constants using variable ``utils.COLNAMES_DF``.
    """
    DATE = 'date'
    """Date column"""

    USERNAME = 'username'
    """Username column"""

    MESSAGE = 'message'
    """Message column"""

    MESSAGE_LENGTH = 'message_length'
    """Message length column"""

    FirstMessage = 'first_message_date'
    """Date of first message column"""

    LastMessage = 'last_message_date'
    """Date of last message column"""

    MESSAGE_NO = 'message_no'
    """Number of Message  column"""

    WORDS_NO = 'total_words_no'
    """Total number of words  column"""

    REPLY_2USER = 'reply_2_user'
    """Who replies to the user the most column"""

    MAX_REPLY_2 = 'max_reply_2'
    """User replies to who the most column"""

    USER_REPLY2 = 'user_reply2'
    """User replies to who the most column"""

    URL_NO = 'url_no'
    """Number of URLs column"""

    LOCATION_NO = 'location_no'
    """Number of locations column"""

    FILE_NO = 'file_no'
    """Number of files column"""

    OUT_DEGREE = 'out_degree'
    """Total number of sent message column"""

    IN_DEGREE = 'in_degree'
    """Total number of received message column"""

    EMOJI_NO = 'emoji_no'
    """Total number of emojies column"""

    EMOJI_Fav = 'emoji_fav'
    """Favorite emojies column"""

COLNAMES_DF = ColnamesDf()

######### parsing functions #####################
regex_simplifier = {
    '%Y': r'(?P<year>\d{2,4})',
    '%y': r'(?P<year>\d{2,4})',
    '%m': r'(?P<month>\d{1,2})',
    '%d': r'(?P<day>\d{1,2})',
    '%H': r'(?P<hour>\d{1,2})',
    '%I': r'(?P<hour>\d{1,2})',
    '%M': r'(?P<minutes>\d{2})',
    '%S': r'(?P<seconds>\d{2})',
    '%P': r'(?P<ampm>[AaPp].? ?[Mm].?)',
    '%p': r'(?P<ampm>[AaPp].? ?[Mm].?)',
    '%name': fr'(?P<{COLNAMES_DF.USERNAME}>[^:]*)'
}

def df_from_txt_whatsapp(text, hformats=None, encoding='utf-8'):
    """Load chat as a DataFrame.

    Args:
        filepath (str): Path to the file. Accepted sources are:

                * Local file, e.g. 'path/to/file.txt'.
        hformat (str, optional): :ref:`Format of the header <The header format>`, e.g.
                                    ``'[%y-%m-%d %H:%M:%S] - %name:'``. Use following keywords:

                                    - ``'%y'``: for year (``'%Y'`` is equivalent).
                                    - ``'%m'``: for month.
                                    - ``'%d'``: for day.
                                    - ``'%H'``: for 24h-hour.
                                    - ``'%I'``: for 12h-hour.
                                    - ``'%M'``: for minutes.
                                    - ``'%S'``: for seconds.
                                    - ``'%P'``: for "PM"/"AM" or "p.m."/"a.m." characters.
                                    - ``'%name'``: for the username.

                                    Example 1: For the header '12/08/2016, 16:20 - username:' we have the
                                    ``'hformat='%d/%m/%y, %H:%M - %name:'``.

                                    Example 2: For the header '2016-08-12, 4:20 PM - username:' we have
                                    ``hformat='%y-%m-%d, %I:%M %P - %name:'``.
        encoding (str, optional): Encoding to use for UTF when reading/writing (ex. 'utf-8').
                                  `List of Python standard encodings <https://docs.python.org/3/library/codecs.
                                  html#standard-encodings>`_.

    Returns:
        DataFrame: a DataFrame with three columns, i.e. 'date', 'username', and 'message'

    """

    for hformat in hformats:
        # Build dataframe
        df = _df_from_str(text, hformat)
        if df is not None:
             return df
    print("hformats did not match the provided text. No match was found")
    return None

def generate_regex(hformat):
    r"""Generate regular expression from hformat.

    Args:
        hformat (str): Simplified syntax for the header, e.g. ``'%y-%m-%d, %H:%M:%S - %name:'``.

    Returns:
        str: Regular expression corresponding to the specified syntax.

    """
    items = re.findall(r'\%\w*', hformat)
    for i in items:
        hformat = hformat.replace(i, regex_simplifier[i])

    hformat = hformat + ' '
    hformat_x = hformat.split('(?P<username>[^:]*)')[0]
    return hformat, hformat_x


def _str_from_txt(filepath, encoding='utf-8'):
    """Read text content as string.

    Args:
        filepath (str): Path to a local file.
        encoding (str, optional): Encoding to use for UTF when reading/writing (ex. ‘utf-8’).
                                  `List of Python standard encodings <https://docs.python.org/3/library/codecs.
                                  html#standard-encodings>`_.
    Raises:
        FileNotFoundError: [description]

    Returns:
        str: File content as a string.
    """
    # Read local file
    if os.path.isfile(filepath) and os.access(filepath, os.R_OK):
        with open(filepath, 'r', encoding=encoding) as f:
            text = f.read()
    else:
        raise FileNotFoundError(f"File {filepath} was not found locally or remotely. Please check it exists.")
    return text


def _df_from_str(text,  hformat=None):
    # Get hformat
    if hformat:
        # Bracket is reserved character in RegEx, add backslash before them.
        hformat = hformat.replace('[', r'\[').replace(']', r'\]')
    else:
        raise ValueError(" hformat can't be None.")

    # Generate regex for given hformat
    r, r_x = generate_regex(hformat=hformat)

    # Parse chat to DataFrame
    try:
        df = _parse_chat(text, r)
        df = _remove_alerts_from_df(r_x, df)
        df = _add_schema(df)

        return df
    except:
        pass
    return None

def _parse_chat(text, regex):
    """Parse chat using given regex.

    Args:
        text (str) Whole log chat text.
        regex (str): Regular expression

    Returns:
        pandas.DataFrame: DataFrame with messages sent by users, index is the date the messages was sent.

    Raises:
        RegexError: When provided regex could not match the text.

    """
    result = []
    headers = list(re.finditer(regex, text))
    for i in range(len(headers)):
        try:
            line_dict = _parse_line(text, headers, i)
        except KeyError:
            raise RegexError("Could not match the provided regex with provided text. No match was found.")
        result.append(line_dict)
    df_chat = pd.DataFrame.from_records(result)
    df_chat = df_chat[[COLNAMES_DF.DATE,COLNAMES_DF.USERNAME, COLNAMES_DF.MESSAGE]]
    return df_chat


def _add_schema(df):
    """Add default chat schema to df.

    Args:
        df (pandas.DataFrame): Chat dataframe.

    Returns:
        pandas.DataFrame: Chat dataframe with correct dtypes.

    """
    df = df.astype({
        COLNAMES_DF.DATE: pd.StringDtype(), #'datetime64[ns]',
        COLNAMES_DF.USERNAME: pd.StringDtype(),
        COLNAMES_DF.MESSAGE: pd.StringDtype()
    })
    return df


def _parse_line(text, headers, i):
    """Get date, username and message from the i:th intervention.

    Args:
        text (str): Whole log chat text.
        headers (list): All headers.
        i (int): Index denoting the message number.

    Returns:
        dict: i:th date, username and message.

    """
    result_ = headers[i].groupdict()
    if 'ampm' in result_:
        hour = int(result_['hour'])
        mode = result_.get('ampm').lower()
        if hour == 12 and mode == 'am':
            hour = 0
        elif hour != 12 and mode == 'pm':
            hour += 12
    else:
        hour = int(result_['hour'])

    # Check format of year. If year is 2-digit represented we add 2000
    if len(result_['year']) == 2:
        year = int(result_['year']) + 2000
    else:
        year = int(result_['year'])

    if 'seconds' not in result_:
        date = datetime(year, int(result_['month']), int(result_['day']), hour,
                        int(result_['minutes']))
    else:
        date = datetime(year, int(result_['month']), int(result_['day']), hour,
                        int(result_['minutes']), int(result_['seconds']))
    username = result_[COLNAMES_DF.USERNAME]
    message = _get_message(text, headers, i)
    line_dict = {
        COLNAMES_DF.DATE: date,
        COLNAMES_DF.USERNAME: username,
        COLNAMES_DF.MESSAGE: message
    }
    return line_dict


def _remove_alerts_from_df(r_x, df):
    """Try to get rid of alert/notification messages.

    Args:
        r_x (str): Regular expression to detect whatsapp warnings.
        df (pandas.DataFrame): DataFrame with all interventions.

    Returns:
        pandas.DataFrame: Fixed version of input dataframe.

    """
    df_new = df.copy()
    df_new.loc[:, COLNAMES_DF.MESSAGE] = df_new[COLNAMES_DF.MESSAGE].apply(lambda x: _remove_alerts_from_line(r_x, x))
    return df_new


def _remove_alerts_from_line(r_x, line_df):
    """Remove line content that is not desirable (automatic alerts etc.).

    Args:
        r_x (str): Regula expression to detect WhatsApp warnings.
        line_df (str): Message sent as string.

    Returns:
        str: Cleaned message string.

    """
    if re.search(r_x, line_df):
        return line_df[:re.search(r_x, line_df).start()]
    else:
        return line_df


def _get_message(text, headers, i):
    """Get i:th message from text.

    Args:
        text (str): Whole log chat text.
        headers (list): All headers.
        i (int): Index denoting the message number.

    Returns:
        str: i:th message.

    """
    msg_start = headers[i].end()
    msg_end = headers[i + 1].start() if i < len(headers) - 1 else headers[i].endpos
    msg = text[msg_start:msg_end].strip()
    return msg

################# analysis functions ###############################

def df_participants_features(df_chat):
    df_participants = _get_df_participants(df_chat)
    #df_participants[COLNAMES_DF.FirstMessage] = _add_first_message_date(df_chat, df_participants)
    #df_participants[COLNAMES_DF.LastMessage] = _add_last_message_date(df_chat, df_participants)
    df_participants[COLNAMES_DF.WORDS_NO] = _add_total_words_no(df_chat, df_participants)
    response_matrix = _get_response_matrix(df_chat)
    df_participants[COLNAMES_DF.REPLY_2USER] = _add_replies2user(response_matrix, df_participants)
    response_matrix[COLNAMES_DF.MAX_REPLY_2] = response_matrix.idxmax(axis=1)
    df_participants[COLNAMES_DF.USER_REPLY2] = _add_userreplies2(response_matrix, df_participants)
    df_participants[COLNAMES_DF.URL_NO] = _add_pattern_no(df_chat, df_participants, URL_PATTERN)
    df_participants[COLNAMES_DF.LOCATION_NO] = _add_pattern_no(df_chat, df_participants, LOCATION_PATTERN)
    df_participants[COLNAMES_DF.FILE_NO] = _add_pattern_no(df_chat, df_participants, FILE_PATTERN)
    response_matrix[COLNAMES_DF.OUT_DEGREE] = response_matrix.sum(axis=1)
    df_participants[COLNAMES_DF.OUT_DEGREE] = _add_out_degree(response_matrix, df_participants)
    df_participants[COLNAMES_DF.IN_DEGREE] = _add_in_degree(response_matrix, df_participants)
    # df_participants[COLNAMES_DF.EMOJI_NO] = _add_emoji_counts(df_chat, df_participants)
    # df_participants[COLNAMES_DF.EMOJI_Fav] = _add_emoji_fav(df_chat, df_participants)
    # df_participants[COLNAMES_DF.USERNAME] = _hash_participants(df_participants, COLNAMES_DF.USERNAME)
    # df_participants[COLNAMES_DF.REPLY_2USER] = _hash_participants(df_participants, COLNAMES_DF.REPLY_2USER)
    # df_participants[COLNAMES_DF.USER_REPLY2] = _hash_participants(df_participants, COLNAMES_DF.USER_REPLY2)

    return df_participants


def _get_df_participants(df_chat):
    df = df_chat[COLNAMES_DF.USERNAME].value_counts().rename(COLNAMES_DF.MESSAGE_NO)
    df = pd.DataFrame(df)
    df = df.rename_axis(COLNAMES_DF.USERNAME).reset_index()
    return df


def _add_first_message_date(df_chat, df_participants):
    return df_participants[COLNAMES_DF.USERNAME].apply(lambda u: _get_first_message_user(df_chat, u))


def _get_first_message_user(df_chat, user):
    return df_chat.loc[df_chat[COLNAMES_DF.USERNAME] == user, COLNAMES_DF.DATE].iloc[0]


def _add_last_message_date(df_chat, df_participants):
    return df_participants[COLNAMES_DF.USERNAME].apply(lambda u: _get_last_messages_user(df_chat, u))


def _get_last_messages_user(df_chat, user):
    return df_chat.loc[df_chat[COLNAMES_DF.USERNAME] == user, COLNAMES_DF.DATE].iloc[-1]


def _add_total_words_no(df_chat, df_participants):
    return df_participants[COLNAMES_DF.USERNAME].apply(lambda u: _get_total_wordsno_user(df_chat, u))


def _get_total_wordsno_user(df_chat, user):
    return df_chat.loc[df_chat[COLNAMES_DF.USERNAME] == user, COLNAMES_DF.MESSAGE].\
           apply(lambda x: len(str(x).split(' '))).sum().astype(int)


def _get_response_matrix(df_chat):
    users = set(df_chat[COLNAMES_DF.USERNAME])

    # Get list of username transitions and initialize dicitonary with counts
    user_transitions = df_chat[COLNAMES_DF.USERNAME].tolist()
    responses = {user: dict(zip(users, [0] * len(users))) for user in users}
    # Fill count dictionary
    for i in range(1, len(user_transitions)):
        sender = user_transitions[i]
        receiver = user_transitions[i - 1]
        if sender != receiver:
            responses[sender][receiver] += 1

    responses = pd.DataFrame.from_dict(responses, orient='index')
    # responses[COLNAMES_DF.MAX_REPLY_2] = responses.idxmax(axis=1)
    # responses[COLNAMES_DF.OUT_DEGREE] = responses.sum(axis=1)
    return responses


def _add_replies2user(response_matrix, df_participants):
    return df_participants[COLNAMES_DF.USERNAME].apply(lambda u: _who_replies2user(response_matrix, u))


def _who_replies2user(response_matrix, user):
    return response_matrix[user].idxmax()


def _add_userreplies2(response_matrix, df_participants):
    return df_participants[COLNAMES_DF.USERNAME].apply(lambda u: _user_replies2(response_matrix, u))


def _user_replies2(response_matrix, user):
    return response_matrix.loc[user, COLNAMES_DF.MAX_REPLY_2]


def _get_pattern_count(df_chat, user, pattern):
    return df_chat.loc[df_chat[COLNAMES_DF.USERNAME] == user, COLNAMES_DF.MESSAGE].\
           apply(lambda x: len(re.findall(pattern, x))).sum().astype(int)


def _add_pattern_no(df_chat, df_participants, pattern):
    return df_participants[COLNAMES_DF.USERNAME].apply(lambda u: _get_pattern_count(df_chat, u, pattern))


def _get_out_degree(response_matrix, user):
    return response_matrix.loc[user, COLNAMES_DF.OUT_DEGREE]


def _add_out_degree(response_matrix, df_participants):
    return df_participants[COLNAMES_DF.USERNAME].apply(lambda u: _get_out_degree(response_matrix, u))


def _add_in_degree(response_matrix, df_participants):
    return df_participants[COLNAMES_DF.USERNAME].apply(lambda u: _get_in_degree(response_matrix, u))


def _get_in_degree(response_matrix, user):
    return response_matrix[user].sum()


# def _get_emoji_count(df_chat, user):
#     return sum(df_chat.loc[df_chat[COLNAMES_DF.USERNAME] == user, COLNAMES_DF.MESSAGE].\
#            apply(lambda x: adv.extract_emoji(x)['emoji_counts']).sum())
#
#
# def _add_emoji_counts(df_chat, df_participants):
#     return df_participants[COLNAMES_DF.USERNAME].apply(lambda u: _get_emoji_count(df_chat, u))
#
#
# def _get_fav_emoji(df_chat, user):
#     emoji_count = {}
#     emoji_lst = df_chat.loc[df_chat[COLNAMES_DF.USERNAME] == user, COLNAMES_DF.MESSAGE].\
#            apply(lambda x: adv.extract_emoji(x)['top_emoji']).sum()
#
#     if len(emoji_lst) == 0:
#         return ''
#
#     for itm in emoji_lst:
#         emoji = itm[0]
#         if emoji not in emoji_count:
#             emoji_count[emoji] = 0
#         emoji_count[emoji] += itm[1]
#
#     return max(emoji_count, key=emoji_count.get)
#
#
# def _add_emoji_fav(df_chat, df_participants):
#     return df_participants[COLNAMES_DF.USERNAME].apply(lambda u: _get_fav_emoji(df_chat, u))

#
# def _hash_txt(txt):
#     message = txt.encode()
#     return hashlib.shake_256(message).hexdigest(4)
#
#
# def _hash_participants(df_participants, col_name):
#     return df_participants[col_name].apply(lambda u: _hash_txt(u))


def process(file_data):
    hformats = ['[%d/%m/%y, %H:%M:%S] %name:', '%m/%d/%y, %H:%M - %name:']
    zfile = zipfile.ZipFile(file_data)
    for name in zfile.namelist():
        if re.search('chat.txt', name):
            text = zfile.read(name).decode("utf-8")
            # print(text)
            df_chat = df_from_txt_whatsapp(text, hformats=hformats)
            # #print(df_chat)
            df_participants = df_participants_features(df_chat)
            # #print(df_participants)


    return [{
        "id": "overview",
        "title": "The following files where read:",
        "data_frame": df_participants
    }]