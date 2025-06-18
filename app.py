import streamlit as st
from PIL import Image, UnidentifiedImageError
from ultralytics import YOLO
import tempfile
import gdown
import io
import os

# === SETUP MODEL (Google Drive) =======================================
MODEL_URL  = "https://drive.google.com/file/d/1ZE6fp6XCdQt1EHQLCfZkcVYKNr9-2RdD/view?usp=sharing"
MODEL_PATH = "best.pt"            # tersimpan di root project

# Unduh sekali saja jika file belum ada
if not os.path.exists(MODEL_PATH):
    with st.spinner("🔄 Mengunduh model dari Google Drive..."):
        gdown.download(MODEL_URL, MODEL_PATH, quiet=False, fuzzy=True)

# Muat model
try:
    model = YOLO(MODEL_PATH)      # ganti MODEL_PATH jika disimpan di folder lain
    NAMES = model.names           # mapping index → label dataset (mis. "A", "B", "C")
except Exception as e:
    st.error(f"❌ Gagal memuat model: {e}")
    st.stop()

# === APLIKASI STREAMLIT ===============================================
st.set_page_config(page_title="Deteksi Kualitas Tomat", layout="centered")
st.title("🍅 Deteksi Kualitas Buah Tomat (Grade A, B, C)")
st.caption("Upload gambar tomat, dan sistem akan mendeteksi kualitasnya.")

uploaded_file = st.file_uploader(
    "Upload Gambar Tomat",
    type=["jpg", "jpeg", "png", "heic"],
    accept_multiple_files=False
)

if uploaded_file:
    # ------------------------------------------------------------------
    # 1) Buka & tampilkan gambar asli
    # ------------------------------------------------------------------
    try:
        img = Image.open(uploaded_file).convert("RGB")
    except UnidentifiedImageError:
        st.error("❌ Format gambar tidak didukung. Gunakan .jpg, .jpeg, .png, atau .heic.")
        st.stop()

    st.image(img, caption="Gambar yang Diupload", use_container_width=True)

    # ------------------------------------------------------------------
    # 2) Simpan ke file sementara → lakukan deteksi
    # ------------------------------------------------------------------
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
        img.save(tf.name)
        temp_path = tf.name

    results = model(temp_path)       # list (batch), 1 gambar = index 0
    r = results[0]

    # ------------------------------------------------------------------
    # 3) Visualisasi hasil + tampilkan
    # ------------------------------------------------------------------
    annotated = r.plot()             # ndarray (BGR)
    annotated_pil = Image.fromarray(annotated[..., ::-1])  # ke RGB
    st.image(annotated_pil, caption="Hasil Deteksi dengan Bounding Box",
             use_container_width=True)

    # ------------------------------------------------------------------
    # 4) Rekap jumlah tiap grade
    # ------------------------------------------------------------------
    class_idxs = r.boxes.cls.tolist() if r.boxes else []
    class_names = [NAMES[int(i)] for i in class_idxs]

    count_a = class_names.count("A")
    count_b = class_names.count("B")
    count_c = class_names.count("C")

    st.markdown("### 📊 Ringkasan Deteksi")
    col1, col2, col3 = st.columns(3)
    col1.metric("Grade A", count_a)
    col2.metric("Grade B", count_b)
    col3.metric("Grade C", count_c)

    # ------------------------------------------------------------------
    # 5) Tombol download hasil deteksi
    # ------------------------------------------------------------------
    buf = io.BytesIO()
    annotated_pil.save(buf, format="JPEG")
    st.download_button("💾 Download Hasil Deteksi",
                       data=buf.getvalue(),
                       file_name="hasil_deteksi.jpg",
                       mime="image/jpeg")

    # Bersihkan file sementara
    os.remove(temp_path)
