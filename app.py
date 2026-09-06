import streamlit as st
import pandas as pd
import requests
import google.generativeai as genai

# ==========================================
# 1. KONFIGURASI APLIKASI & URL UTAMA
# ==========================================
st.set_page_config(
    page_title="Aplikasi Pembelajaran Adaptif & Dashboard Guru",
    page_icon="🎓",
    layout="wide"
)

# --- KONFIGURASI URL & API KEY ---
SPREADSHEET_ID = "1ItV1GzJ_xEREEl3tiTZkA6KY0ks6yk2yBuIe3mZwqUw"
SHEET_BANK_SOAL_URL = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/export?format=csv"

# Masukkan URL Google Apps Script & Gemini API Key Anda
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbw8UBXnO11hg8SBFjRAeTSUpENyg8Hjwi0jqQOfQ_sqNMh6JZ0LEvVPIn0tza1iy017/exec"  # Ganti dengan Web App URL Anda
DEFAULT_GEMINI_API_KEY = ""                                             # Ganti dengan Gemini API Key Anda jika ada

if DEFAULT_GEMINI_API_KEY:
    genai.configure(api_key=DEFAULT_GEMINI_API_KEY)

# ==========================================
# 2. HELPER FETCH DATA (AUTO CLEAR CACHE 5 DETIK)
# ==========================================
@st.cache_data(ttl=5)
def fetch_bank_soal():
    try:
        df = pd.read_csv(SHEET_BANK_SOAL_URL)
        df.columns = df.columns.str.strip() # Hapus spasi liar pada header
        
        # Penanganan fleksibel untuk penamaan kolom Tipe Soal
        tipe_col = None
        for col in df.columns:
            if col.lower().replace(" ", "_") in ["tipe_soal", "tipe", "tipesoal"]:
                tipe_col = col
                break
                
        if tipe_col:
            df['Tipe_Soal_Clean'] = df[tipe_col].fillna('ISIAN').astype(str).str.upper().str.strip()
        else:
            df['Tipe_Soal_Clean'] = 'ISIAN'

        # Penanganan fleksibel untuk Opsi Jawaban
        opsi_col = None
        for col in df.columns:
            if col.lower().replace(" ", "_") in ["opsi_jawaban", "opsi", "opsijawaban", "pilihan"]:
                opsi_col = col
                break

        if opsi_col:
            df['Opsi_Jawaban_Clean'] = df[opsi_col].fillna('-')
        else:
            df['Opsi_Jawaban_Clean'] = '-'
            
        return df
    except Exception as e:
        st.error(f"Gagal mengambil data Bank Soal: {e}")
        return pd.DataFrame()

# Helper untuk Mengirim Data Hasil Kerja Siswa ke Google Sheets via Web App
def kirim_nilai_ke_sheet(nama, kelas, id_soal, jawaban_user, status_jawaban, skor):
    if not WEB_APP_URL or "YOUR_SCRIPT_ID" in WEB_APP_URL:
        return False
    try:
        payload = {
            "nama": nama,
            "kelas": kelas,
            "id_soal": id_soal,
            "jawaban": jawaban_user,
            "status": status_jawaban,
            "skor": skor
        }
        response = requests.post(WEB_APP_URL, json=payload, timeout=5)
        return response.status_code == 200
    except Exception:
        return False

# ==========================================
# 3. INITIALIZE SESSION STATE & SIDEBAR NAVIGASI
# ==========================================
bank_soal = fetch_bank_soal()

if 'index_soal' not in st.session_state:
    st.session_state.index_soal = 0
if 'nama_siswa' not in st.session_state:
    st.session_state.nama_siswa = ""
if 'kelas_siswa' not in st.session_state:
    st.session_state.kelas_siswa = ""

with st.sidebar:
    st.title("📌 Navigasi Utama")
    role = st.radio("Pilih Peran Halaman:", ["👨‍🎓 Halaman Siswa (Kuis)", "👨‍🏫 Dashboard Guru (Penilaian)"])
    st.divider()
    
    st.subheader("⚙️ Pengaturan Cache")
    if st.button("🗑️ Clear Cache Manual"):
        st.cache_data.clear()
        st.success("Cache berhasil dibersihkan!")
        st.rerun()

# ==========================================
# 4. HALAMAN SISWA (KUIS & LATIHAN)
# ==========================================
if role == "👨‍🎓 Halaman Siswa (Kuis)":
    st.title("📝 Lembar Kerja Siswa")
    
    # Form Identitas Siswa
    col_a, col_b = st.columns(2)
    with col_a:
        st.session_state.nama_siswa = st.text_input("Masukkan Nama Lengkap:", value=st.session_state.nama_siswa)
    with col_b:
        st.session_state.kelas_siswa = st.text_input("Masukkan Kelas:", value=st.session_state.kelas_siswa)
        
    st.divider()

    if bank_soal.empty:
        st.warning("Data soal tidak ditemukan atau gagal dimuat.")
        st.stop()

    soal = bank_soal.iloc[st.session_state.index_soal]
    id_soal = soal.get('ID_Soal', st.session_state.index_soal + 1)
    tipe_soal = str(soal['Tipe_Soal_Clean'])
    
    st.subheader(f"Soal No. {st.session_state.index_soal + 1} dari {len(bank_soal)}")
    st.caption(f"ID Soal: **{id_soal}** | Level: **{soal.get('Level', '-')}** | Tipe Soal: **{tipe_soal}**")
    
    # Display Teks Soal
    st.markdown(f"### {soal.get('Teks_Soal', '')}")
    
    # Display Hint Video jika ada
    hint_video = soal.get('Hint_Video', '-')
    if pd.notna(hint_video) and str(hint_video).startswith('http'):
        with st.expander("🎬 Lihat Video Petunjuk"):
            st.video(str(hint_video))
            
    jawaban_user = None

    # --- RENDERING UI BERDASARKAN TIPE SOAL ---
    if tipe_soal == 'PG':
        opsi = [o.strip() for o in str(soal['Opsi_Jawaban_Clean']).split(',')]
        jawaban_user = st.radio("Pilih salah satu jawaban:", options=opsi, key=f"pg_{id_soal}")

    elif tipe_soal == 'PGK':
        opsi = [o.strip() for o in str(soal['Opsi_Jawaban_Clean']).split(',')]
        st.write("📌 *Pilih semua jawaban yang menurut Anda benar:*")
        pilihan = []
        for idx, o in enumerate(opsi):
            if st.checkbox(o, key=f"pgk_{id_soal}_{idx}"):
                pilihan.append(o)
        jawaban_user = ", ".join(pilihan) if pilihan else None

    elif tipe_soal == 'MENJODOHKAN':
        opsi = [o.strip() for o in str(soal['Opsi_Jawaban_Clean']).split(',')]
        jawaban_user = st.selectbox("Pilih pasangan jawaban yang tepat:", options=["-- Pilih Pasangan --"] + opsi, key=f"jodoh_{id_soal}")
        if jawaban_user == "-- Pilih Pasangan --":
            jawaban_user = None

    elif tipe_soal == 'BS':
        jawaban_user = st.radio("Tentukan kebenaran pernyataan:", options=["BENAR", "SALAH"], key=f"bs_{id_soal}")

    else: # ISIAN / DEFAULT
        jawaban_user = st.text_input("Ketikkan jawaban Anda:", key=f"isian_{id_soal}")

    # --- SUBMIT & SKORING ---
    st.divider()
    c1, c2 = st.columns([1, 1])

    with c1:
        if st.button("Submit Jawaban", type="primary"):
            if not st.session_state.nama_siswa:
                st.warning("⚠️ Harap isi Nama Anda di bagian atas sebelum menjawab!")
            elif not jawaban_user:
                st.warning("⚠️ Harap isi/pilih jawaban Anda terlebih dahulu!")
            else:
                kunci = str(soal.get('Kunci_Jawaban', '')).strip()
                ans_str = str(jawaban_user).strip()
                
                is_correct = (ans_str.lower() == kunci.lower())
                skor = 100 if is_correct else 0
                status = "BENAR" if is_correct else "SALAH"

                # Kirim ke Web App
                terkirim = kirim_nilai_ke_sheet(
                    st.session_state.nama_siswa,
                    st.session_state.kelas_siswa,
                    id_soal,
                    ans_str,
                    status,
                    skor
                )
                
                if is_correct:
                    st.success("🎉 Jawaban Anda BENAR!")
                else:
                    st.error("❌ Jawaban Anda belum tepat.")
                    petunjuk = soal.get('Petunjuk_Scaffolding_AI', '-')
                    if pd.notna(petunjuk) and petunjuk != '-':
                        st.info(f"💡 **Petunjuk:** {petunjuk}")

                    if DEFAULT_GEMINI_API_KEY:
                        with st.spinner("🤖 AI Tutor sedang menyiapkan saran belajar..."):
                            try:
                                model = genai.GenerativeModel('gemini-1.5-flash')
                                prompt = f"Siswa salah menjawab soal matematika: '{soal.get('Teks_Soal','')}'. Jawaban siswa: '{ans_str}'. Berikan bimbingan ringkas (scaffolding) tanpa membocorkan kunci jawaban secara langsung."
                                res = model.generate_content(prompt)
                                st.markdown(f"**🤖 Bimbingan AI:**\n{res.text}")
                            except Exception as e:
                                pass

    with c2:
        if st.button("Soal Selanjutnya ➡️"):
            if st.session_state.index_soal < len(bank_soal) - 1:
                st.session_state.index_soal += 1
                st.rerun()
            else:
                st.balloons()
                st.success("Selesai! Anda telah mengerjakan seluruh soal.")

# ==========================================
# 5. HALAMAN DASHBOARD GURU (PENILAIAN)
# ==========================================
else:
    st.title("👨‍🏫 Dashboard Penilaian Guru")
    st.caption("Pantau kemajuan pengerjaan siswa dan rekapitulasi skor secara real-time.")
    
    st.info(f"Status Koneksi Web App Apps Script: **{'Terhubung' if WEB_APP_URL and 'YOUR_SCRIPT_ID' not in WEB_APP_URL else 'Belum Dikonfigurasi'}**")

    # Ambil Rekap Data Siswa via Web App Apps Script (Jika Tersedia)
    if st.button("🔄 Refresh Data Hasil Siswa"):
        st.rerun()

    if WEB_APP_URL and "YOUR_SCRIPT_ID" not in WEB_APP_URL:
        try:
            res = requests.get(WEB_APP_URL, timeout=5)
            if res.status_code == 200:
                data_siswa = res.json()
                df_rekap = pd.DataFrame(data_siswa)
                
                st.subheader("📊 Tabel Rekapitulasi Nilai Siswa")
                st.dataframe(df_rekap, use_container_width=True)
                
                # Ringkasan Statistik
                if not df_rekap.empty and 'skor' in df_rekap.columns:
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Total Jawaban Masuk", len(df_rekap))
                    m2.metric("Rata-Rata Skor", f"{df_rekap['skor'].astype(float).mean():.1f}")
                    m3.metric("Siswa Unik", df_rekap['nama'].nunique() if 'nama' in df_rekap.columns else 0)
            else:
                st.warning("Gagal mengambil data dari Google Apps Script.")
        except Exception as e:
            st.error(f"Error memuat data penilaian: {e}")
    else:
        st.warning("Silakan masukkan URL Google Apps Script (`WEB_APP_URL`) Anda pada bagian atas kode untuk menampilkan hasil kerja siswa secara otomatis.")
