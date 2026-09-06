import streamlit as st
import pandas as pd
import requests
import json
import re
import time

# ==========================================
# KONFIGURASI DAN DATA
# ==========================================
st.set_page_config(page_title="Kuis Adaptif Matematika", layout="wide")

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbw8UBXnO11hg8SBFjRAeTSUpENyg8Hjwi0jqQOfQ_sqNMh6JZ0LEvVPIn0tza1iy017/exec"
EXCEL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQxH0HVZkDQamsnLf9XJeARLNHqxtlNDKBSu65Yor3D0-ll0RE9GsWEjQkYRpXAZDALFtqFgrCzzMIb/pub?gid=0&single=true&output=csv"

# URL CSV untuk membaca Log_Ujian pada Dashboard Guru
LOG_URL = EXCEL_URL.replace("gid=0", "gid=LOG_GID_HERE") # Jika diset publik via Apps Script/Sheets CSV

@st.cache_data(ttl=30)
def load_bank_soal():
    try:
        df = pd.read_csv(EXCEL_URL)
        return df
    except Exception as e:
        st.error(f"Gagal memuat bank soal: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=15)
def load_log_ujian():
    try:
        # Mencoba membaca data log aktivitas dari Apps Script / CSV
        df_log = pd.read_csv(EXCEL_URL.replace("gid=0", "gid=12345678")) # Sesuaikan jika ada gid log khusus
        return df_log
    except:
        return pd.DataFrame()

df_soal = load_bank_soal()

def send_log_to_sheets(nama, kelas, id_soal, jawaban, status, skor, durasi_detik):
    if not WEB_APP_URL.strip():
        return
    payload = {
        "nama": nama,
        "kelas": kelas,
        "id_soal": id_soal,
        "jawaban": jawaban,
        "status": status,
        "skor": skor,
        "durasi": durasi_detik
    }
    try:
        requests.post(WEB_APP_URL, data=json.dumps(payload), headers={"Content-Type": "application/json"})
    except Exception as e:
        st.warning(f"Gagal menyinkronkan data ke Google Sheets: {e}")

# ==========================================
# INISIALISASI SESSION STATE
# ==========================================
if "nama" not in st.session_state:
    st.session_state.nama = ""
if "kelas" not in st.session_state:
    st.session_state.kelas = ""
if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False
if "start_time" not in st.session_state:
    st.session_state.start_time = 0
if "soal_start_time" not in st.session_state:
    st.session_state.soal_start_time = 0
if "current_level" not in st.session_state:
    st.session_state.current_level = 1
if "total_soal_dikerjakan" not in st.session_state:
    st.session_state.total_soal_dikerjakan = 0
if "correct_per_level" not in st.session_state:
    st.session_state.correct_per_level = {1: 0, 2: 0, 3: 0, 4: 0}
if "used_soal_ids" not in st.session_state:
    st.session_state.used_soal_ids = []
if "current_soal" not in st.session_state:
    st.session_state.current_soal = None
if "submitted" not in st.session_state:
    st.session_state.submitted = False
if "is_correct" not in st.session_state:
    st.session_state.is_correct = False
if "user_answer" not in st.session_state:
    st.session_state.user_answer = ""
if "history" not in st.session_state:
    st.session_state.history = []

# ==========================================
# FUNGSI NAVIGASI SOAL ADAPTIF
# ==========================================
def get_next_soal():
    if df_soal.empty:
        return None
    
    lvl = st.session_state.current_level
    while st.session_state.correct_per_level.get(lvl, 0) >= 2 and lvl < 4:
        lvl += 1
        st.session_state.current_level = lvl
        
    available_soal = df_soal[
        (df_soal["Level"] == st.session_state.current_level) & 
        (~df_soal["ID_Soal"].isin(st.session_state.used_soal_ids))
    ]
    
    if available_soal.empty:
        available_soal = df_soal[~df_soal["ID_Soal"].isin(st.session_state.used_soal_ids)]
        
    if available_soal.empty:
        return None
        
    return available_soal.sample(n=1).iloc[0]

def next_question_action():
    st.session_state.total_soal_dikerjakan += 1
    st.session_state.submitted = False
    st.session_state.user_answer = ""
    st.session_state.is_correct = False
    
    if st.session_state.total_soal_dikerjakan < 10:
        st.session_state.current_soal = get_next_soal()
        if st.session_state.current_soal is not None:
            st.session_state.used_soal_ids.append(st.session_state.current_soal["ID_Soal"])
            st.session_state.soal_start_time = time.time()

# ==========================================
# TAMPILAN SIDEBAR
# ==========================================
with st.sidebar:
    st.title("📌 Navigasi Utama")
    role = st.radio("Pilih Peran Halaman:", ["🧑‍🎓 Halaman Siswa (Kuis)", "👨‍🏫 Dashboard Guru (Penilaian)"])
    st.markdown("---")
    if st.button("🗑️ Clear Cache Manual"):
        st.cache_data.clear()
        st.success("Cache berhasil dibersihkan!")

# ==========================================
# HALAMAN SISWA
# ==========================================
if role == "🧑‍🎓 Halaman Siswa (Kuis)":
    st.title("📝 Lembar Kerja Siswa (Kuis Adaptif)")
    
    # Form Identitas Siswa
    if not st.session_state.quiz_started:
        st.info("Silakan isi nama dan kelas untuk memulai kuis. Waktu pengerjakan maksimal **60 menit** (10 Soal).")
        col1, col2 = st.columns(2)
        with col1:
            nama_in = st.text_input("Masukkan Nama Lengkap:")
        with col2:
            kelas_in = st.text_input("Masukkan Kelas:")
            
        if st.button("🚀 Mulai Kuis"):
            if nama_in.strip() != "" and kelas_in.strip() != "":
                st.session_state.nama = nama_in
                st.session_state.kelas = kelas_in
                st.session_state.quiz_started = True
                st.session_state.start_time = time.time()
                st.session_state.total_soal_dikerjakan = 0
                st.session_state.current_level = 1
                st.session_state.correct_per_level = {1: 0, 2: 0, 3: 0, 4: 0}
                st.session_state.used_soal_ids = []
                st.session_state.history = []
                
                soal_pertama = get_next_soal()
                if soal_pertama is not None:
                    st.session_state.current_soal = soal_pertama
                    st.session_state.used_soal_ids.append(soal_pertama["ID_Soal"])
                    st.session_state.soal_start_time = time.time()
                st.rerun()
            else:
                st.warning("Mohon isi Nama dan Kelas terlebih dahulu!")

    # Kuis Berlangsung
    elif st.session_state.quiz_started:
        # Perhitungan sisa waktu total (60 menit = 3600 detik)
        elapsed_total = time.time() - st.session_state.start_time
        remaining_total = max(0, 3600 - int(elapsed_total))
        
        # Cek jika waktu habis atau 10 soal sudah dikerjakan
        if remaining_total <= 0 or st.session_state.total_soal_dikerjakan >= 10:
            if remaining_total <= 0:
                st.error("⏰ Waktu 60 menit telah habis! Kuis dihentikan secara otomatis.")
            
            # TAMPILAN RAPOR NARATIF PENCAPAIAN
            st.balloons()
            st.header("📜 Rapor Hasil & Analysis Pencapaian Siswa")
            st.markdown(f"**Nama:** {st.session_state.nama} | **Kelas:** {st.session_state.kelas}")
            
            total_soal = len(st.session_state.history)
            total_benar = sum([1 for h in st.session_state.history if h["status"] == "BENAR"])
            total_skor = total_benar * 10
            avg_time = sum([h["durasi"] for h in st.session_state.history]) / max(1, total_soal)
            
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            col_m1.metric("Total Skor", f"{total_skor} / 100")
            col_m2.metric("Soal Terjawab", f"{total_soal} / 10")
            col_m3.metric("Level Tertinggi", f"Level {st.session_state.current_level}")
            col_m4.metric("Rata-Rata Waktu / Soal", f"{int(avg_time)} detik")
            
            st.markdown("---")
            st.subheader("💡 Narasi & Rekomendasi Evaluasi")
            
            # Logika Narasi Otomatis
            if total_skor >= 80:
                narasi = f"Selamat **{st.session_state.nama}**! Anda menunjukkan pemahaman matematika yang **sangat baik** dan mampu menyelesaikan soal-soal tingkat lanjut hingga **Level {st.session_state.current_level}**. Kecepatan pengerjaan Anda tergolong efektif dengan rata-rata {int(avg_time)} detik per soal."
                saran = "Pertahankan performa ini! Anda siap menerima tantangan materi matematika pada tingkat yang lebih tinggi."
            elif total_skor >= 50:
                narasi = f"Kerja bagus **{st.session_state.nama}**! Anda memiliki dasar pemahaman yang **cukup baik**, berhasil mencapai **Level {st.session_state.current_level}**. Beberapa soal memerlukan kecermatan lebih lanjut terutama saat menghadapi tipe pilihan kompleks atau menjodohkan."
                saran = "Pelajari kembali petunjuk bimbingan (scaffolding) pada soal-soal yang belum tepat agar konsep matematika Anda semakin solid."
            else:
                narasi = f"Terus semangat **{st.session_state.nama}**! Anda telah berusaha menyelesaikan kuis adaptif ini hingga **Level {st.session_state.current_level}**. Terlihat ada beberapa konsep dasar yang masih memerlukan latihan secara berkala."
                saran = "Disarankan untuk mereview kembali video petunjuk dan berdiskusi dengan guru terkait materi yang dirasa sulit."

            st.write(narasi)
            st.info(f"📌 **Saran Pembelajaran:** {saran}")
            
            st.markdown("---")
            st.subheader("⏱️ Detail Log Aktivitas & Ketepatan Pengerjaan")
            df_hist = pd.DataFrame(st.session_state.history)
            if not df_hist.empty:
                st.dataframe(df_hist, use_container_width=True)
            
            if st.button("🔄 Ulangi Kuis"):
                st.session_state.quiz_started = False
                st.rerun()

        else:
            soal = st.session_state.current_soal
            
            # Panel Waktu & Progress Bar
            menit = remaining_total // 60
            detik = remaining_total % 60
            
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Soal No:** {st.session_state.total_soal_dikerjakan + 1} / 10")
            c2.markdown(f"**Level Saat Ini:** {soal['Level']}")
            c3.markdown(f"⏱️ **Sisa Waktu:** {menit:02d}:{detik:02d}")
            st.progress((st.session_state.total_soal_dikerjakan) / 10)
            
            st.markdown("---")
            st.subheader(soal["Teks_Soal"])
            
            hint_video_url = str(soal.get("Hint_Video", "")).strip() if pd.notna(soal.get("Hint_Video")) else ""
            if hint_video_url.startswith("http://") or hint_video_url.startswith("https://"):
                with st.expander("🎬 Lihat Video Petunjuk"):
                    st.video(hint_video_url)

            # Extraksi Opsi Jawaban Pintar
            raw_opsi = str(soal.get("Opsi_Jawaban", "")) if pd.notna(soal.get("Opsi_Jawaban")) else ""
            if ";" in raw_opsi:
                opsi = [o.strip() for o in raw_opsi.split(";") if o.strip()]
            elif "(" in raw_opsi and ")" in raw_opsi:
                opsi = [match.group(0).strip() for match in re.finditer(r'\([^)]+\)', raw_opsi)]
            elif "," in raw_opsi:
                opsi = [o.strip() for o in raw_opsi.split(",") if o.strip()]
            else:
                opsi = [raw_opsi.strip()] if raw_opsi.strip() else []

            user_ans = ""
            tipe = str(soal["Tipe_Soal"]).upper().strip()
            
            if tipe in ["PGK", "PILIHAN GANDA KOMPLEKS"]:
                st.write("Pilihlah semua kemungkinan jawaban yang menurut Anda benar:")
                selected_opts = []
                for idx, opt in enumerate(opsi):
                    checked = st.checkbox(opt, disabled=st.session_state.submitted, key=f"pgk_{idx}")
                    if checked:
                        selected_opts.append(opt)
                user_ans = "; ".join(selected_opts)
                
            elif tipe in ["MENJODOHKAN", "MATCHING"]:
                st.write("Pilih Pasangan/Jawaban yang tepat:")
                if opsi:
                    user_ans = st.selectbox("Pasangan Jawaban:", ["-- Pilih Jawaban --"] + opsi, disabled=st.session_state.submitted, key="input_menjodohkan")
                    if user_ans == "-- Pilih Jawaban --":
                        user_ans = ""
                else:
                    user_ans = st.text_input("Ketikkan jawaban pasangan Anda:", disabled=st.session_state.submitted, key="input_menjodohkan_txt")
                
            elif tipe in ["PG", "PILIHAN GANDA", "BS", "BENAR SALAH"]:
                user_ans = st.radio("Pilih jawaban:", opsi, disabled=st.session_state.submitted, key="input_pg")
                
            else:
                user_ans = st.text_input("Ketikkan jawaban Anda:", disabled=st.session_state.submitted, key="input_def")
                
            st.markdown("---")
            col_sub, col_next = st.columns([1, 1])
            
            with col_sub:
                if not st.session_state.submitted:
                    if st.button(" Submit Jawaban", type="primary"):
                        if str(user_ans).strip() == "":
                            st.warning("Pilih atau isi jawaban terlebih dahulu!")
                        else:
                            durasi_soal = int(time.time() - st.session_state.soal_start_time)
                            st.session_state.submitted = True
                            st.session_state.user_answer = str(user_ans).strip()
                            
                            kunci = str(soal["Kunci_Jawaban"]).strip()
                            
                            if ";" in kunci:
                                kunci_sorted = sorted([item.strip().lower() for item in kunci.split(";") if item.strip()])
                            elif "(" in kunci and ")" in kunci:
                                kunci_sorted = sorted([match.group(0).strip().lower() for match in re.finditer(r'\([^)]+\)', kunci)])
                            else:
                                kunci_sorted = sorted([item.strip().lower() for item in kunci.split(",") if item.strip()])

                            user_ans_sorted = sorted([item.strip().lower() for item in st.session_state.user_answer.split(";") if item.strip()])
                            
                            if user_ans_sorted == kunci_sorted:
                                st.session_state.is_correct = True
                                st.session_state.correct_per_level[soal["Level"]] += 1
                                status_txt = "BENAR"
                                skor_val = 10
                            else:
                                st.session_state.is_correct = False
                                status_txt = "SALAH"
                                skor_val = 0
                                
                            st.session_state.history.append({
                                "no": st.session_state.total_soal_dikerjakan + 1,
                                "id_soal": soal["ID_Soal"],
                                "level": soal["Level"],
                                "jawaban": st.session_state.user_answer,
                                "status": status_txt,
                                "durasi": durasi_soal
                            })

                            send_log_to_sheets(
                                nama=st.session_state.nama,
                                kelas=st.session_state.kelas,
                                id_soal=int(soal["ID_Soal"]),
                                jawaban=st.session_state.user_answer,
                                status=status_txt,
                                skor=skor_val,
                                durasi_detik=durasi_soal
                            )
                            st.rerun()

            if st.session_state.submitted:
                if st.session_state.is_correct:
                    st.success("✅ **Jawaban Anda BENAR!**")
                else:
                    st.error("❌ **Jawaban Anda BELUM TEPAT.**")
                    scaf = soal.get("Petunjuk_Scaffolding", "")
                    if pd.notna(scaf) and str(scaf).strip() != "":
                        st.info(f"💡 **Petunjuk Scaffolding:**\n\n{scaf}")
                
                with col_next:
                    if st.button("Soal Selanjutnya ➡️"):
                        next_question_action()
                        st.rerun()

# ==========================================
# HALAMAN DASHBOARD GURU
# ==========================================
else:
    st.title("👨‍🏫 Dashboard Guru & Rekapitulasi Real-Time")
    
    tab1, tab2 = st.tabs(["📊 Pemantauan Siswa & Log Aktivitas", "📚 Data Bank Soal"])
    
    with tab1:
        st.subheader("📈 Aktivitas & Tren Proses Menjawab Siswa")
        df_log = load_log_ujian()
        
        if df_log.empty:
            st.info("Log pengerjaan siswa terisi secara otomatis melalui sistem Google Sheets saat siswa menyelesaikan soal.")
            # Contoh Visualisasi Tampilan
            st.markdown("**Statistik Ringkas Pengerjaan Kuis**")
            c_g1, c_g2, c_g3 = st.columns(3)
            c_g1.metric("Total Responden", "0 Siswa")
            c_g2.metric("Rata-Rata Ketepatan", "0%")
            c_g3.metric("Rata-Rata Durasi / Soal", "0 Detik")
        else:
            st.dataframe(df_log, use_container_width=True)

    with tab2:
        st.subheader("📊 Data Bank Soal Aktif")
        if not df_soal.empty:
            st.dataframe(df_soal[["ID_Soal", "Level", "Subtopik", "Tipe_Soal", "Teks_Soal", "Petunjuk_Scaffolding"]], use_container_width=True)
