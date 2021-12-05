
from datetime import datetime
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")




@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "GET":
        user_id = session["user_id"]
        asset_values = db.execute("SELECT name_stock2 FROM totals WHERE id_3 =?", user_id)
        asset_values1 = asset_values
        for i in range(0, len(asset_values1)):
            asset_values1[i] = asset_values1[i]["name_stock2"]

        asset_values2=asset_values1

        #getting a list of all of the updates stock values
        for i in range(0, len(asset_values2)):
            asset_values2[i] = {'Name' : lookup(asset_values[i])["symbol"], 'Price' : lookup(asset_values[i])["price"]}
        for i in range(0, len(asset_values)):
            db.execute("UPDATE totals SET current_price = ? WHERE name_stock2=?", asset_values[i]["Price"], asset_values2[i]["Name"])
        db.execute("UPDATE totals SET total = quantity * current_price")
        new_stocks = db.execute("SELECT total, id_3, username_3, name_stock2, company_name, current_price, total, quantity FROM totals WHERE id_3 =?", user_id)
        #list of one integer
        cash_update = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        cash_update2 = cash_update[0]["cash"]
        assets = 0
        for i in range(0, len(new_stocks)):
            assets += float(new_stocks[i]["total"])
        TOTAL = cash_update2 + assets

        return render_template("index1.html", STOCKS=new_stocks, CASH = cash_update2, TOTAL=TOTAL)

    else:
        transaction = request.form.get("transaction")
        if transaction == "buy":
            symbol = request.form.get("symbol")
            symbol = symbol.upper()
            try:
                shares = int(request.form.get("shares"))
            except:
                return apology("You must provide an integer number of shares you want to buy", 400)
            symbol_lookup = lookup(symbol)
            user_id = session["user_id"]
            user_username = session["user_username"]
            if not symbol:
                return apology("You must provide a stock to buy.", 400)
            if not shares:
                return apology("You must provide a number of stocks to buy.", 400)
            if int(shares) < 1:
                return apology("You must provide a positive number of stocks to buy.", 400)
            if not lookup(request.form.get("symbol")):
                return apology("You must provide a valid stock to buy.", 400)
            else:
                PP_share = float(symbol_lookup["price"])
                company_name = symbol_lookup["name"]
                transaction_cost = PP_share * shares
                cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
                if transaction_cost > cash[0]["cash"]:
                    return apology("Can't afford that transaction", 400)
                else:
                    symbols = db.execute("SELECT name_stock FROM stocks WHERE id_2=? GROUP BY name_stock", user_id)
                    symbols2 = symbols
                    for i in range(0, len(symbols2)):
                        symbols2[i] = symbols2[i]["name_stock"]
                    if symbol.upper() in symbols2:
                        db.execute("UPDATE totals SET quantity = quantity + ?, total = total + ? WHERE name_stock2 = ?", shares, transaction_cost, symbol)
                    else:
                        db.execute("INSERT INTO totals (id_3, username_3, name_stock2, quantity, current_price, total, company_name) VALUES(?, ?, ?, ?, ?, ?, ?)", user_id, user_username, symbol, shares, PP_share, transaction_cost, company_name)
                        db.execute("UPDATE totals SET name_stock2 = UPPER(name_stock2)")

                    db.execute("UPDATE users SET cash = cash - ? WHERE id == ? ", transaction_cost, user_id)
                    now = datetime.now()
                    transac_time = now.strftime("%Y-%m-%d %H:%M:%S")
                    db.execute("INSERT INTO stocks (id_2, username_2, quantity, PPS, name_stock, company, time, real_price) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", user_id, user_username, shares, PP_share, symbol, company_name, transac_time, PP_share)
                    db.execute("UPDATE stocks SET name_stock = UPPER(name_stock)")

                    return redirect("/")


        #when transaction is sell
        elif transaction == "sell":
            shares = int(request.form.get("shares"))
            #symbol of the stock obtained from the select menu input
            symbol = request.form.get("symbol")
            symbol = symbol.upper()
            #looking up on the website the value for this symbol
            symbol_lookup = lookup(symbol)
            user_id = session["user_id"]
            user_username = session["user_username"]

            if not shares:
                return apology("You must indicate how many shares you want to sell", 400)
            if int(shares) < 1:
                return apology("You must indicate a positive number of shares you want to sell", 400)
            #when everything is going ok
            #what is the submit button doing
            else:
                #price per share
                PP_share = float(symbol_lookup["price"])
                company_name = symbol_lookup["name"]
                transaction_gain = float(PP_share * -shares)
                test = {'test' : transaction_gain}
                #CHECK IF ENOUGH SHARES
                share_held1 = db.execute("SELECT id_2, username_2, name_stock, company, PPS, SUM(total), SUM(quantity) FROM stocks WHERE id_2 =? AND name_stock == ? GROUP BY name_stock", user_id, symbol)
                share_held2 = share_held1[0]["SUM(quantity)"]
                if int(shares) > share_held2:
                    return apology("You don't have enough shares to realize that transaction", 400)
                else:
                    db.execute("UPDATE totals SET quantity = quantity + ?, total = total + ? WHERE name_stock2 = ?", -shares, transaction_gain, symbol)

                    #applies the gain of the transaction to the cash value in the users db
                    db.execute("UPDATE users SET cash = cash - ? WHERE id == ? ", transaction_gain, user_id)
                    now = datetime.now()
                    transac_time = now.strftime("%Y-%m-%d %H:%M:%S")
                    #now fulfilling the second db
                    db.execute("INSERT INTO stocks (id_2, username_2, quantity, PPS, name_stock, time, total, company) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", user_id, user_username, -shares, PP_share, symbol, transac_time, transaction_gain, company_name)
                    #db.execute("UPDATE stocks SET total =? WHERE total= 0", transaction_gain)
                    db.execute("UPDATE stocks SET name_stock = UPPER(name_stock)")

                    share_held1 = db.execute("SELECT id_2, username_2, name_stock, company, PPS, SUM(total), SUM(quantity) FROM stocks WHERE id_2 =? AND name_stock == ? GROUP BY name_stock", user_id, symbol)
                    share_held2 = share_held1[0]["SUM(quantity)"]
                    if share_held2 == 0:
                        db.execute("DELETE FROM totals WHERE name_stock2 = ?", symbol)


                    return redirect("/")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "GET":
        return render_template("buy.html")

    #when method is POST
    else:
        #symbol of the stock obtained from the input
        symbol = request.form.get("symbol")
        symbol = symbol.upper()
        #number of shares obtained from the input
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("You must provide an integer number of shares you want to buy", 400)
        symbol_lookup = lookup(symbol)
        #variable to get the current user bc session[user_id] = rows[0]["id"]
        #and rows[0] is the row obtained in the database where the username equals
        #the one just entered in login, which means it's the only row outputed
        user_id = session["user_id"]
        user_username = session["user_username"]

        if not symbol:
            return apology("You must provide a stock to buy.", 400)
        if not shares:
            return apology("You must provide a number of stocks to buy.", 400)
        if int(shares) < 1:
            return apology("You must provide a positive number of stocks to buy.", 400)
        if not lookup(request.form.get("symbol")):
            return apology("You must provide a valid stock to buy.", 400)
        #when everything is ok
        else:
            #price per share
            PP_share = float(symbol_lookup["price"])
            company_name = symbol_lookup["name"]
            transaction_cost = PP_share * shares
            #applies the cost of the transaction to the cash value in the users db
            cash = db.execute("SELECT cash FROM users WHERE id = ?", user_id)

            if transaction_cost > cash[0]["cash"]:
                return apology("Can't afford that transaction", 400)
            else:

                symbols = db.execute("SELECT name_stock FROM stocks WHERE id_2=? GROUP BY name_stock", user_id)
                symbols2 = symbols
                for i in range(0, len(symbols2)):
                    symbols2[i] = symbols2[i]["name_stock"]
                #if in database, update
                if symbol.upper() in symbols2:
                    db.execute("UPDATE totals SET quantity = quantity + ?, total = total + ? WHERE name_stock2 = ?", shares, transaction_cost, symbol)
                #if not inside the db, create new line
                else:
                    db.execute("INSERT INTO totals (id_3, username_3, name_stock2, quantity, current_price, total, company_name) VALUES(?, ?, ?, ?, ?, ?, ?)", user_id, user_username, symbol, shares, PP_share, transaction_cost, company_name)
                    db.execute("UPDATE totals SET name_stock2 = UPPER(name_stock2)")

                db.execute("UPDATE users SET cash = cash - ? WHERE id == ? ", transaction_cost, user_id)
                now = datetime.now()
                transac_time = now.strftime("%Y-%m-%d %H:%M:%S")
                #now fulfilling the second db

                db.execute("INSERT INTO stocks (id_2, username_2, quantity, PPS, name_stock, company, time, real_price) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", user_id, user_username, shares, PP_share, symbol, company_name, transac_time, PP_share)
                db.execute("UPDATE stocks SET name_stock = UPPER(name_stock)")


                #column_name = "asset_price"
                #db.execute("UPDATE stocks SET ? = ? WHERE id_2 = ?", column_name, transaction_cost, user_id)

                return redirect("/")









@app.route("/history")
@login_required
def history():
    if request.method == 'GET':
        user_id = session["user_id"]
        data = db.execute("SELECT * FROM stocks WHERE id_2=? ORDER by time DESC", user_id)
        return render_template("history.html", DATA=data)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]
        session["user_username"] = rows[0]["username"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():

    symbol = request.form.get("symbol")

    if request.method == "POST":
        if not symbol:
            return apology("must provide a symbol", 400)
        else:
            quote = lookup(symbol)
            if not quote:
                return apology("must provide a valid symbol", 400)
            else:
                return render_template("quoted.html", Name = quote["name"], Price=quote["price"], Symbol=quote["symbol"])

    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":
        """Register user"""
        if not request.form.get("username"):
            return apology("must provide username", 400)

        if not request.form.get("password"):
            return apology("must provide password", 400)

        if not request.form.get("confirmation"):
            return apology("must provide confirm password", 400)

        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        if len(rows) != 0:
            return apology("this username is already taken", 400)

        if request.form.get("password") != request.form.get("confirmation"):
            return apology("the passwords must match", 400)

        #when every error checking is passed
        else:
            username = request.form.get("username")
            hashed_password = generate_password_hash(request.form.get("password"))
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hashed_password)

        return redirect("/")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == 'POST':
        shares = int(request.form.get("shares"))
        #symbol of the stock obtained from the select menu input
        symbol = request.form.get("symbol")
        symbol = symbol.upper()
        #looking up on the website the value for this symbol
        symbol_lookup = lookup(symbol)
        user_id = session["user_id"]
        user_username = session["user_username"]
        if not shares:
            return apology("You must indicate how many shares you want to sell", 400)
        if int(shares) < 1:
            return apology("You must indicate a positive number of shares you want to sell", 400)
        #when everything is going ok
        #what is the submit button doing
        else:
            #price per share
            PP_share = float(symbol_lookup["price"])
            company_name = symbol_lookup["name"]
            transaction_gain = float(PP_share * -shares)
            test = {'test' : transaction_gain}
            #CHECK IF ENOUGH SHARES
            share_held1 = db.execute("SELECT id_2, username_2, name_stock, company, PPS, SUM(total), SUM(quantity) FROM stocks WHERE id_2 =? AND name_stock == ? GROUP BY name_stock", user_id, symbol)
            share_held2 = share_held1[0]["SUM(quantity)"]
            if int(shares) > share_held2:
                return apology("You don't have enough shares to realize that transaction", 400)
            else:
                db.execute("UPDATE totals SET quantity = quantity + ?, total = total + ? WHERE name_stock2 = ?", -shares, transaction_gain, symbol)
                    #applies the gain of the transaction to the cash value in the users db
                db.execute("UPDATE users SET cash = cash - ? WHERE id == ? ", transaction_gain, user_id)
                now = datetime.now()
                transac_time = now.strftime("%Y-%m-%d %H:%M:%S")
                #now fulfilling the second db
                db.execute("INSERT INTO stocks (id_2, username_2, quantity, PPS, name_stock, time, total, company) VALUES(?, ?, ?, ?, ?, ?, ?, ?)", user_id, user_username, -shares, PP_share, symbol, transac_time, transaction_gain, company_name)
                #db.execute("UPDATE stocks SET total =? WHERE total= 0", transaction_gain)
                db.execute("UPDATE stocks SET name_stock = UPPER(name_stock)")
                share_held1 = db.execute("SELECT id_2, username_2, name_stock, company, PPS, SUM(total), SUM(quantity) FROM stocks WHERE id_2 =? AND name_stock == ? GROUP BY name_stock", user_id, symbol)
                share_held2 = share_held1[0]["SUM(quantity)"]
                if share_held2 == 0:
                    db.execute("DELETE FROM totals WHERE name_stock2 = ?", symbol)

                return redirect("/")
    #display the page when method is GET
    else:
        user_id = session["user_id"]
        new_stocks = db.execute("SELECT id_2, username_2, name_stock, company, PPS, SUM(total), SUM(quantity) FROM stocks WHERE id_2 =? GROUP BY name_stock", user_id)
        return render_template("sell.html", STOCKS=new_stocks)

@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    if request.method == 'GET':
        return render_template("change.html")
    else:
        if not request.form.get("cur_password"):
            return apology("must provide the current password", 400)
        if not request.form.get("new_password1"):
            return apology("must provide new password", 400)
        if not request.form.get("new_password2"):
            return apology("must provide a password confirmation", 400)

        user_id = session["user_id"]
        new_password = request.form.get("new_password1")
        new_password2 = request.form.get("new_password2")
        if new_password != new_password2:
            return apology("the new passwords don't match", 400)
        else:
            new_hash = generate_password_hash(new_password)
            db.execute("UPDATE users SET hash =? WHERE id = ?", new_hash, user_id)
            return render_template("changed.html")

@app.route("/cash", methods=["GET", "POST"])
@login_required
def cash():
    user_id = session["user_id"]
    if request.method == 'POST':
        amount = float(request.form.get("cash"))
        if not amount:
            return apology("You must provide a quantity of cash you want to add to your account", 400)
        if amount < 0:
            return apology("You must provide a positive amount to add to your account", 400)
        db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", amount, user_id)
        return render_template("cash_added.html", AMOUNT = amount)
    else:
        return render_template("cash.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


