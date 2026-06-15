# AuthX – Content Theft Detection & Ownership Verification

AuthX is an AI-powered system designed to detect digital content theft and verify image ownership. It analyzes images using computer vision, signal processing, perceptual hashing, and metadata inspection to determine authenticity and detect manipulation or duplication.

---

## Overview

With the rapid growth of digital media and AI-generated content, verifying originality has become increasingly difficult. AuthX provides a multi-layered verification pipeline that helps identify whether an image is original, copied, manipulated, or AI-generated.

---

## Key Features

- Content theft detection through visual similarity analysis  
- Ownership verification using perceptual hashing  
- Detection of manipulated or AI-generated images  
- Frequency-domain and noise pattern analysis  
- Metadata inspection for origin verification  

---

## System Architecture

AuthX processes an image through multiple independent analysis layers:

1. Image preprocessing  
2. Perceptual hashing  
3. Frequency-domain analysis  
4. Noise and texture analysis  
5. Metadata verification  
6. Final authenticity scoring  

Each layer contributes to a confidence score indicating originality and ownership.

---

## Technologies Used

### Computer Vision & Image Processing
- OpenCV (cv2)
- PIL / Pillow
- NumPy

### Frequency & Signal Processing
- Discrete Cosine Transform (DCT)
- Fast Fourier Transform (FFT)
- Sobel and Laplacian operators
- Gaussian blur for noise extraction

### Perceptual Hashing
- pHash (Perceptual Hash)
- dHash (Difference Hash)
- aHash (Average Hash)

### Metadata Analysis
- EXIF metadata extraction
- Camera and timestamp verification

---

## How It Works

1. The user uploads an image  
2. AuthX extracts visual, frequency, noise, and metadata features  
3. The image is analyzed for similarity, manipulation, and origin clues  
4. The system outputs an authenticity and ownership confidence score  

---

## Output Interpretation

- Original Content – High ownership confidence  
- Suspicious Content – Minor edits or transformations detected  
- Likely Theft – High similarity or manipulation detected  

---
## Screenshots
<img width="1879" height="871" alt="image" src="https://github.com/user-attachments/assets/70337f84-f406-4675-a413-f021e84bac58" />
<img width="1872" height="871" alt="image" src="https://github.com/user-attachments/assets/ca47a94f-d86d-4b1d-96cc-6ab94666cba2" />
<img width="1884" height="870" alt="image" src="https://github.com/user-attachments/assets/85049b87-5aa9-4b5f-9b91-c224e98c2492" />

## Use Cases

- Content creators protecting original work  
- Media and journalism verification  
- E-commerce product image validation  
- Digital forensics and copyright enforcement  
- AI-generated content detection  

---

## Installation

```bash
pip install opencv-python pillow numpy imagehash
