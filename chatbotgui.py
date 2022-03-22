import nltk
from nltk.stem import WordNetLemmatizer
import pickle
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_cors import CORS
from flask_ngrok import run_with_ngrok
import numpy as np
from keras.models import load_model
import json
import matplotlib.pyplot as plt
import warnings
import sqlite3
from bot_model import BotTrainer
from datetime import datetime
from bot_model.JsonParser import appendJson, editJson, deleteJson, intentParser, intentDeparser

# ---------- Load Models -----------
lemmatizer = WordNetLemmatizer()
model = load_model('./bot_model/chatbot_model.h5')
intents = json.loads(open('./bot_model/intents.json', errors="ignore").read())
words = pickle.load(open('./bot_model/words.pkl', 'rb'))
classes = pickle.load(open('./bot_model/classes.pkl', 'rb'))

# ---------- Log File Generation -----------
warnings.filterwarnings('ignore')

# ---------- Load Intent File -----------
json_file_directory = "./bot_model/intents.json"

# ---------- Initialize Flask APP and Enable Cross-Domain -----------
app = Flask(__name__)
app.secret_key = '1a2b3c4d5e'
CORS(app)  # Cross Resource

xaxis = []
yaxis = []
final_msg = []
context = {}


# ---------- Flask Routing -----------
@app.route("/")
def display_dashboard():
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        return render_template('dashboard/dashboard.html', username=session['username'], id=session['id'])
    # User is not loggedin redirect to login page
    return redirect(url_for('check_login'))


@app.route('/login_check', methods=['GET', 'POST'])
def check_login():
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:

        username = request.form['username']
        password = request.form['password']

        # Check if account exists using SQLiteL and Fetch data
        conn = sqlite3.connect('./database/ChatbotMain.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM accounts WHERE username = ? AND password = ?', (username, password))
        account = cursor.fetchone()

        # If account exists in accounts table inside database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['id'] = account[0]
            session['username'] = account[1]

            # Redirect to home page
            return redirect(url_for('display_dashboard'))
        else:
            # Account doesn't exist or username/password incorrect
            flash("Incorrect username/password!", "danger")

    return render_template('auth/login.html', title="Login")


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST' and 'username' in request.form and 'mobile_no' in request.form and 'email' in request.form:
        username = request.form['username']
        mobile_no = request.form['mobile_no']
        email = request.form['email']

        # Create session data, we can access this data in other routes
        session['loggedin'] = True
        session['id'] = "guest"
        session['username'] = username

        # Redirect to home page
        return redirect(url_for('display_dashboard'))

    return render_template('auth/register.html')


@app.route('/password_recovery')
def display_pass_recover():
    return render_template('auth/forgot-password.html')


@app.route('/user_profile')
def profile():
    if 'loggedin' in session:
        if session['id'] != "guest":
            # We need all the account info for the user so we can display it on the profile page
            conn = sqlite3.connect('./database/ChatbotMain.db')
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM accounts WHERE id = ?', (session['id'],))
            account = cursor.fetchone()
            # Show the profile page with account info
            return render_template('auth/profile.html', account=account)
        else:
            return redirect(url_for('display_index'))
    # User is not loggedin redirect to login page
    return redirect(url_for('check_login'))


@app.route('/user_logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    # Redirect to login page
    return redirect(url_for('display_dashboard'))


@app.route("/user_details")
def display_user_details():
    if 'loggedin' in session:
        if session['id'] != "guest":
            return render_template("manager/tables.html")
        else:
            return redirect(url_for('display_dashboard'))

    return redirect(url_for('check_login'))


@app.route("/allQuery_log")
def display_allQuery():
    if 'loggedin' in session:
        conn = sqlite3.connect('./database/ChatbotMain.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM query_log')

        QueryList = []
        for row in cursor:
            Query = {"id": row[0], "Query": row[1], "Intent": row[2], "Accuracy": row[3], "Response": row[4],
                     "ans_state": row[5]}
            QueryList.append(Query)

        return render_template("dashboard/query_viewer.html", dataList=QueryList)


@app.route("/unanswered_log")
def display_unanswered():
    if 'loggedin' in session:
        conn = sqlite3.connect('./database/ChatbotMain.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM unanswered_log')

        QueryList = []
        for row in cursor:
            Query = {"id": row[0], "Query": row[1], "Response": row[2]}
            QueryList.append(Query)

        return render_template("dashboard/query_viewer.html", dataList=QueryList)


@app.route("/intent_config")
def display_intent_manager():
    if 'loggedin' in session:
        if session['id'] != "guest":
            json_file = open(json_file_directory, encoding="utf8")
            data = json.load(json_file)
            json_file.close()

            total_intent = 0
            for entries in data["intents"]:
                total_intent += 1

            return render_template("manager/intent_manager.html", intents=data["intents"], total_intents=total_intent)
        else:
            return redirect(url_for('display_dashboard'))

    return redirect(url_for('check_login'))


@app.route("/intent_add")
def display_intent_adder():
    if 'loggedin' in session:
        if session['id'] != "guest":
            return render_template("manager/intent_add.html")
        else:
            return redirect(url_for('display_dashboard'))
    return redirect(url_for('check_login'))


@app.route("/intent_edit")
def display_intent_edit():
    if 'loggedin' in session:
        if session['id'] != "guest":
            row_id = request.args.get('edit_row_id', None)
            json_file = open(json_file_directory, encoding="utf8")
            data = json.load(json_file)
            json_file.close()

            edit_list = intentDeparser(data, row_id)

            return render_template("manager/intent_edit.html", edit_intent=edit_list)
        else:
            return redirect(url_for('display_dashboard'))

    return redirect(url_for('check_login'))


@app.route("/intent_add_action", methods=['post', 'get'])
def add_intent():
    if 'loggedin' in session:
        if session['id'] != "guest":
            if request.method == 'POST':
                tag = request.form.get('tag')
                pattern = request.form.get('pattern')
                responses = request.form.get('responses')
                extra_responses = []
                choices = request.form.get('choices')
                link = request.form.get('link')
                context_set = request.form.get('cntx-set')
                context_filter = request.form.get('cntx-fltr')

                if request.form.get('resp-check') is not None:
                    res_randomizer = True
                else:
                    res_randomizer = False

                for num_id in range(0, 15, 1):
                    searchId = "extra_res_" + str(num_id)
                    if searchId in request.form:
                        if request.form.get(searchId) != "":
                            extra_responses.append(request.form.get(searchId))

                new_entry = intentParser(tag, pattern, res_randomizer, responses, extra_responses, choices, link,
                                         context_set, context_filter)
                appendJson(new_entry, json_file_directory)

            return redirect(url_for('display_intent_manager'))
        else:
            return redirect(url_for('display_dashboard'))
    return redirect(url_for('check_login'))


@app.route("/intent_edit_action", methods=['post'])
def edit_intent():
    if 'loggedin' in session:
        if session['id'] != "guest":
            if request.method == 'POST':
                row_id = request.form.get('ID')
                tag = request.form.get('tag')
                pattern = request.form.get('pattern')
                responses = request.form.get('responses')
                extra_responses = []
                choices = request.form.get('choices')
                link = request.form.get('link')
                context_set = request.form.get('cntx-set')
                context_filter = request.form.get('cntx-fltr')

                if request.form.get('resp-check') is not None:
                    res_randomizer = True
                else:
                    res_randomizer = False

                for num_id in range(0, 15, 1):
                    searchId = "extra_res_" + str(num_id)
                    if searchId in request.form:
                        if request.form.get(searchId) != "":
                            extra_responses.append(request.form.get(searchId))

                edited_entry = intentParser(tag, pattern, res_randomizer, responses, extra_responses, choices, link,
                                            context_set, context_filter)
                editJson(edited_entry, json_file_directory, row_id)

            return redirect(url_for('display_intent_manager'))
        else:
            return redirect(url_for('display_dashboard'))
    return redirect(url_for('check_login'))


@app.route("/intent_delete_action")
def delete_intent():
    if 'loggedin' in session:
        if session['id'] != "guest":
            row_id = request.args.get('row_id', None)
            deleteJson(row_id, json_file_directory)
            return redirect(url_for('display_intent_manager'))
        else:
            return redirect(url_for('display_dashboard'))
    return redirect(url_for('check_login'))


@app.route("/billing.html")
def billing():
    return render_template("includes/billing.html")


@app.route("/get", methods=["POST"])
def chatbot_response():
    msg = request.form["msg"]
    detected_intents = predict_class(msg, model)
    randomizer, res, extra_res, choices, ext_link = getResponse(detected_intents, intents)

    # res = []
    # ints = []
    # # Bill Check
    # if any(word.isdigit() for word in msg):
    #     for word in msg.split():
    #         if word.isdigit() and len(word) > 5:
    #             ints = predict_class(msg, model)
    #             res = [billing_response_db(word)]
    #             choices = "empty choices"
    #             ext_link = "empty link"
    #             break
    # elif "." in msg:
    #     for url in msg.split():
    #         if "." in url:
    #             ints = predict_class(msg, model)
    #             res = [website_response_db(url)]
    #             choices = "empty choices"
    #             ext_link = "empty link"
    #             break
    # else:
    #     ints = predict_class(msg, model)
    #     res, choices, ext_link = getResponse(ints, intents)
    #
    print(msg)
    print(detected_intents)
    print(res)

    # Store Conversation in logs
    file_name = datetime.now().strftime("%d_%m_%Y") + '.txt'
    file = open('./conversation_log/' + file_name, "a")
    file.write(datetime.now().strftime("<%H:%M:%S> ") + "MSG: " + msg + "| RES: " + str(res) + '\n')
    file.close()

    if msg is not None and detected_intents[0]['intent'] != "noanswer":
        conn = sqlite3.connect('./database/ChatbotMain.db')
        cursor = conn.cursor()
        sql_insert_query = 'INSERT INTO query_log (Query, Intent, Accuracy, Response, ans_state) \
                            VALUES (?,?,?,?,?)'
        cursor.execute(sql_insert_query, (
        msg, detected_intents[0]['intent'], float(detected_intents[0]['probability']), str(res), "answered"))

        conn.commit()
    else:
        conn = sqlite3.connect('./database/ChatbotMain.db')
        cursor = conn.cursor()
        sql_insert_query = 'INSERT INTO query_log (Query, Intent, Accuracy, Response, ans_state) \
                            VALUES (?,?,?,?,?)'
        cursor.execute(sql_insert_query,
                       (msg, detected_intents[0]['intent'], float(detected_intents[0]['probability']), str(res),
                        "unanswered"))

        sql_insert_query = 'INSERT INTO unanswered_log (Query, Response) VALUES (?,?)'
        cursor.execute(sql_insert_query, (msg, res[0]))

        conn.commit()

    data = {"randomizer": randomizer, "responses": res, "extra_responses": extra_res, "choices": choices,
            "link": ext_link}
    return data


@app.route('/billingdata', methods=["POST"])
def database_response():
    msg = request.form["msg"]
    if msg.isnumeric():
        result = billing_response_db(msg)
    else:
        result = website_response_db(msg)

    if result is not None:
        return result
    else:
        return "No Record Found"


@app.route('/plot', methods=["POST"])
def plot():
    total_query_count = 0
    no_ans_count = 0
    # msg = request.form["msg"]

    conn = sqlite3.connect('./database/ChatbotMain.db')
    cursor = conn.cursor()
    cursor.execute('SELECT Intent, Accuracy FROM query_log')
    plot_list = []

    for row in cursor:
        plot_point = {'label': row[0], 'y': row[1]}
        plot_list.append(plot_point)

        total_query_count += 1

    cursor.execute('SELECT * FROM unanswered_log')
    for rows in cursor:
        no_ans_count += 1

    answered_count = (total_query_count - no_ans_count)

    data = {
        "PlotData": plot_list,
        "TQueryCount": total_query_count,
        "AnswerCount": answered_count,
        "NoAnswerCount": no_ans_count
    }
    return data


@app.route('/train_bot')
def initiate_training():
    global model, intents, words, classes

    BotTrainer.train_bot(json_file_directory)

    # Reload newly Trained Model
    model = load_model('./bot_model/chatbot_model.h5')
    intents = json.loads(open('./bot_model/intents.json', errors="ignore").read())
    words = pickle.load(open('./bot_model/words.pkl', 'rb'))
    classes = pickle.load(open('./bot_model/classes.pkl', 'rb'))

    return redirect(url_for('display_intent_manager'))


@app.route('/loadWidget')
def load_Widget():
    return render_template("Widget/CB_widget.html")


# ---------- Bill Calculator -------------------------------------------------------
@app.route("/billingCalc_get", methods=["POST"])
def charges_input():
    c6 = request.form.get("c6", type=int, default=0)
    c7 = request.form.get("c7", type=int, default=0)
    c8 = request.form.get("c8", type=int, default=0)
    c9 = request.form.get("c9", type=int, default=0)
    c10 = request.form.get("c10", type=int, default=0)
    c11 = request.form.get("c11", type=int, default=0)
    c12 = request.form.get("c12", type=int, default=0)
    c13 = request.form.get("c13", type=int, default=0)
    c14 = request.form.get("c14", type=int, default=0)
    c15 = request.form.get("c15", type=int, default=0)
    c16 = request.form.get("c16", type=int, default=0)
    c17 = request.form.get("c17", type=int, default=0)
    c18 = request.form.get("c18", type=int, default=0)
    RGN = request.form.get("RGN")

    # ----------- Formulas ----------------
    L = c6 + c7 + c10 + c9
    BC = c11 + c12
    E = c17
    SNetflix = c18
    iptvchrgs = c14 + c15 + c16
    gst = E * 0.7
    gst = round(gst, 3)

    # -----Region---------------------------
    if RGN == 'ISB':
        st = L * 0.16
        stfed = iptvchrgs * 0.16
        stfbb = BC * 0.16

    elif RGN == 'AJK':
        st = L * 0.195
        stfed = iptvchrgs * 0.195
        stfbb = BC * 0.195
    elif RGN == 'FATA':
        st = L * 0.195
        stfed = iptvchrgs * 0.195
        stfbb = BC * 0.195
    elif RGN == 'SINDH':
        st = L * 0.195
        stfed = iptvchrgs * 0.195
        stfbb = BC * 0.195
    elif RGN == 'KPK':
        st = L * 0.195
        stfed = iptvchrgs * 0.195
        stfbb = BC * 0.195
    else:
        st = 0
        stfed = 0
        stfbb = 0

    T = (L, st, stfed, stfbb, E, SNetflix, BC, iptvchrgs, gst)
    Total = sum(T)
    if Total > 1000:
        WHT = round(Total * 0.1, 2)
    else:
        WHT = 0

    entry = Total
    entry = round(entry, -1)
    # return render_template('index.html', entry = entry,e1 = L,e2=BC,e3=E,e4=SNetflix,e5=iptvchrgs,e6=gst,e7=WHT,e8 = st, e9 =stfed,e10=stfbb)
    data = {
        "entry": entry,
        "e1": L,
        "e2": BC,
        "e3": iptvchrgs,
        "e4": E,
        "e5": 0,
        "e6": SNetflix,
        "e7": st,
        "e8": gst,
        "e9": stfed,
        "e10": stfbb,
        "e11": WHT,
        "e12": 0,
    }

    return data


# ---------- Function Definitions -----------
def billing_response_db(msg):
    flag = 0
    conn = sqlite3.connect('./database/customer.db')
    print("Opened database2 successfully")
    print("msg ->>", msg)
    cur = conn.cursor()
    cur.execute("SELECT * FROM billing")
    table = cur.fetchall()
    for each_value in table:
        if each_value[0] == int(msg):
            flag = 1
            res = "Find: {0} but Temporarily Blocked".format(each_value[0])
            break
    if flag != 1:
        res = None
    return res


def website_response_db(msg):
    flag = 0
    conn1 = sqlite3.connect('./database/customer.db')
    print("Opened database successfully")
    print("msg ->>", msg)
    curr = conn1.cursor()
    curr.execute("SELECT * FROM WEBSITES")
    table = curr.fetchall()
    for each_value in table:
        if each_value[0].strip() == str(msg.strip()):
            flag = 1
            print(each_value[0])
            res = "Find: {0} but Temporarily Blocked".format(each_value[0])
            break
    if flag != 1:
        res = None
    return res


def clean_up_sentence(sentence):
    sentence_words = nltk.word_tokenize(sentence)
    sentence_words = [lemmatizer.lemmatize(word.lower()) for word in sentence_words]
    return sentence_words


# return bag of words array: 0 or 1 for each word in the bag that exists in the sentence
def bow(sentence, words, show_details=True):
    # tokenize the pattern
    sentence_words = clean_up_sentence(sentence)
    # bag of words - matrix of N words, vocabulary matrix
    bag = [0] * len(words)
    for s in sentence_words:
        for i, w in enumerate(words):
            if w == s:
                # assign 1 if current word is in the vocabulary position
                bag[i] = 1
                if show_details:
                    print("found in bag: %s" % w)

    return np.array(bag)


def predict_class(sentence, model):
    # filter out predictions below a threshold
    p = bow(sentence, words, show_details=False)
    res = model.predict(np.array([p]))[0]
    ERROR_THRESHOLD = 0.25
    results = [[i, r] for i, r in enumerate(res) if r > ERROR_THRESHOLD]

    # sort by strength of probability
    results.sort(key=lambda x: x[1], reverse=True)
    return_list = []
    for r in results:
        return_list.append({"intent": classes[r[0]], "probability": str(r[1])})
        intent = classes[r[0]]
        probability = str(r[1])
        global xaxis, yaxis
        x = np.array([intent])
        y = np.array([probability])
        xaxis.append(x)
        yaxis.append(y)
        plt.scatter(x, y)
        # plt.show()

    return return_list


def getResponse(detected_intents, intents_json):
    tag = detected_intents[0]['intent']
    userID = '123'
    list_of_intents = intents_json['intents']
    for i in list_of_intents:
        if i['tag'] == tag:

            if 'context_set' in i:
                # if show_details: print('context:', i['context_set'])
                context[userID] = i['context_set']
            if not 'context_filter' in i or (
                    userID in context and 'context_filter' in i and i['context_filter'] == context[userID]):
                pass

            # First check if setting is available in intent, then return value
            param_list = ['response_randomizer', 'responses', 'extra_responses', 'choices', 'external_link']
            return_list = [False, 'empty', 'empty', 'empty', 'empty']

            for parameter in param_list:
                if parameter == 'response_randomizer' and parameter in i:
                    return_list[0] = i['response_randomizer']

                if parameter == 'responses' and parameter in i:
                    return_list[1] = i['responses']

                if parameter == 'extra_responses' and parameter in i:
                    return_list[2] = i['extra_responses']

                if parameter == 'choices' and parameter in i:
                    return_list[3] = i['choices']

                if parameter == 'external_link' and parameter in i:
                    return_list[4] = i['external_link']

            return return_list[0], return_list[1], return_list[2], return_list[3], return_list[4]


if __name__ == "__main__":
    # run_with_ngrok(app)  # Use this option if you have ngrok and you want to expose your chatbot to the real world

    app.run(debug=True)
