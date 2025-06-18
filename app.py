import streamlit as st
from PIL import Image, UnidentifiedImageError
from ultralytics import YOLO
import tempfile, gdown, os, json, io

# ────────────────────────────────────────────────────────────────
# 1.  KONFIGURASI HALAMAN
# ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Deteksi Kualitas Tomat", layout="centered")

# ────────────────────────────────────────────────────────────────
# 2.  MANAJEMEN USER (LOGIN & SIGNUP)
# ────────────────────────────────────────────────────────────────
USER_FILE = "users.json"

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

users = load_users()

# inisialisasi session_state
if "logged_in"   not in st.session_state: st.session_state.logged_in = False
if "page"        not in st.session_state: st.session_state.page = "login"
if "username"    not in st.session_state: st.session_state.username = ""
if "model"       not in st.session_state: st.session_state.model = None
if "label_names" not in st.session_state: st.session_state.label_names = {}

# ────────────────────────────────────────────────────────────────
# 3.  HALAMAN SIGNUP
# ────────────────────────────────────────────────────────────────
def signup_page():
    st.title("Daftar Akun Baru")
    new_user = st.text_input("Username Baru")
    new_pass = st.text_input("Password", type="password")

    if st.button("Daftar"):
        if new_user in users:
            st.error("❌ Username sudah digunakan.")
        elif new_user == "" or new_pass == "":
            st.warning("⚠️ Username dan Password tidak boleh kosong.")
        else:
            users[new_user] = new_pass
            save_users(users)
            st.success("✅ Berhasil daftar! Anda sudah login.")
            st.session_state.update(logged_in=True, username=new_user, page="main")

    st.button("🔙 Kembali ke Login", on_click=lambda: st.session_state.update(page="login"))

# ────────────────────────────────────────────────────────────────
# 4.  HALAMAN LOGIN
# ────────────────────────────────────────────────────────────────
def login_page():
    st.title("Login ke Aplikasi Tomatect")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in users and users[username] == password:
            st.success("✅ Login berhasil!")
            st.session_state.update(logged_in=True, username=username, page="main")
        else:
            st.error("❌ Username atau password salah.")

    st.button("Belum punya akun? Daftar",
              on_click=lambda: st.session_state.update(page="signup"))

# ────────────────────────────────────────────────────────────────
# 5.  HALAMAN UTAMA (DETEKSI TOMAT)
# ────────────────────────────────────────────────────────────────
def main_page():
    st.title("🍅 TomaTect: Deteksi Kualitas Buah Tomat (Grade A, B, C)")
    st.caption(f"Halo **{st.session_state.username}**, upload gambar tomat untuk dideteksi.")

    # === SETUP MODEL (download sekali lalu cache di session) ===========
    MODEL_URL  = "https://drive.google.com/file/d/1ZE6fp6XCdQt1EHQLCfZkcVYKNr9-2RdD/view?usp=sharing"
    MODEL_PATH = "best.pt"

    if st.session_state.model is None:
        if not os.path.exists(MODEL_PATH):
            with st.spinner("🔄 Mengunduh model dari Google Drive..."):
                gdown.download(MODEL_URL, MODEL_PATH, quiet=False, fuzzy=True)
        try:
            st.session_state.model = YOLO(MODEL_PATH)
            st.session_state.label_names = st.session_state.model.names  # dict idx→label
        except Exception as e:
            st.error(f"❌ Gagal memuat model: {e}")
            st.stop()

    model = st.session_state.model
    NAMES = st.session_state.label_names

    # === Upload Gambar =================================================
    uploaded_file = st.file_uploader(
        "Upload Gambar Tomat",
        type=["jpg", "jpeg", "png", "heic"],
        accept_multiple_files=False
    )

    if uploaded_file:
        # 1) Tampilkan gambar asli
        try:
            img = Image.open(uploaded_file).convert("RGB")
        except UnidentifiedImageError:
            st.error("❌ Format gambar tidak didukung.")
            st.stop()

        st.image(img, caption="Gambar yang Diupload", use_container_width=True)

        # 2) Simpan ke file sementara & deteksi
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
            img.save(tf.name)
            temp_path = tf.name

        results = model(temp_path)
        r = results[0]

        # 3) Visualisasi bounding-box
        annotated = r.plot()                                   # ndarray (BGR)
        annotated_pil = Image.fromarray(annotated[..., ::-1])  # ke RGB
        st.image(annotated_pil, caption="Hasil Deteksi dengan Bounding Box",
                 use_container_width=True)

        # 4) Rekap jumlah tiap grade
        class_idxs  = r.boxes.cls.tolist() if r.boxes else []
        class_names = [NAMES[int(i)] for i in class_idxs]

        st.markdown("### Ringkasan Deteksi")
        col1, col2, col3 = st.columns(3)
        col1.metric("Grade A", class_names.count("A"))
        col2.metric("Grade B", class_names.count("B"))
        col3.metric("Grade C", class_names.count("C"))

        # 5) Tombol download hasil
        buf = io.BytesIO()
        annotated_pil.save(buf, format="JPEG")
        st.download_button("💾 Download Hasil Deteksi",
                           data=buf.getvalue(),
                           file_name="hasil_deteksi.jpg",
                           mime="image/jpeg")

        os.remove(temp_path)

    st.markdown("---")
    if st.button("Logout"):
        st.session_state.update(logged_in=False, page="login", username="")
        st.experimental_rerun()

# ────────────────────────────────────────────────────────────────
# 6.  ROUTER
# ────────────────────────────────────────────────────────────────
if st.session_state.logged_in and st.session_state.page == "main":
    main_page()
elif st.session_state.page == "signup":
    signup_page()
else:
    login_page()
