# SISTEM MONITORING KUALITAS DAN PENGAMBILAN KEPUTUSAN UNTUK DETEKSI DINI DAN KONTROL DISTRIBUSI AIR TOREN PADA KEBUTUHAN RUMAH TANGGA NON-KONSUMSI

**DOKUMEN C-251**  
**DOKUMENTASI CAPSTONE PROJECT**  
DEPARTEMEN TEKNIK ELEKTRO DAN TEKNOLOGI INFORMASI  
FAKULTAS TEKNIK  
UNIVERSITAS GADJAH MADA  
2026

---

## HALAMAN PENGESAHAN

1. **USULAN JUDUL**: Sistem Monitoring Kualitas dan Pengambilan Keputusan untuk Deteksi Dini dan Kontrol Distribusi Air Toren pada Kebutuhan Rumah Tangga Non-Konsumsi  
   *(Quality Monitoring and Decision-Making System for Early Detection and Control of Water Distribution from Water Towers for Non-Consumption Household Use)*
2. **JENIS DOKUMEN**: PERANCANGAN PRODUK DAN SPESIFIKASI
3. **KODE DOKUMEN**: C-251
4. **NOMOR DOKUMEN**: C-251-E_08
5. **NOMOR REVISI**: 0
6. **TANGGAL PENERBITAN**: 2 Juni 2026
7. **KETUA KELOMPOK**:
   - Nama Lengkap: Muhammad Rizqi Aminuddin
   - NIM: 23/519851/TK/57278
   - Prodi: Teknik Biomedis
   - Email: `muhammadrizqiaminuddin@mail.ugm.ac.id`
8. **ANGGOTA 1**:
   - Nama Lengkap: Shofiy Alia Rimala
   - NIM: 23/517426/TK/56915
   - Prodi: Teknik Elektro
   - Email: `shofiyaliarimala@mail.ugm.ac.id`
9. **ANGGOTA 2**:
   - Nama Lengkap: Azfanova Sammy Rafif Saputra
   - NIM: 23/521764/TK/57572
   - Prodi: Teknologi Informasi
   - Email: `azfanovasammyrafifsaputra@mail.ugm.ac.id`
10. **ANGGOTA 3**:
    - Nama Lengkap: Dzulfikar Rizqi Ramadhani
    - NIM: 23/522193/TK/57616
    - Prodi: Teknologi Informasi
    - Email: `dzulfikarrizqiramadhani522193@mail.ugm.ac.id`
12. **DOSEN PEMBIMBING**:
    - Nama Lengkap: Dr. Ir. Guntur Dharma Putra, S.T., M.Sc.
    - NIP: 111 1991 04 2018 02 102
13. **TEMPAT PELAKSANAAN**: Departemen Teknik Elektro dan Teknologi Informasi Fakultas Teknik
14. **JUMLAH HALAMAN**: 82

---

## BUKTI BEBAS PLAGIASI

*(Halaman iii - Terlampir dalam dokumen asli)*

---

## CATATAN REVISI DOKUMEN

| VERSI | TANGGAL | PERBAIKAN |
| :--- | :--- | :--- |
| V.0 | 20/04/2023 | Pembuatan template laporan Capstone Project dalam format LaTeX.<br>• Format dibuat berdasarkan format dokumen DOC yang telah disiapkan sebelumnya.<br>• Contoh pengisian template ini juga diberikan pada dokumen ini. |

---

## INTISARI

Ketersediaan air bersih untuk kebutuhan rumah tangga non-konsumsi sering terganggu akibat penurunan kualitas air toren yang tidak terpantau. Permasalahan ini bersifat kompleks karena penurunan kualitas dapat berasal dari dua sumber berbeda – inlet (tiba-tiba) atau akumulasi kontaminan dalam toren (gradual) yang masing-masing memerlukan respons sistem yang berbeda.

Kompleksitas bertambah karena setiap titik penggunaan air memiliki standar kualitas yang berbeda, sehingga keputusan kontrol distribusi harus bersifat bertingkat dan adaptif, bukan sekadar biner. Permasalahan ini melibatkan integrasi multidisiplin antara kimia sensor, pengolahan sinyal digital, sistem kendali, dan teknologi IoT, sehingga memenuhi kriteria *Complex Engineering Problem* sesuai standar IABEE.

Sistem yang dirancang mengintegrasikan lima sensor bermodul (pH, turbidity, TDS, suhu, *water level*) yang terhubung langsung ke mikrokontroler ESP32. Di dalam ESP32, data hasil konversi ADC difilter menggunakan software FIR moving average filter, lalu dianalisis oleh modul deteksi pola berbasis *rate of change* dan regresi linier, kemudian dinilai menggunakan algoritme *weighted scoring* multi-parameter untuk menghasilkan skor kualitas 0–100. Berdasarkan skor tersebut, sistem mengontrol empat solenoid valve secara independen melalui relay module untuk mendistribusikan air secara bertingkat ke kamar mandi, dapur, cucian, dan taman. Sistem juga dilengkapi override manual per valve via aplikasi HP yang berfungsi sebagai *feedback loop* evaluasi threshold secara adaptif.

---

## DAFTAR ISI

- **HALAMAN PENGESAHAN** (ii)
- **BUKTI BEBAS PLAGIASI** (iii)
- **DAFTAR ISI** (iv)
- **DAFTAR GAMBAR** (ix)
- **DAFTAR TABEL** (x)
- **CATATAN REVISI DOKUMEN** (xi)
- **INTISARI** (xii)
- **BAB 1 PENGANTAR** (1)
  - 1.1 Latar Belakang (1)
  - 1.2 Penjabaran Masalah Umum Menjadi Masalah Teknis (2)
  - 1.3 Kendala-Kendala yang Perlu Dipertimbangkan (3)
  - 1.4 Mata Kuliah dan Kemampuan yang Mendukung (5)
  - 1.5 Usulan Solusi Potensial (8)
- **BAB 2 DASAR TEORI PENDUKUNG** (11)
  - 2.1 Sensor (11)
    - 2.1.1 Sensor pH (11)
    - 2.1.2 Sensor TDS (11)
    - 2.1.3 Sensor Turbidity (11)
    - 2.1.4 Sensor Suhu (11)
    - 2.1.5 Sensor Ketinggian Air (12)
  - 2.2 Mikrokontroler (12)
    - 2.2.1 ESP32 (12)
  - 2.3 MicroSD (13)
  - 2.4 Filter Digital (13)
    - 2.4.1 FIR (13)
  - 2.5 Basis Data (13)
    - 2.5.1 Sistem Manajemen Basis Data (14)
    - 2.5.2 Basis Data Relasional (14)
    - 2.5.3 Basis Data Non Relasional (14)
    - 2.5.4 Basis Data Deret Waktu (14)
  - 2.6 Perangkat Lunak (15)
    - 2.6.1 Front-End (15)
    - 2.6.2 Back-End (15)
    - 2.6.3 RESTful API (15)
    - 2.6.4 WebSocket (16)
    - 2.6.5 Protokol MQTT (16)
    - 2.6.6 Progressive Web App (16)
  - 2.7 Machine Learning (16)
    - 2.7.1 Forecasting Models (17)
  - 2.8 Metrik Kinerja (17)
    - 2.8.1 Akurasi (18)
    - 2.8.2 Presisi (18)
    - 2.8.3 Sensitivitas/Recall (19)
    - 2.8.4 F1-Score (19)
- **BAB 3 ANALISIS STUDI PUSTAKA KUNCI** (20)
  - 3.1 Pemantauan Kondisi Air Toren Berdasarkan Sensor (20)
    - 3.1.1 Sensor pH (20)
    - 3.1.2 Sensor TDS (20)
    - 3.1.3 Sensor Turbidity (21)
    - 3.1.4 Sensor Suhu (22)
    - 3.1.5 Sensor Ketinggian Air (23)
  - 3.2 Analisis Jenis Machine Learning (24)
    - 3.2.1 Analisis Pendekatan Supervised Learning (24)
    - 3.2.2 Analisis Pendekatan Unsupervised Learning (25)
  - 3.3 Analisis Algoritma (25)
    - 3.3.1 Analisis Algoritma GRU (25)
    - 3.3.2 Analisis Algoritma XGBoost (26)
  - 3.4 Metode Deteksi Anomali pada Data Sensor (26)
    - 3.4.1 Deteksi Anomali Berbasis Threshold Statis (26)
    - 3.4.2 Deteksi Anomali Berbasis Statistik Adaptif (27)
    - 3.4.3 Deteksi Anomali Berbasis Machine Learning (27)
    - 3.4.4 Perbandingan Metode Deteksi Anomali (28)
  - 3.5 Metode Pengambilan Keputusan untuk Kontrol Distribusi Air (28)
    - 3.5.1 Rule-Based System (28)
    - 3.5.2 Kendali Logika Fuzzy (29)
    - 3.5.3 Weighted Scoring (29)
    - 3.5.4 Perbandingan Metode Pengambilan Keputusan (29)
  - 3.6 Penggunaan Aplikasi Web sebagai Dashboard pada Sistem Monitoring Berbasis Embedded System (30)
    - 3.6.1 Aplikasi Mobile Native (30)
    - 3.6.2 Aplikasi Web Konvensional (31)
    - 3.6.3 Progressive Web App (PWA) (31)
    - 3.6.4 Perbandingan Platform Antarmuka Pengguna (32)
- **BAB 4 PEMODELAN PERMASALAHAN** (33)
  - 4.1 Pemodelan Akuisisi dan Kalibrasi Sensor (33)
    - 4.1.1 Model Kalibrasi Sensor secara Umum (33)
    - 4.1.2 Pemodelan Sensor Ketinggian Air (33)
    - 4.1.3 Pemodelan Sensor Turbidity (34)
    - 4.1.4 Pemodelan Sensor pH (34)
    - 4.1.5 Pemodelan Sensor TDS (35)
    - 4.1.6 Pemodelan Sensor Suhu (35)
  - 4.2 Pemodelan Filter Digital untuk Reduksi Noise Sensor (35)
    - 4.2.1 Moving Average Filter (36)
    - 4.2.2 Exponentially Weighted Moving Average (EWMA) (36)
  - 4.3 Pemodelan Weighted Scoring untuk Indeks Kualitas Air (36)
    - 4.3.1 Normalisasi Parameter (37)
    - 4.3.2 Perhitungan Skor Komposit (37)
    - 4.3.3 Penetapan Bobot Parameter (38)
    - 4.3.4 Penetapan Ambang Skor per Titik Penggunaan (38)
  - 4.4 Pemodelan Deteksi Anomali Tiba-Tiba (39)
    - 4.4.1 Model Rate of Change (39)
    - 4.4.2 Model Deteksi Berbasis Z-Score Adaptif (40)
  - 4.5 Model Metrik Evaluasi Kinerja Sistem (41)
    - 4.5.1 Metrik Akurasi Sensor (41)
    - 4.5.2 Metrik Evaluasi Deteksi Anomali (41)
    - 4.5.3 Metrik Akurasi Prediksi Waktu Pengurasan (42)
    - 4.5.4 Metrik Efektivitas Kontrol Distribusi (42)
- **BAB 5 PEMILIHAN DAN PENGEMBANGAN METODE** (43)
  - 5.1 Pemilihan Metode Deteksi Anomali (43)
    - 5.1.1 Pengembangan Metode: Deteksi Hibrid (44)
  - 5.2 Pemilihan Jenis Filter LPF (44)
  - 5.3 Pemilihan Metode Pengambilan Keputusan Distribusi Air (45)
  - 5.4 Pemilihan Arsitektur Antarmuka Pengguna (46)
  - 5.5 Pemilihan Protokol Komunikasi (46)
  - 5.6 Pemilihan Sistem Basis Data (47)
  - 5.7 Arsitektur Perangkat Lunak Terpadu (48)
    - 5.7.1 Lapisan Edge Processing pada ESP32 (48)
    - 5.7.2 Lapisan Back-end (48)
    - 5.7.3 Lapisan Front-end PWA (49)
  - 5.8 Ringkasan Pilihan Metode (50)
- **BAB 6 LUARAN DAN SPESIFIKASI YANG DIUSULKAN** (51)
  - 6.1 Luaran yang Dijanjikan (51)
  - 6.2 Spesifikasi Luaran (52)
- **BAB 7 BATASAN PERMASALAHAN** (55)
  - 7.1 Limitasi Dataset (55)
  - 7.2 Toleransi Ketelitian Sensor yang Digunakan (55)
  - 7.3 Limitasi Dana (57)
- **BAB 8 PERANCANGAN UMUM SISTEM** (58)
  - 8.1 Arsitektur Umum Sistem (58)
  - 8.2 Ilustrasi Miniatur Sistem (Prototype Concept) (58)
  - 8.3 Ilustrasi Penggunaan Sistem (59)
  - 8.4 Penyajian Flowchart/Alur Kerja Alat (60)
- **BAB 9 RENCANA ANGGARAN DAN JADWAL KEGIATAN** (63)
  - 9.1 Rencana Anggaran Pelaksanaan Capstone (63)
  - 9.2 Jadwal Pelaksanaan Kegiatan Capstone (64)
- **BAB 10 SIMULASI PENDAHULUAN** (66)
  - 10.1 Simulasi Metode Prediksi Waktu (66)
  - 10.2 Simulasi Perangkat Keras (67)
- **BAB 11 KESIMPULAN** (68)
  - 11.1 Evaluasi Ketercapaian Tujuan (68)
  - 11.2 Ringkasan Desain Akhir (68)
  - 11.3 Rencana Implementasi dan Rekomendasi Pengembangan (70)
- **REFERENSI** (71)
- **LAMPIRAN** (79)

---

## DAFTAR GAMBAR

- **Gambar 2.1**: Mikrokontroler ESP32 (12)
- **Gambar 8.1**: Diagram Blok Umum Sistem (58)
- **Gambar 8.2**: Ilustrasi Miniatur Sistem yang Dirancang (59)
- **Gambar 8.3**: Ilustrasi Penggunaan Sistem oleh Pengguna (60)
- **Gambar 8.4**: Flowchart Keseluruhan Sistem (61)
- **Gambar 10.1**: Simulasi Prediksi Waktu (66)
- **Gambar 10.2**: Simulasi Sensor TDS (67)

---

## DAFTAR TABEL

- **Tabel 3.1**: Perbandingan Metode Deteksi Anomali pada Data Kualitas Air (28)
- **Tabel 3.2**: Perbandingan Metode Pengambilan Keputusan untuk Kontrol Distribusi Air (30)
- **Tabel 3.3**: Perbandingan Platform Antarmuka Pengguna untuk Sistem Monitoring Kualitas Air Toren (32)
- **Tabel 4.1**: Parameter Air untuk Keperluan Higiene dan Sanitasi yang Relevan dengan Proyek (Permenkes No. 2 Tahun 2023) (37)
- **Tabel 4.2**: Bobot Awal Parameter Kualitas Air untuk Kebutuhan Non-Konsumsi (38)
- **Tabel 4.3**: Ambang Skor Minimum per Titik Penggunaan Air (38)
- **Tabel 4.4**: Nilai Ambang Batas Rate of Change per Parameter untuk Deteksi Anomali Tiba-Tiba (40)
- **Tabel 4.5**: Confusion Matrix Sistem Deteksi Anomali Kualitas Air (41)
- **Tabel 5.1**: Perbandingan Pendekatan Deteksi Anomali untuk Sistem Monitoring Kualitas Air Toren (43)
- **Tabel 5.2**: Perbandingan Filter FIR dan IIR (45)
- **Tabel 5.3**: Perbandingan Metode Pengambilan Keputusan Distribusi Air (45)
- **Tabel 5.4**: Pemetaan Protokol Komunikasi Berdasarkan Jalur Data Sistem (47)
- **Tabel 5.5**: Pemetaan Tipe Basis Data Berdasarkan Karakteristik Data (47)
- **Tabel 5.6**: Ringkasan Pilihan Metode Sistem Monitoring Kualitas Air Toren (50)
- **Tabel 6.1**: Contoh Luaran (51)
- **Tabel 6.2**: Spesifikasi Luaran (53)
- **Tabel 9.1**: Estimasi Anggaran Pelaksanaan Kegiatan Capstone (63)
- **Tabel 9.2**: Jadwal Pelaksanaan Kegiatan Capstone (64)
- **Tabel 9.3**: Alokasi Sumber Daya Manusia (65)

---

# BAB 1: PENGANTAR

## 1.1 Latar Belakang

Ketersediaan air bersih merupakan pilar fundamental dalam menunjang kualitas lingkungan hunian, khususnya guna mendukung berbagai aktivitas domestik nonkonsumsi seperti sanitasi, mencuci, serta keperluan mandi. Sebagai kebutuhan dasar yang krusial bagi kesehatan masyarakat, standar air untuk higiene sanitasi secara formal telah diatur dalam Peraturan Menteri Kesehatan No. 2 Tahun 2023. Regulasi tersebut menetapkan parameter fisik, kimia, dan mikrobiologi yang ketat guna menjamin keamanan penggunaan air pada level rumah tangga. Kendati demikian, implementasi nyata dalam pemenuhan standar baku mutu tersebut masih menghadapi tantangan yang signifikan di berbagai wilayah Indonesia [1].

Pada umumnya, instalasi tangki penampungan atau toren berfungsi sebagai mediator distribusi sebelum air dialirkan demi memenuhi beragam utilitas domestik. Namun, aspek higienitas toren secara periodik kerap kali terabaikan dalam tataran praktis. Hal ini merupakan implikasi dari absennya sistem pengawasan yang terintegrasi, rendahnya atensi dari pihak pengguna, serta kendala aksesibilitas fisik menuju titik penyimpanan tersebut.

Dalam skema penyediaan air rumah tangga, unit toren berperan vital sebagai penyangga ketersediaan stok air. Sayangnya, pemantauan kualitas pada media penyimpanan ini sering kali luput dari perhatian. Realitas ini dipertegas oleh data yang menunjukkan bahwa 7 dari 10 rumah tangga di Indonesia secara laten mengonsumsi air yang terindikasi kontaminasi bakteri *E. coli* akibat manajemen penyimpanan yang substandar. Minimnya kesadaran publik, belum adanya sistem deteksi dini yang komprehensif, serta sulitnya jangkauan fisik ke lokasi penempatan toren yang cenderung di area elevasi tinggi semakin meningkatkan risiko degradasi kualitas air pada skala domestik [2].

Seiring waktu, unit toren menjadi sangat rentan terhadap degradasi kualitas yang dipicu oleh sedimentasi, poliferasi alga, hingga invasi mikroorganisme patogen. Penurunan standar higienitas ini umumnya bersifat laten dan terbagi menjadi dua klasifikasi utama: anomali mendadak yang mengindikasikan gangguan pada suplai air masuk, serta degradasi progresif yang mencerminkan akumulasi polutan internal. Selain variabel internal, faktor eksternal seperti intensitas paparan radiasi ultraviolet serta infiltrasi nutrisi organik dari lingkungan sekitar turut memberikan kontribusi signifikan dalam memicu ledakan populasi alga yang memperburuk kualitas air secara masif. Tangki penyimpanan yang jarang mendapatkan perawatan pembersihan sangat rentan terhadap penumpukan sedimen serta penurunan standar biologis. Kontak langsung dengan sinar matahari serta masuknya nutrien mempercepat pertumbuhan lumut secara agresif [3]. Secara saintifik, lapisan biofilm yang dibentuk oleh alga bertindak sebagai inkubator bagi perkembangan bakteri berbahaya seperti *Salmonella typhi* serta protozoa *Cryptosporidium* [4]. Penurunan higienitas ini dapat muncul secara eksponensial maupun bertahap, di mana perubahannya sering kali luput dari deteksi sensorik manusia hingga mencapai kondisi yang mengancam kesehatan [5].

Implikasi dari pemanfaatan sumber air yang telah terpolusi memberikan dampak yang sangat krusial bagi kesehatan publik. Pemakaian air dengan kualitas mikrobiologi yang berada di bawah standar baku mutu memiliki korelasi linear terhadap peningkatan risiko patologi *water-borne diseases*, termasuk di antaranya diare, kolera, serta manifestasi klinis berupa iritasi dermis, di mana populasi anak-anak menjadi kelompok yang paling rentan terinfeksi [6]. Tanpa implementasi mekanisme deteksi dini yang memadai, degradasi kualitas ini sering kali baru teridentifikasi setelah timbulnya anomali visual, aroma yang tidak sedap, atau saat munculnya gangguan kesehatan pada penghuni rumah tangga secara nyata.

Untuk memitigasi problematika tersebut, urgensi terhadap implementasi inovasi teknologi yang kapabel dalam menyelenggarakan monitoring kualitas air secara otomatis dan berkesinambungan menjadi sangat krusial. Dalam konteks ini, perancangan instrumen pemantauan kualitas air yang berbasis integrasi sensor memiliki relevansi yang fundamental. Perangkat ini diproyeksikan untuk mentransmisikan data secara *real-time* terkait parameter fisik serta tingkat higienitas internal toren, sehingga memungkinkan eksekusi langkah preventif yang akseleratif sebelum kualitas air melampaui ambang batas patologis yang ditetapkan dalam regulasi baku mutu kesehatan.

---

## 1.2 Penjabaran Masalah Umum Menjadi Masalah Teknis

Permasalahan umum yang diangkat pada proyek ini adalah ketersediaan dan pemantauan air bersih untuk kebutuhan rumah tangga non-konsumsi, di mana kualitas air di dalam toren rentan mengalami penurunan akibat kombinasi faktor dari kualitas sumber air, kondisi lingkungan sekitar, hingga perawatan yang kurang rutin. Menurut Peavy, Rowe, dan Tchobanoglous (1985) dalam buku *Environmental Engineering*, standar kualitas air sangat bergantung pada tujuan penggunaannya, sehingga setiap aktivitas memiliki tingkat toleransi yang berbeda terhadap cemaran [7]. Sebagai contoh, air yang mengalami sedikit penurunan kualitas mungkin tidak lagi memenuhi standar higienis untuk mandi, namun masih sangat layak digunakan untuk menyiram taman. Oleh karena itu, diperlukan suatu sistem yang dapat memutuskan saluran mana saja yang akan dibuka berdasarkan tingkat kebersihan air. Tingkat kebersihan air tersebut dihitung dengan lima parameter, yaitu *turbidity*, pH, *Total Dissolved Solids* (TDS), suhu, dan ketinggian air.

Topik ini merupakan topik yang kompleks disebabkan oleh beberapa hal sebagai berikut:
1. **Trade-off pengambilan keputusan dan kendala fungsionalitas (Aspek A1)**: Sistem ini berhadapan dengan *trade-off* dalam pengambilan keputusan antara pemantauan kualitas air dan penjagaan ketersediaan air untuk kebutuhan aktivitas lain. Pengambilan keputusan tidak dapat dilakukan secara biner, melainkan harus mendistribusikan air secara bertingkat menyesuaikan standar titik penggunaan (misalnya standar tinggi untuk kamar mandi/dapur, dan standar lebih rendah untuk taman). Hal ini memunculkan kendala fungsionalitas, di mana sistem harus mampu mengolah kombinasi parameter yang dapat saling bertentangan (seperti pH, *turbidity*, dan TDS) secara dinamis tanpa mengurangi fungsionalitas pasokan air harian pengguna.
2. **Karakteristik fisik sensor dan pemeliharaan antardisiplin (Aspek A6)**: Karakteristik kualitas air yang fluktuatif menyebabkan kondisi fisik sensor mudah mengalami *drift* seiring berjalannya waktu. Hal ini memunculkan kendala pemeliharaan (*maintenance*) agar sensor tetap akurat. Permasalahan ini tidak dapat diselesaikan dengan pendekatan tunggal, melainkan mutlak membutuhkan integrasi antardisiplin keilmuan: Teknik Elektro untuk instrumentasi, pembacaan sinyal analog, dan aktuasi relay; Teknologi Informasi untuk komputasi awan, perangkat lunak, dan analitik data; serta Teknik Biomedis untuk pemahaman mendalam terkait parameter biologi-kimia air yang memengaruhi kesehatan.
3. **Integrasi end-to-end subsistem (Aspek A5)**: Perancangan sistem ini memerlukan integrasi *end-to-end* dari berbagai subsistem yang saling bergantung. Prosesnya mencakup akuisisi data dari lima sensor analog (pH, kekeruhan, TDS, suhu, ketinggian air), pemrosesan di mikrokontroler, aktuasi empat katup solenoid secara independen, hingga komunikasi data ke *cloud*. Kualitas pembacaan data sensor secara langsung memengaruhi sistem aktuasi katup. Kondisi ini menghadirkan kendala interoperabilitas, di mana penyatuan berbagai protokol perangkat keras analog/digital dan perangkat lunak *cloud* harus disinkronisasi agar sistem berjalan dengan tingkat reliabilitas (*uptime*) $>95\%$.
4. **Kendala operasional lingkungan dan batasan biaya (Aspek A7)**: Perangkat ini harus beroperasi secara kontinu di lingkungan toren dengan kelembapan tinggi dan suhu yang berfluktuasi. Kondisi ini rentan memicu *noise* dan *drift* pada sensor. Jika gagal memitigasi hal ini, sistem dapat mendistribusikan air yang terkontaminasi atau sebaliknya memberikan *false alarm*. Di sisi lain, proyek ini dibatasi secara ketat oleh anggaran pembiayaan maksimal sebesar Rp2.000.000 (maks. realisasi Rp3.000.000).
5. **Penerapan matematika dan sains dasar (Aspek A8)**: Untuk menyelesaikan tantangan teknis, mendeteksi pola (*rate of change*), serta menyaring data *noise*, proyek ini sangat bergantung pada konsep matematika, sains dasar, dan rekayasa.

---

## 1.3 Kendala-Kendala yang Perlu Dipertimbangkan

Untuk mendapatkan solusi yang tepat, Tim Capstone DTETI 2026 Kelompok E-08 mempertimbangkan kendala-kendala berikut:
- **a. Ekonomi**: Desain solusi harus terjangkau bagi pengguna rumah tangga. Total biaya pembuatan perangkat dibatasi maksimal Rp3.000.000 sehingga pemilihan sensor, mikrokontroler, relay, dan katup solenoid harus menyeimbangkan antara harga dan kualitas tanpa mengorbankan fungsionalitas utama.
- **b. Lingkungan**: Desain solusi harus mampu beroperasi secara andal pada lingkungan toren yang memiliki kelembapan tinggi ($RH > 80\%$) dan suhu fluktuatif. Komponen elektronik harus terlindungi dari kontak langsung air. Sensor dan material yang bersentuhan dengan air harus bersifat *food-safe* / netral dan tidak mencemari air yang dipantau.
- **c. Keselamatan**: Mengingat sistem menggabungkan komponen kelistrikan dengan media air, instalasi catu daya, ESP32, dan relay harus dipastikan terlindung dari risiko korsleting maupun kebocoran arus. Selain itu, mekanisme kontrol distribusi dan fitur override manual harus dirancang agar tidak menyebabkan pengguna kehilangan akses air sepenuhnya dalam kondisi darurat.
- **d. Hukum, Aspek Legal, dan Perizinan**: Komunikasi nirkabel berbasis IoT harus menggunakan pita frekuensi legal tak berlisensi (WiFi 2,4 GHz). Sistem mengacu pada standar baku mutu Permenkes No. 2 Tahun 2023. Aspek privasi dan keamanan data pengguna pada platform web dikelola dengan autentikasi yang aman.
- **e. Keberlanjutan dan Keandalan**: Ditargetkan mencapai *uptime* $\ge 95\%$. Komponen yang dipilih harus memiliki ketahanan jangka panjang dan kemudahan kalibrasi ulang secara berkala.
- **f. Sosial dan Kemudahan Penggunaan**: Antarmuka dashboard dan mekanisme *manual override* per valve harus mudah dioperasikan oleh masyarakat awam non-teknis secara intuitif.

---

## 1.4 Mata Kuliah dan Kemampuan yang Mendukung

1. **Kalkulus Variabel Jamak**: Penilaian kualitas air dimodelkan sebagai fungsi multivariabel yang menghitung skor kelayakan berdasarkan perubahan simultan beberapa parameter (pH, TDS, turbidity, suhu).
2. **Persamaan Diferensial**: Perubahan parameter dimodelkan secara dinamis seiring waktu sebagai dasar prediksi *early warning* sisa hari kelayakan air toren.
3. **Isyarat dan Sistem**: Penyaringan *noise* frekuensi tinggi menggunakan *digital low-pass filtering* (FIR Moving Average Filter), pemenuhan teorema sampling Nyquist-Shannon pada konversi ADC, serta pemodelan LTI pada operasi differencing ($x[n] - x[n-1]$) dan regresi tren temporal.
4. **Teknik Kendali**: Sistem kendali lingkar tertutup (*closed-loop control*), analisis tanggapan peralihan untuk memastikan respons sistem $\le 3$ detik, aksi on/off kendali 4 solenoid valve, serta evaluasi kestabilan kendali untuk menekan *false alarm rate* $\le 10\%$.
5. **Probabilitas dan Variabel Acak**: Analisis sebaran stokastik data sensor, evaluasi matriks konfusi, dan penilaian risiko *false positive*.
6. **Elektronika Analog**: Pengkondisian sinyal sensor analog melalui rangkaian filter pasif, pembagi tegangan, dan penguat operasional sebelum dibaca ADC mikrokontroler.
7. **Kimia Dasar**: Prinsip potensial elektrokimia dan persamaan Nernst pada probe pH elektroda kaca; konduktivitas ionik terlarut pada sensor TDS; korelasi termal dan pH terhadap laju degradasi biofilm mikroorganisme.
8. **Sensor dan Transduser**: Prinsip konversi besaran fisis/kimia ke sinyal listrik, analisis karakteristik statik-dinamik (akurasi, linearitas, sensitivitas, histeresis, dan *drift*), kalibrasi kurva regresi, serta penentuan resolusi 12-bit ADC.
9. **Sistem Mikroprosesor**: Pemrograman mikrokontroler ESP32 sebagai unit komputasi tepi (*edge processing*) dan pengendali relai solenoid.
10. **Pemrograman Dasar**: Implementasi algoritma modular, manajemen memori, dan otomasi alur logika berbasis C/C++.
11. **Pengembangan Aplikasi Web**: Pembangunan sistem front-end, back-end, serta RESTful API dan WebSocket untuk visualisasi dan kendali jarak jauh.
12. **Teknologi Basis Data**: Perancangan skema penyimpanan terstruktur untuk log aktivitas dan basis data deret waktu untuk telemetri sensor.
13. **Kecerdasan Buatan**: Penerapan algoritma *Machine Learning* dan *Deep Learning* (GRU & XGBoost) untuk inferensi regresi *time-series* dan prediksi sisa umur pakai air (*Remaining Useful Life* / RUL).
14. **Sistem Tertanam dan Internet of Things (IoT)**: Integrasi komunikasi nirkabel berbasis MQTT broker untuk pertukaran data ringan secara berkesinambungan.
15. **Statistika**: Evaluasi metrik kesalahan regresi ($R^2$, MAPE, MAE) dan penyusunan ambang batas adaptif berbasis Z-score.

---

## 1.5 Usulan Solusi Potensial

Permasalahan monitoring dan kontrol air toren bersifat *open-ended*. Dari studi literatur, terdapat 4 alternatif pendekatan:
1. **Pendekatan filtrasi/penyaringan aktif (UV/RO)**: Mampu memurnikan air secara langsung [12], namun berbiaya operasional tinggi, memerlukan perawatan membran/lampu secara rutin, dan tidak menyediakan monitoring distribusi bertingkat.
2. **Pendekatan monitoring murni tanpa aktuasi**: Menggunakan sensor berbasis IoT [13, 14], murah dan mudah dipasang, namun tidak mampu memitigasi risiko secara preventif karena tidak ada penutupan katup otomatis per titik penggunaan.
3. **Pendekatan kontrol biner (satu katup utama)**: Menghentikan suplai total saat air buruk [15, 16], namun berdampak buruk bagi pengguna karena memutus pasokan air secara total meskipun air masih bisa digunakan untuk menyiram tanaman.
4. **Pendekatan monitoring multisensor dan pengambilan keputusan adaptif berbasis IoT (Solusi yang Dipilih)**: Mengintegrasikan lima sensor, pemrosesan tepi ESP32, algoritma *weighted scoring*, aktuasi bertingkat pada 4 solenoid valve independen, model *machine learning* untuk peramalan pengurasan toren, dan antarmuka PWA dengan dukungan *manual override*.

---

# BAB 2: DASAR TEORI PENDUKUNG

## 2.1 Sensor

Sensor adalah transduser masukan yang menerima stimulus fisis/kimia dan mengubahnya menjadi sinyal elektrik yang dapat diukur [20].

### 2.1.1 Sensor pH
Mengukur konsentrasi ion hidrogen melalui elektroda membran kaca selektif dan elektroda referensi $Ag/AgCl$ [21]. Beda potensial yang dihasilkan sebanding dengan derajat keasaman larutan.

### 2.1.2 Sensor TDS
Mengukur *Total Dissolved Solids* berdasarkan konduktivitas elektrik (*Electrical Conductivity* / EC) larutan dengan mengalirkan arus AC di antara dua kutub probe [22].

### 2.1.3 Sensor Turbidity
Mendeteksi hamburan cahaya akibat partikel tersuspensi menggunakan prinsip nephelometri (sudut $90^\circ$) dalam satuan NTU (*Nephelometric Turbidity Units*) [23].

### 2.1.4 Sensor Suhu
Sensor suhu mendeteksi energi termal dan mengubahnya menjadi variabel elektrik [24]. Proyek ini menggunakan modul digital DS18B20 berbasis protokol 1-Wire.

### 2.1.5 Sensor Ketinggian Air
Mendeteksi permukaan cairan dalam toren secara non-kontak menggunakan transduser ultrasonik berdasarkan *time-of-flight* pantulan gelombang akustik [25].

---

## 2.2 Mikrokontroler & ESP32

Mikrokontroler mengintegrasikan CPU, memori (RAM/Flash), dan periferal I/O dalam satu chip IC [26]. ESP32 dipilih karena memiliki prosesor dual-core Tensilica Xtensa 32-bit, ADC 12-bit, serta modul nirkabel Wi-Fi 802.11 b/g/n dan Bluetooth terintegrasi.

## 2.3 MicroSD

Modul kartu MicroSD bertindak sebagai penyimpanan sekunder *non-volatile* eksternal melalui antarmuka SPI untuk *data logging* lokal saat terjadi *network outage*.

## 2.4 Filter Digital & FIR

Filter digital menyaring komponen derau frekuensi tinggi yang berasal dari intervensi elektromagnetik dan turbulensi fluida [27]. Filter *Finite Impulse Response* (FIR) diimplementasikan secara non-rekursif sehingga memiliki sifat *inherently stable* (selalu stabil secara numerik) [28].

---

## 2.5 Basis Data

Sistem menerapkan pendekatan penyimpanan hibrid:
- **DBMS Relasional (PostgreSQL)**: Menangani data transaksional terstruktur dengan kepatuhan ACID, seperti profil pengguna, konfigurasi *threshold*, dan rekam *manual override* [29, 30].
- **Basis Data Deret Waktu (InfluxDB)**: Dioptimalkan khusus untuk mengelola data telemetri berindeks waktu (*time-series*) berfrekuensi tinggi dengan mekanisme *downsampling* dan *retention policy* otomatis [32].

---

## 2.6 Perangkat Lunak & Protokol Komunikasi

- **Front-End & Back-End**: Dibangun terpisah; front-end menangani rendering interaktif dan visualisasi grafik data, sedangkan back-end memproses algoritma evaluasi dan koordinasi aktuator [33].
- **RESTful API**: Berfungsi menyediakan rute permintaan *stateless* untuk operasi non-real-time seperti otentikasi akun dan pembacaan log historis [34].
- **WebSocket**: Komunikasi persisten dua arah (*full-duplex*) berlatensi rendah untuk mendistribusikan telemetri langsung ke *browser* pengguna [35].
- **MQTT**: Protokol *publish-subscribe* dengan *overhead* header paket yang sangat kecil, ideal untuk ESP32 pada jaringan berdaya rendah [36].
- **Progressive Web App (PWA)**: Aplikasi berbasis web yang dilengkapi *service worker* untuk caching offline dan penerimaan *push notification* tanpa beban pembuatan aplikasi Android/iOS terpisah [37].

---

## 2.7 Machine Learning & Forecasting Models

Machine learning mengekstrak pola dari data deret waktu untuk membedakan antara anomali suplai (*sudden drop*) dan degradasi internal toren (*gradual drift*) [38, 39]. Model peramalan time-series (GRU dan XGBoost dengan *feature engineering*) memproyeksikan lintasan degradasi untuk memperkirakan *Remaining Useful Life* (RUL) sebelum toren wajib dikuras [43].

---

## 2.8 Metrik Kinerja

Evaluasi model klasifikasi dan deteksi didasarkan pada *Confusion Matrix* yang terdiri dari:
- **True Positive (TP)**: Anomali aktual terdeteksi sebagai anomali.
- **True Negative (TN)**: Kondisi normal terdeteksi sebagai kondisi normal.
- **False Positive (FP)**: Kondisi normal terdeteksi sebagai anomali (*false alarm*).
- **False Negative (FN)**: Anomali aktual terlewat dan dianggap kondisi normal.

Formulasi matematis metrik:

$$\text{Accuracy} = \frac{\text{TP} + \text{TN}}{\text{TP} + \text{TN} + \text{FP} + \text{FN}}$$

$$\text{Precision} = \frac{\text{TP}}{\text{TP} + \text{FP}}$$

$$\text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}}$$

$$\text{F1-Score} = 2 \times \frac{\text{Precision} \times \text{Recall}}{\text{Precision} + \text{Recall}}$$

---

# BAB 3: ANALISIS STUDI PUSTAKA KUNCI

## 3.1 Pemantauan Kondisi Air Toren Berdasarkan Sensor

1. **Sensor pH**: Novenpa & Dzulkiflih [44] serta Mahpul et al. [45] mencatat akurasi sensor pH mencapai 96,41%, namun rentan terhadap fluktuasi suhu dan *drift* pada larutan berkadar asam/basa ekstrim, sehingga kompensasi suhu mutlak diperlukan.
2. **Sensor TDS**: Arifin et al. [46] dan Novenpa & Dzulkiflih [44] membuktikan pembacaan berbasis konduktivitas memiliki tingkat ketelitian 94,77%. Sensitivitas dapat menurun akibat kontaminasi mineral yang menempel pada batang elektroda.
3. **Sensor Turbidity**: Nur Aziezah et al. [47] dan Samsul Arifin et al. [46] menunjukkan sensor kekeruhan nephelometrik memiliki linearitas kalibrasi $R^2 = 0,9986$. Namun, sensor sensitif terhadap intensitas cahaya lingkungan toren serta gelembung udara mikroskopis.
4. **Sensor Suhu (DS18B20)**: Menghasilkan resolusi digital 12-bit [48]. Studi van der Wielen et al. [53] menunjukkan suhu $>20^{\circ}\text{C}$ memicu percepatan proliferasi patogen biofilm toren. Kalibrasi *oil-bath* dapat menekan eror hingga $\pm 0,85\%$ [51].
5. **Sensor Ketinggian Air (HC-SR04)**: Bae & Ji [59] merekomendasikan filter berbasis median untuk meniadakan riak air. Sahoo & Udgata [60] serta Li et al. [61] membuktikan bahwa kecepatan rambat suara berubah sebesar $0,6\text{ m/s}$ per $^\circ\text{C}$, sehingga kompensasi berbasis suhu DS18B20 wajib diterapkan untuk mencegah galat jarak hingga $2,7\%$.

---

## 3.2 Analisis Jenis Machine Learning

- **Supervised Learning**: Efektif untuk klasifikasi kualitas dan regresi sisa waktu menggunakan data berlabel [66].
- **Unsupervised Learning**: Mampu mendeteksi pencilan (*outlier*) tanpa label historis yang masif, namun sulit memisahkan tipe gangguan [67].

## 3.3 Analisis Algoritma (GRU vs XGBoost)

- **GRU (Gated Recurrent Unit)**: Menggunakan mekanisme *reset gate* dan *update gate* untuk mengingat ketergantungan temporal jangka panjang secara rekursif, sangat unggul dalam data deret waktu sekuensial.
- **XGBoost**: Sangat cepat dalam komputasi dan interpretasi *feature importance* [68], namun membutuhkan rekayasa fitur manual (*lag*, statistik bergulir) untuk menangkap dependensi waktu.

---

## 3.4 Metode Deteksi Anomali pada Data Sensor

### Tabel 3.1: Perbandingan Metode Deteksi Anomali pada Data Kualitas Air
| Parameter | Threshold Statis | Statistik Adaptif | Machine Learning |
| :--- | :--- | :--- | :--- |
| **Kemampuan deteksi anomali tiba-tiba** | Tinggi | Tinggi | Tinggi |
| **Kemampuan deteksi anomali gradual** | Rendah | Tinggi | Tinggi |
| **Kebutuhan data historis** | Tidak | Sedang | Tinggi |
| **Beban komputasi** | Sangat Rendah | Rendah | Sedang–Tinggi |
| **Tingkat false positive** | Tinggi | Sedang | Rendah |
| **Kemampuan adaptasi lokal** | Tidak | Ya | Ya |
| **Kemudahan implementasi** | Tinggi | Sedang | Rendah |

---

## 3.5 Metode Pengambilan Keputusan untuk Kontrol Distribusi Air

### Tabel 3.2: Perbandingan Metode Pengambilan Keputusan untuk Kontrol Distribusi Air
| Parameter | Rule-Based | Fuzzy Logic | Weighted Scoring |
| :--- | :--- | :--- | :--- |
| **Penanganan kondisi batas** | Buruk | Sangat Baik | Baik |
| **Transparansi keputusan** | Tinggi | Sedang | Tinggi |
| **Beban komputasi** | Sangat Rendah | Sedang | Rendah |
| **Kemudahan penyesuaian lokal** | Sedang | Rendah | Tinggi |
| **Kebutuhan keahlian domain** | Sedang | Tinggi | Sedang |
| **Kemampuan distribusi bertingkat** | Sedang | Baik | Sangat Baik |

---

## 3.6 Platform Antarmuka Pengguna

### Tabel 3.3: Perbandingan Platform Antarmuka Pengguna untuk Sistem Monitoring Kualitas Air Toren
| Parameter | Mobile Native | Web Konvensional | PWA |
| :--- | :--- | :--- | :--- |
| **Jumlah basis kode** | 2 (Android/iOS) | 1 | 1 |
| **Proses instalasi** | Wajib (toko aplikasi) | Tidak perlu | Opsional |
| **Dukungan notifikasi push** | Sangat andal | Terbatas | Cukup andal |
| **Kemampuan offline** | Penuh | Tidak | Sebagian |
| **Akses lintas perangkat** | Terbatas | Penuh | Penuh |
| **Beban pengembangan** | Tinggi | Sedang | Sedang |
| **Kesesuaian untuk CPS satu unit** | Berlebihan | Baik | Sangat Baik |

---

# BAB 4: PEMODELAN PERMASALAHAN

## 4.1 Pemodelan Akuisisi dan Kalibrasi Sensor

Secara umum, hubungan antara besaran listrik sensor $V$ dan nilai fisis $Q$ dimodelkan secara linier:

$$Q = a \cdot V + b \tag{4.1}$$

Akurasi dievaluasi menggunakan koefisien determinasi $R^2$:

$$R^2 = 1 - \frac{\sum_{i=1}^n (Q_i - \hat{Q}_i)^2}{\sum_{i=1}^n (Q_i - \overline{Q})^2} \tag{4.2}$$

dengan kriteria keberhasilan kalibrasi disyaratkan $R^2 \ge 0,95$.

### 4.1.2 Sensor Ketinggian Air
Memetakan waktu pantul gelombang ultrasonik menjadi jarak ketinggian air $0 - 200\text{ cm}$.

### 4.1.3 Sensor Turbidity
Akibat saturasi optik pada tingkat kekeruhan tinggi, hubungan tegangan dan kekeruhan dimodelkan menggunakan persamaan polinomial orde dua:

$$Q = a \cdot (V_{\text{turb}})^2 + b \cdot (V_{\text{turb}}) + c \tag{4.3}$$

### 4.1.4 Sensor pH
Mengikuti persamaan elektrokimia Nernst:

$$E = E_0 - \frac{RT}{nF} \cdot \ln [H^+] \tag{4.4}$$

Pada suhu $25^\circ\text{C}$, persamaan disederhanakan menjadi:

$$E \approx E_0 - 59,16 \cdot \text{pH} \quad (\text{dalam mV}) \tag{4.5}$$

### 4.1.5 Sensor TDS
Konversi konduktivitas larutan ($\mu\text{S/cm}$) ke konsentrasi padatan terlarut (ppm):

$$\text{TDS} = k_{\text{TDS}} \cdot K \tag{4.6}$$

dengan konstanta empiris $k_{\text{TDS}} \approx 0,5 - 0,7$.

### 4.1.6 Sensor Suhu
Resolusi data digital 12-bit sensor DS18B20:

$$\Delta T = \frac{1}{2^{12}} \times 16 = 0,0625^\circ\text{C/LSB} \tag{4.7}$$

$$T = D \times 0,0625^\circ\text{C} \tag{4.8}$$

---

## 4.2 Pemodelan Filter Digital untuk Reduksi Noise Sensor

### 4.2.1 Moving Average Filter (FIR)
$$\hat{Q}(t) = \frac{1}{N} \sum_{k=0}^{N-1} Q(t-k) \tag{4.9}$$

### 4.2.2 Exponentially Weighted Moving Average (EWMA)
$$\hat{Q}(t) = \alpha \cdot Q(t) + (1-\alpha) \cdot \hat{Q}(t-1) \tag{4.10}$$

di mana $\alpha \in (0, 1]$ adalah faktor pelunakan (*smoothing factor*).

---

## 4.3 Pemodelan Weighted Scoring untuk Indeks Kualitas Air

Normalisasi sub-indeks parameter ke-i ke skala $0 - 100$:

$$q_i = \frac{|Q_i - Q_{\text{ideal}, i}|}{Q_{\text{max}, i} - Q_{\text{ideal}, i}} \times 100 \tag{4.11}$$

### Tabel 4.1: Baku Mutu Air Higiene & Sanitasi (Permenkes No. 2 Tahun 2023)
| No | Jenis Parameter | Kadar Maksimum yang Diperbolehkan | Satuan |
| :---: | :--- | :--- | :--- |
| 1 | Suhu | Suhu udara $\pm 3$ | $^\circ\text{C}$ |
| 2 | Total Dissolved Solids (TDS) | $< 300$ | mg/L (ppm) |
| 3 | Kekeruhan (Turbidity) | $< 3$ | NTU |
| 4 | pH | 6,5 – 8,5 | - |

Skor kualitas air komposit $S$:

$$S = \sum_{i=1}^n w_i q_i \tag{4.12}$$

dengan konstrain normalisasi bobot:

$$\sum_{i=1}^n w_i = 1 \tag{4.13}$$

### Tabel 4.2: Bobot Parameter Kualitas Air
| No. | Parameter | Bobot ($w_i$) | Alasan Penetapan |
| :---: | :--- | :---: | :--- |
| 1 | Turbidity | 0,35 | Indikator visual utama; langsung dirasakan pengguna |
| 2 | pH | 0,30 | Risiko iritasi kulit dan korosi pipa |
| 3 | TDS | 0,20 | Indikator pencemaran mineral dan zat kimia terlarut |
| 4 | Suhu | 0,15 | Faktor pendukung; memicu percepatan reaksi degradasi biologis |
| **Total** | | **1,00** | |

### Logika Distribusi Katup
Status setiap solenoid valve ke-$j$:

$$\text{Status}_{\text{valve}, j} = \begin{cases} \text{BUKA}, & \text{jika } S \le S_{th, j} \\ \text{TUTUP}, & \text{jika } S > S_{th, j} \end{cases} \tag{4.14}$$

### Tabel 4.3: Ambang Batas Skor per Titik Distribusi
| Valve | Titik Penggunaan | Ambang Skor Maks. ($S_{th}$) | Pertimbangan |
| :---: | :--- | :---: | :--- |
| 1 | Kamar Mandi | 30 | Kontak mukosa & kulit langsung; standar paling ketat |
| 2 | Dapur (non-minum) | 35 | Mencuci peralatan makan |
| 3 | Cucian Pakaian | 55 | Kontak tidak langsung; standar moderat |
| 4 | Taman / Penyiraman | 70 | Non-kontak manusia; toleransi cemaran tertinggi |

---

## 4.4 Pemodelan Deteksi Anomali Tiba-Tiba

Laju perubahan parameter:

$$\Delta Q_i(t) = \hat{Q}_i(t) - \hat{Q}_i(t-\Delta t) \tag{4.15}$$

Pemicu peringatan mendadak (*sudden alert*):

$$\text{SuddenAlert}_i = \begin{cases} 1, & \text{jika } |\Delta Q_i(t)| > \theta_i \\ 0, & \text{jika } |\Delta Q_i(t)| \le \theta_i \end{cases} \tag{4.16}$$

Alarm sistem global:

$$\text{SuddenAlert}_{\text{system}} = \bigvee_{i=1}^n \text{SuddenAlert}_i \tag{4.17}$$

### Tabel 4.4: Nilai Ambang Batas Rate of Change ($\theta_i$)
| No | Parameter | Ambang Batas ($\theta_i$) | Satuan | Justifikasi |
| :---: | :--- | :---: | :--- | :--- |
| 1 | Turbidity | 2,0 | NTU/interval | Variasi stabil $< 0,5$ NTU; kenaikan $> 2$ mengindikasikan sedimen inlet |
| 2 | pH | 0,5 | unit pH/interval | Variasi diurnal $< 0,2$; perubahan $> 0,5$ menandakan anomali kimiawi |
| 3 | TDS | 25 | ppm/interval | Variasi toren tertutup $< 10$ ppm; perubahan $> 25$ ppm indikasi kontaminasi |
| 4 | Suhu | 1,5 | $^\circ\text{C}$/interval | Fluktuasi termal lingkungan $< 0,5^\circ\text{C}$; lonjakan menandakan air baru |

### Model Z-Score Adaptif
$$Z_i(t) = \frac{Q_i(t) - \mu_i(t)}{\sigma_i(t)} \tag{4.18}$$

$$\text{Anomali Terdeteksi} \iff |Z_i(t)| > Z_{\text{th}} \tag{4.19}$$

dengan $Z_{\text{th}} = 2,5 - 3,0$.

---

## 4.5 Model Metrik Evaluasi Kinerja Sistem

- **Akurasi Sensor (MAPE)**:
  $$\text{MAPE} = \frac{1}{n} \sum_{k=1}^n \left| \frac{Q_{\text{ref}, k} - Q_{\text{sensor}, k}}{Q_{\text{ref}, k}} \right| \times 100\% \tag{4.20}$$
- **Akurasi Deteksi**:
  $$\text{Akurasi Deteksi} = \frac{\text{TP} + \text{TN}}{\text{TP} + \text{TN} + \text{FP} + \text{FN}} \tag{4.21}$$
- **False Alarm Rate**:
  $$\text{False Alarm Rate} = \frac{\text{FP}}{\text{FP} + \text{TN}} \tag{4.22}$$
- **Recall (Sensitivitas)**:
  $$\text{Recall} = \frac{\text{TP}}{\text{TP} + \text{FN}} \tag{4.23}$$
- **Akurasi Prediksi Waktu Kritis Pengurasan**:
  $$\text{MAE}_{\text{EWS}} = \frac{1}{n} \sum_{k=1}^n |t_{\text{pred}, k}^* - t_{\text{actual}, k}^*| \tag{4.24}$$
- **Efektivitas Kontrol Distribusi Bertingkat**:
  $$\text{Efektivitas Distribusi} = \frac{\text{Jumlah keputusan valve yang sesuai}}{\text{Total keputusan valve yang dievaluasi}} \times 100\% \tag{4.25}$$

---

# BAB 5: PEMILIHAN DAN PENGEMBANGAN METODE

## 5.1 s.d. 5.6 Analisis Pemilihan Arsitektur

### Tabel 5.1: Perbandingan Pendekatan Deteksi Anomali
| Parameter | Threshold Statis | Statistik Adaptif | Machine Learning |
| :--- | :--- | :--- | :--- |
| Kemampuan deteksi mendadak | Tinggi | Tinggi | Tinggi |
| Kemampuan deteksi gradual | Rendah | Tinggi | Tinggi |
| Kebutuhan data historis | Tidak ada | Sedang | Tinggi |
| Beban komputasi ESP32 | Sangat ringan | Ringan | Sedang–Berat |
| Kemampuan adaptasi lokal | Tidak | Ya | Ya |
| Kesesuaian timeline | Tinggi | Tinggi | Rendah |

### Tabel 5.2: Perbandingan Filter FIR dan IIR
| No | Aspek | FIR | IIR |
| :---: | :--- | :--- | :--- |
| 1 | Jenis | Non-rekursif | Rekursif |
| 2 | Stabilitas numerik | Selalu stabil | Berpotensi tidak stabil |
| 3 | Efisiensi komputasi | Butuh lebih banyak koefisien | Lebih hemat koefisien |
| 4 | Respons fasa | Linear | Tidak linear |
| 5 | Kompleksitas implementasi | Sederhana | Lebih kompleks |
| 6 | Ketergantungan keluaran lalu | Tidak ada | Ada |
| 7 | Risiko akumulasi overflow | Rendah | Lebih tinggi |
| 8 | Kesesuaian untuk ESP32 | **Sangat sesuai** | Perlu perhatian |

### Tabel 5.4: Pemetaan Protokol Komunikasi Terpadu
| Jalur Data | Protokol | Justifikasi Teknis |
| :--- | :--- | :--- |
| **ESP32 ke Back-end** | MQTT | Ringan, hemat bandwidth, tahan koneksi fluktuatif |
| **Back-end ke PWA (Live)** | WebSocket | *Full-duplex*, pembaruan instan tanpa *polling* |
| **PWA ke Back-end (Operasi)** | HTTP/REST | Ideal untuk *fetch* log historis dan update konfigurasi |
| **Notifikasi Darurat** | Web Push / WA / Email | Menjamin keterbacaan peringatan dini secara luas |

### Tabel 5.5: Pemetaan Sistem Basis Data
| Jenis Data | Tipe DBMS | Justifikasi |
| :--- | :--- | :--- |
| **Data telemetri sensor periodik** | Time-Series (InfluxDB) | Kompresi tinggi, agregasi rentang waktu cepat |
| **Profil pengguna, konfigurasi, log override** | Relasional (PostgreSQL) | Menjamin konsistensi ACID dan integritas relasional |

---

## 5.7 Arsitektur Perangkat Lunak Terpadu

1. **Lapisan Edge Processing (ESP32)**:
   - Akuisisi 5 sensor secara berkala.
   - Filter low-pass EWMA peredam noise.
   - Deteksi dini anomali tiba-tiba via *Rate of Change* & Z-Score adaptif untuk memicu pemutusan katup darurat lokal secara otonom.
   - Pengiriman payload JSON via protokol MQTT ke server serta pencadangan berkas ke kartu MicroSD.
2. **Lapisan Back-end Server**:
   - Berfungsi sebagai MQTT Subscriber & REST/WebSocket provider.
   - Mengolah algoritma regresi time-series dan machine learning (RUL forecasting).
   - Menghitung nilai *Weighted Scoring* komposit dan sinkronisasi status kendali katup.
   - Mengelola otentikasi JWT dan pencatatan audit log kegiatan manual override.
3. **Lapisan Front-end (PWA)**:
   - Dashboard responsif dengan grafik riwayat pengukuran sensor.
   - Panel kendali katup solenoid individual dengan proteksi dialog konfirmasi risiko.
   - Penampil notifikasi peringatan bertingkat (peringatan bahaya langsung dan estimasi hari pengurasan).

### Tabel 5.6: Ringkasan Pilihan Metode
| Aspek Sistem | Metode yang Dipilih |
| :--- | :--- |
| **Pengukuran Kualitas Air** | Sensor elektrokimia in-situ (pH, TDS, turbidity, suhu) + ultrasonik level |
| **Deteksi Anomali Mendadak** | Kombinasi *Rate of Change* dan Z-score adaptif pada ESP32 |
| **Deteksi Anomali Gradual** | Analisis tren regresi linier deret waktu historis |
| **Peringatan Dini (EWS)** | Prediksi sisa waktu pengurasan toren (*Remaining Useful Life*) |
| **Pengambilan Keputusan Katup** | *Weighted Scoring* multi-parameter dengan ambang batas bertingkat |
| **Antarmuka Pengguna** | Progressive Web App (PWA) |
| **Protokol Komunikasi** | MQTT (Edge ke Server) & WebSocket/REST (Server ke Web) |
| **Penyimpanan Data** | InfluxDB (Time-series) + PostgreSQL (Relasional) |

---

# BAB 6: LUARAN DAN SPESIFIKASI YANG DIUSULKAN

## 6.1 Luaran yang Dijanjikan

### Tabel 6.1: Rincian Luaran Proyek
| Jenis Luaran | Deskripsi Fungsional |
| :--- | :--- |
| **Prototipe Monitoring & Kontrol Perangkat Keras** | Kotak kontrol berbasis mikrokontroler ESP32, 5 modul sensor (pH, TDS, turbidity, suhu, ketinggian air), modul relai 4-channel, dan 4 unit katup solenoid 12V DC. Mendukung aktuasi bertingkat ke titik kamar mandi, dapur, mesin cuci, dan taman, serta fitur *manual override*. |
| **Dashboard Monitoring Berbasis Web** | Antarmuka dashboard PWA real-time via WebSocket, penampil grafik historis, panel kontrol katup jarak jauh, dan visualisasi skor kelayakan air. |
| **Early Warning System: Prediksi Pengurasan** | Model peramalan sisa umur toren (RUL). Sistem menerbitkan peringatan apabila ambang kritis diproyeksikan tercapai dalam waktu $\le 10$ hari. |
| **Early Warning System: Deteksi Anomali** | Penutupan protektif seluruh valve seketika saat terdeteksi anomali lonjakan polutan mendadak dan pengiriman notifikasi instan. |

---

## 6.2 Spesifikasi Luaran

### Tabel 6.2: Spesifikasi Teknis Sistem
| No | Parameter Spesifikasi | Satuan | Standar / Nilai | Keterangan |
| :---: | :--- | :---: | :---: | :--- |
| 1 | Tegangan Masukan Utama | Volt (V) | 12 V DC | Catu daya relai & katup solenoid (Penjelasan A) |
| 2 | Rentang Pengukuran pH | - | pH 0 – 14 | Modul pH meter elektroda kaca (Penjelasan B) |
| 3 | Rentang Kekeruhan | NTU | 0 – 455 NTU | Modul optik turbiditas (Penjelasan C) |
| 4 | Rentang Pengukuran TDS | ppm | 0 – 1000 ppm | Modul konduktivitas elektrik larutan (Penjelasan D) |
| 5 | Rentang Pengukuran Suhu | $^\circ\text{C}$ | $-10^\circ\text{C} \text{ s.d. } +85^\circ\text{C}$ | Sensor DS18B20 digital presisi $\pm 0,5^\circ\text{C}$ (Penjelasan E) |
| 6 | Rentang Ketinggian Air | cm | 0 – 200 cm | Transduser HC-SR04 (Penjelasan F) |
| 7 | Unit Solenoid Valve | unit | 4 valve | Tipe *Normally Closed* (N/C) 1/2 inci (Penjelasan G) |
| 8 | Waktu Respons Dashboard | ms | $\le 1000\text{ ms}$ | Latensi eksekusi permintaan sistem web (Penjelasan H) |

---

# BAB 7: BATASAN PERMASALAHAN

## 7.1 Limitasi Dataset
- Perekaman data dilakukan selama kurun waktu 90 hari pada satu instalasi tangki uji coba toren air skala perumahan.
- Karakteristik pasokan air terbatas pada instalasi pengujian lokal dan belum mencakup variasi kontaminan biologis/kimiawi ekstrim dari berbagai ragam sumur bor daerah lain.
- Waktu pengamatan berfokus pada validasi fungsionalitas algoritma distribusi dan tren pembentukan biofilm awal.

## 7.2 Toleransi Ketelitian Sensor
- **Sensor Suhu DS18B20**: Toleransi $\pm 0,5^\circ\text{C}$ pada rentang $-10^\circ\text{C}$ sampai $+85^\circ\text{C}$ [77].
- **Sensor Ketinggian HC-SR04**: Akurasi $\pm 3\text{ mm}$, pembacaan dapat dipengaruhi oleh kondensasi uap toren dan sudut rambat [78].
- **Sensor TDS (SEN0244)**: Akurasi $\pm 10\%$ *full scale* pada $25^\circ\text{C}$ [79]; tidak membedakan jenis ion mineral spesifik.
- **Sensor pH (SEN0161-V2)**: Akurasi $\pm 0,1\text{ pH}$ [80]; membutuhkan kalibrasi buffer berkala.
- **Sensor Turbidity (SEN0189)**: Memberikan estimasi kekeruhan relatif ($4,1 \pm 0,3\text{ V}$ pada air jernih) [81], rentan terhadap goresan atau biofilm pada kaca optik.

## 7.3 Limitasi Dana
Total anggaran perancangan dan implementasi purwarupa dibatasi sebesar maksimal **Rp3.000.000,00**.

---

# BAB 8: PERANCANGAN UMUM SISTEM

## 8.1 Arsitektur Sistem

Sistem dibagi menjadi tiga hierarki fungsional:
1. **Subsistem Akuisisi Data (Input)**: Sensor pH, turbidity, TDS, suhu DS18B20, dan ketinggian air terhubung ke rangkaian pengkondisi sinyal.
2. **Subsistem Pemrosesan (Decision Unit)**: ESP32 memproses filter EWMA, evaluasi ambang *Rate of Change*, dan perhitungan skor komposit.
3. **Subsistem Aktuasi (Output)**: Modul relai 4-channel menggerakkan 4 unit katup solenoid 12V (Kamar Mandi, Dapur, Cucian, Taman). Modul MicroSD dan koneksi Wi-Fi ke MQTT Broker menangani data telemetri.

```
+-----------------------------------------------------------+
|               1. SUBSISTEM AKUISISI DATA                  |
|   [pH] [Turbidity] [TDS] [DS18B20 Suhu] [HC-SR04 Level]   |
+-----------------------------+-----------------------------+
                              | Sinyal Analog/Digital
                              v
+-----------------------------------------------------------+
|         2. SUBSISTEM PEMROSESAN & PENGAMBILAN KEPUTUSAN   |
|                    (Mikrokontroler ESP32)                 |
|  - Filter Digital (EWMA / Moving Average)                 |
|  - Deteksi Anomali Mendadak (Rate of Change / Z-Score)    |
|  - Perhitungan Indeks Kualitas Air (Weighted Scoring)     |
|  - Keputusan Kontrol Distribusi Bertingkat                |
+--------------+------------------------------+-------------+
               | Logika Driver Relai          | MQTT / WiFi
               v                              v
+-----------------------------+  +--------------------------+
|    3. SUBSISTEM AKTUASI     |  |   4. LAPISAN APLIKASI    |
|  [Relay Driver 4-Channel]   |  |   - MQTT Broker          |
|              |              |  |   - PostgreSQL & InfluxDB|
|   +----------+----------+   |  |   - Engine ML & EWS      |
|   | Valve 1: Kamar Mandi|   |  |   - Dashboard PWA Web    |
|   | Valve 2: Dapur      |   |  +--------------------------+
|   | Valve 3: Cucian     |   |
|   | Valve 4: Taman      |   |
|   +---------------------+   |
+-----------------------------+
```

---

## 8.2 & 8.3 Konsep Miniatur & Penggunaan Sistem

Prototipe dirancang dalam wujud tangki penampung miniatur. Komponen elektronik ditempatkan dalam *Control Box* IP65 di bagian atas toren. Pengguna mengakses sistem melalui peramban web pada smartphone atau desktop:
1. Autentikasi Pengguna (Login/Register).
2. Memantau telemetri sensor real-time.
3. Memeriksa riwayat grafik deret waktu kualitas air.
4. Memantau status operasi masing-masing solenoid valve.
5. Melakukan tindakan *Manual Override* pembukaan/penutupan katup.
6. Menerima notifikasi peringatan dini bahaya cemaran atau jadwal pengurasan toren.

---

## 8.4 Alur Kerja Sistem (Flowchart)

```
                       +-------------------+
                       |       MULAI       |
                       +---------+---------+
                                 |
                                 v
                       +-------------------+
                       | Inisialisasi      |
                       | Perangkat Keras   |
                       +---------+---------+
                                 |
                                 v
                       +-------------------+
                       | Konek WiFi & MQTT |
                       +---------+---------+
                                 |
                                 v
                       +-------------------+
                       | Baca 5 Nilai      |
                       | Sensor            |
                       +---------+---------+
                                 |
                                 v
                       +-------------------+
                       | Filter Digital    |
                       | EWMA              |
                       +---------+---------+
                                 |
                                 v
                    /-------------------------\
                   /     Deteksi Anomali       \      YA
                  <      Lonjakan Mendadak?     >------------+
                   \                           /             |
                    \-------------------------/              |
                                 | TIDAK                     v
                                 v                 +-------------------+
                    /-------------------------\    | Tutup Semua Valve |
                   /     Hasil Model RUL       \   +---------+---------+
                  <      Kritis <= 10 Hari?     >            |
                   \                           /             v
                    \-------------------------/    +-------------------+
                       | YA            | TIDAK     | Kirim Notifikasi  |
                       |               |           | Bahaya Anomali    |
                       v               |           +---------+---------+
             +-------------------+     |                     |
             | Kirim Notifikasi  |     |                     |
             | Early Warning     |     |                     |
             +---------+---------+     |                     |
                       |               |                     |
                       +-------+-------+                     |
                               |                             |
                               v                             |
                     +-------------------+                   |
                     | Hitung Skor       |                   |
                     | Komposit (WQI)    |                   |
                     +---------+---------+                   |
                               |                             |
                               v                             |
                     +-------------------+                   |
                     | Keputusan Kontrol |                   |
                     | 4 Valve Bertingkat|                   |
                     +---------+---------+                   |
                               |                             |
                               v                             |
                     +-------------------+                   |
                     | Publish Data ke   |<------------------+
                     | MQTT Broker       |
                     +---------+---------+
                               |
                               v
                     +-------------------+
                     | Jeda Waktu Siklus |
                     +---------+---------+
                               |
                               +------> (Kembali ke Pembacaan Sensor)
```

---

# BAB 9: RENCANA ANGGARAN DAN JADWAL KEGIATAN

## 9.1 Rencana Anggaran Biaya

### Tabel 9.1: Estimasi Anggaran Pengadaan Komponen
| No. | Nama Komponen / Deskripsi Barang | Jumlah | Harga Satuan (Rp) | Total Biaya (Rp) |
| :---: | :--- | :---: | :---: | :---: |
| 1 | ESP32 DEVKITC V4 ESP-WROOM-32D | 1 unit | 80.000,00 | 80.000,00 |
| 2 | Sensor Suhu Probe Waterproof DS18B20 | 1 unit | 14.000,00 | 14.000,00 |
| 3 | HC-SR04 Ultrasonic Range Finder | 1 unit | 15.000,00 | 15.000,00 |
| 4 | TDS Meter V1.0 Module Water Quality | 1 unit | 55.000,00 | 55.000,00 |
| 5 | Kabel Jumper 20 cm Male-Female | 40 pcs | 15.000,00 | 15.000,00 |
| 6 | Turbidity Sensor Kit Suspended Particle | 1 unit | 200.000,00 | 200.000,00 |
| 7 | Solenoid Valve N/C 12V DC 1/2 Inci | 4 unit | 46.000,00 | 184.000,00 |
| 8 | Modul Relay 1-Channel 5V Optocoupler | 4 unit | 15.000,00 | 60.000,00 |
| 9 | Modul Adapter Sensor Suhu DS18B20 | 1 unit | 20.000,00 | 20.000,00 |
| 10 | pH Meter Kit Elektroda BNC PH-45002C | 1 unit | 212.000,00 | 212.000,00 |
| 11 | Tangki Penampung Plastik (Ember Toren) | 1 unit | 20.000,00 | 20.000,00 |
| 12 | Pipa PVC 1/2 Inci 50 cm | 4 unit | 20.000,00 | 80.000,00 |
| 13 | Knee 90 Derajat 1/2 Inci | 2 unit | 5.000,00 | 10.000,00 |
| 14 | Fitting Tee 1/2 Inci | 3 unit | 5.000,00 | 15.000,00 |
| 15 | Kotak Panel Box Waterproof IP65 | 1 unit | 55.000,00 | 55.000,00 |
| 16 | Kabel Serabut Merah-Hitam 1m | 4 meter | 2.000,00 | 8.000,00 |
| 17 | MicroSD Card Storage | 1 unit | 100.000,00 | 100.000,00 |
| 18 | Modul Antarmuka MicroSD SPI | 1 unit | 20.000,00 | 20.000,00 |
| **-** | **Kebutuhan Expo & Sosialisasi** | | | |
| 19 | X-Banner Promosi | 1 unit | 110.000,00 | 110.000,00 |
| 20 | Pamflet Kegiatan | 30 lembar | 1.300,00 | 39.000,00 |
| 21 | Stiker Penandaan | 40 lembar | 800,00 | 32.000,00 |
| **TOTAL** | | | | **1.334.000,00** |

---

## 9.2 Jadwal & Alokasi Penugasan

### Tabel 9.2: Linimasa Kegiatan Capstone Project 2026
| Tahap Kegiatan | Feb | Mar | Apr | Mei | Jun | Jul | Agu | Sep | Okt | Nov | Des |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Persiapan** | | | | | | | | | | | |
| a. Perumusan Masalah | X | | | | | | | | | | |
| b. Studi Literatur | X | X | | | | | | | | | |
| **Pelaksanaan** | | | | | | | | | | | |
| a. Perancangan Perangkat Keras | | X | X | | | | | | | | |
| b. Perancangan Perangkat Lunak | | X | X | | | | | | | | |
| c. Perancangan Machine Learning | | X | X | | | | | | | | |
| d. Pengembangan Perangkat Keras | | | | X | X | X | | | | | |
| e. Pengembangan Perangkat Lunak | | | | X | X | X | | | | | |
| f. Pengembangan Machine Learning | | | | X | X | X | | | | | |
| g. Pengujian Kinerja Terpadu | | | | | | | X | X | | | |
| h. Evaluasi dan Perbaikan | | | | | | | | X | X | | |
| **Penyelesaian** | | | | | | | | | | | |
| a. Penyempurnaan Akhir (*Finishing*) | | | | | | | | | | X | |
| b. Pembuatan Laporan Akhir | | | | | | | | | | X | X |

### Tabel 9.3: Alokasi Sumber Daya Manusia
| Tahapan Kerja Proyek | Rizqi (Biomedis) | Shofiy (Elektro) | Ano (TI) | Fikar (TI) |
| :--- | :---: | :---: | :---: | :---: |
| **Perumusan Masalah & Domain Kimia Air** | **PIC** | Anggota | Anggota | Anggota |
| **Perancangan & Integrasi Hardware** | Anggota | **PIC** | - | - |
| **Pengembangan Firmware & Filter ESP32** | Anggota | **PIC** | Anggota | - |
| **Arsitektur Cloud, MQTT & Database** | - | - | **PIC** | Anggota |
| **Pengembangan Frontend PWA & UI/UX** | - | - | **PIC** | - |
| **Pengembangan Model Machine Learning** | - | - | Anggota | **PIC** |
| **Evaluasi Kinerja & Pelaporan Dokumen** | **PIC** | Anggota | Anggota | Anggota |

---

# BAB 10: SIMULASI PENDAHULUAN

## 10.1 Simulasi Metode Prediksi Waktu (RUL)

Simulasi dilakukan untuk memprediksi sisa waktu kelayakan air sebelum toren harus dikuras menggunakan dua algoritma: **XGBoost** dan **Gated Recurrent Unit (GRU)**. Model menerima input empat fitur sensor yang dinormalisasi pada skala 0–1 (kekeruhan, TDS, pH, dan suhu) selama kurun waktu 60 hari. 

Pada pengujian hari ke-45 (dengan nilai aktual ground truth sisa umur $RUL = 55,0\text{ hari}$):
- **Model XGBoost** memprediksi sisa waktu sebesar **8,1 hari** (galat sangat besar).
- **Model GRU** memprediksi sisa waktu sebesar **35,0 hari** (mendekati tren ground truth).

Hal ini membuktikan bahwa arsitektur jaringan saraf berulang seperti GRU jauh lebih tangguh dalam mengekstraksi dependensi urutan temporal data deret waktu dibandingkan model regresi berbasis pohon (*tree boosting*).

## 10.2 Simulasi Perangkat Keras

Uji pembacaan probe TDS terhadap dua sampel air menghasilkan:
1. **Air Jernih (Sampel A)**: Terbaca nilai ADC 251–261 ($0,20 - 0,21\text{ V}$), terkonversi menjadi nilai TDS **83 ppm**.
2. **Air Keruh (Sampel B)**: Menunjukkan peningkatan linier keluaran tegangan dengan nilai pembacaan **125 ppm**.

Hasil pada Serial Monitor menunjukkan respons dinamis yang stabil dan konsisten.

---

# BAB 11: KESIMPULAN

## 11.1 Evaluasi Ketercapaian Tujuan

Proyek perancangan sistem pemantauan kualitas dan kontrol distribusi air toren rumah tangga non-konsumsi berhasil merumuskan seluruh arsitektur hardware dan software yang terintegrasi. Sistem memenuhi seluruh kriteria *Complex Engineering Problem* IABEE melalui penyatuan instrumentasi elektrokimia, konversi ADC terfilter digital pada mikrokontroler ESP32, model klasifikasi adaptif, dan pengendali aktuasi 4-saluran independen berbasis *weighted scoring*.

## 11.2 Ringkasan Desain Akhir

- **Instrumen Sensor**: pH, Kekeruhan (Turbidity), TDS, Suhu (DS18B20), dan Ultrasonik Level.
- **Unit Pengolah Tepi**: Mikrokontroler ESP32 (ADC 12-bit, filter digital FIR/EWMA, deteksi lonjakan seketika).
- **Unit Pengendali Aktuator**: Modul Relai 4-channel mengendalikan 4 unit katup solenoid 12V N/C (Kamar Mandi, Dapur, Cucian, Kebun).
- **Platform Telemetri**: PWA dengan dukungan WebSocket live stream, notifikasi *early warning*, dan opsi *manual override*.

### 11.2.1 Validasi Fungsional Sistem
Uji coba integrasi awal menunjukkan seluruh komponen mampu berkomunikasi stabil: ESP32 dapat membaca data sensor, menyaring derau sinyal, melakukan kalkulasi logika lokal, dan memicu sakelar relai sesuai profil ambang batas yang ditentukan.

### 11.2.2 Keterbatasan Desain
- Validasi jangka panjang belum mencakup kondisi fluktuasi cuaca ekstrim di lapangan terbuka.
- Pembobotan parameter masih berbasis nilai literatur teoretis dan membutuhkan kalibrasi lanjutan melalui pengujian empiris.
- Desain tata letak PCB kustom dan manajemen pengkabelan modular masih perlu disempurnakan pada tahap Capstone 2.

## 11.3 Rencana Implementasi dan Pengembangan Lanjutan
1. Melakukan kalibrasi komparatif berkala terhadap instrumen laboratorium bersertifikasi.
2. Menyempurnakan model inferensi prediktif GRU pada back-end server menggunakan dataset riil.
3. Menerapkan skema *failsafe* otomatis jika terjadi anomali catu daya atau kehilangan sinyal Wi-Fi.

---

# REFERENSI

- [1] M. P. Pangestu and M. F. D. Lusno, "Kualitas Air Minum Rumah Tangga di Indonesia Berdasarkan Parameter Fisik, Kimia, dan Mikrobiologi: Studi Cross-Sectional Mengacu pada Standar Nasional," *Jurnal Penelitian Inovatif (JUPIN)*, vol. 5, no. 2, pp. 1689–1696, May 2025, doi: 10.54082/jupin.1534.
- [2] A. N. M. Arif, "Krisis Air Bersih dan Dampaknya terhadap Permasalahan Kesehatan Masyarakat di Indonesia," *Chapters Indonesia*, Dec. 2024.
- [3] I. Septia, "Penyebab Air Tandon Terkontaminasi dan Cara Mengatasinya," *Tedmond Groups*, Mar. 22, 2025.
- [4] Penguin Indonesia, "Apakah Air Berlumut Berbahaya? Ini 5 Dampaknya," *Penguin Indonesia*, Apr. 23, 2026.
- [5] Sahabi Tandon Air, "Bahaya di Balik Tandon Berlumut: Dari Diare hingga Masalah Pencernaan, Ini Cara Mencegahnya," *Sahabi Tandon Air*, Jul. 9, 2026.
- [6] S. Na'imah, "7 Jenis Penyakit Akibat Pencemaran Air," *Hello Sehat*, Nov. 23, 2021.
- [7] G. Tchobanoglous, H. S. Peavy, and D. R. Rowe, *Environmental Engineering*, New York: McGraw-Hill, 1985.
- [8] R. Singh et al., "Water Quality Monitoring and Management of Building Water Tank Using Industrial Internet of Things," *Sustainability*, vol. 13, no. 15, p. 8452, 2021.
- [9] F. Jan, N. Min-Allah, S. Saeed, S. Z. Iqbal, and R. Ahmed, "IoT-Based Solutions to Monitor Water Level, Leakage, and Motor Control for Smart Water Tanks," *Water*, vol. 14, no. 3, p. 309, 2022.
- [10] V. Sathananthavathi, A. Shiva, and S. S. Sivasubash, "Intelligent Water Quality and Level Detection System Using Hybrid Classifier," *Wireless Personal Communications*, vol. 136, 2024.
- [11] N. A. Dharmawan, P. Nugroho, and S. B. Wibowo, "Development of IoT Devices for Drinking Water Quality Monitoring Systems," DTETI FT UGM, 2023.
- [12] S. Swathi, C. Suganya, N. Hariharan, and I. Bildass Santhosam, "Water Utility Conservation and Management Approach Using IoT," *IJRASET*, vol. 11, no. 4, 2023.
- [13] S. Geetha and S. Gouthami, "Internet of Things Enabled Real Time Water Quality Monitoring System," *Smart Water*, vol. 2, no. 1, 2016.
- [14] S. Pasika and S. T. Gandla, "Smart Water Quality Monitoring System with Cost-Effective Using IoT," *Heliyon*, vol. 6, no. 7, p. e04096, 2020.
- [15] A. T. Chafa, G. P. Chirinda, and S. Matope, "Design of a Real-Time Water Quality Monitoring and Control System Using Internet of Things (IoT)," *Cogent Engineering*, vol. 9, no. 1, 2022.
- [16] R. AlGhamdi and S. K. Sharma, "IoT-Based Smart Water Management Systems for Residential Buildings in Saudi Arabia," *Processes*, vol. 10, no. 11, p. 2462, 2022.
- [17] A. Dahal, T. L. Tulasi, and S. Moulik, "AquaSense: Real-Time Smart Water Quality Monitoring and Alert System in an IoT-Enabled Environment," *National Academy Science Letters*, 2025.
- [18] J. G. Natividad and T. D. Palaoag, "IoT Based Model for Monitoring and Controlling Water Distribution," *IOP Conf. Ser.: Mater. Sci. Eng.*, vol. 482, p. 012045, 2019.
- [19] S. Tinelli and I. Juran, "Artificial Intelligence-Based Monitoring System of Water Quality Parameters for Early Detection of Non-Specific Bio-Contamination in Water Distribution Systems," *Water Supply*, vol. 19, no. 6, pp. 1785–1795, 2019.
- [20] P. Subramanian and S. A. David, "Sensors - An Overview," *Conference Paper*, 2021.
- [21] Supmea Automation, "Apa itu sensor pH bagaimana cara kerjanya?," 2024.
- [22] Rudiyanto and Hanifadinna, "Perancangan TDS Monitoring pada Air Boiler Berbasis Mikrokontroler," ITSB, 2021.
- [23] Alat Uji, "Pengertian Turbidity Sensor dan Cara Kerjanya," 2024.
- [24] PT Mitrainti Sejahtera Eletrindo, "Sensor Suhu: Definisi, Prinsip Kerja, dan Klasifikasinya," *MISEL*, 2024.
- [25] Alat Uji, "Sensor Level Air: Pengertian, Fungsi, Jenis dan Aplikasi Terbaru," 2024.
- [26] STMicroelectronics, "STM32 32-bit Arm Cortex MCUs," 2026.
- [27] Bohrium SciencePedia, "Low-pass Filter," 2026.
- [28] Bohrium SciencePedia, "Finite Impulse Response Filters," 2026.
- [29] R. Elmasri and S. B. Navathe, *Fundamentals of Database Systems*, 7th ed., Pearson, 2015.
- [30] J. L. Harrington, *Relational Database Design*, Elsevier, 2009.
- [31] V. Kumar and Tambi, "A Comparison of SQL and NO-SQL Database Management Systems," *IJAREEIE*, 2024.
- [32] P. John, J. Hynek, T. Hruska, and M. Valny, "Application of Time Series Database for IoT Smart City Platform," in *Proc. SCSP*, Prague, 2023.
- [33] Telkom University, "Aplikasi Berbasis Web: Pengertian, Jenis, Contoh, Keunggulan," *DOCIF*, 2025.
- [34] R. T. Fielding, "Architectural Styles and the Design of Network-based Software Architectures," Ph.D. dissertation, UC Irvine, 2000.
- [35] I. Fette and A. Melnikov, "The WebSocket Protocol," *IETF RFC 6455*, Dec. 2011.
- [36] OASIS, "MQTT Version 5.0," OASIS Standard, 2019.
- [37] D. Fortunato and J. Bernardino, "Progressive Web Apps: An Alternative to the Native Mobile Apps," in *Proc. CISTI*, 2018.
- [38] A. L. Samuel, "Some Studies in Machine Learning Using the Game of Checkers," *IBM J. Res. Dev.*, vol. 3, no. 3, pp. 210–229, 1959.
- [39] T. M. Mitchell, *Machine Learning*, McGraw-Hill, 1997.
- [40] E. A. Lee, "Cyber Physical Systems: Design Challenges," in *Proc. IEEE ISORC*, 2008.
- [41] B. Čičo, T. Biba, and I. Shabani, "Design of a cattle-health-monitoring system using microservices and IoT devices," *Computers*, vol. 11, no. 5, p. 79, 2022.
- [42] I. Malavolta et al., "Hybrid mobile apps in the Google Play Store," in *Proc. IEEE/ACM MOBILESoft*, 2017.
- [43] R. P. Masini, M. C. Medeiros, and E. F. Mendes, "Machine learning advances for time series forecasting," *J. Econ. Surv.*, vol. 37, no. 1, pp. 76–111, 2023.
- [44] N. N. Novenpa dan Dzulkiflih, "Alat Pendeteksi Kualitas Air Portable dengan Parameter pH, TDS dan Suhu Berbasis Arduino Uno," *Jurnal Inovasi Fisika Indonesia (IFI)*, vol. 9, no. 2, pp. 85–92, 2020.
- [45] M. K. Mahpul, A. A. Jaya, dan M. M. Amin, "Aplikasi Pendeteksi Kualitas Air di Rumah Menggunakan Arduino," *JIRE*, vol. 5, no. 2, pp. 246–255, 2022.
- [46] S. Arifin et al., "Sistem Monitoring pH Air, Total Dissolved Solids (TDS) dan Kekeruhan Air pada Tandon berbasis Internet of Things (IoT)," *Magnetic*, vol. 5, no. 2, pp. 84–93, 2024.
- [47] N. Aziezah et al., "Sipekernik: Sistem Pemantau Kekeruhan Air dan Pengairan pada Akuaponik," *JTIM*, vol. 4, no. 4, pp. 261–271, 2023.
- [48] W. H. Sugiharto dan H. Susanto, "Real-time water quality assessment via IoT: monitoring pH, TDS, temperature, and turbidity," *ISI*, vol. 28, no. 4, 2023.
- [49] J. A. Abdinoor et al., "Performance of low-cost air temperature sensors and applied calibration techniques," *Atmosphere*, vol. 16, no. 7, p. 842, 2025.
- [50] J. A. Rodríguez-Rama et al., "Metrological validation of low-cost DS18B20 digital temperature sensors," *Metrology*, vol. 6, no. 1, p. 21, 2026.
- [51] R. A. Koestoer et al., "A simple method for calibration of temperature sensor DS18B20 waterproof in oil bath," *AIP Conf. Proc.*, vol. 2062, 2019.
- [52] A. Elyounsi dan A. N. Kalashnikov, "Evaluating suitability of a DS18B20 temperature sensor for use in an accurate air temperature distribution measurement network," *Eng. Proc.*, vol. 10, no. 1, p. 56, 2021.
- [53] P. W. J. J. van der Wielen et al., "Influence of temperature on growth of four different opportunistic pathogens in drinking water biofilms," *Microorganisms*, vol. 11, no. 6, p. 1574, 2023.
- [54] N. M. Farhat et al., "Effect of water temperature on biofouling development in reverse osmosis membrane systems," *Water Res.*, vol. 103, pp. 149–159, 2016.
- [55] A. Bogler dan E. Bar-Zeev, "Membrane distillation biofouling: Impact of feedwater temperature," *Environ. Sci. Technol.*, vol. 52, no. 17, pp. 10019–10029, 2018.
- [56] S. S. Sarnin, A. B. Hussein, dan D. B. Zahidi, "Development of water quality system using GSM module," in *Proc. IEEE IoT*, 2020.
- [57] S. E. Putri dan V. Arinal, "Pengembangan sistem monitoring kualitas air dan kendali pakan budidaya ikan berbasis IoT," *JIMIK*, 2025.
- [58] R. Bogdan et al., "Low-cost Internet-of-Things water-quality monitoring system for rural areas," *Sensors*, vol. 23, no. 8, p. 3919, 2023.
- [59] I. Bae and U. Ji, "Outlier detection and smoothing process for water level data measured by ultrasonic sensor in stream flows," *Water*, vol. 11, no. 5, p. 951, 2019.
- [60] A. K. Sahoo and S. K. Udgata, "A novel ANN-based adaptive ultrasonic measurement system for accurate water level monitoring," *IEEE Trans. Instrum. Meas.*, vol. 69, no. 6, pp. 3232–3241, 2020.
- [61] S. Li, W. Gao, and W. Liu, "A novel temperature drift compensation algorithm for liquid-level measurement systems," *Micromachines*, vol. 16, no. 1, p. 24, 2024.
- [62] S. C. Olisa et al., "Smart two-tank water quality and level detection system via IoT," *Heliyon*, vol. 7, no. 8, p. e07651, 2021.
- [63] S. E. Christodoulou, E. Kourti, and A. Agathokleous, "Waterloss detection in water distribution networks using wavelet change-point detection," *Water Resour. Manag.*, vol. 31, no. 3, pp. 979–994, 2016.
- [64] S. H. Kim, "Multiple leak detection algorithm for pipe network," *Mech. Syst. Signal Process.*, vol. 139, p. 106645, 2020.
- [65] F. Jan et al., "IoT-based solutions to monitor water level, leakage, and motor control for smart water tanks," *Water*, vol. 14, no. 3, p. 309, 2022.
- [66] M. Padma Sree et al., "Smart Industrial Real-Time Water Quality Monitoring and Prediction Using Machine Learning," *IJCRT*, 2025.
- [67] E. Santos-Fernandez et al., "New Bayesian and Deep Learning Spatio-Temporal Models Can Reveal Anomalies in Sensor Data More Effectively," *Water Research*, 2025.
- [68] T. Chen and C. Guestrin, "XGBoost: A Scalable Tree Boosting System," in *Proc. ACM SIGKDD*, 2016.
- [69] Y. Chen et al., "Research and Design of Distributed IoT Water Environment Monitoring System Based on LoRa," *Wirel. Commun. Mob. Comput.*, 2021.
- [70] F. Muharemi, D. Logofătu, and F. Leon, "Machine learning approaches for anomaly detection of water quality on a real-world data set," *J. Inf. Telecommun.*, 2019.
- [71] E. El-Shafeiy et al., "Real-Time Anomaly Detection for Water Quality Sensor Monitoring Based on Multivariate Deep Learning Technique," *Sensors*, 2023.
- [72] H. Fakhrurroja et al., "Water quality assessment monitoring system using fuzzy logic and the internet of things," 2023.
- [73] T. D. Banda et al., "Development of Water Quality Indices (WQIs): A Review," *Pol. J. Environ. Stud.*, vol. 29, no. 3, 2020.
- [74] M. G. Uddin, S. Nash, and A. I. Olbert, "A review of water quality index models and their use for assessing surface water quality," *Ecol. Indic.*, vol. 122, p. 107218, 2021.
- [75] A. Al-Fuqaha et al., "Internet of Things: A survey on enabling technologies, protocols, and applications," *IEEE Commun. Surv. Tutor.*, vol. 17, no. 4, pp. 2347–2376, 2015.
- [76] V. Puranik, A. Sharma, and N. Joshi, "Comparative analysis of WebSocket and HTTP for real-time IoT dashboard applications," in *Proc. ic-ETITE*, 2020.
- [77] Maxim Integrated, "DS18B20 Programmable Resolution 1-Wire Digital Thermometer Datasheet," 2026.
- [78] ELECFreaks, "Ultrasonic Ranging Module HC-SR04 Datasheet," 2026.
- [79] DFRobot, "Gravity: Analog TDS Sensor / Meter for Arduino (SKU: SEN0244)," 2026.
- [80] DFRobot, "Gravity: Analog pH Sensor / Meter Kit V2 (SKU: SEN0161-V2)," 2026.
- [81] DFRobot, "Gravity: Analog Turbidity Sensor for Arduino (SKU: SEN0189)," 2026.

---

# LAMPIRAN

## A. Surat Pernyataan Capstone Design
- **Judul Proyek**: Sistem Monitoring Kualitas dan Pengambilan Keputusan untuk Deteksi Dini dan Kontrol Distribusi Air Toren pada Kebutuhan Rumah Tangga Non-Konsumsi
- **Tema**: Sustainable Environment for Living Systems (SDG-12)
- **Anggota & Peran**:
  1. Muhammad Rizqi Aminuddin (Teknik Biomedis) – Hardware & Chem-Bio Analysis
  2. Shofiy Alia Rimala (Teknik Elektro) – Hardware Engineer
  3. Azfanova Sammy Rafif Saputra (Teknologi Informasi) – Software Engineer
  4. Dzulfikar Rizqi Ramadhani (Teknologi Informasi) – ML Engineer
- **Dosen Pembimbing**: Dr. Ir. Guntur Dharma Putra, S.T., M.Sc. (NIP: 111199104201802102)

## B. Pemetaan Capaian Pembelajaran Lulusan (CPL / PLO)
- CPL-1 s.d. CPL-10 dinyatakan terpenuhi dan telah dikonfirmasi oleh Dosen Pembimbing.

## C. Kriteria Keberhasilan Terukur (Surat Pernyataan IABEE)

| No | Parameter / Ukuran | Kriteria Keberhasilan | Satuan |
| :---: | :--- | :---: | :---: |
| 1 | Akurasi Pembacaan Sensor | $\ge 95$ | % |
| 2 | Konsistensi Pembacaan Sensor (Deviasi) | $\le 5$ | % |
| 3 | Waktu Respons Sistem End-to-End | $\le 3$ | detik |
| 4 | Akurasi Pengambilan Keputusan | $\ge 85$ | % |
| 5 | False Alarm Rate | $\le 10$ | % |
| 6 | Akurasi Deteksi Pola Penurunan | $\ge 80$ | % |
| 7 | Akurasi Prediksi Early Warning (MAE) | $\le 1$ | hari |
| 8 | Efektivitas Kontrol 4 Valve | $\ge 90$ | % |
| 9 | Kesesuaian Distribusi Bertingkat | $\ge 85$ | % |
| 10 | Fungsionalitas Manual Override | $100$ | % |
| 11 | Reliabilitas Sistem (Uptime) | $\ge 95$ | % |
| 12 | Biaya Total Pembuatan Purwarupa | $\le 3.000.000$ | Rp |