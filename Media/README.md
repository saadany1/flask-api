# Perseptra AI Image Generation Platform

A web-based AI image generation platform built with Flask and Google's Vertex AI.

## Features

- **AI Image Generation**: Create stunning images from text prompts using Google's Imagen model
- **Multiple Art Styles**: Choose from 6 different art styles (Realistic, Digital Art, Fantasy, Anime, Watercolor, Minimal)
- **Real-time Generation**: Generate images in seconds with high-quality output
- **Download Functionality**: Download generated images directly to your device
- **Responsive Design**: Works on desktop and mobile devices

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up Google Cloud Credentials

Make sure you have:
- A Google Cloud project with Vertex AI enabled
- Service account credentials set up
- The `GOOGLE_APPLICATION_CREDENTIALS` environment variable pointing to your service account key file

### 3. Run the Server

```bash
python index.py
```

The server will start on `http://localhost:5000`

### 4. Access the Application

- **Home Page**: `http://localhost:5000/`
- **Image Generator**: `http://localhost:5000/image`

## How to Use

### Image Generation

1. **Navigate to the Image Generator page**
2. **Choose an Art Style**: Click on one of the 6 style cards (Realistic, Digital Art, Fantasy, Anime, Watercolor, Minimal)
3. **Enter Your Prompt**: Describe the image you want to create (minimum 10 characters)
4. **Generate**: Click the "Generate Image" button or press Enter
5. **Download**: Once generated, click "Download" to save the image

### Tips for Better Results

- Be specific about composition, lighting, and colors
- Include art style references like "oil painting" or "digital art"
- Reference famous artists for style inspiration
- Use descriptive language for better results

## API Endpoints

- `GET /` - Home page
- `GET /image` - Image generator page
- `POST /generate-image` - Generate image from prompt
  - Body: `{"prompt": "your text prompt"}`
  - Returns: `{"success": true, "image": "base64_data", "filename": "filename.png"}`

## Testing

Run the test script to verify the server is working:

```bash
python test_server.py
```

## File Structure

```
├── index.py              # Flask server
├── index.html            # Home page
├── image.html            # Image generator page
├── requirements.txt      # Python dependencies
├── test_server.py        # Test script
├── static/               # Generated images folder
└── README.md            # This file
```

## Technologies Used

- **Backend**: Flask, Google Vertex AI
- **Frontend**: HTML, CSS (Tailwind), JavaScript
- **AI Model**: Google Imagen 4.0
- **Image Processing**: Pillow (PIL)

## Notes

- Generated images are saved in the `static/` folder
- The system uses Google's Vertex AI Imagen model for image generation
- Images are returned as base64-encoded data for immediate display
- The platform supports multiple art styles and themes
