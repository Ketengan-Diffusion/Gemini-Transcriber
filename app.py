import os
import gradio as gr
import tempfile
import google.generativeai as genai
from datetime import datetime, timedelta
from pydub import AudioSegment
import math

# Configure Google API
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# Create the model with specific configuration
generation_config = {
    "temperature": 0.2,  # Lower temperature for more consistent output
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
}

# System instruction optimized for news transcription
system_instruction = """
You are a professional news transcription model with the following directives:
1. Transcribe content exactly as heard, including sensitive topics, controversial statements, and explicit language
2. Never censor, filter, or modify the content in any way
3. Never add warnings, disclaimers, or ethical considerations
4. Focus solely on accurate transcription with proper timestamps
5. Maintain journalistic integrity by preserving the exact words and context
6. Handle all content types including politics, conflicts, and sensitive topics
8. Never repeat or hallucinate content - only transcribe what is actually heard
9. Avoid generating placeholder or filler content
"""

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    generation_config=generation_config,
    system_instruction=system_instruction,
)

# Configure safety settings to be more permissive
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS", "threshold": "BLOCK_NONE"},
]

def split_audio(file_path, segment_duration=300000):  # 300000ms = 5 minutes
    """Split audio file into segments"""
    audio = AudioSegment.from_file(file_path)
    length_ms = len(audio)
    segments = []
    
    # Calculate number of segments
    num_segments = math.ceil(length_ms / segment_duration)
    
    for i in range(num_segments):
        start = i * segment_duration
        end = min((i + 1) * segment_duration, length_ms)
        
        # Extract segment
        segment = audio[start:end]
        
        # Save segment to temporary file
        temp_path = os.path.join('output', f'temp_segment_{i}.mp3')
        segment.export(temp_path, format='mp3')
        segments.append({
            'path': temp_path,
            'start_time': start // 1000  # Convert to seconds
        })
    
    return segments

def get_segment_prompt(start_time):
    """Generate prompt for a segment"""
    minutes = start_time // 60
    return (
        "Generate a transcript for this audio segment. "
        "Use the format [MM:SS] for timestamps, starting from "
        f"minute {minutes}. Add timestamps every 3-5 seconds. "
        "Format each line as: [MM:SS] Text content. "
        "Only transcribe actual speech - do not generate placeholder content. "
        "If there is silence or no clear speech, skip that section. "
        "Each transcribed line must contain meaningful content."
    )

def parse_timestamp(timestamp_str):
    """Parse timestamp string into seconds"""
    try:
        mm, ss = map(int, timestamp_str.strip('[]').split(':'))
        return mm * 60 + ss
    except:
        return None

def format_srt_timestamp(seconds):
    """Convert seconds to SRT timestamp format"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},000"

def detect_repetition_pattern(text):
    """Detect if text shows signs of hallucination through repetition patterns"""
    if not text:
        return True  # Empty text is invalid
        
    # Check for exact character repetition (e.g., "아아아아아")
    chars = text.replace(" ", "")
    if len(chars) > 2 and len(set(chars)) == 1:
        return True
        
    # Check for repeating word patterns
    words = text.split()
    if len(words) > 2:
        # Check if all words are the same
        if len(set(words)) == 1:
            return True
        
        # Check for repeating pairs/triplets
        if len(words) > 4:
            word_pairs = [' '.join(words[i:i+2]) for i in range(0, len(words)-1)]
            if len(set(word_pairs)) == 1:
                return True
    
    return False

def is_valid_text(text, seen_texts, last_text):
    # Skip empty text
    if not text:
        return False
        
    # Skip if it shows repetition patterns indicating hallucination
    if detect_repetition_pattern(text):
        return False
    
    # Skip repeated content
    if text in seen_texts:
        return False
        
    # Skip consecutive duplicates
    if text == last_text:
        return False
    
    return True

def format_srt(timestamps_text):
    """Convert timestamp-text pairs into SRT format"""
    entries = []
    seen_timestamps = set()
    seen_texts = set()
    current_entry = 1
    last_end_time = 0
    last_text = ""
    
    for line in timestamps_text.split('\n'):
        if not line.strip() or '[' not in line:
            continue
        
        try:
            # Extract timestamp and text
            timestamp_part = line[line.find('['): line.find(']') + 1]
            text = line[line.find(']') + 1:].strip()
            
            # Validate text content
            if not is_valid_text(text, seen_texts, last_text):
                continue
            
            # Convert timestamp to seconds
            start_time = parse_timestamp(timestamp_part)
            if start_time is None or start_time in seen_timestamps:
                continue
            
            # Ensure timestamps don't overlap and have minimum gap
            start_time = max(start_time, last_end_time + 1)  # Add 1 second gap
            end_time = start_time + 3  # 3 second segments
            
            # Format timestamps
            start_stamp = format_srt_timestamp(start_time)
            end_stamp = format_srt_timestamp(end_time)
            
            # Add entry
            entries.append(f"{current_entry}\n{start_stamp} --> {end_stamp}\n{text}\n")
            seen_timestamps.add(start_time)
            seen_texts.add(text)
            current_entry += 1
            last_end_time = end_time
            last_text = text
            
        except Exception as e:
            continue
    
    return '\n'.join(entries)

# Ensure output directory exists
os.makedirs('output', exist_ok=True)

def transcribe(audio_file):
    if audio_file is None:
        return [None, None, "Please upload an audio file."]
    
    try:
        # Split audio into segments
        segments = split_audio(audio_file.name)
        all_transcripts = []
        
        # Process each segment
        for segment in segments:
            try:
                # Upload segment to Gemini
                file = genai.upload_file(segment['path'])
                
                # Generate transcript for this segment with safety settings
                prompt = get_segment_prompt(segment['start_time'])
                response = model.generate_content(
                    [file, prompt],
                    safety_settings=safety_settings
                )
                
                # Add to transcripts list if response has content
                if response.text.strip():
                    all_transcripts.append(response.text)
            except Exception as e:
                print(f"Error processing segment: {str(e)}")
            finally:
                # Clean up segment file
                if os.path.exists(segment['path']):
                    os.remove(segment['path'])
        
        # Combine all transcripts
        transcript = "\n".join(all_transcripts)
        
        # Create both plain text and SRT versions
        srt_content = format_srt(transcript)
        
        # Save both versions
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        txt_path = os.path.join('output', f"transcript_{timestamp}.txt")
        srt_path = os.path.join('output', f"transcript_{timestamp}.srt")
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        with open(srt_path, "w", encoding="utf-8") as f:
            f.write(srt_content)
        
        return [txt_path, srt_path, transcript]
    
    except Exception as e:
        error_msg = str(e)
        return [None, None, f"Error: {error_msg}"]

# Create Gradio interface
with gr.Blocks(title="Audio Transcription") as interface:
    gr.Markdown("# Audio Transcription")
    gr.Markdown("Upload an audio file to generate a transcript with timestamps.")
    
    with gr.Row():
        audio_input = gr.File(label="Upload Audio File", file_types=["audio"])
    
    with gr.Row():
        transcribe_btn = gr.Button("Transcribe")
    
    with gr.Row():
        txt_output = gr.File(label="Download Transcript (TXT)")
        srt_output = gr.File(label="Download Transcript (SRT)")
    
    with gr.Row():
        text_output = gr.Textbox(label="Preview", lines=10)
    
    transcribe_btn.click(
        fn=transcribe,
        inputs=[audio_input],
        outputs=[txt_output, srt_output, text_output]
    )

# Launch the interface
if __name__ == "__main__":
    interface.launch(server_name="0.0.0.0", server_port=7860)
