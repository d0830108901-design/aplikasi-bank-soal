import streamlit as st
import pandas as pd
import requests
import json
import random

# ==========================================
# KONFIGURASI DAN DATA
# ==========================================
st.set_page_config(page_title="Kuis Adaptif Matematika", layout="wide")

# Web App URL Google Apps Script Anda untuk menyimpan log jawaban ke Log_Ujian
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbw8UBXnO11hg8SBFjRAeTSUpENyg8Hjwi0jqQOfQ_sqNMh6JZ0LEvVPIn0tza1iy017/exec"

# URL Publikasi CSV Google Sheets Bank Soal Anda
EXCEL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQxH0HVZkDQamsnLf9XJeARLNHqxtlNDKBSu65Yor3D0-ll0RE9GsWEjQkYRpXAZDALFtqFgrCzzMIb/pub?gid=0&single=true&output=csv"

@st.cache_data(ttl=60)
def load_bank_soal():
    try:
        df = pd.read_csv(EXCEL_URL)
        return df
    except Exception as e:
        st.error(f"Gagal memuat bank soal: {e}")
        return pd.DataFrame()

df_soal = load_bank_soal()

# Fungsi untuk Mengirim Data Hasil Soal ke Google Sheets via Apps Script
def send_log_to_sheets(nama, kelas, id_soal, jawaban, status, skor):
    if not WEB_APP_URL.strip():
        return
    payload = {
        "nama": nama,
        "kelas": kelas,
        "id_soal": id_soal,
        "jawaban": jawaban,
        "status": status,
        "skor": skor
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
    
    # Cek level: Jika level aktif sudah memiliki 2 jawaban benar, naik level
    lvl = st.session_state.current_level
    while st.session_state.correct_per_level.get(lvl, 0) >= 2 and lvl < 4:
        lvl += 1
        st.session_state.current_level = lvl
        
    # Filter soal di level aktif yang belum pernah dikerjakan
    available_soal = df_soal[
        (df_soal["Level"] == st.session_state.current_level) & 
        (~df_soal["ID_Soal"].isin(st.session_state.used_soal_ids))
    ]
    
    # Jika soal di level aktif habis, ambil dari level acak lain yang belum dikerjakan
    if available_soal.empty:
        available_soal = df_soal[~df_soal["ID_Soal"].isin(st.session_state.used_soal_ids)]
        
    if available_soal.empty:
        return None
        
    # Acak dan pilih 1 soal secara random
    selected = available_soal.sample(n=1).iloc[0]
    return selected

def next_question_action():
    st.session_state.total_soal_dikerjakan += 1
    st.session_state.submitted = False
    st.session_state.user_answer = ""
    st.session_state.is_correct = False
    
    if st.session_state.total_soal_dikerjakan < 10:
        st.session_state.current_soal = get_next_soal()
        if st.session_state.current_soal is not None:
            st.session_state.used_soal_ids.append(st.session_state.current_soal["ID_Soal"])

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
        st.info("Silakan isi nama dan kelas terlebih dahulu untuk memulai kuis (Maksimal 10 Soal).")
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
                st.session_state.total_soal_dikerjakan = 0
                st.session_state.current_level = 1
                st.session_state.correct_per_level = {1: 0, 2: 0, 3: 0, 4: 0}
                st.session_state.used_soal_ids = []
                st.session_state.history = []
                
                # Pilih soal pertama
                soal_pertama = get_next_soal()
                if soal_pertama is not None:
                    st.session_state.current_soal = soal_pertama
                    st.session_state.used_soal_ids.append(soal_pertama["ID_Soal"])
                st.rerun()
            else:
                st.warning("Mohon isi Nama dan Kelas terlebih dahulu!")

    # Jika Kuis Berlangsung
    elif st.session_state.quiz_started and st.session_state.total_soal_dikerjakan < 10:
        soal = st.session_state.current_soal
        
        if soal is None:
            st.success("🎉 Soal dalam bank soal telah habis!")
            st.session_state.total_soal_dikerjakan = 10
            st.rerun()
        else:
            # Header Informasi
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Soal No:** {st.session_state.total_soal_dikerjakan + 1} / 10")
            c2.markdown(f"**Level Saat Ini:** {soal['Level']}")
            c3.markdown(f"**Tipe Soal:** {soal['Tipe_Soal']}")
            st.progress((st.session_state.total_soal_dikerjakan) / 10)
            
            st.markdown("---")
            st.subheader(soal["Teks_Soal"])
            
            # Validasi & Tampilan Video Hint
            hint_video_url = str(soal.get("Hint_Video", "")).strip() if pd.notna(soal.get("Hint_Video")) else ""
            if hint_video_url.startswith("http://") or hint_video_url.startswith("https://"):
                with st.expander("🎬 Lihat Video Petunjuk"):
                    st.video(hint_video_url)

            # Input Jawaban Siswa
            user_ans = ""
            tipe = str(soal["Tipe_Soal"]).upper()
            
            if tipe == "ISIAN":
                user_ans = st.text_input("Ketikkan jawaban Anda:", disabled=st.session_state.submitted, key="input_isian")
            elif tipe in ["PG", "PILIHAN GANDA"]:
                opsi = str(soal["Opsi_Jawaban"]).split(";") if pd.notna(soal.get("Opsi_Jawaban")) else []
                user_ans = st.radio("Pilih jawaban:", opsi, disabled=st.session_state.submitted, key="input_pg")
            else:
                user_ans = st.text_input("Ketikkan jawaban Anda:", disabled=st.session_state.submitted, key="input_def")
                
            st.markdown("---")
            
            # Tombol Submit & Next
            col_sub, col_next = st.columns([1, 1])
            
            with col_sub:
                if not st.session_state.submitted:
                    if st.button(" Submit Jawaban", type="primary"):
                        if str(user_ans).strip() == "":
                            st.warning("Isi jawaban terlebih dahulu!")
                        else:
                            st.session_state.submitted = True
                            st.session_state.user_answer = str(user_ans).strip()
                            
                            # Evaluasi Jawaban
                            kunci = str(soal["Kunci_Jawaban"]).strip()
                            if st.session_state.user_answer.lower() == kunci.lower():
                                st.session_state.is_correct = True
                                st.session_state.correct_per_level[soal["Level"]] += 1
                                status_txt = "BENAR"
                                skor_val = 10
                            else:
                                st.session_state.is_correct = False
                                status_txt = "SALAH"
                                skor_val = 0
                                
                            # Simpan ke histori lokal
                            st.session_state.history.append({
                                "no": st.session_state.total_soal_dikerjakan + 1,
                                "id_soal": soal["ID_Soal"],
                                "level": soal["Level"],
                                "jawaban": st.session_state.user_answer,
                                "status": status_txt
                            })

                            # Kirim Log otomatis ke Google Sheets
                            send_log_to_sheets(
                                nama=st.session_state.nama,
                                kelas=st.session_state.kelas,
                                id_soal=int(soal["ID_Soal"]),
                                jawaban=st.session_state.user_answer,
                                status=status_txt,
                                skor=skor_val
                            )
                            st.rerun()

            # Tampilan Hasil Evaluasi & Petunjuk Scaffolding
            if st.session_state.submitted:
                if st.session_state.is_correct:
                    st.success("✅ **Jawaban Anda BENAR!** Kinerja yang sangat baik.")
                else:
                    st.error("❌ **Jawaban Anda BELUM TEPAT.**")
                    
                    # Menampilkan Petunjuk Scaffolding
                    scaf = soal.get("Petunjuk_Scaffolding", "")
                    if pd.notna(scaf) and str(scaf).strip() != "":
                        st.info(f"💡 **Petunjuk Scaffolding (Bimbingan):**\n\n{scaf}")
                
                with col_next:
                    if st.button("Soal Selanjutnya ➡️"):
                        next_question_action()
                        st.rerun()

    # Rangkuman Setelah 10 Soal Selesai
    else:
        st.balloons()
        st.header("🏆 Kuis Selesai!")
        st.write(f"Terima kasih **{st.session_state.nama}** (Kelas {st.session_state.kelas}). Anda telah menyelesaikan 10 soal.")
        
        total_benar = sum([1 for h in st.session_state.history if h["status"] == "BENAR"])
        st.metric("Total Skor (Benar)", f"{total_benar * 10} / 100")
        st.metric("Level Terakhir Dicapai", f"Level {st.session_state.current_level}")
        
        st.subheader("📋 Ringkasan Hasil Pengerjaan:")
        df_hist = pd.DataFrame(st.session_state.history)
        st.dataframe(df_hist, use_container_width=True)
        
        if st.button("🔄 Ulangi Kuis"):
            st.session_state.quiz_started = False
            st.rerun()

# ==========================================
# HALAMAN GURU
# ==========================================
else:
    st.title("👨‍🏫 Dashboard Guru & Rekapitulasi")
    st.write("Pantau hasil capaian kuis siswa secara real-time.")
    if not df_soal.empty:
        st.subheader("📊 Data Bank Soal Aktif")
        st.dataframe(df_soal[["ID_Soal", "Level", "Subtopik", "Tipe_Soal", "Teks_Soal", "Petunjuk_Scaffolding"]], use_container_width=True)
