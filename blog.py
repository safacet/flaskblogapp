from flask import Flask, render_template, flash, redirect, url_for, session, logging, request
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.handlers.sha2_crypt import sha256_crypt
from passlib import hash
from functools import wraps

#Kullanici giris Decorateri
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "logged_in" in session:
            return f(*args, **kwargs)
        else:
            flash("<strong>Dikkat!</strong> Önce giriş yapmalısınız!", "danger")
            return redirect(url_for("login"))
    return decorated_function

#Kullanici Kayit Formu
class RegisterForm(Form):
    name = StringField("İsim Soyisim:", validators=[validators.Length(min=4,max=25, message="İsminiz 4-25 karakter aralığında olmalıdır!")])
    username = StringField("Kullanıcı Adı:", validators=[validators.Length(min=5,max=35, message="Kulanıcı adınız 5-35 karakter arası olabilir!")])
    email = StringField("Email Adresi:", validators=[validators.Email(message="Lütfen Geçerli Bir E-Mail Adresi Girin!")])
    password = PasswordField("Parola:", validators=[
        validators.DataRequired(message="Lütfen bir parola belirleyin!"),
        validators.EqualTo(fieldname= "confirm", message="Parolanız Eşleşmedi")
    ])
    confirm = PasswordField("Parola Doğrula:")

# Login Formu
class LoginForm(Form):
    username = StringField("Kullanıcı Adı:")
    password = PasswordField("Parola:")

#Makale Form
class ArticleForm(Form):
    title = StringField("Başlık:", validators=[validators.length(min=5, max=100)])
    content = TextAreaField("Makale İçeriği", validators=[validators.length(min=10)])

app = Flask(__name__)
app.secret_key = "safablog"

app.config["MYSQL_HOST"] = "127.0.0.1"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = ""
app.config["MYSQL_DB"] = "safablog"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

#Ana Sayfa
@app.route("/")
def index():
    return render_template("index.html")

#Hakkinda Sayfasi
@app.route("/about")
def about():
    return render_template("about.html")

#Makale Sayfasi
@app.route("/articles")
def articles():
    cursor = mysql.connection.cursor()
    query = "Select * from articles order by id desc"
    result = cursor.execute(query)

    if result > 0:
        articles = cursor.fetchall()
        cursor.close()
        return render_template("articles.html", articles = articles)
    else:
        return render_template("articles.html")

#Kontrol Paneli
@app.route("/dashboard")
@login_required
def dashboard():
    cursor = mysql.connection.cursor()
    query = "Select * From articles where author = %s"
    result = cursor.execute(query, (session["username"],))
    if result > 0:
        articles = cursor.fetchall()
        cursor.close()
        return render_template("dashboard.html", articles = articles)
    else:
        return render_template("dashboard.html")

#Kayit Olma Fonksiyonu
@app.route("/register", methods = ["GET", "POST"])
def register():
    form = RegisterForm(request.form)

    if request.method == "POST" and form.validate():
        name = form.name.data
        username = form.username.data
        email = form.email.data
        password = sha256_crypt.encrypt(form.password.data)
        

        cursor = mysql.connection.cursor()
        query1 = "select username from users where username = %s"
        result = cursor.execute(query1, (username,))

        if result > 0:
            flash("""<strong>Kapılmış!</strong> Bu kullanıcı ismi zaten alınmış. Bu sensen <a href="/login"> Giriş Yap!</a>""", "warning")
            return redirect(url_for("register"))

        query = "Insert into users(name, email, username, password) VALUES(%s, %s, %s, %s)"

        cursor.execute( query, (name, email, username, password))
        mysql.connection.commit()
        cursor.close()

        flash("<strong>Hoşgeldin!</strong> Başarıyla kayıt oldunuz!", category="success")

        return redirect(url_for("login"))
    else:
        return render_template("register.html", form = form)

#Log-in islemi
@app.route("/login", methods = ["GET", "POST"])
def login():
    form = LoginForm(request.form)
    if request.method == "POST":
        username = form.username.data
        password_entered = form.password.data
        
        cursor = mysql.connection.cursor()
        query = "Select * from users where username = %s"

        result = cursor.execute(query,(username,))

        if result > 0:
            data = cursor.fetchone()
            cursor.close()
            real_password = data["password"]
            if sha256_crypt.verify(password_entered, real_password):
                flash("<strong>Hoşgeldin!</strong> Giriş yapıldı!", "success")
                
                session["logged_in"] = True
                session["username"] = username

                return redirect(url_for("index"))
            else:
                flash("<strong>Dikkat!</strong> Parola Yanlış!", "danger")
                redirect(url_for("login"))
        else:
            flash("<strong>Dikkat!</strong> Böyle bir kullanıcı bulunmuyor!", "danger")
            redirect(url_for("login"))

    return render_template("login.html", form = form)


#Log-out Islemi
@app.route("/logout")
def logout():
    session.clear()
    flash("<strong>Güle Güle!</strong> Çıkış yapıldı", "info")
    return redirect(url_for("index"))


#Makale Ekleme
@app.route("/addarticle", methods = ["GET", "POST"])
@login_required
def addarticle():
    form = ArticleForm(request.form)
    if request.method == "POST" and form.validate:
        title = form.title.data
        content = form.content.data
        cursor = mysql.connection.cursor()
        query = "Insert into articles(title, author, content) values(%s, %s, %s)"
        cursor.execute(query,(title, session["username"], content))
        mysql.connection.commit()
        query2 = "select * from articles where content = %s "
        cursor.execute(query2, (content,))
        data = cursor.fetchone()
        id = data["id"]
        cursor.close()
        flash("<strong>Teşekkürler!</strong> Makaleniz Başarıyla Eklendi.", "success")
        return redirect("/article/{}".format(id))
    return render_template("addarticle.html", form = form)

#Makale Silme
@app.route("/delete/<string:id>")
@login_required
def delete(id):
    cursor = mysql.connection.cursor()
    query = "Select * From articles where author = %s and id = %s"
    result = cursor.execute(query, (session["username"], id))
    if result > 0:
        query2 = "Delete from articles where id = %s"
        cursor.execute(query2, (id,))
        mysql.connection.commit()
        cursor.close()
        flash("<strong>Silindi!</strong> Artık böyle bir makale yok!", "success")
        return redirect(url_for("dashboard"))
    else:
        flash("<strong>Opps!</strong> Böyle bir makale yok veya bu işleme yetkiniz yok!", "danger")
        return redirect(url_for("index"))

#Makale Duzenleme
@app.route("/edit/<string:id>", methods= ["GET", "POST"])
@login_required
def edit(id):
    if request.method == "GET":
        cursor = mysql.connection.cursor()
        query = "Select * from articles where id = %s"
        result = cursor.execute(query, (id,))
        article = cursor.fetchone()
        if  (result > 0 and session["username"] == article["author"]) or session["username"] == "safacet":
            
            cursor.close()
            form = ArticleForm()
            form.title.data = article["title"]
            form.content.data = article["content"]
            return render_template("edit.html", form = form)
        else:
            flash("<strong>Opps!</strong> Böyle bir makale yok veya bu işleme yetkiniz yok!", "danger")
            return redirect(url_for("index"))

    else:
        #POST kismi
        form = ArticleForm(request.form)
        newTitle = form.title.data
        newContent = form.content.data
        query = "update articles set title = %s, content = %s where id = %s"
        cursor = mysql.connection.cursor()
        cursor.execute(query, (newTitle, newContent, id))
        mysql.connection.commit()
        cursor.close()
        flash("<strong>Güncellendi!</strong> Makaleniz başarılı bir şekilde güncellediniz.", "success")
        return redirect("/article/{}".format(id))


#Makale Detay Sayfasi
@app.route("/article/<string:id>")
def article(id):
    cursor = mysql.connection.cursor()
    query = "Select * from articles where id = %s"
    result = cursor.execute(query, (id,))
    if result > 0:
        article = cursor.fetchone()
        cursor.close()
        return render_template("article.html", article = article)
    else:
        return render_template("article.html")


#Arama URL
@app.route("/search", methods = ["GET", "POST"])
def search():
    if request.method == "GET":
        return redirect(url_for("index"))
    else:
        keyword = request.form.get("keyword")

        cursor = mysql.connection.cursor()

        query = "select * from articles where title like '%" + keyword + "%'"

        result = cursor.execute(query)

        if result == 0:
            flash("<strong>Opps</strong> Arama kriterlerine uygun makale bulunamadı", "warning")
            return redirect(url_for("articles"))
        else:
            articles = cursor.fetchall()
            return render_template("articles.html", articles = articles)

if __name__ == "__main__":
    app.run(debug=True)