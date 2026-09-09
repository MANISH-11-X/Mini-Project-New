from flask import Flask, redirect, request, render_template, session 
from pymongo import MongoClient 
from plyer import notification 
from bson.objectid import ObjectId 
from datetime import timedelta, datetime 
import threading 
import time 
import markdown 
from google import genai 
 
genai_client = genai.Client(api_key="YOUR_API_KEY")  # Replace with your actual API key
 
app = Flask(__name__) 
 
app.secret_key = "manish" 
app.permanent_session_lifetime = timedelta(days=15) 
 
 
client = MongoClient("mongodb://localhost:27017") 
 
db = client["food_manager"] 
 
collection = db["collection"] 
 
reg = db["register"] 
 
DAYS_BEFORE_EXPIRY = 1 
 
 
def check_expiry(): 
 
    while True: 
 
        today = datetime.now().date() 
 
        reminder_date = today + timedelta( 
        days=DAYS_BEFORE_EXPIRY 
        ) 
 
        foods = collection.find() 
 
        for food in foods: 
 
            expiry = datetime.strptime( 
            food["expiry"], 
            "%Y-%m-%d" 
            ).date() 
 
            if expiry == reminder_date: 
 
                notification.notify( 
                title="Food Expiry Reminder", 
                message=f"{food['food_name']} will expire tomorrow!", 
                timeout=10 
                ) 
 
        time.sleep(36000) 
 
@app.route("/") 
def home(): 
    return render_template("reg.html") 
 
@app.route("/webhome") 
def webhome(): 
    return render_template('web.html') 
 
@app.route("/register", methods=["POST", "GET"]) 
def register(): 
 
    if request.method == "POST": 
 
        name = request.form["name"] 
        email = request.form["email"] 
        password = request.form["password"] 
 
        reg.insert_one({ 
            "name": name, 
            "email": email, 
            "password": password 
        }) 
 
        notification.notify( 
            title="Grocery Food Manager", 
            message="Register Successfully!" 
        ) 
 
        return redirect("/loginn") 
 
    return render_template("reg.html") 
 
 
# Login Page 
 
@app.route("/loginn") 
def login_page(): 
    return render_template("login.html") 
 
# Login 
@app.route("/login", methods=["POST", "GET"]) 
def login(): 
 
    if request.method == "GET": 
        return render_template("login.html") 
 
    email = request.form["email"] 
    password = request.form["password"] 
 
    user = reg.find_one({ 
        "email": email, 
        "password": password 
    }) 
 
    if user: 
 
        session.permanent = True 
 
        session["user_id"] = str(user["_id"]) 
        session["user_name"] = user["name"] 
        session["user_email"] = user["email"] 
 
        return render_template('web.html') 
 
    return "Invalid email or password" 

# Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/loginn")
 
@app.route("/account") 
def account(): 
 
    if "user_id" not in session: 
        return redirect("/loginn") 
 
    user = reg.find_one({ 
        "_id": ObjectId(session["user_id"]) 
    }) 
 
    if not user: 
        return "User not found" 
 
    return render_template( 
        "account.html", 
        user=user 
    ) 
 
     
# Add Food Page 
@app.route("/add") 
def add_food(): 
 
    if "user_email" not in session: 
        return redirect("/") 
 
    return render_template("add.html") 
 
# Add Food 
@app.route("/add", methods=["POST"]) 
def add(): 
 
    if "user_id" not in session: 
        return redirect("/") 
 
    food_name = request.form["food_name"] 
    category = request.form["category"] 
    quantity = request.form["quantity"] 
    expiry = request.form["expiry"] 
 
    collection.insert_one({ 
        "food_name": food_name, 
        "category": category, 
        "quantity": quantity, 
        "expiry": expiry, 
        "user_id": session["user_id"] 
    }) 
 
    notification.notify( 
        title="Grocery Food Manager", 
        message=f"{food_name} Added Successfully!" 
    ) 
 
    return redirect("/view") 
 
# View Food 
@app.route("/view") 
def view(): 
 
    if "user_id" not in session: 
        return redirect("/") 
 
    foods = collection.find({ 
        "user_id": session["user_id"] 
    }) 
 
    return render_template("view.html", foods=foods) 
 
# Delete Food 
@app.route("/delete/<id>") 
def delete(id): 
 
    if "user_id" not in session: 
        return redirect("/") 
 
    collection.delete_one({ 
        "_id": ObjectId(id), 
        "user_id": session["user_id"] 
    }) 
 
    notification.notify( 
        title="Grocery Food Manager", 
        message="Food Deleted Successfully!" 
    ) 
 
    return redirect("/view") 
 
# Search Food 
@app.route("/search") 
def search(): 
 
    if "user_id" not in session: 
        return redirect("/") 
 
    food_name = request.args.get("food_name", "") 
 
    foods = collection.find({ 
        "user_id": session["user_id"], 
        "food_name": { 
            "$regex": food_name, 
            "$options": "i" 
        } 
    }) 
 
    return render_template("view.html", foods=foods) 
 
@app.route("/accd") 
def accd(): 
 
    acc = reg.find() 
    return render_template('accd.html', acc = acc) 
 
@app.route("/delete_user/<u_id>") 
def delete_user(u_id): 
 
    reg.delete_one({ 
        "_id": ObjectId(u_id) 
    }) 
 
    notification.notify( 
        title="Grocery Food Manager", 
        message="Account Deleted Successfully!" 
    ) 
 
    return redirect("/register") 
 
@app.route("/f") 
def f(): 
    return render_template('index.html') 
 
@app.route("/food", methods = ["POST"]) 
def food(): 
 
    if request.method == "POST": 
 
        foodname = request.form["foodname"] 
 
        response = genai_client.models.generate_content( 
        model="gemini-3.6-flash", 
        contents= f"""food name: {foodname} 
        Suggest exactly 3 recipes using this food.

For each recipe, use this exact Markdown structure:

## Recipe 1: Recipe Name

### Ingredients
- Ingredient 1
- Ingredient 2
- Ingredient 3
- Ingredient 4

### Steps
1. Step one
2. Step two
3. Step three
4. Step four

## Recipe 2: Recipe Name

### Ingredients
- Ingredient 1
- Ingredient 2
- Ingredient 3

### Steps
1. Step one
2. Step two
3. Step three

## Recipe 3: Recipe Name

### Ingredients
- Ingredient 1
- Ingredient 2
- Ingredient 3

### Steps
1. Step one
2. Step two
3. Step three

Keep the recipes concise.
Return ONLY Markdown. Do not use HTML.
        """ 
        ) 
 
        result = markdown.markdown(response.text) 
         
    return render_template( 
        'index.html', 
        foodname = foodname, 
        result = result 
    ) 
 
# Run App 
 
threading.Thread(target=check_expiry, daemon=True).start() #target tells run the function check_expiry in a separate thread, daemon=True means it will run in the background and exit when the main program exits 
 
 
app.run(debug=True)
