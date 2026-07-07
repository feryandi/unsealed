![Unsealed Project](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/unsealed.reload.png)

Toolkit untuk membaca, mendekode, dan melihat (viewer) berbagai file biner milik game **Seal Online**.

Seal Online adalah game online yang sangat populer di Indonesia. Tetapi jika dibandingkan dengan Ragnarok Online, RF Online, dan sejenisnya tidak banyak open-source project yang mengutak-atik daleman game ini. Semuanya biasanya ditutup-tutupi untuk kepentingan pribadi maupun alasan lain. Project ini dibuat sebagai tempat berbagi ilmu tentang game Seal Online dari sisi teknis dan programming. Project ini akan mulai dari mengupas file-file yang digunakan oleh game Seal Online, dan semoga bisa berlanjut ke berbagai hal teknis lain.

> **Disclaimer:** Project ini dibuat hanya untuk tujuan edukasi. Kami tidak mengizinkan penggunaan komersial maupun aktivitas ilegal apa pun terhadap server resmi game. Software disediakan apa adanya ("as-is").

## Fitur

- **Buka isi game Seal Online** — ekstrak dan jelajahi model 3D karakter, monster, map, tekstur, sprite, hingga tampilan menu langsung dari file game aslinya.
- **Konversi ke format standar** — ubah model dan animasi menjadi **glTF / GLB** serta tekstur menjadi **PNG**, siap dibuka di Blender, Unity, atau tool 3D favoritmu.
- **Buka arsip SPAK** — akses arsip `.spak` tanpa perlu tahu atau memasukkan password; semuanya ditangani otomatis.
- **Viewer 3D & 2D interaktif** — putar, geser, dan zoom model, mainkan animasi, telusuri map, serta lihat tekstur, sprite, dan menu — bahkan langsung dari dalam arsip game tanpa perlu mengekstrak terlebih dahulu.

## Kebutuhan Sistem

Untuk membuka `unsealed-viewer` dibutuhkan GPU/driver yang mendukung **OpenGL 3.3 Core.**

## Cara Pakai

Unduh binary siap-pakai dari halaman
[Releases](https://github.com/feryandi/unsealed/releases) — tersedia untuk
Windows, Linux, dan macOS, tanpa perlu memasang Python. Terdapat dua program:

- **`unsealed-reader`** — decoder/konverter dengan command line (CLI). Jalankan, lalu masukkan path file game pada prompt untuk membukanya (hasil disimpan di tempat yang sama dengan file asal, atau gunakan `-o <dir>` untuk menyimpan di direktori lain).
- **`unsealed-viewer`** — viewer 3D/2D interaktif. Jalankan lalu buka file lewat tombol **Open File**, atau berikan path file sebagai argumen.

Ingin menjalankan dari source code? Lihat bagian [Kontribusi](#kontribusi).

## Screenshots

![Actor Viewer](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/actor.png)

![Map Viewer](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/map.png)

![Menu Viewer](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/menu.png)

![Model Viewer](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/model.png)

![Sprite Viewer](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/sprite.png)

![Texture Viewer](https://raw.githubusercontent.com/feryandi/unsealed/main/docs/assets/texture.png)

## Kontribusi

Kontribusi sangat diterima — baik menambah dukungan format baru, memperbaiki bug, maupun menyempurnakan viewer. Project ini adalah satu package Python `unsealed` dengan dua subpackage:

- `unsealed.reader` — decoder/encoder + CLI (`unsealed-reader`).
- `unsealed.viewer` — viewer 3D/2D interaktif (`unsealed-viewer`); dependensi GPU bersifat opsional.

Siapkan development environment (disarankan memakai virtual environment):

```bash
# Clone repository
git clone https://github.com/feryandi/unsealed.git
cd unsealed

# Virtual environment
python -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate

# Install lengkap: reader + viewer + tools pengembangan
pip install -e ".[viewer,dev]"
```

Sebelum membuka pull request, pastikan lint dan test lolos:

```bash
ruff check src && ruff format src
pytest
```

Langkah kontribusi:

1. Fork repository ini, lalu buat branch baru dari `main`.
2. Buat perubahan beserta test bila memungkinkan, dan jaga agar lint tetap bersih.
3. Buka pull request dengan penjelasan singkat mengenai perubahan yang dibuat.

Menemukan bug atau punya usulan format baru untuk didukung? Silakan buka [issue](https://github.com/feryandi/unsealed/issues).
