import streamlit as st
import pandas as pd
import requests
import json
import re
import time
from io import BytesIO

# Library untuk Export PDF
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# ==========================================
# KONFIGURASI DAN DATA
# ==========================================
st.set_page_config(page_title="Kuis Adaptif Matematika", layout="wide")

WEB_APP_URL = "https://script.google.com/macros/s/AKfycbzsDuCf2XmyxNsg3lflVUMig_7OBdeJtXXRKUiLxRb6toL11cRyb4IwWnhosE5NrE8C/exec"
EXCEL_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQxH0HVZkDQamsnLf9XJeARLNHqxtlNDKBSu65Yor3D0-ll0RE9GsWEjQkYRpXAZDALFtqFgrCzzMIb/pub?gid=0&single=true&output=csv"

@st.cache_data(ttl=30)
def load_bank_soal():
    try:
        df = pd.read_csv(EXCEL_URL)
        return df
    except Exception as e:
        st.error(f"Gagal memuat bank soal: {e}")
        return pd.DataFrame()

def load_log_ujian_remote():
    """Membaca log pengerjaan siswa langsung dari Google Apps Script"""
    if not WEB_APP_URL.strip():
        return pd.DataFrame()
    try:
        res = requests.get(WEB_APP_URL + "?action=read_log", timeout=5)
        if res.status_code == 200:
            data = res.json()
            return pd.DataFrame(data)
    except:
        pass
    return pd.DataFrame()

df_soal = load_bank_soal()

def send_log_to_sheets(nama, kelas, sekolah, id_soal, no_soal, jawaban, status, skor, durasi_detik):
    if not WEB_APP_URL.strip():
        return
    payload = {
        "nama": nama,
        "kelas": kelas,
        "sekolah": sekolah,
        "id_soal": id_soal,
        "no_soal": no_soal,
        "jawaban": jawaban,
        "status": status,
        "skor": skor,
        "durasi": durasi_detik
    }
    try:
        requests.post(WEB_APP_URL, data=json.dumps(payload), headers={"Content-Type": "application/json"})
    except Exception as e:
        st.warning(f"Gagal menyinkronkan log ke Google Sheets: {e}")

# ==========================================
# FUNGSI GENERATE PDF
# ==========================================
def generate_pdf_rapor(nama, kelas, sekolah, total_skor, total_soal, level_tertinggi, avg_time, narasi, saran, df_hist):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=16, alignment=1, spaceAfter=15)
    story.append(Paragraph("<b>RAPOR HASIL EVALUASI KUIS ADAPTIF MATEMATIKA</b>", title_style))
    story.append(Spacer(1, 10))
    
    info_text = f"<b>Nama Siswa:</b> {nama}<br/><b>Kelas:</b> {kelas}<br/><b>Asal Sekolah:</b> {sekolah}"
    story.append(Paragraph(info_text, styles['Normal']))
    story.append(Spacer(1, 15))
    
    data_summary = [
        ["Total Skor", "Soal Terjawab", "Level Tertinggi", "Rata-Rata Durasi/Soal"],
        [f"{total_skor} / 100", f"{total_soal} / 10", f"Level {level_tertinggi}", f"{int(avg_time)} Detik"]
    ]
    t_summary = Table(data_summary, colWidths=[120, 120, 120, 130])
    t_summary.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4A90E2")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_summary)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("<b>Narasi & Analysis Pencapaian:</b>", styles['Heading2']))
    story.append(Paragraph(narasi, styles['Normal']))
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>Saran Pembelajaran:</b> {saran}", styles['Normal']))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("<b>Detail Log Pengerjaan Soal:</b>", styles['Heading2']))
    
    table_data = [["No", "ID Soal", "Level", "Jawaban", "Status", "Durasi (Detik)"]]
    for idx, row in df_hist.iterrows():
        table_data.append([
            str(row.get('no', idx+1)),
            str(row.get('id_soal', '-')),
            str(row.get('level', '-')),
            str(row.get('jawaban', '-')),
            str(row.get('status', '-')),
            str(row.get('durasi', '-'))
        ])
    
    t_hist = Table(table_data, colWidths=[30, 60, 50, 180, 80, 90])
    t_hist.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#333333")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 8),
    ]))
    story.append(t_hist)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

# ==========================================
# INISIALISASI SESSION STATE
# ==========================================
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "nama" not in st.session_state:
    st.session_state.nama = ""
if "kelas" not in st.session_state:
    st.session_state.kelas = ""
if "sekolah" not in st.session_state:
    st.session_state.sekolah = ""
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
# FUNGSI NAVIGASI SOAL
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
# TAMPILAN AWAL (SELEKSI PERAN / LANDING PAGE)
# ==========================================
if st.session_state.user_role is None:
    st.title("🎓 Portal Kuis Adaptif Matematika")
    st.subheader("Selamat Datang! Silakan pilih peran Anda untuk masuk ke sistem:")
    
    col_sis, col_gur = st.columns(2)
    
    with col_sis:
        st.info("### 🧑‍🎓 Halaman Siswa")
        st.write("Akses pengerjaan kuis adaptif matematika, bimbingan otomatis, dan unduh rapor pencapaian.")
        if st.button("Masuk Sebagai Siswa 🚀", use_container_width=True, type="primary"):
            st.session_state.user_role = "Siswa"
            st.rerun()

    with col_gur:
        st.success("### 👨‍🏫 Dashboard Guru")
        st.write("Pantau aktivitas pengerjaan siswa secara real-time, analisis statistik, dan cetak rekap penilaian.")
        if st.button("Masuk Sebagai Guru 📊", use_container_width=True):
            st.session_state.user_role = "Guru"
            st.rerun()

else:
    # Navigation Bar Atas
    top_col1, top_col2 = st.columns([4, 1])
    with top_col1:
        st.caption(f"Peran Aktif: **{st.session_state.user_role}**")
    with top_col2:
        if st.button("🔄 Ganti Peran"):
            st.session_state.user_role = None
            st.rerun()

    st.markdown("---")

    # ==========================================
    # HALAMAN SISWA
    # ==========================================
    if st.session_state.user_role == "Siswa":
        st.title("📝 Lembar Kerja Siswa (Kuis Adaptif)")
        
        # Form Identitas Siswa Lengkap
        if not st.session_state.quiz_started:
            st.info("Silakan lengkapi identitas Anda di bawah ini sebelum memulai kuis (Durasi: 60 Menit / Maksimal 10 Soal).")
            col1, col2, col3 = st.columns(3)
            with col1:
                nama_in = st.text_input("Nama Lengkap:")
            with col2:
                kelas_in = st.text_input("Kelas:")
            with col3:
                sekolah_in = st.text_input("Asal Sekolah:")
                
            if st.button("🚀 Mulai Kuis", type="primary"):
                if nama_in.strip() != "" and kelas_in.strip() != "" and sekolah_in.strip() != "":
                    st.session_state.nama = nama_in
                    st.session_state.kelas = kelas_in
                    st.session_state.sekolah = sekolah_in
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
                    st.warning("Mohon lengkapi seluruh data identitas (Nama, Kelas, dan Asal Sekolah)!")

        # Kuis Berlangsung
        elif st.session_state.quiz_started:
            elapsed_total = time.time() - st.session_state.start_time
            remaining_total = max(0, 3600 - int(elapsed_total))
            
            # Penghentian Otomatis
            if remaining_total <= 0 or st.session_state.total_soal_dikerjakan >= 10:
                if remaining_total <= 0:
                    st.error("⏰ Waktu 60 menit telah habis! Kuis dihentikan.")
                
                st.balloons()
                st.header("📜 Rapor Hasil & Analysis Pencapaian Siswa")
                st.markdown(f"**Nama:** {st.session_state.nama} | **Kelas:** {st.session_state.kelas} | **Sekolah:** {st.session_state.sekolah}")
                
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
                
                if total_skor >= 80:
                    narasi = f"Selamat {st.session_state.nama}! Anda menunjukkan pemahaman matematika yang sangat baik dan mampu menyelesaikan soal-soal tingkat lanjut hingga Level {st.session_state.current_level}. Kecepatan pengerjaan Anda tergolong efektif dengan rata-rata {int(avg_time)} detik per soal."
                    saran = "Pertahankan performa ini! Anda siap menerima tantangan materi matematika pada tingkat yang lebih tinggi."
                elif total_skor >= 50:
                    narasi = f"Kerja bagus {st.session_state.nama}! Anda memiliki dasar pemahaman yang cukup baik, berhasil mencapai Level {st.session_state.current_level}. Beberapa soal memerlukan kecermatan lebih lanjut."
                    saran = "Pelajari kembali petunjuk bimbingan (scaffolding) pada soal-soal yang belum tepat agar konsep matematika Anda semakin solid."
                else:
                    narasi = f"Terus semangat {st.session_state.nama}! Anda telah berusaha menyelesaikan kuis adaptif ini hingga Level {st.session_state.current_level}. Terlihat ada beberapa konsep dasar yang masih memerlukan latihan secara berkala."
                    saran = "Disarankan untuk mereview kembali video petunjuk dan berdiskusi dengan guru terkait materi yang dirasa sulit."

                st.write(narasi)
                st.info(f"📌 **Saran Pembelajaran:** {saran}")
                
                st.markdown("---")
                st.subheader("⏱️ Detail Log Aktivitas & Ketepatan Pengerjaan")
                df_hist = pd.DataFrame(st.session_state.history)
                if not df_hist.empty:
                    st.dataframe(df_hist, use_container_width=True)
                
                # Opsi Export ke PDF
                if PDF_AVAILABLE:
                    pdf_bytes = generate_pdf_rapor(
                        st.session_state.nama, st.session_state.kelas, st.session_state.sekolah,
                        total_skor, total_soal, st.session_state.current_level, avg_time,
                        narasi, saran, df_hist
                    )
                    st.download_button(
                        label="📄 Download Rapor Hasil (PDF)",
                        data=pdf_bytes,
                        file_name=f"Rapor_{st.session_state.nama.replace(' ', '_')}.pdf",
                        mime="application/pdf",
                        type="primary"
                    )
                else:
                    st.warning("Library ReportLab belum terinstall untuk export PDF. Silakan install `reportlab`.")

                if st.button("🔄 Ulangi Kuis"):
                    st.session_state.quiz_started = False
                    st.rerun()

            else:
                soal = st.session_state.current_soal
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
                    st.write("Pilihlah semua jawaban yang menurut Anda benar:")
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
                    # Default index=None agar pilihan tidak tercentang otomatis
                    user_ans = st.radio("Pilih jawaban:", opsi, index=None, disabled=st.session_state.submitted, key="input_pg")
                    if user_ans is None:
                        user_ans = ""
                    
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
                                    
                                current_no = st.session_state.total_soal_dikerjakan + 1
                                st.session_state.history.append({
                                    "no": current_no,
                                    "id_soal": soal["ID_Soal"],
                                    "level": soal["Level"],
                                    "jawaban": st.session_state.user_answer,
                                    "status": status_txt,
                                    "durasi": durasi_soal
                                })

                                send_log_to_sheets(
                                    nama=st.session_state.nama,
                                    kelas=st.session_state.kelas,
                                    sekolah=st.session_state.sekolah,
                                    id_soal=int(soal["ID_Soal"]),
                                    no_soal=current_no,
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
        st.title("👨‍🏫 Dashboard Guru & Monitoring Real-Time")
        
        tab1, tab2 = st.tabs(["📊 Pemantauan Siswa (Real-Time)", "📚 Data Bank Soal"])
        
        with tab1:
            col_ref1, col_ref2 = st.columns([3, 1])
            with col_ref1:
                st.subheader("📈 Siswa Aktif & Log Pengerjaan")
            with col_ref2:
                if st.button("🔄 Refresh Data Real-Time"):
                    st.rerun()
            
            df_log = load_log_ujian_remote()
            
            if df_log.empty:
                st.info("Belum ada data masuk dari Google Sheets atau Web App URL belum terhubung sempurna.")
            else:
                st.dataframe(df_log, use_container_width=True)
                
                # Export PDF Rekap Guru
                if PDF_AVAILABLE:
                    csv_data = df_log.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Download Data Rekap (CSV)",
                        data=csv_data,
                        file_name="Rekap_Nilai_Siswa.csv",
                        mime="text/csv"
                    )

        with tab2:
            st.subheader("📊 Data Bank Soal Aktif")
            if not df_soal.empty:
                st.dataframe(df_soal[["ID_Soal", "Level", "Subtopik", "Tipe_Soal", "Teks_Soal", "Petunjuk_Scaffolding"]], use_container_width=True)
