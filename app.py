from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# Koneksi ke database MySQL
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="rental_db"
)

from flask import Flask, render_template, request, redirect, url_for, session

# Atur secret key untuk session
app.secret_key = 'secret_key_admin'

# Halaman login admin
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None  # Default tidak ada error
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Validasi login
        if username == 'admin' and password == 'admin123':  # Ganti sesuai dengan data Anda
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Nama pengguna atau kata sandi salah!'  # Set error message jika salah

    # Render halaman login dengan pesan error jika ada
    return render_template('login.html', error=error)


#admin dashbord
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('logged_in'):
        flash('Silakan login terlebih dahulu!', 'warning')
        return redirect(url_for('admin_login'))

    try:
        cursor = db.cursor(dictionary=True)

        # Ambil daftar kendaraan
        cursor.execute("SELECT * FROM vehicles")
        vehicles = cursor.fetchall()

        # Ambil laporan order
        cursor.execute("SELECT orders.id, orders.customer_name, orders.rental_days, orders.total_price, orders.order_date, vehicles.name AS vehicle_name FROM orders JOIN vehicles ON orders.vehicle_id = vehicles.id")
        orders = cursor.fetchall()

        cursor.close()

        return render_template('admin_dashboard.html', vehicles=vehicles, orders=orders)
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return f"Database error: {err}"
#logout admin
@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin_login'))

# Halaman utama untuk daftar kendaraan (Admin View)
@app.route('/')
def index():
    try:
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT * FROM vehicles")
        vehicles = cursor.fetchall()
        cursor.close()
        return render_template('rent.html', vehicles=vehicles)
    except mysql.connector.Error as err:
        print(f"Error: {err}")
        return f"Database error: {err}"

# Tambah kendaraan baru (Admin View)
@app.route('/admin/add_vehicle', methods=['POST', 'GET'])
def add_vehicle():
    if request.method == 'GET':
        # Render halaman form tambah kendaraan
        return render_template('add_vehicle.html')
    
    if request.method == 'POST':
        try:
            # Ambil data dari form
            name = request.form['name']
            price_per_day = request.form['price_per_day']
            stock = request.form['stock']

            # Insert ke database
            cursor = db.cursor()
            query = "INSERT INTO vehicles (name, price_per_day, stock) VALUES (%s, %s, %s)"
            cursor.execute(query, (name, price_per_day, stock))
            db.commit()
            cursor.close()

            # Redirect ke dashboard dengan pesan sukses
            return redirect('/admin/dashboard')
        except mysql.connector.Error as err:
            # Log error dan kembalikan pesan
            print(f"Database Error: {err}")
            return f"Database Error: {err}", 500
        except Exception as e:
            # Tangani error lainnya
            print(f"Application Error: {e}")
            return f"Application Error: {e}", 500


# Update kendaraan (Admin View)
@app.route('/update_vehicle/<int:vehicle_id>', methods=["GET", "POST"])
def update_vehicle(vehicle_id):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM vehicles WHERE id = %s", (vehicle_id,))
    vehicle = cursor.fetchone()
    if request.method == "POST":
        name = request.form['name']
        price_per_day = request.form['price_per_day']
        stock = request.form['stock']

        cursor.execute("UPDATE vehicles SET name = %s, price_per_day = %s, stock = %s WHERE id = %s",
                       (name, price_per_day, stock, vehicle_id))
        db.commit()
        cursor.close()
        return redirect(url_for('admin_dashboard'))
    cursor.close()
    return render_template("update_vehicle.html", vehicle=vehicle)

# Hapus kendaraan (Admin View)
@app.route('/admin/delete_vehicle/<int:vehicle_id>', methods=['POST'])
def delete_vehicle(vehicle_id):
    try:
        cursor = db.cursor()
        cursor.execute("DELETE FROM vehicles WHERE id = %s", (vehicle_id,))
        db.commit()
        cursor.close()
        return redirect(url_for('admin_dashboard'))
    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return f"Terjadi kesalahan: {err}"

def get_all_vehicles():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM vehicles")  # Mengambil semua data kendaraan
    vehicles = cursor.fetchall()
    cursor.close()
    return vehicles

# Pelanggan menyewa kendaraan
@app.route('/rent', methods=['GET', 'POST'])
def rent_vehicle():
    if request.method == 'POST':
        # Ambil data dari form
        customer_name = request.form.get('customer_name')
        vehicle_id = request.form.get('vehicle_id')
        rental_days = request.form.get('rental_days')

        if not all([customer_name, vehicle_id, rental_days]):
            return "Form tidak lengkap", 400

        # Ambil harga kendaraan
        cursor = db.cursor(dictionary=True)
        cursor.execute("SELECT price_per_day, stock FROM vehicles WHERE id = %s", (vehicle_id,))
        vehicle = cursor.fetchone()

        if not vehicle:
            return "Kendaraan tidak ditemukan", 404

        if vehicle['stock'] <= 0:
            return "Kendaraan tidak tersedia", 400

        total_price = vehicle['price_per_day'] * int(rental_days)

        # Kurangi stok kendaraan
        cursor.execute("UPDATE vehicles SET stock = stock - 1 WHERE id = %s", (vehicle_id,))

        # Simpan pesanan
        cursor.execute("""
            INSERT INTO orders (customer_name, vehicle_id, rental_days, total_price, order_date)
            VALUES (%s, %s, %s, %s, CURDATE())
        """, (customer_name, vehicle_id, rental_days, total_price))
        db.commit()
        cursor.close()

        # Kembali ke halaman sewa dengan pesan sukses
        message = f"Pesanan berhasil! Total harga: Rp{total_price}. Klik kembali untuk menyewa lagi."
        return render_template('rent.html', vehicles=get_all_vehicles(), message=message)

    # Untuk GET request, tampilkan form dengan kendaraan yang tersedia
    return render_template('rent.html', vehicles=get_all_vehicles())

# Laporan pesanan (Admin View)
@app.route('/orders')
def orders():
    try:
        # Ambil data pesanan dan urutkan berdasarkan jumlah hari
        cursor = db.cursor(dictionary=True)
        cursor.execute("""
            SELECT orders.id, orders.customer_name, vehicles.name AS vehicle_name, orders.rental_days, orders.total_price
            FROM orders
            JOIN vehicles ON orders.vehicle_id = vehicles.id
            ORDER BY orders.rental_days ASC
        """)
        orders = cursor.fetchall()
        cursor.close()

        return render_template('orders.html', orders=orders)

    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
        return f"Terjadi kesalahan: {err}"

# Menjalankan aplikasi Flask
if __name__ == '__main__':
    app.run(debug=True)
