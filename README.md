![Unsealed Project](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/unsealed.png)

# Unsealed Project

Toolkit untuk membaca, mendekode, dan melihat (viewer) berbagai file biner milik game **Seal Online**.

Seal Online adalah game online yang sangat populer di Indonesia. Tetapi jika dibandingkan dengan Ragnarok Online, RF Online, dan sejenisnya tidak banyak open-source project yang mengutak-atik daleman game ini. Semuanya biasanya ditutup-tutupi untuk kepentingan pribadi maupun alasan lain. Project ini dibuat sebagai tempat berbagi ilmu tentang game Seal Online dari sisi teknis dan programming. Project ini akan mulai dari mengupas file-file yang digunakan oleh game Seal Online, dan semoga bisa berlanjut ke berbagai hal teknis lain.

**Disclaimer:** Project ini dibuat hanya untuk tujuan edukasi. Kami tidak mengizinkan penggunaan komersial maupun aktivitas ilegal apa pun terhadap server resmi game. Software disediakan apa adanya ("as-is").


## Fitur

- **Mendekode** format Seal Online ke format standar terbuka:
  - Mesh / actor (`.ms1`, `.act`, beserta tulang `.bn1` + animasi `.an1`) → glTF / GLB (`.glb`, `.gltf`)
  - Tekstur (`.tex`, `.te1`) → PNG
  - Map (`.map`) → heightmap PNG + object yang diekstrak
  - Menu (`.men`) dan sprite atlas (`.spr`)
  - Data terenkripsi (`.edt`) → file plaintext yang sudah didekode (decode & encode)
- **Membuka arsip `.spak`** — arsip terenkripsi ZipCrypto milik Seal Online. Password diturunkan otomatis sesuai versi client; tidak perlu memasukkan key secara manual.
- **Viewer 3D interaktif** — orbit/pan model, memainkan animasi, menjelajahi map, melihat tekstur, sprite, dan menu, serta **membuka file langsung dari dalam `.spak` tanpa perlu mengekstrak terlebih dahulu**.


## Kebutuhan Sistem

- **Python 3.8+**
- Untuk viewer: GPU/driver yang mendukung **OpenGL 3.3 Core**


## Instalasi

Package Python berada di dalam subdirektori `unsealed/` pada repository ini.

```bash
# Clone repository
git clone https://github.com/feryandi/unsealed.git
cd unsealed

# Install CLI inti (disarankan editable install)
pip install -e ./unsealed
```

Untuk memakai viewer 3D interaktif, install juga dependensi opsional `viewer`
(pygame, PyOpenGL, imgui-bundle, …):

```bash
pip install -e "./unsealed[viewer]"
```

> Tips: disarankan menggunakan virtual environment.
> ```bash
> python -m venv venv
> source venv/bin/activate     # Windows: venv\Scripts\activate
> pip install -e "./unsealed[viewer]"
> ```


## Cara Pakai

### Tool baris perintah (decode / konversi)

Setelah terinstall, jalankan konverter sebagai module atau lewat script
`unsealed` yang sudah terpasang:

```bash
python -m unsealed              # atau cukup:  unsealed
python -m unsealed -o output    # simpan hasil ke ./output, bukan di samping file input
```

Tool akan menampilkan prompt interaktif. Masukkan path file game, lalu file
tersebut akan didekode ke direktori output (secara default sama dengan
direktori file input):

```
Enter filepath (or 'quit' to exit): C:\Seal Online\actor\E_cook_m.ms1
```

| Opsi | Keterangan |
|---|---|
| `-o`, `--output <dir>` | Direktori output (default: sama dengan direktori file input). |

### Viewer 3D

```bash
python -m unsealed.viewer                 # terbuka dengan layar sambutan (belum ada file)
python -m unsealed.viewer path/to/file    # langsung membuka sebuah file
```

Gunakan tombol **Open File** di UI (atau berikan path lewat baris perintah)
untuk memuat file yang didukung. Kontrol umum:

| Aksi | Kontrol |
|---|---|
| Orbit | Drag tombol kiri / kanan mouse |
| Geser (pan) | Drag tombol tengah mouse |
| Zoom | Scroll wheel |
| Play / Pause animasi | `Space` |
| Ganti animasi | `Up` / `Down` |
| Toggle wireframe | `W` |
| Buka file | `O` |
| Sisipkan model ke map yang sedang terbuka | `I` |
| Keluar | `Esc` |

### Membuka arsip `.spak`

Seal Online mengemas sebagian besar asetnya ke dalam arsip `.spak` yang
terproteksi password. Unsealed membacanya secara langsung. Kamu tidak perlu
tahu atau memasukkan password-nya.

**CLI:** arahkan konverter ke file `.spak`. Seluruh isi arsip akan diekstrak
(dengan tetap mempertahankan struktur folder di dalamnya), lalu setiap anggota
yang dikenali akan dikonversi:

```
Enter filepath (or 'quit' to exit): C:\Seal Online\actor\actor.SPAK
```

**Viewer:** buka `.spak` seperti file lainnya. Panel **Archive** akan muncul
berisi daftar file yang bisa dilihat di dalamnya; klik salah satu untuk
membukanya. Karena seluruh arsip sudah dibongkar di belakang layar, file
pendamping (tekstur `.tex`, tulang `.bn1`, animasi `.an1`, dll. milik sebuah
model) otomatis ditemukan walaupun berada di dalam arsip yang sama.

<!-- TODO(screenshot): tambahkan screenshot viewer dengan sebuah .spak terbuka dan
     panel browser "Archive" terlihat, lalu simpan di docs/assets/ dan tautkan di sini. -->


## Format file yang didukung

| Ekstensi | Tipe | Output |
|---|---|---|
| `.ms1` | Mesh file (+ opsional tulang `.bn1`, animasi `.an1`) | `.glb` / `.gltf` |
| `.act` | Actor file | `.glb` / `.gltf` |
| `.map` | Map file | heightmap `.png` + object yang diekstrak |
| `.men` | Menu / UI file | viewer |
| `.spr` | Sprite atlas | viewer |
| `.tex` | Texture file | `.png` |
| `.te1` | Texture file | `.png` |
| `.edt` | Data file terenkripsi (stream cipher LCG) | `decoded_<nama>.edt` (plaintext); mendukung encode kembali |
| `.sha` | Material shader gaya Q3 | di-parse (dipakai format lain) |
| `.spak` | Arsip terkemas (terenkripsi) | dibongkar + anggotanya dikonversi |

Format yang didukung viewer: `.ms1`, `.act`, `.map`, `.tex`, `.te1`, `.spr`, `.men`, dan `.spak` (menjelajahi isi).


## Screenshots

![Actor Viewer](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/actor.png)

![Map Viewer](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/map.png)

![Menu Viewer](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/menu.png)

![Model Viewer](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/model.png)

![Sprite Viewer](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/sprite.png)

![Texture Viewer](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/texture.png)


## Roadmap
Project ini dibuat pada saat waktu senggang, sehingga dibutuhkan waktu yang cukup lama untuk melakukan update berkala.


### Phase 0

- [x] ms1 - Mesh File
- [x] bn1 - Bone File
- [x] an1 - Animation File


### Phase 1

- [x] tex - Texture File
- [x] act - Actor File


### Phase 2

- [x] map - Map File
- [x] mdt - Archive File

### Phase 3

- [x] Viewer App

### Phase 4

- [x] spr - Sprite File
- [x] te1 - Texture File
- [x] sha - Material Shader File

### Phase 5

- [x] men - Menu File
- [x] spak - Packed Archive (terenkripsi)
- [x] edt - Encoded Data File (decode & encode)
- [ ] mat - Material File

### Phase 6

Viewer App improvements
- [ ] Shader Support
- [ ] Animation Sound and Effect Support
- [ ] Character Viewer
