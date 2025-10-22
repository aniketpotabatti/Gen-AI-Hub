# YouTube Video Summarizer

A Streamlit-based web application that allows users to input a YouTube URL and get an AI-powered summary of the video, including transcript extraction, metadata, and structured summaries.

## Features

- **YouTube Transcript Extraction**: Automatically fetches and processes video transcripts
- **AI-Powered Summaries**: Uses Google Gemini AI to generate comprehensive summaries
- **Video Metadata Display**: Shows title, channel, views, likes, publish date, and thumbnail
- **Professional UI**: Clean, responsive interface with YouTube branding
- **Date Formatting**: Displays publish dates in dd-mm-yyyy format
- **Error Handling**: Robust handling of missing data or API issues

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd End-to-End-Youtube-Video-Summarizer
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up environment variables:
   Create a `.env` file in the root directory and add your Google API key:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   ```

4. Run the application:
   ```bash
   streamlit run app.py
   ```

## Usage

1. Open the app in your browser (usually http://localhost:8501)
2. Enter a YouTube URL in the text input field
3. Click "Summarize" to get the video summary
4. View the extracted metadata and AI-generated summary

## Requirements

- Python 3.8+
- yt-dlp
- python-dotenv
- streamlit
- google-generativeai

## Project Structure

```
End-to-End-Youtube-Video-Summarizer/
├── app.py              # Main Streamlit application
├── requirements.txt    # Python dependencies
├── .env                # Environment variables (not in repo)
├── README.md           # This file
├── .gitignore          # Git ignore rules
└── youtube.png         # YouTube logo (optional)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is open source and available under the MIT License.

## Troubleshooting

- Ensure your Google API key is valid and set in .env
- For transcript issues, check if the video has captions available
