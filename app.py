import streamlit as st
from PIL import Image, UnidentifiedImageError
from ultralytics import YOLO
from fpdf import FPDF
import tempfile, gdown, os, json, io, datetime
# Import yang diperlukan untuk kamera
from streamlit_webrtc import webrtc_streamer, VideoTransformerBase, WebRtcMode
import av # Diperlukan oleh streamlit-webrtc untuk penanganan frame
import numpy as np # Diperlukan untuk konversi gambar
# Hapus import psycopg2 dan bcrypt karena tidak menggunakan database

# ╭───────────────────  AUTO-THEME  ───────────────────╮
#   Light ⬅︎ default | otomatis gelap jika device dark
# ╰─────────────────────────────────────────────────────╯
st.markdown(
    """
    <style id="auto-theme">
    @media (prefers-color-scheme: dark) {
      :root {
        --primary-color:#ff6347;
        --text-color:#eeeeee;
        --background-color:#1e1e1e;
        --secondary-background-color:#262730;
      }
    }
    @media (prefers-color-scheme: light), (prefers-color-scheme: no-preference) {
      :root {
        --primary-color:#d13b0c;
        --text-color:#000000;
        --background-color:#ffffff;
        --secondary-background-color:#fdfdf5;
      }
    }
    body, .stApp {
      background-color: var(--background-color);
      color: var(--text-color);
    }
    input, textarea, .stTextInput > div > div, .stPasswordInput > div > div,
    .stButton > button {
      background-color: var(--secondary-background-color) !important;
      color: var(--text-color) !important;
      border: 1px solid #ccc;
    }
    .stButton > button:hover {
      background-color: #ecebe1 !important;
      color: var(--text-color) !important;
    }
    ::placeholder { color:#666 !important; opacity:1; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ───────────────────────────────────────────────
#  SELANJUTNYA TETAPI KODE LAMA TANPA BAGIAN THEME
# ───────────────────────────────────────────────

def force_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

st.set_page_config(page_title="TomaTect: Deteksi Kualitas Tomat", layout="centered")

## Manajemen Pengguna (File JSON)


USER_FILE = "users.json"

def load_users():
    """Memuat data pengguna dari file JSON."""
    return json.load(open(USER_FILE)) if os.path.exists(USER_FILE) else {}

def save_users(u):
    """Menyimpan data pengguna ke file JSON."""
    json.dump(u, open(USER_FILE, "w"))

# Muat pengguna saat aplikasi dimulai
users = load_users()

defaults = {
    "logged_in": False,
    "page": "login",
    "username": "",
    "model": None,
    "label_names": {},
    "sub_page": "Deteksi"
}
for k, v in defaults.items():
    st.session_state.setdefault(k, v)

def signup():
    st.title("Daftar Akun")
    u = st.text_input("Username Baru")
    p = st.text_input("Password", type="password")
    if st.button("Daftar"):
        if u in users:
            st.error("Username sudah ada.")
        elif not u or not p:
            st.warning("Username / Password kosong.")
        else:
            users[u] = p # Simpan password tanpa hashing
            save_users(users)
            st.success("Berhasil daftar, silakan login.")
            st.session_state.page = "login"
            force_rerun()
    st.button("Kembali ke Login", on_click=lambda: st.session_state.update(page="login"))

def login():
    st.title("Login TomaTect")
    u = st.text_input("Username", key="username_input")
    p = st.text_input("Password", type="password", key="password_input")
    if st.button("Login", key="login_button"):
        if u in users and users[u] == p:
            st.session_state.update(logged_in=True, username=u, page="main")
            force_rerun()
        else:
            st.error("Username / Password salah.")
    st.button("Belum punya akun? Daftar", key="signup_button", on_click=lambda: st.session_state.update(page="signup"))

---

## Halaman Utama Aplikasi

```python
def about_page():
    st.title("Tingkat Kematangan Tomat")
    st.write("""
    Kematangan tomat merupakan indikator penting dalam penentuan kualitas, rasa, serta waktu panen dan distribusi. Berikut adalah tiga kategori utama tingkat kematangan tomat yang digunakan dalam aplikasi TomaTect:
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.image("https://raw.githubusercontent.com/rahmidwintan/TomatEct/main/images/matang.png", caption="Matang", use_container_width=True)
        st.markdown("""
        **Matang (Grade A)** - Warna merah merata  
        - Tekstur lembut  
        - Siap dikonsumsi langsung
        """)

    with col2:
        st.image("https://raw.githubusercontent.com/rahmidwintan/TomatEct/main/images/setengah_matang.png", caption="Setengah Matang", use_container_width=True)
        st.markdown("""
        **Setengah Matang (Grade B)** - Warna merah-kuning  
        - Masih keras sebagian  
        - Cocok untuk penyimpanan atau distribusi
        """)

    with col3:
        st.image("https://raw.githubusercontent.com/rahmidwintan/TomatEct/main/images/mentah.png", caption="Mentah", use_container_width=True)
        st.markdown("""
        **Mentah (Grade C)** - Warna hijau mendominasi  
        - Tekstur keras  
        - Belum siap konsumsi, cocok untuk pematangan lanjutan
        """)

    st.write("---")
    st.info("Klasifikasi ini digunakan sebagai dasar untuk deteksi otomatis kualitas tomat dalam aplikasi TomaTect.")

def detect_page():
    st.title("TomaTect: Deteksi Tingkat Kematangan Tomat")
    st.caption("Deteksi Tomat Sekarang!")

    MODEL_URL  = "https://drive.google.com/file/d/1ZE6fp6XCdQt1EHQLCfZkcVYKNr9-2RdD/view?usp=sharing"
    MODEL_PATH = "best.pt"

    # ── load model sekali saja ──
    if st.session_state.model is None:
        if not os.path.exists(MODEL_PATH):
            with st.spinner("Mengunduh model…"):
                gdown.download(MODEL_URL, MODEL_PATH, quiet=False, fuzzy=True)
        st.session_state.model = YOLO(MODEL_PATH)
        st.session_state.label_names = st.session_state.model.names

    model, NAMES = st.session_state.model, st.session_state.label_names

    # PDF gabungan (inisialisasi di sini agar bisa digunakan untuk upload dan kamera)
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # Flag untuk melacak apakah ada konten yang ditambahkan ke PDF
    pdf_has_content = False

    # --- Bagian Kamera Belakang ---
    st.markdown("---")
    st.header("📸 Ambil Gambar dari Kamera Belakang")
    st.info("Pastikan Anda memberikan izin akses kamera pada browser Anda.")

    webrtc_ctx = webrtc_streamer(
        key="camera-input",
        mode=WebRtcMode.SENDRECV,
        video_receiver_size=400,
        media_stream_constraints={"video": True, "audio": False},
    )

    captured_image_placeholder = st.empty()

    if webrtc_ctx.video_receiver:
        if st.button("Ambil Foto dari Kamera"):
            try:
                frame = webrtc_ctx.video_receiver.get_frame(timeout=1.0)
                if frame:
                    img_array = frame.to_ndarray(format="bgr24")
                    img_pil = Image.fromarray(img_array[:, :, ::-1])

                    captured_image_placeholder.image(img_pil, caption="Gambar yang Diambil dari Kamera", width=600)

                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
                        img_pil.save(tf.name)
                        temp_path_camera = tf.name

                    r = model(temp_path_camera)[0]
                    annotated_camera = Image.fromarray(r.plot()[..., ::-1])
                    st.image(annotated_camera, caption="Hasil Deteksi dari Kamera", use_container_width=True)

                    cls_camera = [NAMES[int(i)] for i in (r.boxes.cls.tolist() if r.boxes else [])]
                    a_camera, b_camera, c_camera = cls_camera.count("A"), cls_camera.count("B"), cls_camera.count("C")
                    col1_cam, col2_cam, col3_cam = st.columns(3)
                    col1_cam.metric("Grade A (Kamera)", a_camera)
                    col2_cam.metric("Grade B (Kamera)", b_camera)
                    col3_cam.metric("Grade C (Kamera)", c_camera)

                    buf_camera = io.BytesIO()
                    annotated_camera.save(buf_camera, format="JPEG")
                    st.download_button(
                        "Download Hasil Deteksi (Kamera)",
                        buf_camera.getvalue(),
                        f"hasil_kamera_{datetime.datetime.now():%Y%m%d_%H%M%S}.jpeg",
                        "image/jpeg"
                    )

                    # Tambahkan ke PDF
                    pdf.add_page()
                    pdf.set_font("Times", size=10)
                    pdf.set_xy(10, 10)
                    pdf.multi_cell(0, 8,
                        f"[Kamera] Gambar dari Kamera\n"
                        f"Grade A : {a_camera}   Grade B : {b_camera}   Grade C : {c_camera}\n"
                        f"Tanggal  : {datetime.datetime.now():%d/%m/%Y %H:%M}\n"
                        f"Pengguna : {st.session_state.username}"
                    )
                    img_path_annot_camera = f"{temp_path_camera}_annot.jpg"
                    annotated_camera.save(img_path_annot_camera)
                    pdf.image(img_path_annot_camera, x=20, y=55, w=170, h=140)
                    os.remove(img_path_annot_camera)
                    os.remove(temp_path_camera)
                    pdf_has_content = True # Set flag bahwa PDF punya konten
                else:
                    st.warning("Tidak ada frame yang diterima dari kamera. Pastikan kamera aktif.")
            except Exception as e:
                st.error(f"Terjadi kesalahan saat mengambil atau memproses gambar dari kamera: {e}")

    st.markdown("---") # Pemisah antara bagian kamera dan upload

    # --- Bagian Pemrosesan Uploaded Files ---
    st.header("⬆️ Upload Gambar dari Perangkat")
    uploaded_files = st.file_uploader(
        "Upload Gambar", type=["jpg", "jpeg", "png", "heic"],
        accept_multiple_files=True
    )

    if uploaded_files:
        for idx, uploaded in enumerate(uploaded_files, 1):
            st.markdown(f"###  {uploaded.name}")

            try:
                img = Image.open(uploaded).convert("RGB")
            except UnidentifiedImageError:
                st.error("Format tidak didukung.");  continue
            st.image(img, caption="Gambar Asli", width=800)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
                img.save(tf.name)
                temp_path_uploaded = tf.name

            r = model(temp_path_uploaded)[0]
            annotated = Image.fromarray(r.plot()[..., ::-1])
            st.image(annotated, caption="Hasil Deteksi", use_container_width=True)

            cls = [NAMES[int(i)] for i in (r.boxes.cls.tolist() if r.boxes else [])]
            a, b, c = cls.count("A"), cls.count("B"), cls.count("C")
            col1, col2, col3 = st.columns(3)
            col1.metric("Grade A", a); col2.metric("Grade B", b); col3.metric("Grade C", c)

            buf = io.BytesIO()
            annotated.save(buf, format="JPEG")
            st.download_button(f"Download Gambar – {uploaded.name}",
                               buf.getvalue(), f"hasil_{uploaded.name}", "image/jpeg")

            # Tambahkan ke PDF
            pdf.add_page()
            pdf.set_font("Times", size=10)
            pdf.set_xy(10, 10)
            pdf.multi_cell(0, 8,
                f"[{idx}] {uploaded.name}\n"
                f"Grade A : {a}   Grade B : {b}   Grade C : {c}\n"
                f"Tanggal  : {datetime.datetime.now():%d/%m/%Y %H:%M}\n"
                f"Pengguna : {st.session_state.username}"
            )
            img_path_annot_uploaded = f"{temp_path_uploaded}_annot.jpg"
            annotated.save(img_path_annot_uploaded)
            pdf.image(img_path_annot_uploaded, x=20, y=55, w=170, h=140)
            os.remove(img_path_annot_uploaded)
            os.remove(temp_path_uploaded)
            pdf_has_content = True # Set flag bahwa PDF punya konten

    # Tombol download PDF gabungan
    if pdf_has_content:
        pdf_bytes = pdf.output(dest="S").encode("latin1")
        st.download_button("Download Laporan Gabungan (PDF)",
                           pdf_bytes, "laporan_tomatect_gabungan.pdf", "application/pdf")
    else:
        st.info("Upload gambar atau ambil foto dari kamera untuk melihat hasil deteksi dan membuat laporan.")


def main_app():
    with st.sidebar:
        st.markdown(f"Username")
        st.markdown(f"👤 **{st.session_state.username}**")
        st.session_state.sub_page = st.radio("Menu", ["Deteksi", "Tentang Tomat"])
        if st.button("Logout"):
            st.session_state.update(logged_in=False, page="login", username="")
            force_rerun()
    if st.session_state.sub_page == "Tentang Tomat":
        about_page()
    else:
        detect_page()

if st.session_state.page == "signup":
    signup()
elif not st.session_state.logged_in:
    login()
elif st.session_state.page == "main":
    main_app()
else:
    st.session_state.page = "login"; login()
