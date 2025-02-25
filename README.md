# Audio Transcription App

A simple audio transcription application that uses Google's Gemini model to transcribe audio files and generate both text and SRT format transcripts. Tested for short news

## Features

- Simple web interface using Gradio
- Utilizing Google's gemini multimodal LLM
- Supports various audio file formats. The supported format currently supported are mp3, m4a, wav
- Generates timestamped transcripts
- Exports in both TXT and SRT formats
- Runs all components locally except for the Gemini model

## Setup

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your Google API key:
```bash
# On Windows
set GOOGLE_API_KEY=your_api_key_here

# On Linux/macOS
export GOOGLE_API_KEY=your_api_key_here
```

3. Run the application:
```bash
python app.py
```
or
```bash
$env:GOOGLE_API_KEY='your_api_key_here'; python app.py #if you want just to use disposable API 
```

4. Open your browser and navigate to `http://localhost:7860`

## Usage

1. Upload an audio file using the file upload button
2. Click "Transcribe" to process the file
3. Once processing is complete, you can:
   - Download the transcript in TXT format (timestamped text)
   - Download the transcript in SRT format (subtitle format)
   - Preview the transcript directly in the browser

## Exported Formats

### TXT Format
The TXT format includes timestamps in [MM:SS] format followed by the transcribed text:
```
[00:00] This is the beginning of the transcript
[00:15] This is the next segment
```

### SRT Format
The SRT format follows the standard subtitle format:
```
1
00:00:00,000 --> 00:00:02,000
This is the beginning of the transcript

2
00:00:15,000 --> 00:00:17,000
This is the next segment
```

## Notes

- The application uses Gradio for the web interface, making it lightweight and easy to use
- All processing is done locally except for the transcription which uses Google's Gemini model
- Currently no speaker diarization is performed - the transcript focuses on the content only
- Timestamps are grouped logically to maintain context rather than breaking at every pause

## Todo

 - [ ] Make translation feature
 - [ ] Supporting diarization
 - [ ] Token counter and API price counter
 - [ ] Multi batch processing
 - [ ] Adjusting API rate limit
