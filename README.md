<div align="center">

<br/>

<img src="assets/logo_white.png" alt="OralCancer AI" width="180"/>

<br/>
<br/>

# OralCancer AI

### Intelligent Oral Cancer Detection & Segmentation Platform

<br/>

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.10-41CD52?style=flat-square&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.11-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](https://pytorch.org)
[![OpenCV](https://img.shields.io/badge/OpenCV-4.12-5C3EE8?style=flat-square&logo=opencv&logoColor=white)](https://opencv.org)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?style=flat-square&logo=windows&logoColor=white)](https://microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)

<br/>

> A graduation project desktop application that assists doctors in early oral cancer detection
> using deep learning — combining U-Net segmentation and ConvNeXt / EfficientNet classification.

<br/>

> [!WARNING]
> **First time setup required after cloning.**
> The AI model weights are not included in this repository due to their large size (~418 MB).
> After cloning, you **must** run the following command before starting the app:
> ```
> python setup_models.py
> ```
> This downloads all 4 model files automatically. You only need to do this **once**.

<br/>

[**Getting Started**](#-getting-started) &nbsp;·&nbsp;
[**Features**](#-features) &nbsp;·&nbsp;
[**AI Models**](#-ai-models) &nbsp;·&nbsp;
[**Architecture**](#-system-architecture) &nbsp;·&nbsp;
[**Team**](#-team)

<br/>

</div>

---

## 📌 Table of Contents

- [About The Project](#-about-the-project)
- [Features](#-features)
- [System Requirements](#-system-requirements)
- [Getting Started](#-getting-started)
- [Project Structure](#-project-structure)
- [System Architecture](#-system-architecture)
- [AI Models](#-ai-models)
- [Database Schema](#-database-schema)
- [Build as EXE](#-build-as-exe)
- [Team](#-team)
- [Acknowledgements](#-acknowledgements)

---

## 🎯 About The Project

**OralCancer AI** is a professional desktop application developed as a graduation project at the **Faculty of Computer and Information Science, Ain Shams University**. It leverages **deep learning** to assist medical professionals in the early detection and diagnosis of oral cancer through microscopic cell image analysis.

### The Problem

Oral cancer is one of the most common cancers worldwide. When detected **early (Stage I/II)**, the survival rate exceeds **80%**. However, when diagnosed at a **late stage**, it drops below **30%**. The challenge is that early-stage oral cancer is difficult to distinguish visually, and specialist pathologists are not always available in every hospital or clinic.

### The Solution

OralCancer AI provides doctors with an **AI-powered second opinion** by:

- Performing automatic **cell segmentation** to highlight suspicious regions in the tissue image
- **Classifying** the tissue as Malignant or Benign with a confidence score
- Storing all examinations in a **secure local database**
- Generating **printable medical reports** for each examination

All of this runs **completely offline** on the doctor's Windows computer — no internet connection required after setup, and no patient data ever leaves the machine.

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🔐 Authentication & Security
- Secure login with SHA-256 password hashing
- Role-based access control (Admin / Doctor)
- Forced password change on first login
- Session management per doctor

### 👨‍⚕️ Doctor Management
- Add, edit, and deactivate doctor accounts
- Full doctor profiles with specialization
- Admin controls for password resets
- Activity tracking per doctor

### 👥 Patient Management
- Complete patient records system
- Full examination history per patient
- Search and filter patients
- Gender-aware patient avatars

</td>
<td width="50%">

### 🔬 AI Examination System
- Upload oral cell microscopy images
- U-Net cell **segmentation** with mask overlay
- **Classification** into Malignant / Benign
- Confidence score for each result
- Side-by-side result comparison
- Save results with doctor's notes

### ⚡ Quick Check Mode
- Instant AI analysis without saving to database
- Designed for fast on-the-spot consultations

### 📊 Dashboard & Reports
- Live statistics (patients, examinations, accuracy)
- Malignant vs Benign case breakdown
- Printable PDF examination reports
- Complete audit trail per doctor

</td>
</tr>
</table>

---

## 💻 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Windows 10 (64-bit) | Windows 11 (64-bit) |
| **RAM** | 8 GB | 16 GB |
| **Storage** | 2 GB free | 5 GB free |
| **CPU** | Intel Core i5 | Intel Core i7 / i9 |
| **GPU** | Not required | NVIDIA GPU with CUDA for faster inference |
| **Python** | 3.11+ | 3.11 |

---

## 🚀 Getting Started

### Option A — Run the Installer *(Recommended for doctors)*

1. Download **`OralCancerAI_Setup.exe`** from the [Releases](../../releases) page
2. Double-click the installer and follow the setup wizard
3. Launch the app from the Desktop shortcut

```
Default credentials:
  Username : admin
  Password : admin123

⚠️  You will be required to change the password on first login.
```

---

### Option B — Run from Source Code *(For developers)*

#### Step 1 — Clone the repository

```bash
git clone https://github.com/momen-tarek111/OralCancerAI.git
cd OralCancerAI
```

---

#### Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

---

#### Step 3 — Download AI model weights

> [!WARNING]
> The model weight files are **not included** in the repository due to their large size (~418 MB).
> You **must** run this step before the app will launch.

```bash
python setup_models.py
```

This will automatically download the following files into `models/weights/`:

| File | Size | Purpose |
|------|------|---------|
| `unet_weights2.pth` | ~119 MB | Cell segmentation (U-Net) |
| `best_convnext_4.pth` | ~106 MB | Cancer classification (ConvNeXt) |
| `best_convnext_5.pth` | ~106 MB | Cancer classification — ensemble |
| `best_efficientnet_2.pth` | ~68 MB | Cancer classification (EfficientNet) |

> You only need to run `setup_models.py` **once**. After that, the files are stored locally.

---

#### Step 4 — Run the application

```bash
python main.py
```

---

## 📁 Project Structure

```
OralCancerAI/
│
├── 📁 assets/                        # UI images and icons
│   ├── logo.png                      # Application logo
│   ├── logo_white.png                # White logo variant
│   ├── dashboard.png                 # Sidebar navigation icons
│   ├── doctors.png
│   ├── patients.png
│   ├── cell_image.png                # Sample images used in UI
│   ├── segmentation_image.png
│   ├── classification_image.png
│   └── ...                           # Other UI assets
│
├── 📁 core/                          # Core application services
│   ├── database.py                   # SQLite connection, queries, CRUD
│   ├── initializer.py                # App bootstrap & first-run DB setup
│   ├── security.py                   # Password hashing & authentication
│   └── test_runner.py                # Development testing utilities
│
├── 📁 models/                        # Data models & AI inference
│   ├── 📁 weights/                   # ⚠️ Downloaded via setup_models.py
│   │   ├── unet_weights2.pth         # U-Net segmentation weights
│   │   ├── best_convnext_4.pth       # ConvNeXt classifier weights
│   │   ├── best_convnext_5.pth       # ConvNeXt classifier weights v2
│   │   └── best_efficientnet_2.pth   # EfficientNet classifier weights
│   ├── examination.py                # Examination ORM model
│   ├── patient.py                    # Patient ORM model
│   └── user.py                       # User / Doctor ORM model
│
├── 📁 views/                         # All UI screens (PySide6 / Qt6)
│   ├── splash.py                     # Startup loading screen
│   ├── login.py                      # Doctor authentication screen
│   ├── main_layout.py                # Root window + sidebar navigation
│   ├── dashboard.py                  # Statistics overview screen
│   ├── doctors.py                    # Doctors list screen
│   ├── add_doctor.py                 # Add new doctor form
│   ├── update_doctor.py              # Edit doctor details form
│   ├── doctor_profile.py             # View doctor profile
│   ├── patients.py                   # Patients list screen
│   ├── add_patient.py                # Register new patient form
│   ├── patient_details.py            # Patient info + examination history
│   ├── new_examination.py            # ⭐ AI analysis screen
│   ├── examination_details.py        # View saved examination results
│   ├── examination_report.py         # Printable medical report
│   ├── quick_check.py                # Fast AI check without saving
│   ├── my_profile.py                 # Logged-in doctor's own profile
│   ├── update_my_profile.py          # Edit own profile form
│   ├── change_my_password.py         # Change own password screen
│   └── change_password.py            # Admin: change any user's password
│
├── main.py                           # ▶ Application entry point
├── setup_models.py                   # ▶ First-time model weight downloader
├── requirements.txt                  # Python package dependencies
├── OralCancerAI.spec                 # PyInstaller build configuration
├── .gitignore                        # Git ignore rules
├── .gitattributes                    # Git LFS tracking configuration
└── README.md                         # This file
```

---

## 🏗️ System Architecture

```
╔══════════════════════════════════════════════════════════════════╗
║                      PRESENTATION LAYER                          ║
║                    PySide6 Qt6  (views/)                         ║
║                                                                  ║
║  Splash → Login → Dashboard → Patients → Examination → Report   ║
╚═══════════════════════════╦══════════════════════════════════════╝
                            ║
╔═══════════════════════════╩══════════════════════════════════════╗
║                     BUSINESS LOGIC LAYER                         ║
║                        Core  (core/)                             ║
║                                                                  ║
║         database.py  │  security.py  │  initializer.py           ║
╚══════════════╦════════════════════════════╦═════════════════════╝
               ║                            ║
╔══════════════╩═════════════╗  ╔═══════════╩══════════════════════╗
║         DATA LAYER         ║  ║           AI LAYER               ║
║                            ║  ║                                  ║
║  SQLite Database           ║  ║   PyTorch Inference Engine       ║
║  ~/.OralCancerApp/         ║  ║                                  ║
║  oral_cancer.db            ║  ║  ┌──────────────────────────┐   ║
║                            ║  ║  │  U-Net  (Segmentation)   │   ║
║  models/                   ║  ║  │  unet_weights2.pth       │   ║
║  ├── user.py               ║  ║  └──────────────────────────┘   ║
║  ├── patient.py            ║  ║  ┌──────────────────────────┐   ║
║  └── examination.py        ║  ║  │  ConvNeXt (Classifier)   │   ║
║                            ║  ║  │  best_convnext_*.pth     │   ║
╚════════════════════════════╝  ║  └──────────────────────────┘   ║
                                ║  ┌──────────────────────────┐   ║
                                ║  │ EfficientNet (Classifier) │   ║
                                ║  │ best_efficientnet_*.pth  │   ║
                                ║  └──────────────────────────┘   ║
                                ╚══════════════════════════════════╝
```

### Screen Navigation Flow

```
App Launch
    │
    ▼
Splash Screen  (loads DB + AI models)
    │
    ▼
Login Screen
    │
    ├── First Login ──► Change Password Screen
    │                           │
    └───────────────────────────▼
                          Main Layout
                       (Sidebar Navigation)
                               │
           ┌───────────────────┼──────────────────┐
           ▼                   ▼                  ▼
       Dashboard           Patients           Doctors
                               │                  │
                               ▼                  ▼
                        Patient Details     Doctor Profile
                               │
                    ┌──────────┴───────────┐
                    ▼                      ▼
             New Examination          Quick Check
                    │
                    ▼
           Examination Details
                    │
                    ▼
           Examination Report  (PDF Export)
```

---

## 🤖 AI Models

The system uses an **ensemble of 3 deep learning architectures** to deliver accurate and reliable diagnostic results.

---

### Model 1 — U-Net (Segmentation)

| Property | Details |
|----------|---------|
| **Architecture** | U-Net with encoder-decoder and skip connections |
| **Task** | Pixel-level semantic segmentation of cancerous regions |
| **Input** | RGB oral cell microscopy image |
| **Output** | Binary mask highlighting suspicious regions |
| **Weight file** | `unet_weights2.pth` (~119 MB) |
| **Framework** | PyTorch |

U-Net was selected for its proven performance in **biomedical image segmentation**. The encoder-decoder structure with skip connections preserves fine-grained spatial details critical for identifying small cancerous regions accurately.

---

### Model 2 — ConvNeXt (Classification)

| Property | Details |
|----------|---------|
| **Architecture** | ConvNeXt (modern pure-CNN, 2022) |
| **Task** | Binary classification — Malignant / Benign |
| **Input** | RGB cell image (224 × 224) |
| **Output** | Class label + probability confidence score |
| **Weight files** | `best_convnext_4.pth`, `best_convnext_5.pth` (~106 MB each) |
| **Framework** | PyTorch + TorchVision |

ConvNeXt modernizes the classic ResNet with transformer-inspired design choices, achieving **state-of-the-art accuracy** on image classification benchmarks while remaining a fully convolutional network with no attention overhead.

---

### Model 3 — EfficientNet (Classification)

| Property | Details |
|----------|---------|
| **Architecture** | EfficientNet-B2 |
| **Task** | Binary classification — Malignant / Benign |
| **Input** | RGB cell image (260 × 260) |
| **Output** | Class label + probability confidence score |
| **Weight file** | `best_efficientnet_2.pth` (~68 MB) |
| **Framework** | PyTorch + TorchVision |

EfficientNet scales network width, depth, and resolution together using a compound coefficient, achieving high accuracy with **significantly fewer parameters** than traditional architectures of comparable performance.

---

### Inference Pipeline

```
Doctor Uploads Cell Image
          │
          ▼
  ┌───────────────────────────────┐
  │          Preprocessing        │
  │  • Resize to model input size │
  │  • Normalize pixel values     │
  │  • Convert to PyTorch tensor  │
  └──────────────┬────────────────┘
                 │
        ┌────────┴─────────┐
        │                  │
        ▼                  ▼
  ┌───────────┐    ┌────────────────────┐
  │   U-Net   │    │  ConvNeXt          │
  │   Model   │    │  +  EfficientNet   │
  └─────┬─────┘    └────────┬───────────┘
        │                   │
        ▼                   ▼
  Segmentation         Ensemble Vote
     Mask              (averaged confidence)
        │                   │
        └──────────┬─────────┘
                   │
                   ▼
        ┌──────────────────────────────┐
        │        Results Display       │
        │  • Original image            │
        │  • Segmentation overlay      │
        │  • Malignant / Benign label  │
        │  • Confidence percentage     │
        └──────────────────────────────┘
                   │
                   ▼
      Save to Database + Generate Report
```

---

## 🗄️ Database Schema

The database is stored **locally** on each machine at:
```
C:\Users\{username}\.OralCancerApp\oral_cancer.db
```

Patient data **never leaves the device** and is never transmitted over any network.

### `applicationUser` — System accounts

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment primary key |
| `username` | TEXT UNIQUE | Login username |
| `password_hashed` | TEXT | SHA-256 hashed password |
| `full_name` | TEXT | Doctor's full name |
| `email` | TEXT | Contact email address |
| `role` | TEXT | `admin` or `doctor` |
| `is_active` | INTEGER | Account enabled / disabled |
| `must_change_password` | INTEGER | Forces password change on next login |
| `created_at` | TEXT | Account registration timestamp |
| `last_login` | TEXT | Last successful login timestamp |

### `Patient` — Patient records

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment primary key |
| `name` | TEXT | Patient full name |
| `age` | INTEGER | Patient age |
| `gender` | TEXT | Male / Female |
| `phone` | TEXT | Contact phone number |
| `created_at` | TEXT | Registration date |

### `Examination` — AI analysis records

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PK | Auto-increment primary key |
| `patient_id` | INTEGER FK | Linked patient record |
| `doctor_id` | INTEGER FK | Doctor who performed the exam |
| `original_image` | BLOB | Uploaded cell image (binary) |
| `segmentation_image` | BLOB | U-Net output segmentation mask |
| `classification_result` | TEXT | Malignant / Benign |
| `confidence_score` | REAL | Model confidence (0.0 – 1.0) |
| `notes` | TEXT | Doctor's written notes |
| `created_at` | TEXT | Examination timestamp |

---

## 🔧 Build as EXE

> [!NOTE]
> This project does not include a `.spec` file in the repository since it would
> contain a path specific to the original developer's machine. Instead, build the
> EXE using the PyInstaller command below, which works correctly regardless of
> where you clone the repository.

To build a standalone Windows executable that requires no Python installation on the target machine:

### Step 1 — Generate the app icon

```bash
python -c "from PIL import Image; Image.open('assets/logo.png').convert('RGBA').save('assets/icon.ico', format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
```

### Step 2 — Build the EXE

Run this single command from the project root (in Command Prompt):

```bash
pyinstaller --name OralCancerAI ^
  --windowed ^
  --icon=assets/icon.ico ^
  --add-data "assets;assets" ^
  --add-data "models/weights;models/weights" ^
  --hidden-import=sqlalchemy ^
  --hidden-import=sqlalchemy.sql ^
  --hidden-import=sqlalchemy.orm ^
  --hidden-import=sqlalchemy.dialects.sqlite ^
  --hidden-import=pytorch_grad_cam ^
  --hidden-import=pytorch_grad_cam.grad_cam ^
  --hidden-import=pytorch_grad_cam.base_cam ^
  --hidden-import=pytorch_grad_cam.utils ^
  --hidden-import=pytorch_grad_cam.utils.image ^
  --hidden-import=ttach ^
  --hidden-import=matplotlib ^
  --hidden-import=matplotlib.pyplot ^
  --hidden-import=matplotlib.backends.backend_agg ^
  --collect-submodules=torch ^
  --collect-submodules=torchvision ^
  main.py
```

> **Note:** The `^` symbols are line-continuation characters for Windows Command Prompt. You can paste the whole block as-is.

### Step 3 — Run the EXE

The output will be located at:
```
dist/OralCancerAI/OralCancerAI.exe
```

> **Note:** The final build folder will be approximately 1.5 GB due to the bundled PyTorch runtime and AI model weights. This is expected for medical AI desktop applications.

> [!TIP]
> If you encounter a `ModuleNotFoundError` during the first run of the EXE, it usually means a library has hidden internal dependencies that PyInstaller missed. Add `--hidden-import=<missing_module_name>` to the command above and rebuild.
---

## 📦 Requirements

```
PySide6>=6.10.0
torch>=2.11.0
torchvision>=0.26.0
opencv-python>=4.12.0
numpy>=2.1.0
Pillow>=10.4.0
reportlab>=5.0.0
requests>=2.31.0
pyinstaller>=6.19.0
```

Install everything at once:
```bash
pip install -r requirements.txt
```

---

## 👨‍💻 Team

<table>
<tr>
<td align="center" width="200">
<br/>
<b>Momen Tarek Nagaty</b>
<br/>
<sub>Lead Developer</sub>
<br/>
<sub>UI · Database · AI Integration</sub>
<br/>
<a href="https://github.com/momen-tarek111">@momen-tarek111</a>
</td>
<td align="center" width="200">
<br/>
<b>Amira Tharwat Hanna</b>
<br/>
<sub>AI / ML Engineer</sub>
<br/>
<sub>Model Training · Evaluation</sub>
</td>
<td align="center" width="200">
<br/>
<b>Mariam Naeem Senada</b>
<br/>
<sub>AI / ML Engineer</sub>
<br/>
<sub>Model Architecture · Testing</sub>
</td>
</tr>
<tr>
<td align="center" width="200">
<br/>
<b>Mina Makram Sedkey</b>
<br/>
<sub>Data Engineer</sub>
<br/>
<sub>Dataset · Preprocessing</sub>
</td>
<td align="center" width="200">
<br/>
<b>Simon Hanna Riad</b>
<br/>
<sub>Data Engineer</sub>
<br/>
<sub>Data Collection · Annotation</sub>
</td>
<td align="center" width="200">
<br/>
<b>Mina Ashraf Maher</b>
<br/>
<sub>Research & Documentation</sub>
<br/>
<sub>Testing · Quality Assurance</sub>
</td>
</tr>
</table>

---

## 🎓 Academic Supervision

<table>
<tr>
<td width="50%">

**DR. Maryam Al-Berry**
Associate Professor
Scientific Computing Department
Faculty of Computer and Information Science
Ain Shams University

</td>
<td width="50%">

**TA. Manar Sultan**
Teaching Assistant
Scientific Computing Department
Faculty of Computer and Information Science
Ain Shams University

</td>
</tr>
</table>

**Faculty:** Faculty of Computer and Information Science
**University:** Ain Shams University
**Academic Year:** 2024 / 2025

---

## 🙏 Acknowledgements

- [PyTorch](https://pytorch.org) — Deep learning framework used for all AI models
- [PySide6 / Qt for Python](https://doc.qt.io/qtforpython/) — Desktop UI framework
- [OpenCV](https://opencv.org) — Image processing and preprocessing pipeline
- [ReportLab](https://reportlab.com) — PDF medical report generation
- [U-Net: Convolutional Networks for Biomedical Image Segmentation](https://arxiv.org/abs/1505.04597) — Ronneberger et al., 2015
- [A ConvNet for the 2020s](https://arxiv.org/abs/2201.03545) — Liu et al., 2022
- [EfficientNet: Rethinking Model Scaling for Convolutional Neural Networks](https://arxiv.org/abs/1905.11946) — Tan & Le, 2019
- Special thanks to the **Scientific Computing Department** at Ain Shams University for their guidance and support throughout this project.

---

<div align="center">

<br/>

**OralCancer AI** — Graduation Project · Faculty of Computer and Information Science · Ain Shams University · 2024 / 2025

<br/>

*Built with the goal of making early oral cancer detection accessible to every doctor.*

<br/>

⭐ If you found this project useful, please consider giving it a star!

<br/>

</div>